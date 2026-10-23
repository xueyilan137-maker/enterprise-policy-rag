"""Server-side adapter for this project's local Dify precheck workflow."""
import json
from dataclasses import dataclass, field

import httpx
from pydantic import ValidationError
from src.rules_api import Report


class WorkflowCallError(RuntimeError):
    def __init__(self, kind, http_status=None, workflow_run_id=None):
        self.kind = kind
        self.http_status = http_status
        self.workflow_run_id = workflow_run_id
        super().__init__(kind)  # No raw upstream body, input, or credential in errors.


def parse_result(body):
    if not isinstance(body, dict) or not isinstance(body.get('data'), dict):
        raise WorkflowCallError('invalid_response')
    data = body['data']
    run_id = body.get('workflow_run_id')
    if not isinstance(run_id, str) or not run_id or data.get('id') != run_id:
        raise WorkflowCallError('invalid_run_id')
    if data.get('status') != 'succeeded':
        raise WorkflowCallError('workflow_'+str(data.get('status')), 200, run_id)
    try:
        outputs = data['outputs']
        report = Report.model_validate(json.loads(outputs['report_json']))
        if outputs['status'] != report.status or outputs['request_id'] != report.request_id:
            raise ValueError('Mismatched outputs')
    except (KeyError, TypeError, ValueError, ValidationError):
        raise WorkflowCallError('invalid_report', 200, run_id) from None
    return {'workflow_run_id': run_id, 'report': report.model_dump()}


@dataclass
class WorkflowClient:
    api_key: str = field(repr=False)
    api_base: str = 'http://127.0.0.1:18080/v1'

    def run(self, application, *, transport=None):
        body=self.call({'application_json':json.dumps(application,ensure_ascii=False)},transport=transport)
        return parse_result(body)

    def extract(self,text,*,transport=None):
        body=self.call({'application_json':'{}','action':'extract','extraction_text':text},transport=transport,timeout=90)
        data=body.get('data',{}) if isinstance(body,dict) else {}
        run_id=body.get('workflow_run_id') if isinstance(body,dict) else None
        if not isinstance(data,dict):raise WorkflowCallError('invalid_response',200)
        if not isinstance(run_id,str) or not run_id or data.get('id')!=run_id:raise WorkflowCallError('invalid_run_id')
        if data.get('status')!='succeeded':raise WorkflowCallError('workflow_'+str(data.get('status')),200,run_id)
        outputs=data.get('outputs')
        raw=outputs.get('model_json') if isinstance(outputs,dict) else None
        if not isinstance(raw,str):raise WorkflowCallError('invalid_response',200,run_id)
        return dict(workflow_run_id=run_id,raw_model=raw,total_tokens=data.get('total_tokens'),elapsed_time=data.get('elapsed_time'))

    def call(self, inputs, *, transport=None, timeout=30):
        # Limit credentials to the authorized local deployment. No redirects or retries.
        if self.api_base != 'http://127.0.0.1:18080/v1':
            raise ValueError('Only the configured local Dify deployment is supported')
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout, connect=5), trust_env=False,
                              follow_redirects=False, transport=transport) as client:
                response = client.post(self.api_base+'/workflows/run',
                    headers={'Authorization': 'Bearer '+self.api_key},
                    json={'inputs': inputs,
                          'response_mode': 'blocking', 'user': 'policy-demo-backend-DEMO-001'})
        except httpx.TimeoutException:
            raise WorkflowCallError('upstream_timeout') from None
        except httpx.RequestError:
            raise WorkflowCallError('upstream_unavailable') from None
        if response.status_code != 200:
            raise WorkflowCallError('http_error', response.status_code)
        try:
            body = response.json()
        except ValueError:
            raise WorkflowCallError('invalid_response', 200) from None
        return body
