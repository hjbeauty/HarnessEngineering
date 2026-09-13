"""Deterministic course setup/recording. Never invokes an LLM or executes generated code."""
import argparse
import copy
import importlib.metadata
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import yaml

MODEL = 'z-ai/glm-5.3-flash'
DATA_HASH = '60f14a8cbe5fd6eba994ef2f6c43fbc714b232a3d7a37e60cb02ee6cdad9f0d8'
REQUEST = '현재 작업 폴더의 data/sales.csv를 분석하고 업무 보고서를 만들어 주세요.\n필요한 파일은 직접 만들고, 완료되면 무엇을 만들었는지 알려 주세요.\n'
IGNORE_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules'}
SETTINGS = {
 'model.provider':'openrouter', 'model.default':MODEL,
 'terminal.backend':'local', 'terminal.cwd':'/workspace',
 'agent.reasoning_effort':'low', 'agent.reasoning_overrides':{},
 'memory.memory_enabled':False, 'memory.user_profile_enabled':False,
 'skills.write_approval':True,
 'auxiliary.background_review.enabled':False,
 'auxiliary.title_generation.enabled':False,
 'approvals.mode':'manual',
}


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def write_json(p, value): p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(d, key):
    for part in key.split('.'):
        if not isinstance(d,dict) or part not in d: return None
        d=d[part]
    return d

def has(d, key):
    for part in key.split('.'):
        if not isinstance(d,dict) or part not in d:return False
        d=d[part]
    return True


def check_request(records):
    p=records/'request.md'
    if not p.is_file() or p.read_text(encoding='utf-8-sig')!=REQUEST:
        raise ValueError('The fixed Baseline request was changed or is missing.')


def put(d, key, value):
    parts=key.split('.')
    for part in parts[:-1]:
        if part not in d: d[part]={}
        if not isinstance(d[part],dict): raise ValueError('Unexpected config structure: '+key)
        d=d[part]
    d[parts[-1]]=value


def config_read(home):
    p=home/'config.yaml'
    d=yaml.safe_load(p.read_text(encoding='utf-8')) if p.exists() else {}
    if d is None: d={}
    if not isinstance(d,dict): raise ValueError('config.yaml must be a mapping')
    return d


def learning_state(home):
    d=config_read(home)
    rows={}
    for folder in ['skills','memories']:
        root=home/folder
        if root.is_symlink(): raise ValueError('Linked learning-state directory: '+folder)
        if root.exists():
            for p in sorted(root.rglob('*')):
                if p.is_symlink(): raise ValueError('Linked learning-state entry: '+str(p.relative_to(home)))
                if p.is_file(): rows[str(p.relative_to(home))]={'sha256':digest(p),'bytes':p.stat().st_size}
    for name in ['SOUL.md','MEMORY.md','USER.md','AGENTS.md']:
        p=home/name
        if p.is_symlink(): raise ValueError('Linked state file: '+name)
        if p.is_file(): rows[name]={'sha256':digest(p),'bytes':p.stat().st_size}
    selected={k:get(d,k) for k in SETTINGS}
    selected['agent.disabled_toolsets']=get(d,'agent.disabled_toolsets')
    selected['fallback_providers']=d.get('fallback_providers')
    for group in ['delegation','compression']:
        selected[group]={k:get(d,group+'.'+k) for k in ['provider','model','base_url','fallback_providers']}
    selected['auxiliary_model_routes']={k:{field:v.get(field) for field in ['provider','model','base_url','enabled']} for k,v in d.get('auxiliary',{}).items() if isinstance(v,dict)}
    try:version=importlib.metadata.version('hermes-agent')
    except importlib.metadata.PackageNotFoundError:version='unconfirmed'
    return {'utc':now(),'installed_package_version':version,'configured_values':selected,'learning_file_hashes':rows,
            'note':'Hashes do not establish which skills were actually loaded. Inspect tool logs separately.'}


def files(root):
    found={};skipped=[]
    def visit(folder):
        for p in sorted(folder.iterdir()):
            rel=p.relative_to(root).as_posix()
            if p.is_symlink(): raise ValueError('Symbolic link cannot be safely archived: '+rel)
            if p.is_dir():
                if p.name not in IGNORE_DIRS: visit(p)
                else: skipped.append(rel+'/')
            elif p.is_file():
                if p.name.startswith('.env') or p.suffix=='.key':
                    skipped.append(rel);continue
                if p.stat().st_size > 50*1024*1024: raise ValueError('File over 50 MiB requires separate preservation: '+rel)
                content=p.read_bytes()
                if re.search(rb'sk-or-v1-[A-Za-z0-9_-]{16,}',content): raise ValueError('Possible API key in file; redact a separate copy before archival: '+rel)
                found[rel]=hashlib.sha256(content).hexdigest()
    if root.exists():visit(root)
    return found,skipped


def copy_snapshot(root,dest,manifest):
    dest.mkdir()
    for rel in manifest:
        target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/rel,target)
        if digest(target)!=manifest[rel]: raise ValueError('File changed during capture: '+rel)


