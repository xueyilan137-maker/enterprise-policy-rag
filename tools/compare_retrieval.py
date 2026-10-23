"""Compare matched retrieval runs without hiding per-case regressions or errors."""
import argparse
import json
from pathlib import Path


def compare(baseline, candidate):
    for field in ('cases_sha256', 'policy_sha256', 'dataset_ids', 'retrieval_model', 'top_k'):
        if field not in baseline or baseline[field] != candidate.get(field):
            raise ValueError('Unmatched experiment field: ' + field)
    if baseline.get('query_variant') != 'original':
        raise ValueError('Baseline must use original queries')
    left = {row['id']: row for row in baseline['rows']}
    right = {row['id']: row for row in candidate['rows']}
    if not left or left.keys() != right.keys() or len(left) != len(baseline['rows']) or len(right) != len(candidate['rows']):
        raise ValueError('Case IDs must be identical, unique and nonempty')
    rows = []
    for id, old in left.items():
        new = right[id]
        if old['version'] != new['version'] or old['query'] != new['query']:
            raise ValueError('Case input differs: ' + id)
        if old['status'] != 'ok' or new['status'] != 'ok':
            outcome = 'invalid'
        elif old.get('foreign_version_ids') or new.get('foreign_version_ids'):
            outcome = 'invalid'
        else:
            delta = new['clause_recall_at_k'] - old['clause_recall_at_k']
            outcome = 'improved' if delta > 0 else 'regressed' if delta < 0 else 'unchanged'
        rows.append(dict(id=id, outcome=outcome,
            baseline_recall=old.get('clause_recall_at_k'), candidate_recall=new.get('clause_recall_at_k'),
            baseline_clauses=old.get('retrieved_clause_ids'), candidate_clauses=new.get('retrieved_clause_ids')))
    counts = {kind: sum(r['outcome'] == kind for r in rows) for kind in ('improved', 'regressed', 'unchanged', 'invalid')}
    return dict(scope='development retrieval comparison; not answer quality or human review',
        query_variant=candidate['query_variant'], cases_sha256=baseline['cases_sha256'], counts=counts,
        regression_gate_passed=counts['regressed'] == 0 and counts['invalid'] == 0,
        baseline_mean=baseline['mean_clause_recall_on_success'], candidate_mean=candidate['mean_clause_recall_on_success'], rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compare(json.loads(args.baseline.read_text(encoding='utf-8')), json.loads(args.candidate.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'report': str(args.output), 'counts': result['counts'], 'regression_gate_passed': result['regression_gate_passed']}))
