import json
import unittest
from src.precheck_workflow import response_gate
from tools.build_precheck_workflow import build


class PrecheckWorkflowTests(unittest.TestCase):
    def test_http_and_invalid_responses_fail(self):
        for status in (401,403,422,429,500):
            with self.assertRaises(ValueError): response_gate(status,'{}')
        for body in ('not-json','{}','{"status":"approved","is_precheck":true}'):
            with self.assertRaises(ValueError): response_gate(200,body)

    def test_preserves_business_status_and_report(self):
        report=dict(status='needs_manual_review',is_precheck=True,request_id='real-request',findings=[{'code':'MEAL_DAILY_OVER_LIMIT'}])
        result=response_gate(200,json.dumps(report))
        self.assertEqual(json.loads(result['report_json']),report)
        report['approved_amount']='100.00'
        with self.assertRaises(ValueError): response_gate(200,json.dumps(report))

    def test_public_dsl_has_no_token_or_local_url_and_embeds_gate(self):
        dsl=build()
        self.assertEqual(dsl['workflow']['environment_variables'][1]['value'],'')
        self.assertNotIn('http://policy-rules',json.dumps(dsl))
        gate=dsl['workflow']['graph']['nodes'][2]['data']
        scope={};exec(gate['code'],scope)
        with self.assertRaises(ValueError): scope['main'](401,'{}')
