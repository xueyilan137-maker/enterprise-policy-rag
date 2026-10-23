"""Real local HTTP acceptance, private synthetic results, no credential output."""
import copy
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]


def main():
    token=(ROOT/'.local/rules.env').read_text(encoding='utf-8').strip().removeprefix('RULES_API_TOKEN=')
    sample=json.loads((ROOT/'data/examples/expense-001.json').read_text(encoding='utf-8'))
    cases=[]
    def add(name, mutate, expected_http, expected_status=None, credential=token):
        case=copy.deepcopy(sample);mutate(case)
        request=Request('http://127.0.0.1:18081/v1/prechecks',data=json.dumps(case).encode('utf-8'),
            headers={'Content-Type':'application/json','Authorization':'Bearer '+credential})
        try:
            with build_opener(ProxyHandler({})).open(request,timeout=10) as response:
                status,body=response.status,json.load(response)
        except HTTPError as exc:
            status,body=exc.code,json.load(exc)
        assert status==expected_http,(name,status)
        if expected_status: assert body['status']==expected_status,(name,body['status'])
        cases.append(dict(case=name,http_status=status,response=body))
    add('same-day-60-plus-60',lambda c:None,200,'needs_manual_review')
    def missing(c):
        c['expense_items']=c['expense_items'][:1];c['total_amount']='60.00';c['expense_items'][0]['receipt_present']=False
    add('missing-receipt',missing,200,'needs_materials')
    def clean(c):
        c['expense_items']=c['expense_items'][:1];c['total_amount']='60.00'
    add('no-rule-issues',clean,200,'no_issues_found')
    add('float-money-rejected',lambda c:c.update(total_amount=120.0),422)
    add('wrong-credential',lambda c:None,401,credential='invalid-test')
    add('other-employee',lambda c:c.update(employee_id='DEMO-OTHER'),403)
    add('client-history-rejected',lambda c:c.update(previous_receipt_ids=[]),422)
    target=ROOT/'.local/evaluations/rules-api-live-001.json'
    target.write_text(json.dumps(dict(mode='live_http',cases=cases),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Passed',len(cases),'real HTTP cases; saved',target)


if __name__=='__main__': main()
