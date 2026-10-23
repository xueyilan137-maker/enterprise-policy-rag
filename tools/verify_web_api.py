"""Real localhost HTTP checks for the web demo; does not submit a review or call a model."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]


def main():
    args=argparse.ArgumentParser()
    args.add_argument('application_id')
    args.add_argument('--snapshot',action='store_true')
    options=args.parse_args()
    base='http://127.0.0.1:18082';origin={'Origin':base};checks=[]
    saved=ROOT/'.local/evidence/web-application-before-review.json'
    def check(name,condition):
        assert condition,name
        checks.append(name)
    with httpx.Client(base_url=base,trust_env=False,timeout=10) as client:
        check('anonymous private data rejected',client.get('/v1/applications').status_code==401)
        response=client.get('/')
        check('page and CSP served',response.status_code==200 and "script-src 'self'" in response.headers['content-security-policy'])
        check('private config inaccessible',client.get('/.local/business-auth.json').status_code==404)
        check('sample download',client.get('/examples/trip-note-001.md').status_code==200)
        check('login requires origin',client.post('/web/session',json={'profile':'finance'}).status_code==403)
        check('foreign origin rejected',client.post('/web/session',json={'profile':'finance'},headers={'Origin':'https://foreign.invalid'}).status_code==403)
        response=client.post('/web/session',json={'profile':'employee'},headers=origin)
        check('httpOnly strict cookie',response.status_code==200 and 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=strict' in response.headers['set-cookie'])
        check('employee identity server bound',client.get('/v1/me').json()['employee_id']=='DEMO-001')
        check('employee cannot list review queue',client.get('/v1/review-queue').status_code==403)
        check('employee cannot read finance detail',client.get('/v1/review-applications/'+options.application_id).status_code==403)
        check('cookie mutation without origin rejected',client.post('/v1/applications/'+options.application_id+'/precheck').status_code==403)
        app=client.get('/v1/applications/'+options.application_id).json()
        check('completed actual Dify precheck',app['precheck']['status']=='completed' and len(app['precheck']['workflow_run_id'])>10)
        check('rule facts retained',app['precheck']['result']['report']['facts']['item_sum']=='120.00')
        extraction=client.get('/v1/extractions/'+app['extraction_id']).json()
        check('validated real model extraction',extraction['status']=='completed' and extraction['result']['validation']['status']=='validated')
        check('exact source lines',all(e['start_line']>=1 and e['end_line']>=e['start_line'] for e in extraction['result']['validation']['evidence'].values()))
        policy=client.get('/v1/policies/v2').json()
        check('policy source snapshot matches',policy['policy_snapshot_sha256']==app['precheck']['result']['report']['policy_snapshot_sha256'])
        private=json.loads((ROOT/'.local/business-auth.json').read_text(encoding='utf-8'))
        other={'Authorization':'Bearer '+next(u['token'] for u in private['users'] if u['employee_id']=='DEMO-002')}
        check('other employee cannot view',client.get('/v1/applications/'+options.application_id,headers=other).status_code==404)
        client.post('/web/session',json={'profile':'finance'},headers=origin)
        check('finance role server bound',client.get('/v1/me').json()['employee_id']=='FINANCE-DEMO')
        check('finance queue available',client.get('/v1/review-queue').status_code==200)
        finance=client.get('/v1/review-applications/'+options.application_id).json()
        check('finance source bundle',len(finance['source_materials'])==2 and finance['precheck']==app['precheck'])
        check('review cannot inject approval',client.post('/v1/review-applications/'+options.application_id+'/reviews',json={'decision':'approved','note':'Synthetic invalid approval'},headers=dict(origin,**{'Idempotency-Key':'negative-only'})).status_code==422)
        check('csrf review blocked',client.post('/v1/review-applications/'+options.application_id+'/reviews',json={'decision':'follow_up','note':'Synthetic origin rejection'},headers={'Idempotency-Key':'negative-only'}).status_code==403)
        if options.snapshot:
            assert app['review'] is None,'Preserve the original before-review snapshot'
            assert not saved.exists(),'Do not overwrite original snapshot'
            saved.write_text(json.dumps(dict(application=app,extraction=extraction),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        else:
            before=json.loads(saved.read_text(encoding='utf-8'))
            check('original report unchanged after review',before['application']['precheck']==app['precheck'])
            check('model result unchanged after review',before['extraction']==extraction)
            check('independent review persisted',finance['review'] is not None and finance['review']['reviewer']=='FINANCE-DEMO')
            check('employee sees same review',finance['review']==app['review'])
        client.delete('/web/session',headers=origin)
        check('logout invalidates session',client.get('/v1/me').status_code==401)
    output=ROOT/'.local/evaluations'/('web-api-live-'+str(time.time_ns())+'.json')
    output.write_text(json.dumps(dict(mode='real_http_no_model_calls',application_id=options.application_id,
        checks=checks,application=app,extraction=extraction),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Passed',len(checks),'real HTTP checks; saved',output)


if __name__=='__main__':main()
