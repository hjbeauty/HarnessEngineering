"""Trusted, Python-only course helper. Never invokes an Agent or reads credentials.
The temporary helper alone receives /course-host; Dashboard mounts stay unchanged.
"""
import argparse, copy, hashlib, json, os, platform, shutil, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
import yaml

CSV_SHA='60f14a8cbe5fd6eba994ef2f6c43fbc714b232a3d7a37e60cb02ee6cdad9f0d8'
CONFLICT='\n- 충돌 시험: 보고서는 /workspace/result/에 저장합니다.\n'
EXPECTED={'terminal.backend':'local','terminal.cwd':'/workspace','model.provider':'openrouter','model.default':'z-ai/glm-5.3-flash','agent.reasoning_effort':'low','agent.reasoning_overrides':None,'approvals.mode':'manual','memory.memory_enabled':False,'memory.user_profile_enabled':False,'skills.write_approval':True,'auxiliary.background_review.enabled':False,'auxiliary.title_generation.enabled':False}
EXTRA=['agent.disabled_toolsets','command_allowlist']

def stamp(): return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:6]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,msg):
    if not ok: raise RuntimeError(msg)
def write_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,indent=2)
def tree(p):
    require(p.is_dir() and not p.is_symlink(),f'Not a regular directory: {p.name}')
    out={}
    for root,dirs,files in os.walk(p,followlinks=False):
        for n in dirs+files:
            q=Path(root)/n
            require(not q.is_symlink(),f'Links are not followed: {q.name}')
            require(q.is_file() or q.is_dir(),f'Unsupported file type: {q.name}')
            out[q.relative_to(p).as_posix()]='DIR' if q.is_dir() else sha(q)
    return out

def get(c,key):
    cur=c
    for part in key.split('.'):
        if not isinstance(cur,dict) or part not in cur: return {'present':False,'value':None}
        cur=cur[part]
    return {'present':True,'value':cur}
def put(c,key,item):
    parts=key.split('.'); cur=c
    for part in parts[:-1]:
        if part not in cur:
            if not item['present']: return
            cur[part]={}
        require(isinstance(cur[part],dict),'Config section is not a mapping')
        cur=cur[part]
    if item['present']: cur[parts[-1]]=item['value']
    else: cur.pop(parts[-1],None)
def settings(c): return {k:get(c,k) for k in list(EXPECTED)+EXTRA}
def acceptable(c):
    bad=[]
    for k,expected in EXPECTED.items():
        v=get(c,k)['value']
        if k=='agent.reasoning_overrides' and v in (None,{}): continue
        if type(v)!=type(expected) or v!=expected: bad.append(k)
    disabled=get(c,'agent.disabled_toolsets')['value']
    if not isinstance(disabled,list) or not {'memory','session_search'}.issubset(disabled): bad.append('agent.disabled_toolsets')
    return bad

def state_tree(home):
    return {n:tree(home/n) if (home/n).exists() else None for n in ('memories','skills')}
def capture(home,dest):
    dest.mkdir()
    meta={'settings':settings(yaml.safe_load((home/'config.yaml').read_text()) or {}),'trees':state_tree(home)}
    for n,t in meta['trees'].items():
        if t is not None: shutil.copytree(home/n,dest/n)
    require({n:tree(dest/n) if t is not None else None for n,t in meta['trees'].items()}==meta['trees'],'Harness backup differs.')
    write_json(dest/'state.json',meta)
    return meta

def verify_saved(cp):
    saved=json.loads((cp/'manifest.json').read_text())
    actual=tree(cp); actual.pop('manifest.json',None)
    require(actual==saved,'Checkpoint integrity failed. Preserve files; do not restore.')

