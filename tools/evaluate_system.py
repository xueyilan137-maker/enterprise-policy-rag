"""Frozen pack planning and actual material HTTP evaluation; reserve requires prior human label review."""
import argparse
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import httpx
from src.evaluation import (PACKS,EvaluationGate,load_pack,read,snapshot,assert_frozen,require_human_reviews,
                            label_digest,score_material,summarize)


def system_paths(pack):
    paths=[str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'src').glob('*.py')]
    paths+=['requirements.txt','requirements-dev.txt','dify/precheck-workflow.template.yml',
            'dify/policy-chatflow.template.yml','data/policies/travel.json','data/corpus/manifest.json',
            'tools/evaluate_system.py','tools/evaluate_qa.py','tools/evaluate_reserved_retrieval.py',
            'tools/evaluate_retrieval.py','tools/evaluate_related.py']
    paths=[p for p in paths if (ROOT/p).is_file()]
    paths += [str((pack['folder']/name).relative_to(ROOT)).replace('\\','/') for name in
              ('qa.inputs.json','materials.inputs.json','gold.json','REVIEW.md','EXPOSURE.md') if (pack['folder']/name).exists()]
    # All actual chatflow templates, even if differently named in the current repo.
    paths+= [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'dify').glob('*chatflow*.yml')]
    paths+= [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'data/eval').glob('dev*.jsonl')]
    paths+= [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'web').glob('*') if p.suffix in ('.js','.html','.css')]
    paths+= [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'data/corpus').glob('*.md')]
    return sorted(set(paths))


def freeze(pack):
    target=pack['folder']/'manifest.json'
    if target.exists():raise EvaluationGate('Manifest already exists; preserve it and version a new pack')
    state=read(ROOT/'.local/precheck-workflow-state.json')
    manifest=dict(pack=pack['name'],split='prospective_reserve_pending_human' if pack['name'].startswith('reserve') else 'development_pilot',
        created_at=datetime.now(timezone.utc).isoformat(),files=snapshot(ROOT,system_paths(pack)),
        workflow_version=state['published_version'],extractor_version=state['extractor_version'],
        chatflow_version=4,model=state['extraction_model'],qa_count=len(pack['qa']),material_count=len(pack['materials']),
        novelty='Assistant-authored combinations on known synthetic policies; not third-party blind/OOD data')
    target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Frozen',pack['name'],'without network calls')


