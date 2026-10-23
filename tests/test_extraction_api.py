import json
import tempfile
import time
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from src.business_api import create_app
from src.application_store import ApplicationStore
from src.narrative import EXTRACTOR_VERSION
from test_narrative import candidate


class ExtractFixture:
    def __init__(self,missing=False):self.calls=0;self.missing=missing
    def extract(self,text):
        self.calls+=1;body=candidate(text)
        if self.missing:body['fields']['total_amount']=dict(value=None,quote=None)
        return dict(workflow_run_id='fixture-extract-run',raw_model=json.dumps(body,ensure_ascii=False),total_tokens=100,elapsed_time=1)


class ExtractionApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'application.sqlite3'
        self.users=[dict(employee_id='DEMO-001',token='1'*40),dict(employee_id='DEMO-002',token='2'*40)]
        self.auth={'Authorization':'Bearer '+'1'*40,'Idempotency-Key':'extract-test'}
        self.other={'Authorization':'Bearer '+'2'*40}

    def tearDown(self):self.tmp.cleanup()
    def upload(self,client):
        md=client.post('/v1/materials?filename=note.md',headers=dict(self.auth,**{'Content-Type':'text/markdown'}),
            content=Path('data/examples/trip-note-001.md').read_bytes()).json()['material_id']
        csv=client.post('/v1/materials?filename=items.csv',headers=dict(self.auth,**{'Content-Type':'text/csv'}),
            content=Path('data/examples/expense-items-001.csv').read_bytes()).json()['material_id']
        return dict(narrative_material_id=md,csv_material_id=csv)
    def wait(self,client,id):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            result=client.get('/v1/extractions/'+id,headers=self.auth).json()
            if result['status'] not in ('pending','running'):return result
            time.sleep(.01)
        self.fail('Fixture extraction unfinished')

    def test_validated_extraction_is_owned_deduplicated_and_used_server_side(self):
        fixture=ExtractFixture()
        with TestClient(create_app(self.path,self.users,fixture)) as client:
            source=self.upload(client)
            response=client.post('/v1/extractions',json=source,headers=self.auth)
            self.assertEqual(response.status_code,202);id=response.json()['extraction_id']
            result=self.wait(client,id);self.assertEqual(result['result']['validation']['status'],'validated')
            self.assertEqual(client.post('/v1/extractions',json=source,headers=self.auth).json()['extraction_id'],id)
            self.assertEqual(fixture.calls,1)
            self.assertEqual(client.get('/v1/extractions/'+id,headers=self.other).status_code,404)
            bad=client.post('/v1/applications/from-extraction',json=dict(extraction_id=id,total_amount='0.00'),headers=self.auth)
            self.assertEqual(bad.status_code,422)
            application=client.post('/v1/applications/from-extraction',json=dict(extraction_id=id),headers=self.auth)
            self.assertEqual(application.status_code,201)
            self.assertEqual(application.json()['extraction_id'],id)
            self.assertEqual(len(application.json()['materials']),2)
            self.assertEqual(application.json()['application']['total_amount'],'120.00')

    def test_missing_evidence_does_not_create_application(self):
        with TestClient(create_app(self.path,self.users,ExtractFixture(missing=True))) as client:
            source=self.upload(client)
            id=client.post('/v1/extractions',json=source,headers=self.auth).json()['extraction_id']
            self.assertEqual(self.wait(client,id)['result']['validation']['status'],'needs_materials')
            self.assertEqual(client.post('/v1/applications/from-extraction',json=dict(extraction_id=id),headers=self.auth).status_code,422)
            self.assertEqual(client.post('/v1/applications/from-material',json=dict(material_id=source['narrative_material_id'],total_amount='120.00'),headers=self.auth).status_code,422)

    def test_interrupted_extraction_is_not_reclaimed(self):
        store=ApplicationStore(self.path)
        # Repository recovery test uses explicit source fixtures, not a real model call.
        source=dict(sha256='a',parser_version='test',status='parsed')
        a,_=store.save_material('DEMO-001','a',b'a',source)
        source=dict(source,sha256='b');b,_=store.save_material('DEMO-001','b',b'b',source)
        id,_=store.enqueue_extraction('DEMO-001',a,b,EXTRACTOR_VERSION)
        store.claim_extraction(id);store.recover()
        self.assertEqual(store.extraction(id,'DEMO-001')['status'],'indeterminate')
        self.assertIsNone(store.claim_extraction(id))