class Course:
    def __init__(self,host=Path('/course-host'),home=Path('/opt/data')):
        self.host=host; self.home=home; self.ws=host/'workspace'
        self.records=host/'records'; self.rec=self.records/'lesson05'
        self.pending=self.records/'lesson05-pending.json'; self.starter=host/'starter/lesson05'
    def config(self): return yaml.safe_load((self.home/'config.yaml').read_text()) or {}
    def guard(self):
        require(not self.pending.exists(),'Pending operation exists. Preserve lesson05-pending.json and all backups; do not repeat actions.')
        for p in [self.host,self.home,self.records,self.ws]:
            require(p.is_dir() and not p.is_symlink(),f'Expected a regular directory: {p.name}')
        require(sha(self.host/'inputs/lesson03/sales.csv')==CSV_SHA,'Original 200-row CSV differs or is missing.')
    def journal(self,action,backup):
        write_json(self.pending,{'action':action,'backup':str(backup),'started_utc':stamp()})
    def done(self,dest): self.pending.rename(dest)
    def prepare(self):
        self.guard(); require(not self.rec.exists(),'Lesson05 records already exist. Use checks or restore; do not overwrite.')
        require(not acceptable(self.config()),'Settings differ: '+', '.join(acceptable(self.config())))
        tree(self.ws); tree(self.starter); state_tree(self.home)
        self.journal('prepare',self.rec)
        self.rec.mkdir(); cp=self.rec/'checkpoint'; cp.mkdir()
        shutil.copytree(self.ws,self.rec/'prior-workspace')
        require(tree(self.ws)==tree(self.rec/'prior-workspace'),'Prior workspace copy differs.')
        capture(self.home,cp/'harness')
        entry=cp/'entry-workspace'; shutil.copytree(self.starter,entry)
        p=entry/'context/environment.md'
        p.write_text(p.read_text().replace('@UTC@',datetime.now(timezone.utc).isoformat()).replace('@PYTHON@',platform.python_version()).replace('@UID@',str(os.getuid())),encoding='utf-8')
        write_json(cp/'manifest.json',tree(cp)); verify_saved(cp)
        self.ws.rename(self.rec/'workspace-before-prepare')
        shutil.copytree(entry,self.ws)
        require(tree(self.ws)==tree(entry),'Entry workspace copy differs.')
        shutil.copy2(self.host/'templates/context_review.md',self.rec/'context_review.md')
        write_json(self.rec/'prepared.json',{'entry':'checkpoint/entry-workspace','original_csv_sha256':CSV_SHA,'state_scope':'selected settings, memories, skills; credentials and session database excluded'})
        self.done(self.rec/'prepare-result.json')
        print('PREPARE_PASS: prior work preserved; Lesson05 entry checkpoint saved.')
    def compare(self,stage):
        self.guard(); cp=self.rec/'checkpoint'; verify_saved(cp)
        expected=tree(cp/'entry-workspace')
        if stage=='conflict':
            p=cp/'entry-workspace/context/conventions.md'
            expected['context/conventions.md']=hashlib.sha256(p.read_bytes()+CONFLICT.encode()).hexdigest()
        actual=tree(self.ws)
        diffs=[k for k in sorted(set(expected)|set(actual)) if expected.get(k)!=actual.get(k)]
        before=json.loads((cp/'harness/state.json').read_text()); current=settings(self.config())
        settings_diff=[]
        for k,v in before['settings'].items():
            now=current[k]
            if k=='agent.reasoning_overrides' and v['value'] in (None,{}) and now['value'] in (None,{}): continue
            if now!=v: settings_diff.append(k)
        state_ok=state_tree(self.home)==before['trees']
        out={'stage':stage,'workspace_matches':not diffs,'workspace_differences':diffs,'settings_match':not settings_diff,'settings_differences':settings_diff,'memory_and_skills_unchanged':state_ok,'original_csv_unchanged':True,'request_sha256':sha(self.ws/'review_request.txt') if (self.ws/'review_request.txt').is_file() else None,'scope':'Checks files and saved settings; assess reasoning and actual tool use from the exported Chat.'}
        path=self.rec/('check-'+stage+'-'+stamp()+'.json'); write_json(path,out)
        print(json.dumps(out,ensure_ascii=False,indent=2)); print('RECORDED: records/lesson05/'+path.name)
        require(not diffs and not settings_diff and state_ok,'CHECK_STOPPED: differences recorded. Preserve the Chat; use the guide recovery procedure.')
        print('START_READY' if stage=='start' else 'CHECK_PASS: '+stage)
    def conflict(self):
        self.compare('review')
        p=self.ws/'context/conventions.md'
        p.write_bytes(p.read_bytes()+CONFLICT.encode())
        print('CONFLICT_READY: one line added to context/conventions.md.')
    def resolve(self):
        self.compare('conflict')
        p=self.ws/'context/conventions.md'
        p.write_bytes((self.rec/'checkpoint/entry-workspace/context/conventions.md').read_bytes())
        print('RESOLVE_PASS: intentional conflicting line removed; outputs/ remains authoritative.')
    def restore(self):
        self.guard(); cp=self.rec/'checkpoint'; verify_saved(cp)
        require((self.rec/'prepared.json').is_file(),'Preparation incomplete. Preserve the pending journal.')
        tree(self.ws); state_tree(self.home); self.config()
        attempt=self.records/('lesson05-attempt-'+stamp())
        self.journal('restore',attempt); attempt.mkdir()
        # Preserve observed files and changed Harness state before restoring anything.
        shutil.copytree(self.ws,attempt/'workspace-after-attempt')
        require(tree(self.ws)==tree(attempt/'workspace-after-attempt'),'Attempt backup differs.')
        capture(self.home,attempt/'harness-after-attempt')
        shutil.copytree(cp,attempt/'checkpoint'); verify_saved(attempt/'checkpoint')
        saved=json.loads((cp/'harness/state.json').read_text())
        config=self.config()
        for k,v in saved['settings'].items(): put(config,k,v)
        # Merge only the recorded fields. Unrelated configuration and secrets are retained.
        config_path=self.home/'config.yaml'
        temp=self.home/('lesson05-config-'+uuid.uuid4().hex+'.tmp')
        temp.write_text(yaml.safe_dump(config,allow_unicode=True,sort_keys=False),encoding='utf-8')
        temp.chmod(config_path.stat().st_mode & 0o777); os.replace(temp,config_path)
        for n,t in saved['trees'].items():
            p=self.home/n
            if p.exists(): shutil.rmtree(p)
            if t is not None: shutil.copytree(cp/'harness'/n,p)
        self.ws.rename(attempt/'workspace-moved')
        shutil.copytree(cp/'entry-workspace',self.ws)
        old=self.rec; old.rename(attempt/'lesson05-records'); self.rec.mkdir()
        shutil.copytree(attempt/'checkpoint',self.rec/'checkpoint')
        shutil.copy2(attempt/'lesson05-records/prepared.json',self.rec/'prepared.json')
        shutil.copy2(self.host/'templates/context_review.md',self.rec/'context_review.md')
        require(tree(self.ws)==tree(self.rec/'checkpoint/entry-workspace'),'Restored workspace differs.')
        require(settings(self.config())==saved['settings'],'Restored settings differ.')
        require(state_tree(self.home)==saved['trees'],'Restored Memory/Skill files differ.')
        self.done(attempt/'restore-result.json')
        print('RESTORE_PASS: Lesson05 entry files and recorded Harness state restored.')
        print('BACKUP: records/'+attempt.name)
        print('Do not run prepare again. Start Hermes, open a NEW Chat, then check start.')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['prepare','check','conflict','resolve','restore']); ap.add_argument('stage',nargs='?',default='start',choices=['start','review','conflict','final']); a=ap.parse_args()
    try:
        require(os.getuid()!=0,'Run this helper as the hermes user, not root.')
        c=Course()
        if a.action=='check': c.compare(a.stage)
        else: getattr(c,a.action)()
    except Exception as e:
        print('STOP: '+str(e),file=sys.stderr); sys.exit(1)
