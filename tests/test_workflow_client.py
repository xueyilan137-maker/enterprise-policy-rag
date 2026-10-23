import json
import unittest
from pathlib import Path
import httpx
from src.expense_rules import precheck
from src.workflow_client import WorkflowClient, WorkflowCallError, parse_result


class WorkflowClientTests(unittest.TestCase):
    def test_extract_checks_envelope_and_returns_raw_candidate_for_server_validation(self):
        client=WorkflowClient('test-secret')
        for body in ({'data':None},{'workflow_run_id':'r','data':{'id':'r','status':'succeeded','outputs':None}}):
            with self.assertRaises(WorkflowCallError):
                client.extract('source',transport=httpx.MockTransport(lambda request:httpx.Response(200,json=body)))
        body=dict(workflow_run_id='r',data=dict(id='r',status='succeeded',outputs={'model_json':'raw candidate'}))
        result=client.extract('source',transport=httpx.MockTransport(lambda request:httpx.Response(200,json=body)))
        self.assertEqual(result['raw_model'],'raw candidate')

    def response(self):
        report=precheck(json.loads(Path('data/examples/expense-001.json').read_text(encoding='utf-8')))
        report['request_id']='request-1'
        return dict(workflow_run_id='run-1',data=dict(id='run-1',status='succeeded',outputs=dict(
            report_json=json.dumps(report),status=report['status'],request_id='request-1')))

    def test_valid_report_and_two_distinct_identifiers(self):
        result=parse_result(self.response())
        self.assertEqual(result['workflow_run_id'],'run-1')
        self.assertEqual(result['report']['request_id'],'request-1')

    def test_http_200_failed_is_not_business_success(self):
        body=self.response();body['data']['status']='failed'
        with self.assertRaises(WorkflowCallError) as caught: parse_result(body)
        self.assertEqual(caught.exception.kind,'workflow_failed')

    def test_malformed_and_inconsistent_outputs_fail(self):
        for mutation in ('run','report','status'):
            body=self.response()
            if mutation=='run': body['workflow_run_id']='other'
            elif mutation=='report': body['data']['outputs']['report_json']='{}'
            else: body['data']['outputs']['status']='no_issues_found'
            with self.assertRaises(WorkflowCallError): parse_result(body)

    def test_credential_errors_and_timeout_are_sanitized(self):
        def forbidden(request): return httpx.Response(401,json={'detail':'sensitive upstream body'})
        client=WorkflowClient('test-secret')
        self.assertNotIn('test-secret',repr(client))
        with self.assertRaises(WorkflowCallError) as caught:
            client.run({},transport=httpx.MockTransport(forbidden))
        self.assertEqual(caught.exception.http_status,401)
        self.assertNotIn('sensitive',str(caught.exception))
        def timeout(request): raise httpx.ReadTimeout('sensitive error')
        with self.assertRaises(WorkflowCallError) as caught:
            client.run({},transport=httpx.MockTransport(timeout))
        self.assertEqual(caught.exception.kind,'upstream_timeout')
