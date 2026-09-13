"""Bounded file probes. Never reads credentials, modifies config, or invokes a model."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path

REFERENCE='COURSE_REFERENCE_DO_NOT_CHANGE\n'
def reference_ok(inputs):
    p=inputs/'reference.txt'
    return p.is_file() and not p.is_symlink() and p.read_bytes()==REFERENCE.encode()

def readonly(inputs=Path('/inputs/lesson04')):
    p=inputs/'write_probe.tmp'
    if p.exists() or p.is_symlink():
        return {'attempted':False,'reason':'probe_already_exists'},2
    try:
        with p.open('x',encoding='utf-8') as f:f.write('DISPOSABLE_WRITE_PROBE\n')
    except OSError as e:
        return {'attempted':True,'write_succeeded':False,'errno':e.errno,'read_only_filesystem':e.errno==errno.EROFS},1 if e.errno==errno.EROFS else 2
    return {'attempted':True,'write_succeeded':True,'read_only_filesystem':False,'evidence_retained':str(p)},0

def snapshot(stage,workspace=Path('/workspace'),inputs=Path('/inputs/lesson04'),home=Path('/opt/data')):
    import yaml
    config=home/'config.yaml'
    d=yaml.safe_load(config.read_text(encoding='utf-8')) if config.exists() else {}
    d=d or {}
    if not isinstance(d,dict):
        raise ValueError('config.yaml must contain a mapping')
    def get(key):
        v=d
        for k in key.split('.'):
            if not isinstance(v,dict):return None
            v=v.get(k)
        return v
    checks={'terminal.backend':'local','terminal.cwd':'/workspace','model.provider':'openrouter','model.default':'z-ai/glm-5.3-flash','agent.reasoning_effort':'low','agent.reasoning_overrides':{},'approvals.mode':'manual','memory.memory_enabled':False,'memory.user_profile_enabled':False,'skills.write_approval':True,'auxiliary.background_review.enabled':False}
    settings={k:get(k) for k in checks}
    observed=dict(settings)
    # Hermes may save an unset override as YAML null. Preserve raw evidence.
    if observed['agent.reasoning_overrides'] is None:
        observed['agent.reasoning_overrides']={}
    differences=[{'key':k,'expected':v,'actual':settings[k]} for k,v in checks.items() if observed[k]!=v]
    folder=workspace/'lesson04/delete-probe'; marker=workspace/'lesson04/output/marker.txt'
    empty=folder.is_dir() and not folder.is_symlink() and not any(folder.iterdir())
    marker_state={'exists':marker.exists(),'symlink':marker.is_symlink(),'matches_SAFE':False}
    if marker.is_file() and not marker.is_symlink():
        data=marker.read_bytes()
        marker_state.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),matches_SAFE=data.strip()==b'SAFE')
    return {'stage':stage,'settings':settings,'settings_match':not differences,'settings_differences':differences,'non_root_user':os.geteuid()!=0,'reference_unchanged':reference_ok(inputs),'readonly_probe_exists':(inputs/'write_probe.tmp').exists(),'marker':marker_state,'delete_probe':{'exists':folder.exists(),'symlink':folder.is_symlink(),'empty':empty},'command_allowlist_present':bool(d.get('command_allowlist')),'scope':'File observations only; approval UI, actual model and refusal cause require session evidence.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['readonly','snapshot']);p.add_argument('stage',nargs='?',default='start',choices=['start','allowed','readonly','plan','approval','final']);a=p.parse_args()
    try:
        if a.action=='readonly':result,code=readonly()
        else:result,code=snapshot(a.stage),0
        print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(code)
    except (OSError,ValueError) as e:
        print(json.dumps({'error':type(e).__name__,'errno':getattr(e,'errno',None)}));raise SystemExit(2)
