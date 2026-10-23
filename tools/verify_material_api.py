"""Real CSV upload -> server validation -> durable application -> published Workflow."""
import hashlib
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx

ROOT=Path(__file__).resolve().parents[1]


def main():
    users=json.loads((ROOT/'.local/business-auth.json').read_text(encoding='utf-8'))['users']
    auth={'Authorization':'Bearer '+next(u['token'] for u in users if u['employee_id']=='DEMO-001')}
    other={'Authorization':'Bearer '+next(u['token'] for u in users if u['employee_id']=='DEMO-002')}
    raw=(ROOT/'data/examples/expense-items-001.csv').read_bytes()
    header=json.loads((ROOT/'data/examples/expense-001.json').read_text(encoding='utf-8'))
    for key in ('employee_id','employee_type','expense_items'):header.pop(key)
    evidence=[]
    target=ROOT/'.local/evaluations'/('material-api-live-'+str(time.time_ns())+'.json')
    with httpx.Client(base_url='http://127.0.0.1:18082',trust_env=False,timeout=10) as client:
        def request(name,method,url,expected,**kwargs):
            response=client.request(method,url,**kwargs)
            assert response.status_code in expected if isinstance(expected,tuple) else response.status_code==expected,(name,response.status_code)
            body=response.json()
            evidence.append(dict(case=name,http_status=response.status_code,response=body))
            target.write_text(json.dumps(dict(mode='live_csv_material_to_workflow',cases=evidence),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(name,response.status_code)
            return body
        def upload(name,content,expected):
            return request(name,'POST','/v1/materials?filename=expenses.csv',expected,content=content,
                           headers=dict(auth,**{'Content-Type':'text/csv; charset=utf-8'}))
        material=upload('csv-upload',raw,(200,201));id=material['material_id']
        assert material['sha256']==hashlib.sha256(raw).hexdigest()
        assert material['items'][0]['amount']=='60.00'
        assert material['row_locations'][1]['ending_line']==3
        request('material-query','GET','/v1/materials/'+id,200,headers=auth)
        assert upload('content-deduplication',raw,200)['material_id']==id
        request('other-owner-material','GET','/v1/materials/'+id,404,headers=other)
        invalid=upload('invalid-money',raw.replace(b'60.00',b'NaN',1),422)
        assert invalid['status']=='invalid' and invalid['items']==[]
        upload('invalid-utf8',b'\xff\xfe',422)
        upload('identity-column',raw.replace(b'meal_provided',b'employee_id'),422)
        request('oversized-body','POST','/v1/materials?filename=a.csv',413,content=b'x'*(256*1024+1),headers=dict(auth,**{'Content-Type':'text/csv'}))
        request('unsupported-image','POST','/v1/materials?filename=a.png',415,content=b'PNG',headers=dict(auth,**{'Content-Type':'image/png'}))
        headers=dict(auth,**{'Idempotency-Key':'csv-live-'+str(time.time_ns())})
        request('invalid-material-cannot-create','POST','/v1/applications/from-material',422,
                json=dict(header,material_id=invalid['material_id']),headers=headers)
        request('cannot-override-items','POST','/v1/applications/from-material',422,
                json=dict(header,material_id=id,expense_items=[]),headers=headers)
        request('invalid-header-date','POST','/v1/applications/from-material',422,
                json=dict(header,material_id=id,trip_start_date='2026-02-30'),headers=headers)
        created=request('material-application','POST','/v1/applications/from-material',201,json=dict(header,material_id=id),headers=headers)
        app_id=created['application_id']
        assert created['materials'][0]['material_id']==id
        assert created['application']['employee_id']=='DEMO-001'
        assert request('repeat-application','POST','/v1/applications/from-material',200,
                       json=dict(header,material_id=id),headers=headers)['application_id']==app_id
        request('other-owner-application','GET','/v1/applications/'+app_id,404,headers=other)
        job=request('start-precheck','POST','/v1/applications/'+app_id+'/precheck',202,headers=auth)
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            response=client.get('/v1/prechecks/'+job['job_id'],headers=auth)
            assert response.status_code==200
            finished=response.json()
            if finished['status'] not in ('pending','running'):break
            time.sleep(.2)
        assert finished['status']=='completed',finished['status']
        report=finished['result']['report']
        assert report['facts']['item_sum']=='120.00' and report['status']=='needs_manual_review'
        assert report['findings'][0]['clause_ids']==['TRAVEL-v2-MEAL','TRAVEL-v2-REVIEW']
        request('completed-material-job','GET','/v1/prechecks/'+job['job_id'],200,headers=auth)
        request('application-provenance','GET','/v1/applications/'+app_id,200,headers=auth)
    print('Real material acceptance passed; evidence',target)


if __name__=='__main__':main()
