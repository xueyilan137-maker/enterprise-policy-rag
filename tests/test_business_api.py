import copy
import json
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from fastapi.testclient import TestClient

from src.application_store import ApplicationStore
from src.business_api import create_app
from src.expense_rules import precheck
from src.workflow_client import WorkflowCallError


class WorkflowFixture:
    """Explicit test fixture; real HTTP is verified separately."""
    def __init__(self,error=None):
        self.error=error;self.calls=0;self.lock=Lock()

    def run(self,payload):
        with self.lock: self.calls+=1
        if self.error: raise self.error
        report=precheck(payload);report['request_id']='fixture-request'
        return {'workflow_run_id':'fixture-run','report':report}


class BusinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'applications.sqlite3'
        self.users=[{'employee_id':id,'token':str(i)*40} for i,id in enumerate(('DEMO-001','DEMO-002'),1)]
        self.headers={'Authorization':'Bearer '+self.users[0]['token'],'Idempotency-Key':'test-1'}
        self.other={'Authorization':'Bearer '+self.users[1]['token']}
        self.payload=json.loads(Path('data/examples/expense-001.json').read_text(encoding='utf-8'))
        self.payload.pop('employee_id');self.payload.pop('employee_type')

    def tearDown(self): self.tmp.cleanup()

    def app(self,fixture): return create_app(self.path,self.users,fixture)

    def finished(self,client,job_id):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            job=client.get('/v1/prechecks/'+job_id,headers=self.headers).json()
            if job['status'] not in ('pending','running'): return job
            time.sleep(.01)
        self.fail('Fixture job did not finish')

    def test_auth_identity_injection_and_scope(self):
        with TestClient(self.app(WorkflowFixture())) as client:
            self.assertEqual(client.get('/v1/me').status_code,401)
            self.assertEqual(client.get('/v1/me',headers=self.headers).json()['employee_id'],'DEMO-001')
            for field in ('employee_id','employee_type','previous_receipt_ids','role'):
                value=copy.deepcopy(self.payload);value[field]='injected'
                self.assertEqual(client.post('/v1/applications',json=value,headers=self.headers).status_code,422)
            self.assertEqual(client.post('/v1/applications',json=self.payload,headers=dict(self.other,**{'Idempotency-Key':'x'})).status_code,403)

    def test_idempotent_creation_conflict_and_private_queries(self):
        with TestClient(self.app(WorkflowFixture())) as client:
            first=client.post('/v1/applications',json=self.payload,headers=self.headers)
            self.assertEqual(first.status_code,201)
            id=first.json()['application_id']
            repeated=client.post('/v1/applications',json=self.payload,headers=self.headers)
            self.assertEqual(repeated.status_code,200);self.assertEqual(repeated.json()['application_id'],id)
            self.assertEqual(first.json()['application']['employee_id'],'DEMO-001')
            changed=copy.deepcopy(self.payload);changed['reason']='changed'
            self.assertEqual(client.post('/v1/applications',json=changed,headers=self.headers).status_code,409)
            self.assertEqual(client.get('/v1/applications/'+id,headers=self.other).status_code,404)
            self.assertEqual(client.post('/v1/applications/'+id+'/precheck',headers=self.other).status_code,404)

    def test_one_job_and_saved_report_after_reopening(self):
        fixture=WorkflowFixture()
        with TestClient(self.app(fixture)) as client:
            id=client.post('/v1/applications',json=self.payload,headers=self.headers).json()['application_id']
            started=client.post('/v1/applications/'+id+'/precheck',headers=self.headers)
            self.assertEqual(started.status_code,202);job_id=started.json()['job_id']
            job=self.finished(client,job_id)
            self.assertEqual(job['status'],'completed')
            self.assertEqual(job['result']['report']['status'],'needs_manual_review')
            self.assertEqual([x['status'] for x in job['events']],['pending','running','completed'])
            self.assertEqual(client.get('/v1/prechecks/'+job_id,headers=self.other).status_code,404)
            self.assertEqual(client.post('/v1/applications/'+id+'/precheck',headers=self.headers).json()['job_id'],job_id)
        with TestClient(self.app(fixture)) as client:
            self.assertEqual(client.get('/v1/applications/'+id,headers=self.headers).json()['precheck']['result'],job['result'])
        self.assertEqual(fixture.calls,1)

    def test_known_failure_is_saved_without_success_report_or_retry(self):
        fixture=WorkflowFixture(WorkflowCallError('workflow_failed',200,'failed-run'))
        with TestClient(self.app(fixture)) as client:
            id=client.post('/v1/applications',json=self.payload,headers=self.headers).json()['application_id']
            job_id=client.post('/v1/applications/'+id+'/precheck',headers=self.headers).json()['job_id']
            job=self.finished(client,job_id)
            self.assertEqual(job['status'],'failed');self.assertIsNone(job['result'])
            self.assertEqual(job['workflow_run_id'],'failed-run')
            client.post('/v1/applications/'+id+'/precheck',headers=self.headers)
        self.assertEqual(fixture.calls,1)

    def test_timeout_is_indeterminate_not_retried(self):
        with TestClient(self.app(WorkflowFixture(WorkflowCallError('upstream_timeout')))) as client:
            id=client.post('/v1/applications',json=self.payload,headers=self.headers).json()['application_id']
            job_id=client.post('/v1/applications/'+id+'/precheck',headers=self.headers).json()['job_id']
            job=self.finished(client,job_id)
            self.assertEqual(job['status'],'indeterminate');self.assertIsNone(job['result'])

    def test_invalid_amount_and_duplicate_item_ids_rejected_before_storage(self):
        with TestClient(self.app(WorkflowFixture())) as client:
            for amount in (120.0,'NaN','-1.00'):
                payload=copy.deepcopy(self.payload);payload['total_amount']=amount
                self.assertEqual(client.post('/v1/applications',json=payload,headers=self.headers).status_code,422)
            self.payload['expense_items'][1]['item_id']='0'
            self.assertEqual(client.post('/v1/applications',json=self.payload,headers=self.headers).status_code,422)

    def test_concurrent_repository_creation_and_claim_are_atomic(self):
        store=ApplicationStore(self.path)
        with ThreadPoolExecutor(max_workers=8) as pool:
            created=list(pool.map(lambda _:store.create('DEMO-001','same',self.payload),range(8)))
        self.assertEqual(sum(new for _,new in created),1)
        self.assertEqual(len({id for id,_ in created}),1)
        id=created[0][0]
        with ThreadPoolExecutor(max_workers=8) as pool:
            jobs=list(pool.map(lambda _:store.enqueue(id,'DEMO-001'),range(8)))
        self.assertEqual(sum(new for _,new in jobs),1)
        job_id=jobs[0][0]
        with ThreadPoolExecutor(max_workers=8) as pool:
            claims=list(pool.map(lambda _:store.claim(job_id),range(8)))
        self.assertEqual(sum(payload is not None for payload in claims),1)

    def test_recovery_marks_interrupted_without_running_again(self):
        store=ApplicationStore(self.path)
        ids=[store.create('DEMO-001',str(i),self.payload)[0] for i in range(2)]
        jobs=[store.enqueue(id,'DEMO-001')[0] for id in ids]
        store.claim(jobs[0]);store.recover()
        self.assertEqual(store.job(jobs[0],'DEMO-001')['status'],'indeterminate')
        self.assertEqual(store.job(jobs[1],'DEMO-001')['status'],'failed')
        self.assertIsNone(store.claim(jobs[0]));self.assertIsNone(store.claim(jobs[1]))
