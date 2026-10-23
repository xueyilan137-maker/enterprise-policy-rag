import json
import sqlite3
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from fastapi.testclient import TestClient

from src.application_store import ApplicationStore,Conflict
from src.business_api import create_app
from src.expense_rules import precheck
from src.material_parser import MAX_BYTES,parse_expense_csv


class CsvWorkflowFixture:
    def __init__(self):self.calls=0
    def run(self,payload):
        self.calls+=1
        report=precheck(payload);report['request_id']='fixture-request'
        return dict(workflow_run_id='fixture-run',report=report)


class MaterialApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'applications.sqlite3'
        self.users=[dict(employee_id='DEMO-001',token='1'*40),dict(employee_id='DEMO-002',token='2'*40)]
        self.headers={'Authorization':'Bearer '+'1'*40,'Idempotency-Key':'csv-1'}
        self.other={'Authorization':'Bearer '+'2'*40}
        self.raw=Path('data/examples/expense-items-001.csv').read_bytes()
        self.header=json.loads(Path('data/examples/expense-001.json').read_text(encoding='utf-8'))
        for key in ('employee_id','employee_type','expense_items'):self.header.pop(key)
        self.workflow=CsvWorkflowFixture()

    def tearDown(self):self.tmp.cleanup()
    def app(self):return create_app(self.path,self.users,self.workflow)
    def upload(self,client,raw=None,name='expenses.csv',**kwargs):
        return client.post('/v1/materials',params={'filename':name},content=self.raw if raw is None else raw,
            headers=dict(self.headers,**{'Content-Type':'text/csv'}),**kwargs)
    def counts(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return tuple(db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('materials','applications','jobs'))

    def test_upload_to_saved_application_and_fixture_workflow(self):
        with TestClient(self.app()) as client:
            upload=self.upload(client);self.assertEqual(upload.status_code,201)
            material=upload.json();id=material['material_id']
            details=dict(self.header,material_id=id)
            created=client.post('/v1/applications/from-material',json=details,headers=self.headers)
            self.assertEqual(created.status_code,201)
            app=created.json()
            self.assertEqual(app['materials'][0]['sha256'],material['sha256'])
            self.assertEqual(app['application']['expense_items'][0]['amount'],'60.00')
            self.assertEqual(app['application']['employee_id'],'DEMO-001')
            job_id=client.post('/v1/applications/'+app['application_id']+'/precheck',headers=self.headers).json()['job_id']
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                job=client.get('/v1/prechecks/'+job_id,headers=self.headers).json()
                if job['status']=='completed':break
                time.sleep(.01)
            self.assertEqual(job['result']['report']['status'],'needs_manual_review')
            self.assertEqual(self.workflow.calls,1)
            repeated=client.post('/v1/applications/from-material',json=details,headers=self.headers)
            self.assertEqual(repeated.status_code,200)
            self.assertEqual(repeated.json()['application_id'],app['application_id'])

    def test_invalid_material_stored_but_never_becomes_application(self):
        with TestClient(self.app()) as client:
            response=self.upload(client,self.raw.replace(b'60.00',b'NaN',1))
            self.assertEqual(response.status_code,422)
            material=response.json();self.assertEqual(material['status'],'invalid')
            self.assertEqual(material['items'],[])
            self.assertEqual(client.get('/v1/materials/'+material['material_id'],headers=self.headers).status_code,200)
            result=client.post('/v1/applications/from-material',json=dict(self.header,material_id=material['material_id']),headers=self.headers)
            self.assertEqual(result.status_code,422)
        self.assertEqual(self.counts(),(1,0,0));self.assertEqual(self.workflow.calls,0)

    def test_oversize_type_and_path_rejected_before_storage(self):
        with TestClient(self.app()) as client:
            self.assertEqual(self.upload(client,b'x'*(MAX_BYTES+1)).status_code,413)
            for name in ('../invoice.csv','C:\\invoice.csv','folder/file.csv'):
                self.assertEqual(self.upload(client,name=name).status_code,422)
            self.assertEqual(self.upload(client,name='invoice.pdf').status_code,415)
            self.assertEqual(client.post('/v1/materials?filename=a.csv',content=self.raw,
                headers=dict(self.headers,**{'Content-Type':'application/octet-stream'})).status_code,415)
        self.assertEqual(self.counts(),(0,0,0))

    def test_material_ownership_and_no_client_parsed_item_override(self):
        with TestClient(self.app()) as client:
            id=self.upload(client).json()['material_id']
            self.assertEqual(client.get('/v1/materials/'+id,headers=self.other).status_code,404)
            self.assertEqual(client.post('/v1/materials?filename=a.csv',content=self.raw,
                headers=dict(self.other,**{'Content-Type':'text/csv'})).status_code,403)
            for key in ('expense_items','employee_id','role'):
                payload=dict(self.header,material_id=id);payload[key]='override'
                self.assertEqual(client.post('/v1/applications/from-material',json=payload,headers=self.headers).status_code,422)
            bad=dict(self.header,material_id=id,trip_start_date='2026-02-30')
            self.assertEqual(client.post('/v1/applications/from-material',json=bad,headers=self.headers).status_code,422)
        self.assertEqual(self.counts(),(1,0,0))

    def test_content_deduplication_and_source_aware_idempotency(self):
        with TestClient(self.app()) as client:
            id=self.upload(client).json()['material_id']
            duplicate=self.upload(client,name='renamed.csv')
            self.assertEqual(duplicate.status_code,200);self.assertEqual(duplicate.json()['material_id'],id)
            details=dict(self.header,material_id=id)
            client.post('/v1/applications/from-material',json=details,headers=self.headers)
            other=self.upload(client,b'\xef\xbb\xbf'+self.raw).json()['material_id']
            self.assertNotEqual(other,id)
            self.assertEqual(client.post('/v1/applications/from-material',json=dict(self.header,material_id=other),headers=self.headers).status_code,409)
        self.assertEqual(self.counts(),(2,1,0))

    def test_concurrent_upload_deduplication_and_raw_bytes_retained(self):
        store=ApplicationStore(self.path);parsing=parse_expense_csv(self.raw)
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(lambda _:store.save_material('DEMO-001','a.csv',self.raw,parsing),range(6)))
        self.assertEqual(sum(new for _,new in results),1)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT raw FROM materials').fetchone()[0],self.raw)
        self.assertIsNone(store.material(results[0][0],'DEMO-002'))

    def test_v1_migration_preserves_old_application_and_idempotency(self):
        store=ApplicationStore(self.path)
        id,_=store.create('DEMO-001','old-key',{'old':'payload'})
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executescript('DROP TABLE application_materials; DROP TABLE materials; PRAGMA user_version=1;')
        migrated=ApplicationStore(self.path)
        self.assertEqual(migrated.create('DEMO-001','old-key',{'old':'payload'}),(id,False))
        self.assertEqual(migrated.application(id,'DEMO-001')['materials'],[])
        with closing(sqlite3.connect(self.path)) as db, db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