def evaluate_materials(pack,mode):
    manifest=assert_frozen(pack)
    if mode=='reserve':require_human_reviews(pack,[c['id'] for c in pack['materials']])
    if not pack['materials']:raise EvaluationGate('No material cases')
    stamp=str(time.time_ns());target=ROOT/'.local/evaluations'/('system-'+pack['name']+'-'+stamp+'.json')
    target.parent.mkdir(exist_ok=True,parents=True)
    if mode=='reserve':
        marker=ROOT/'.local/eval-ledger'/pack['name']/'materials-started.json';marker.parent.mkdir(exist_ok=True,parents=True)
        try:
            with marker.open('x',encoding='utf-8') as file:json.dump(dict(report=str(target.relative_to(ROOT)),started_at=datetime.now(timezone.utc).isoformat()),file)
        except FileExistsError:raise EvaluationGate('Reserve track already started; inspect original evidence, do not automatically rerun') from None
    config=read(ROOT/'.local/business-auth.json')
    auth={'Authorization':'Bearer '+next(u['token'] for u in config['users'] if u['employee_id']=='DEMO-001')}
    rows=[];report=dict(mode='live_material_'+mode,pack=pack['name'],manifest=manifest,rows=rows,
        label_review='human_reviewed_assertions' if mode=='reserve' else 'assistant_provisional_development_only',
        scope='actual business HTTP -> published extraction Workflow -> server validation -> immutable application -> published rule Workflow; no human financial review')
    def save():
        report['summary']=summarize(rows,len(pack['materials']))
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with httpx.Client(base_url='http://127.0.0.1:18082',headers=auth,trust_env=False,follow_redirects=False,timeout=10) as client:
        def checked(response,allowed=(200,)):
            if response.status_code not in allowed:raise EvaluationGate('HTTP '+str(response.status_code))
            return response.json()
        def poll(path):
            deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                record=checked(client.get(path))
                if record['status'] not in ('pending','running'):return record
                time.sleep(.5)
            raise EvaluationGate('Local polling deadline; remote outcome unknown; do not retry')
        for case in pack['materials']:
            started=time.monotonic();row=dict(id=case['id'],execution='error',label_sha256=label_digest(pack,case['id']))
            try:
                # Only input files are submitted. Gold, review statements and expected findings never enter model input.
                n=checked(client.post('/v1/materials',params={'filename':case['id']+'.md'},content=case['narrative'].encode(),headers={'Content-Type':'text/markdown'}),(200,201))
                c=checked(client.post('/v1/materials',params={'filename':case['id']+'.csv'},content=case['csv'].encode(),headers={'Content-Type':'text/csv'}),(200,201))
                response=client.post('/v1/extractions',json=dict(narrative_material_id=n['material_id'],csv_material_id=c['material_id']))
                task=checked(response,(200,202));row['fresh_extraction_task']=response.status_code==202
                row['extraction']=poll('/v1/extractions/'+task['extraction_id'])
                if row['extraction']['extractor_version']!=manifest['extractor_version']:raise EvaluationGate('Deployed extractor protocol differs from snapshot')
                if row['extraction']['status']!='completed':raise EvaluationGate('Extraction terminal state '+row['extraction']['status'])
                response=client.post('/v1/applications/from-extraction',json={'extraction_id':task['extraction_id']},
                    headers={'Idempotency-Key':'eval-'+pack['name']+'-'+task['extraction_id']})
                row['creation_http_status']=response.status_code
                if row['extraction']['result']['validation']['status']=='validated':
                    app=checked(response,(200,201));row['application']=app
                    job=checked(client.post('/v1/applications/'+app['application_id']+'/precheck'),(200,202))
                    row['precheck']=poll('/v1/prechecks/'+job['job_id'])
                    if row['precheck']['status']!='completed':raise EvaluationGate('Precheck terminal state '+row['precheck']['status'])
                else:
                    row['application']=None
                    if response.status_code!=422:raise EvaluationGate('Invalid extraction creation boundary changed')
                if mode=='reserve' and not row['fresh_extraction_task']:raise EvaluationGate('Reused task invalidates fresh reserve timing; no retry')
                row['execution']='completed'
            except (httpx.RequestError,ValueError,KeyError,TypeError) as exc:
                row['error']=str(exc) if isinstance(exc,EvaluationGate) else type(exc).__name__
            row['latency_seconds']=round(time.monotonic()-started,3)
            row['score']=score_material(row,pack['gold'][case['id']]);rows.append(row);save()
            print(case['id'],row['execution'],'pass='+str(row['score']['case_pass']),flush=True)
    print(json.dumps({'report':str(target),'summary':report['summary']},ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('plan','freeze','pilot','reserve'))
    parser.add_argument('--pack',choices=PACKS,default='reserve-v1')
    args=parser.parse_args();pack=load_pack(args.pack)
    if args.action=='freeze':freeze(pack)
    elif args.action=='plan':
        manifest=assert_frozen(pack)
        pending=[]
        if args.pack.startswith('reserve'):
            for c in pack['qa']+pack['materials']:
                try:require_human_reviews(pack,[c['id']])
                except EvaluationGate:pending.append(c['id'])
        print(json.dumps(dict(pack=args.pack,qa=len(pack['qa']),materials=len(pack['materials']),human_review_pending=pending,
            frozen=True,workflow_version=manifest['workflow_version'],network_calls=0),ensure_ascii=False))
    else:
        if (args.action=='pilot')!=(args.pack=='pilot-v1'):raise EvaluationGate('Pilot and reserve modes cannot be relabeled')
        evaluate_materials(pack,args.action)


if __name__=='__main__':
    try:main()
    except EvaluationGate as exc:raise SystemExit(str(exc)) from None
