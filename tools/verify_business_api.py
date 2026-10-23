"""Real local business API acceptance; persists synthetic applications and evidence."""
import argparse
import copy
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--expect-workflow-failure',action='store_true',help='Use only during explicitly arranged upstream fault injection')
    parser.add_argument('--check-saved',type=Path,help='Query an earlier successful report after restarting the business service')
    args=parser.parse_args()
    users=json.loads((ROOT/'.local/business-auth.json').read_text(encoding='utf-8'))['users']
    headers={'Authorization':'Bearer '+next(u['token'] for u in users if u['employee_id']=='DEMO-001')}
    other={'Authorization':'Bearer '+next(u['token'] for u in users if u['employee_id']=='DEMO-002')}
    evidence=[]
    target=ROOT/'.local/evaluations'/('business-api-live-'+str(time.time_ns())+'.json')
    with httpx.Client(base_url='http://127.0.0.1:18082',trust_env=False,timeout=10) as client:
        def request(name,method,url,expected,**kwargs):
            response=client.request(method,url,**kwargs)
            assert response.status_code==expected,(name,response.status_code)
            body=response.json()
            evidence.append(dict(case=name,http_status=response.status_code,response=body))
            target.write_text(json.dumps(dict(mode='live_business_api',cases=evidence),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(name,response.status_code)
            return body
        request('health','GET','/health',200)
        if args.check_saved:
            previous=json.loads(args.check_saved.read_text(encoding='utf-8'))
            stored=next(x['response'] for x in previous['cases'] if x['case']=='completed-job')
            current=request('saved-after-restart','GET','/v1/prechecks/'+stored['job_id'],200,headers=headers)
            assert current==stored,'Saved task changed after restart'
            print('Saved result preserved; evidence',target)
            return
        request('unauthenticated','GET','/v1/me',401)
        request('server-identity','GET','/v1/me',200,headers=headers)
        sample=json.loads((ROOT/'data/examples/expense-001.json').read_text(encoding='utf-8'))
        sample.pop('employee_id');sample.pop('employee_type')
        key='live-'+str(time.time_ns());write_headers=dict(headers,**{'Idempotency-Key':key})
        injected=copy.deepcopy(sample);injected['employee_id']='DEMO-OTHER'
        request('reject-identity-field','POST','/v1/applications',422,json=injected,headers=write_headers)
        created=request('create','POST','/v1/applications',201,json=sample,headers=write_headers)
        id=created['application_id']
        repeated=request('repeat-create','POST','/v1/applications',200,json=sample,headers=write_headers)
        assert repeated['application_id']==id
        changed=copy.deepcopy(sample);changed['reason']='Different payload'
        request('idempotency-conflict','POST','/v1/applications',409,json=changed,headers=write_headers)
        request('other-user-read','GET','/v1/applications/'+id,404,headers=other)
        request('other-user-start','POST','/v1/applications/'+id+'/precheck',404,headers=other)
        started=request('start','POST','/v1/applications/'+id+'/precheck',202,headers=headers)
        job_id=started['job_id']
        duplicate=request('repeat-start','POST','/v1/applications/'+id+'/precheck',200,headers=headers)
        assert duplicate['job_id']==job_id
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            response=client.get('/v1/prechecks/'+job_id,headers=headers)
            assert response.status_code==200
            job=response.json()
            if job['status'] not in ('pending','running'):break
            time.sleep(.2)
        expected='failed' if args.expect_workflow_failure else 'completed'
        assert job['status']==expected,job['status']
        if expected=='completed':
            assert job['result']['report']['status']=='needs_manual_review'
            assert job['result']['report']['facts']['item_sum']=='120.00'
            assert job['workflow_run_id']==job['result']['workflow_run_id']
        else:
            assert job['result'] is None and job['error_code']=='workflow_failed'
        request('completed-job' if expected=='completed' else 'failed-job','GET','/v1/prechecks/'+job_id,200,headers=headers)
        request('other-user-job','GET','/v1/prechecks/'+job_id,404,headers=other)
        current=request('stored-application','GET','/v1/applications/'+id,200,headers=headers)
        assert current['precheck']['job_id']==job_id
    print('Real business API acceptance passed; evidence',target)


if __name__=='__main__':main()
