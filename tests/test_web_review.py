import copy
import hashlib
import json
import sqlite3
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient
from src.application_store import ApplicationStore, Conflict
from src.business_api import create_app
from src.web_sessions import COOKIE, DemoSessions, TTL
from test_business_api import WorkflowFixture


class WebReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3'
        self.users=[dict(employee_id='DEMO-001',token='1'*40),dict(employee_id='DEMO-002',token='2'*40)]
        self.payload=json.loads(Path('data/examples/expense-001.json').read_text(encoding='utf-8'))
        self.payload.pop('employee_id');self.payload.pop('employee_type')
        self.origin={'Origin':'http://testserver'}
        self.key={'Idempotency-Key':'review-1',**self.origin}
        self.fixture=WorkflowFixture();self.app=create_app(self.path,self.users,self.fixture)

    def tearDown(self):self.tmp.cleanup()

    def login(self,client,profile):
        result=client.post('/web/session',json=dict(profile=profile),headers=self.origin)
        self.assertEqual(result.status_code,200)
        return result

    def application(self,client,completed=True):
        self.login(client,'employee')
        response=client.post('/v1/applications',json=self.payload,headers=dict(self.origin,**{'Idempotency-Key':'new-1'}))
        self.assertEqual(response.status_code,201)
        id=response.json()['application_id']
        if completed:
            job=client.post('/v1/applications/'+id+'/precheck',headers=self.origin).json()
            for _ in range(200):
                job=client.get('/v1/prechecks/'+job['job_id']).json()
                if job['status']=='completed':break
                time.sleep(.01)
            self.assertEqual(job['status'],'completed')
        return id

    def test_session_cookie_origin_expiry_and_logout(self):
        with TestClient(self.app) as client:
            self.assertEqual(client.post('/web/session',json={'profile':'finance'}).status_code,403)
            self.assertEqual(client.post('/web/session',json={'profile':'finance'},headers={'Origin':'https://evil.example'}).status_code,403)
            self.assertEqual(client.post('/web/session',json={'profile':'finance','role':'admin'},headers=self.origin).status_code,422)
            result=self.login(client,'employee')
            self.assertIn('HttpOnly',result.headers['set-cookie']);self.assertIn('SameSite=strict',result.headers['set-cookie'])
            old=client.cookies.get(COOKIE)
            self.assertNotIn(old,result.text)
            self.assertEqual(client.get('/v1/me').json()['role'],'employee')
            self.assertEqual(client.post('/v1/applications',json=self.payload,headers={'Idempotency-Key':'x'}).status_code,403)
            self.login(client,'finance');self.assertNotEqual(old,client.cookies.get(COOKIE))
            self.assertEqual(client.get('/v1/me',headers={'Cookie':COOKIE+'='+old}).status_code,401)
            self.assertEqual(client.get('/v1/me',headers={'Authorization':'Bearer invalid'}).status_code,401)
            client.delete('/web/session',headers=self.origin)
            self.assertEqual(client.get('/v1/me').status_code,401)
        sessions=DemoSessions();token=sessions.create('employee')
        sessions.values[token]=(time.monotonic()-1,{'role':'employee'})
        self.assertIsNone(sessions.get(token))

    def test_employee_isolation_and_finance_cannot_submit(self):
        with TestClient(self.app) as client:
            id=self.application(client)
            self.assertEqual(client.get('/v1/review-queue').status_code,403)
            self.assertEqual(client.get('/v1/review-applications/'+id).status_code,403)
            self.assertEqual(client.post('/v1/review-applications/'+id+'/reviews',json={'decision':'reviewed','note':'合成夹具核对记录'},headers=self.key).status_code,403)
            self.assertEqual(client.get('/v1/applications').json()['total'],1)
            other={'Authorization':'Bearer '+'2'*40}
            self.assertEqual(client.get('/v1/applications',headers=other).json()['total'],0)
            self.assertEqual(client.get('/v1/applications/'+id,headers=other).status_code,404)
            self.login(client,'finance')
            self.assertEqual(client.get('/v1/review-queue').json()['total'],1)
            self.assertEqual(client.get('/v1/applications/'+id).status_code,404)
            self.assertEqual(client.post('/v1/applications',json=self.payload,headers=dict(self.origin,**{'Idempotency-Key':'finance'})).status_code,403)

    def test_review_immutable_idempotent_hash_and_employee_can_read(self):
        with TestClient(self.app) as client:
            id=self.application(client);before=client.get('/v1/applications/'+id).json()['precheck']
            self.login(client,'finance')
            for extra in ('reviewer','approved_amount','employee_id','report_sha256'):
                bad=dict(decision='reviewed',note='合成测试人工核对记录');bad[extra]='injected'
                self.assertEqual(client.post('/v1/review-applications/'+id+'/reviews',json=bad,headers=self.key).status_code,422)
            body=dict(decision='follow_up',note='合成测试：需进一步核对供餐说明。')
            first=client.post('/v1/review-applications/'+id+'/reviews',json=body,headers=self.key)
            self.assertEqual(first.status_code,201);review=first.json()
            self.assertEqual(review['reviewer'],'FINANCE-DEMO')
            self.assertEqual(client.post('/v1/review-applications/'+id+'/reviews',json=body,headers=self.key).status_code,200)
            changed=dict(body,note='不同的备注不能覆盖历史记录。')
            self.assertEqual(client.post('/v1/review-applications/'+id+'/reviews',json=changed,headers=self.key).status_code,409)
            self.assertEqual(client.post('/v1/review-applications/'+id+'/reviews',json=body,headers=dict(self.key,**{'Idempotency-Key':'new-key'})).status_code,409)
            self.login(client,'employee');after=client.get('/v1/applications/'+id).json()
            self.assertEqual(after['precheck'],before);self.assertEqual(after['review'],review)
            with closing(sqlite3.connect(self.path)) as db:
                raw=db.execute('SELECT result FROM jobs').fetchone()[0]
            self.assertEqual(review['report_sha256'],hashlib.sha256(raw.encode()).hexdigest())
        reopened=ApplicationStore(self.path)
        self.assertEqual(reopened.application(id,'DEMO-001')['review'],review)

    def test_incomplete_report_and_invalid_review_are_rejected(self):
        with TestClient(self.app) as client:
            id=self.application(client,False);self.login(client,'finance')
            for decision in ('reviewed','approved'):
                result=client.post('/v1/review-applications/'+id+'/reviews',json=dict(decision=decision,note='完整的复核备注。'),headers=self.key)
                self.assertEqual(result.status_code,422)
            self.assertEqual(client.post('/v1/review-applications/missing/reviews',json=dict(decision='reviewed',note='完整的复核备注。'),headers=self.key).status_code,404)

    def test_concurrent_review_has_only_one_record(self):
        store=ApplicationStore(self.path);payload=dict(self.payload,employee_id='DEMO-001',employee_type='ordinary')
        id,_=store.create('DEMO-001','a',payload);job,_=store.enqueue(id,'DEMO-001');store.claim(job)
        store.finish(job,'completed',self.fixture.run(payload),run_id='fixture')
        def record(i):
            try:return store.save_review(id,'FINANCE-DEMO','key-'+str(i),'follow_up','并发测试：需要人工核对。')[1]
            except Conflict:return False
        with ThreadPoolExecutor(max_workers=6) as pool:self.assertEqual(sum(pool.map(record,range(6))),1)

    def test_static_scope_security_headers_and_policy_snapshot(self):
        with TestClient(self.app) as client:
            response=client.get('/')
            self.assertEqual(response.status_code,200);self.assertIn('no-store',response.headers['cache-control'])
            self.assertIn("script-src 'self'",response.headers['content-security-policy'])
            self.assertEqual(client.get('/assets/app.js').status_code,200)
            self.assertEqual(client.get('/examples/business-auth.json').status_code,404)
            self.assertEqual(client.get('/.local/business-auth.json').status_code,404)
            self.assertEqual(client.get('/',headers={'Host':'evil.example'}).status_code,400)
            self.assertEqual(client.get('/v1/policies/v2').status_code,401)
            self.login(client,'employee')
            policy=client.get('/v1/policies/v2').json()
            self.assertEqual(len(policy['clauses']),9);self.assertEqual(len(policy['policy_snapshot_sha256']),64)
            self.assertEqual(client.get('/v1/applications?limit=101').status_code,422)

    def test_v3_migration_preserves_existing_report(self):
        store=ApplicationStore(self.path)
        id,_=store.create('DEMO-001','old',dict(self.payload,employee_id='DEMO-001',employee_type='ordinary'))
        before=store.application(id,'DEMO-001')
        with closing(sqlite3.connect(self.path)) as db,db:
            db.executescript('DROP TABLE reviews; PRAGMA user_version=3;')
        migrated=ApplicationStore(self.path)
        self.assertEqual(migrated.application(id,'DEMO-001'),before)
        with closing(sqlite3.connect(self.path)) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
