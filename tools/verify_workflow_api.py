"""Real published Workflow API acceptance; no model, no mock or automatic retries."""
import copy
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.workflow_client import WorkflowClient, WorkflowCallError

ROOT = Path(__file__).resolve().parents[1]


def main():
    config=json.loads((ROOT/'.local/precheck-app-api.json').read_text(encoding='utf-8'))
    sample=json.loads((ROOT/'data/examples/expense-001.json').read_text(encoding='utf-8'))
    client=WorkflowClient(config['api_key'],config['api_base'])
    cases=[]
    target=ROOT/'.local/evaluations'/('workflow-api-live-'+str(time.time_ns())+'.json')
    def check(name, application, expected, selected_client=client, expected_http=None):
        try:
            result=selected_client.run(application)
            assert result['report']['status']==expected, name
            entry=dict(case=name,outcome='succeeded',http_status=200,**result)
        except WorkflowCallError as exc:
            entry=dict(case=name,outcome=exc.kind,http_status=exc.http_status,workflow_run_id=exc.workflow_run_id)
            assert exc.kind==expected,(name,exc.kind)
            if expected_http is not None: assert exc.http_status==expected_http,(name,exc.http_status)
        cases.append(entry)
        target.write_text(json.dumps(dict(mode='live_published_workflow_api',cases=cases),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(name,entry['outcome'])
    check('same-day-60-plus-60',sample,'needs_manual_review')
    first=cases[-1]['report']
    assert first['findings'][0]['facts']=={'expense_date':'2026-08-01','actual':'120.00','limit':'100.00'}
    clean=copy.deepcopy(sample);clean['expense_items']=clean['expense_items'][:1];clean['total_amount']='60.00'
    check('no-rule-issues',clean,'no_issues_found')
    missing=copy.deepcopy(clean);missing['expense_items'][0]['receipt_present']=False
    check('missing-receipt',missing,'needs_materials')
    v1=copy.deepcopy(sample);v1.update(trip_start_date='2026-06-01',trip_end_date='2026-06-02',submitted_date='2026-06-22')
    for item in v1['expense_items']: item['expense_date']='2026-06-01'
    check('v1-meal-limit',v1,'needs_manual_review')
    assert cases[-1]['report']['policy_version']=='v1'
    assert cases[-1]['report']['findings'][0]['facts']['limit']=='80.00'
    bad=copy.deepcopy(sample);bad['total_amount']=120.0
    check('float-money',bad,'workflow_failed',expected_http=200)
    other=copy.deepcopy(sample);other['employee_id']='DEMO-OTHER'
    check('other-employee',other,'workflow_failed',expected_http=200)
    check('invalid-app-credential',sample,'http_error',WorkflowClient('invalid-test'),401)
    print('Passed',len(cases),'real published API cases; saved',target)


if __name__=='__main__': main()
