"""Live paired development experiment: primary Recall@3 vs bounded merged coverage (<=4)."""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.policy_data import ROOT, load_policy, select_version
from src.retrieval_query import retrieval_query
from src.related_evidence import review_plan, merge_review
from tools.evaluate_retrieval import score_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=ROOT/'data/eval/dev.source-reviewed.jsonl')
    parser.add_argument('--limit', type=int, default=9)
    parser.add_argument('--min-interval', type=float, default=7)
    args = parser.parse_args()
    if not 1 <= args.limit <= 20 or args.min_interval < 0:
        parser.error('Invalid limits')
    base = os.environ.get('DIFY_API_BASE', '').rstrip('/')
    key = os.environ.get('DIFY_DATASET_API_KEY', '')
    parsed = urlparse(base)
    if not key or parsed.username or parsed.password or parsed.query or parsed.fragment or not (
        parsed.scheme == 'https' or parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')):
        parser.error('Provide dataset credentials with HTTPS or local HTTP; no URL credentials')
    raw = args.cases.read_bytes()
    cases = [json.loads(line) for line in raw.decode('utf-8').splitlines()]
    cases = [c for c in cases if c['action'] == 'retrieve'][:args.limit]
    policy = load_policy()
    datasets = {v: os.environ.get('DIFY_DATASET_'+v.upper(), '') for v in ('v1', 'v2')}
    if any(not value for value in datasets.values()) or len(set(datasets.values())) != len(datasets):
        parser.error('Provide distinct version-isolated dataset IDs')
    rows, request_count = [], 0
    last_call = None

    def retrieve(version, query, top_k):
        nonlocal last_call, request_count
        if last_call is not None:
            time.sleep(max(0, args.min_interval - (time.monotonic() - last_call)))
        last_call = time.monotonic()
        request_count += 1
        payload = dict(query=query, retrieval_model=dict(search_method='semantic_search',
            reranking_enable=False, top_k=top_k, score_threshold_enabled=False))
        request = Request(base+'/datasets/'+datasets[version]+'/retrieve', data=json.dumps(payload).encode(),
            headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'})
        with urlopen(request, timeout=45) as response:
            records = json.load(response)['records']
        # Validate the API schema and all returned evidence, including supplemental.
        score_records(records, ['TRAVEL-'+version+'-REVIEW'], version, top_k)
        return records[:top_k]

    for case in cases:
        version = select_version(policy, case['trip_start_date'])['version']
        row = dict(id=case['id'], version=version, query=case['query'], status='error', supplemental_requests=0)
        try:
            query = retrieval_query(case['query'], 'city-hint')
            primary = retrieve(version, query, 3)
            row['primary'] = score_records(primary, case['expected_clause_ids'], version, 3)
            normalized = [dict(content=r['segment']['content']) for r in primary]
            plan = review_plan(case['query'], normalized, version)
            merged = normalized
            if plan['needed'] == 'yes':
                row['supplemental_requests'] = 1
                row['supplemental_query'] = plan['query']
                extra = retrieve(version, plan['query'], 1)
                row['supplemental_records'] = extra
                merged = merge_review(normalized, [dict(content=r['segment']['content']) for r in extra], version)['result']
            context = score_records([dict(segment=dict(content=r['content'])) for r in merged], case['expected_clause_ids'], version, 4)
            row.update(context=context, context_count=len(merged), primary_records=primary,
                retrieval_query=query, status='ok' if not context['foreign_version_ids'] else 'version_leak')
        except HTTPError as exc:
            row['error'] = 'HTTP '+str(exc.code)
        except (URLError, TimeoutError, ValueError, KeyError, TypeError, AttributeError) as exc:
            row['error'] = type(exc).__name__
        rows.append(row)
    good = [r for r in rows if r['status'] == 'ok']
    report = dict(mode='live_paired_related_evidence', scope='development only; not answer quality',
        cases_sha256=hashlib.sha256(raw).hexdigest(), policy_sha256=hashlib.sha256((ROOT/'data/policies/travel.json').read_bytes()).hexdigest(),
        review_status=sorted({c['review_status'] for c in cases}), dataset_ids=datasets,
        primary_query_variant='city-hint', primary_top_k=3, supplemental_top_k=1, max_context_records=4,
        supplemental_query='预审与人工复核', reranking_enable=False, score_threshold_enabled=False,
        requested_cases=len(rows), successful_cases=len(good), failed_cases=len(rows)-len(good), http_requests=request_count,
        mean_primary_recall_at_3=sum(r['primary']['clause_recall_at_k'] for r in good)/len(good) if good else None,
        mean_merged_evidence_coverage=sum(r['context']['clause_recall_at_k'] for r in good)/len(good) if good else None,
        regressions=[r['id'] for r in good if r['context']['clause_recall_at_k'] < r['primary']['clause_recall_at_k']], rows=rows)
    target = ROOT/'.local/evaluations'/('related-'+str(time.time_ns())+'.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('successful_cases', 'failed_cases', 'http_requests', 'mean_primary_recall_at_3', 'mean_merged_evidence_coverage', 'regressions')}))
    print('Report:', target)
    return 0 if len(good) == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