def read_api_key(home):
    # Only read the key saved through Hermes API Keys, never print it.
    from dotenv import dotenv_values
    key=dotenv_values(home/'.env').get('OPENROUTER_API_KEY')
    if not key: raise ValueError('OPENROUTER_API_KEY is missing. Save it in the dashboard API Keys page.')
    return key


def request_json(url,key=None):
    headers={'User-Agent':'AN-Harness-Course-Environment-Check'}
    if key: headers['Authorization']='Bearer '+key
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)


def action(name,workspace=Path('/workspace'),records=Path('/records'),inputs=Path('/inputs/lesson03'),home=Path('/opt/data')):
    seal=records/'SHA256.json'
    if name=='verify':
        if not seal.is_file(): raise ValueError('No frozen Baseline exists.')
        expected=json.loads(seal.read_text(encoding='utf-8'))
        current,skipped=files(records)
        current.pop('SHA256.json',None)
        differences=sorted(set(current)^set(expected) | {k for k in set(current)&set(expected) if current[k]!=expected[k]})
        if differences or skipped: raise ValueError('Baseline integrity check failed: '+', '.join(differences+skipped))
        print('BASELINE_INTEGRITY_PASS');return
    if seal.exists(): raise ValueError('Baseline is already frozen. Use verify; do not replace it.')
    records.mkdir(parents=True,exist_ok=True)
    if name=='prepare':
        source=inputs/'sales.csv'
        if digest(source)!=DATA_HASH:raise ValueError('Provided sales.csv differs from the course source.')
        target=workspace/'data/sales.csv';target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and digest(target)!=DATA_HASH: raise ValueError('Existing working data differs; not overwritten.')
        if not target.exists():shutil.copyfile(source,target)
        for rel,text in [('request.md',REQUEST),('response.md',''),('metadata.md','# Baseline 실행 기록\n\n- 실행 시각·시간대: [기록]\n- 세션 ID 또는 제목: [기록]\n- 요청 모델: z-ai/glm-5.3-flash\n- 실제 모델·공급자(Activity): [기록]\n- 추론 설정: low\n- 작업 폴더: /workspace\n- 사용자 요청 횟수: [기록]\n- 종료 상태(완료/실패/추가 질문 대기/중단): [기록]\n- 실제 읽은 데이터·생성 파일: [기록]\n- 내부 재시도·승인·중단: [기록]\n- 입력·출력 토큰 / 전체 비용(USD): [기록]\n- Skill 조회·Memory 변경·과거 세션 검색 관찰: [기록]\n- 통제 상태(확인/변경 발생/미확인): [기록]\n- 제한사항: [기록]\n')]:
            p=records/rel
            if not p.exists():p.write_text(text,encoding='utf-8')
        print('PREPARE_PASS: 200 rows; original data/request preserved.');return
    if name=='configure':
        if (records/'before.json').exists():raise ValueError('Before state already recorded. Do not reconfigure this run.')
        model=next((x for x in request_json('https://openrouter.ai/api/v1/models')['data'] if x['id']==MODEL),None)
        if model is None:raise ValueError('Course GLM is unavailable. Do not silently substitute another model.')
        efforts=model.get('reasoning',{}).get('supported_efforts',[])
        if efforts and 'low' not in efforts:raise ValueError('Catalog no longer supports low effort. Review before proceeding.')
        status=request_json('https://openrouter.ai/api/v1/key',read_api_key(home))['data']
        limit=status.get('limit');remaining=status.get('limit_remaining')
        if limit is None or float(limit)>5 or remaining is None or float(remaining)<=0 or status.get('limit_reset'):
            raise ValueError('Use a key with a total cap of at most USD 5, no reset, and a positive remaining cap.')
        d=config_read(home)
        # Check known keys against the installed version before any config write.
        from hermes_cli.config import DEFAULT_CONFIG
        # model accepts a scalar or mapping; reasoning_effort is documented but optional.
        documented_optional={'model.provider','model.default','agent.reasoning_effort'}
        missing=[k for k in SETTINGS if k not in documented_optional and not has(DEFAULT_CONFIG,k) and not has(d,k)]
        if missing:raise ValueError('Installed settings require review: '+', '.join(missing))
        if d.get('mcp_servers') or get(d,'memory.provider') not in [None,'','local','builtin','none']:
            raise ValueError('Existing external tools/memory detected. Use the dedicated course environment; nothing changed.')
        backup=home/'course-backups';backup.mkdir(exist_ok=True)
        cp=home/'config.yaml'
        if cp.exists():shutil.copyfile(cp,backup/('before-lesson03-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.yaml'))
        if not isinstance(d.get('model'),dict):d['model']={}
        d['auxiliary']={**copy.deepcopy(DEFAULT_CONFIG.get('auxiliary',{})),**d.get('auxiliary',{})}
        for k,v in SETTINGS.items():put(d,k,v)
        disabled=get(d,'agent.disabled_toolsets') or []
        if not isinstance(disabled,list):raise ValueError('disabled_toolsets must be a list')
        put(d,'agent.disabled_toolsets',sorted(set(disabled)|{'memory','session_search'}))
        # Keep every model slot on the selected GLM; avoid legacy fallback to other models.
        d['fallback_providers']=[];d.pop('fallback_model',None)
        for group in ['delegation','compression']:
            d.setdefault(group,{}).update({'provider':'openrouter','model':MODEL,'base_url':''})
        d['delegation']['fallback_providers']=[]
        for task,value in d.get('auxiliary',{}).items():
            if isinstance(value,dict) and task not in ['background_review']:
                value.update({'provider':'openrouter','model':MODEL,'base_url':''});value.pop('fallback_chain',None)
        d.setdefault('model',{})['base_url']='https://openrouter.ai/api/v1'
        temp=cp.with_suffix('.lesson03.tmp');temp.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8');temp.replace(cp)
        write_json(records/'model_catalog.json',model)
        write_json(records/'connection_check.json',{'utc':now(),'authenticated':True,'limit':limit,'limit_remaining':remaining,'model_inference_performed':False})
        write_json(records/'settings_check.json',learning_state(home))
        print('CONFIGURE_PASS: key authenticated; GLM catalog found; settings written. No model inference performed.');return
    if name=='before':
        check_request(records)
        if (records/'before.json').exists():raise ValueError('Before state exists. Do not overwrite; continue with the recorded run.')
        if not (records/'connection_check.json').exists():raise ValueError('Run configure before recording the start state.')
        if digest(workspace/'data/sales.csv')!=DATA_HASH:raise ValueError('Working data changed before Baseline.')
        manifest,skipped=files(workspace)
        extra=[k for k in manifest if k!='data/sales.csv' and k!='.gitignore' and not k.startswith('evidence/lesson02/')]
        if extra:raise ValueError('Prior project files detected; no deletion performed: '+', '.join(extra[:12]))
        state=learning_state(home)
        # YAML null / an absent optional override mapping and {} all mean
        # no per-model override. Preserve the raw value in evidence records.
        observed_settings=dict(state['configured_values'])
        if observed_settings.get('agent.reasoning_overrides') is None:
            observed_settings['agent.reasoning_overrides']={}
        bad=[k for k,v in SETTINGS.items() if observed_settings.get(k)!=v]
        if not {'memory','session_search'}.issubset(set(state['configured_values'].get('agent.disabled_toolsets') or [])):bad.append('agent.disabled_toolsets')
        if bad:raise ValueError('Baseline settings differ: '+', '.join(bad))
        copy_snapshot(workspace,records/'before-files',manifest)
        write_json(records/'learning_before.json',state)
        write_json(records/'before.json',{'utc':now(),'files':manifest,'excluded':skipped})
        print('BEFORE_PASS: start state recorded. Send the saved request once.');return
    if name=='freeze':
        check_request(records)
        for rel in ['before.json','request.md','response.md','metadata.md']:
            p=records/rel
            if not p.is_file() or not p.read_text(encoding='utf-8-sig').strip(): raise ValueError('Required record missing or empty: '+rel)
        if '[기록]' in (records/'metadata.md').read_text(encoding='utf-8-sig'):raise ValueError('Fill metadata placeholders; use 미확인 for unobserved values.')
        if (records/'after-files').exists():raise ValueError('Partial or prior collection exists. Preserve it; do not overwrite.')
        previous=json.loads((records/'before.json').read_text(encoding='utf-8'))['files']
        current,skipped=files(workspace)
        copy_snapshot(workspace,records/'after-files',current)
        state=learning_state(home);write_json(records/'learning_after.json',state)
        old=json.loads((records/'learning_before.json').read_text(encoding='utf-8'))
        write_json(records/'changes.json',{'created':[k for k in current if k not in previous],'modified':[k for k in current if k in previous and current[k]!=previous[k]],'deleted':[k for k in previous if k not in current],'excluded':skipped,'learning_state_changed':old['learning_file_hashes']!=state['learning_file_hashes'],'selected_settings_changed':old['configured_values']!=state['configured_values'],'input_unchanged':current.get('data/sales.csv')==DATA_HASH})
        write_json(records/'capture.json',{'utc':now(),'quality_evaluated':False,'scope':'workspace regular files; excluded dependency folders, secrets and linked paths are not a full system snapshot'})
        manifest,skipped_records=files(records)
        if skipped_records:raise ValueError('Unexpected excluded record files. Review before sealing.')
        write_json(seal,manifest)
        action('verify',workspace,records,inputs,home)
        print('FREEZE_PASS: preserve this folder. Result quality was not graded.');return
    raise ValueError('Unknown action')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','configure','before','freeze','verify'])
    try:action(p.parse_args().action)
    except urllib.error.HTTPError as e:
        print('STOP: OpenRouter HTTP '+str(e.code)+'. No key or response body printed.',file=sys.stderr);sys.exit(1)
    except Exception as e:
        # Do not print arbitrary network exception bodies or headers containing credentials.
        message=str(e) if isinstance(e,(ValueError,FileNotFoundError)) else type(e).__name__
        print('STOP: '+message,file=sys.stderr);sys.exit(1)
