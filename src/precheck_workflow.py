"""Response gate embedded in Dify; failures never become business approvals."""
import json


def response_gate(status_code, body):
    if status_code != 200:
        raise ValueError('Rules API failed with HTTP '+str(status_code))
    result = json.loads(body)
    if not isinstance(result, dict) or result.get('is_precheck') is not True:
        raise ValueError('Invalid precheck response')
    if result.get('status') not in ('needs_manual_review', 'needs_materials', 'no_issues_found'):
        raise ValueError('Invalid precheck status')
    if not isinstance(result.get('findings'), list) or not isinstance(result.get('request_id'), str):
        raise ValueError('Incomplete precheck response')
    if 'approved_amount' in result:
        raise ValueError('Unexpected settlement field')
    return {'report_json': json.dumps(result, ensure_ascii=False), 'status': result['status'], 'request_id': result['request_id']}
