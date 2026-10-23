"""Prospective evaluation gates and explicit metrics. No automatic semantic judge."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKS=('pilot-v1','reserve-v1')


class EvaluationGate(ValueError):pass


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def load_pack(name,root=ROOT):
    if name not in PACKS:raise EvaluationGate('Unknown evaluation pack')
    folder=root/'data/eval'/name
    qa=read(folder/'qa.inputs.json');materials=read(folder/'materials.inputs.json');gold=read(folder/'gold.json')
    cases=qa+materials;ids=[c['id'] for c in cases]
    if len(ids)!=len(set(ids)) or set(ids)!=set(gold):raise EvaluationGate('Case IDs and labels must match exactly')
    if any(not c.get('scenario_group') or c.get('source_kind')!='original_synthetic' for c in cases):
        raise EvaluationGate('Case provenance required')
    return dict(name=name,folder=folder,qa=qa,materials=materials,gold=gold)


def snapshot(root,paths):return {str(p):digest(root/p) for p in sorted(paths)}


def verify_snapshot(root,hashes):
    for path,expected in hashes.items():
        relative=Path(path)
        if relative.is_absolute() or '..' in relative.parts:raise EvaluationGate('Snapshot path outside workspace')
        if not (root/relative).is_file() or digest(root/relative)!=expected:raise EvaluationGate('Frozen file changed: '+path)


def assert_frozen(pack,root=ROOT):
    path=pack['folder']/'manifest.json'
    if not path.exists():raise EvaluationGate('Freeze the pack and system before evaluation')
    manifest=read(path)
    if manifest['pack']!=pack['name']:raise EvaluationGate('Pack identity mismatch')
    verify_snapshot(root,manifest['files'])
    return manifest


def label_digest(pack,id):
    body={'input':next(c for c in pack['qa']+pack['materials'] if c['id']==id),'gold':pack['gold'][id]}
    return hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def require_human_reviews(pack,ids,root=ROOT):
    reviews=read(pack['folder']/'human-reviews.json')['reviews']
    missing=[]
    for id in ids:
        matches=[r for r in reviews if r.get('id')==id]
        if len(matches)!=1:missing.append(id);continue
        record=matches[0]
        if (record.get('decision')!='approved' or record.get('source')!='human_user' or
                record.get('label_sha256')!=label_digest(pack,id) or not record.get('reviewer') or
                not record.get('evidence_file') or not record.get('reviewed_at')):missing.append(id)
        elif not str(record['evidence_file']).startswith('.local/') or not (root/record['evidence_file']).is_file():missing.append(id)
        elif record.get('evidence_sha256')!=digest(root/record['evidence_file']):missing.append(id)
    if missing:raise EvaluationGate('Human label review pending: '+','.join(missing))


def finding_units(findings):
    return Counter((f['code'],tuple(sorted(f['item_ids'])),tuple(sorted(f['clause_ids']))) for f in findings)


def compare_findings(actual,expected):
    a,b=finding_units(actual),finding_units(expected)
    return dict(tp=sum((a&b).values()),fp=sum((a-b).values()),fn=sum((b-a).values()),exact=a==b)


def score_material(record,expected):
    if record.get('execution')!='completed':
        return dict(case_pass=False,execution_error=True,findings=compare_findings([],expected.get('findings',[])))
    validation=record['extraction']['result']['validation']
    codes={i['code'] for i in validation['issues']}
    gate=(validation['status']==expected['validation_status'] and set(expected['required_issue_codes'])<=codes)
    created=record.get('application') is not None
    if not expected['application_created']:
        return dict(case_pass=gate and not created and record.get('creation_http_status')==422,
                    execution_error=False,findings=compare_findings([],[]),semantic_field_accuracy=None)
    report=record.get('precheck',{}).get('result') or {}
    report=report.get('report',{})
    compared=compare_findings(report.get('findings',[]),expected['findings'])
    correct=(record.get('precheck',{}).get('status')=='completed' and report.get('is_precheck') is True and
        report.get('policy_version')==expected['policy_version'] and report.get('status')==expected['report_status'] and
        report.get('facts',{}).get('item_sum')==expected['item_sum'] and compared['exact'])
    return dict(case_pass=gate and created and correct,execution_error=False,findings=compared,semantic_field_accuracy=None)


def summarize(rows,requested):
    tp=sum(r['score']['findings']['tp'] for r in rows);fp=sum(r['score']['findings']['fp'] for r in rows);fn=sum(r['score']['findings']['fn'] for r in rows)
    passed=sum(r['score']['case_pass'] for r in rows)
    return dict(requested=requested,observed=len(rows),passed=passed,case_pass_fraction=passed/requested if requested else None,
        missing_or_not_run=requested-len(rows),execution_errors=sum(r['score']['execution_error'] for r in rows),
        finding_tp=tp,finding_fp=fp,finding_fn=fn,finding_precision=tp/(tp+fp) if tp+fp else None,
        finding_recall=tp/(tp+fn) if tp+fn else None,semantic_field_accuracy=None,
        notice='Case pass uses fixed provisional/reviewed labels; not real-business accuracy. Undefined precision/recall stays null.')
