"""Live Dify retrieval measurement, no answer-generation or mock fallback.

Credentials come from process environment only. Result files contain no auth headers.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.policy_data import ROOT, load_policy, select_version
from src.retrieval_query import retrieval_query


def score_records(records, expected, version, top_k):
    if not isinstance(records, list):
        raise ValueError('Dify response records must be a list')
    found = set()
    foreign = set()
    for record in records[:top_k]:
        text = record.get('segment', {}).get('content')
        if not isinstance(text, str):
            raise ValueError('Missing segment.content; response schema must be checked')
        ids = set(re.findall(r'\bTRAVEL-v\d+-[A-Z]+\b', text))
        found.update(ids)
        foreign.update(c for c in ids if not c.startswith(f'TRAVEL-{version}-'))
    if not expected:
        raise ValueError('Recall requires nonempty gold clause IDs')
    return {'clause_recall_at_k': len(found & set(expected))/len(set(expected)),
            'retrieved_clause_ids': sorted(found), 'foreign_version_ids': sorted(foreign)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--top-k', type=int, default=3)
    parser.add_argument('--cases', type=Path, default=ROOT/'data/eval/dev.jsonl', help='Explicit development cases; never select a holdout for tuning')
    parser.add_argument('--query-variant', choices=('original', 'city-hint'), default='original',
                        help='Single-factor experiment: append a city classification hint for lodging questions')
    parser.add_argument('--limit', type=int, default=3, help='Bounded smoke run; 3 live requests by default')
    parser.add_argument('--min-interval', type=float, default=7.0, help='Respect Cloud Sandbox knowledge rate limits')
    args = parser.parse_args()
    if not 1 <= args.top_k <= 10 or not 1 <= args.limit <= 20 or args.min_interval < 0:
        parser.error('Invalid limits')
    base = os.environ.get('DIFY_API_BASE', '').rstrip('/')
    key = os.environ.get('DIFY_DATASET_API_KEY', '')
    if not base or not key:
        parser.error('Set DIFY_API_BASE and DIFY_DATASET_API_KEY; do not use a model-provider key')
    parsed = urlparse(base)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error('Base URL must not contain credentials/query/fragment')
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')):
        parser.error('Use HTTPS for remote endpoints')
    p = load_policy()
    case_bytes = args.cases.read_bytes()
    cases = [json.loads(s) for s in case_bytes.decode('utf-8').splitlines()]
    cases = [c for c in cases if c['action'] == 'retrieve'][:args.limit]
    dataset_map = {}
    for c in cases:
        version = select_version(p, c['trip_start_date'])['version']
        dataset = os.environ.get('DIFY_DATASET_'+version.upper(), '')
        if not re.fullmatch(r'[a-zA-Z0-9-]+', dataset):
            parser.error(f'Set DIFY_DATASET_{version.upper()} to a version-isolated knowledge base ID')
        dataset_map[version] = dataset
    if len(dataset_map) > 1 and len(set(dataset_map.values())) != len(dataset_map):
        parser.error('Baseline requires distinct knowledge bases for different policy versions')
    rows = []
    for i, c in enumerate(cases):
        if i:
            time.sleep(args.min_interval)
        version = select_version(p, c['trip_start_date'])['version']
        query = retrieval_query(c['query'], args.query_variant)
        payload = {'query': query, 'retrieval_model': {
            'search_method': 'semantic_search', 'reranking_enable': False,
            'top_k': args.top_k, 'score_threshold_enabled': False}}
        request = Request(f'{base}/datasets/{dataset_map[version]}/retrieve',
            data=json.dumps(payload).encode('utf-8'), method='POST',
            headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'})
        started = time.monotonic()
        row = {'id': c['id'], 'version': version, 'status': 'error', 'query': c['query'], 'retrieval_query': query}
        try:
            with urlopen(request, timeout=30) as response:
                body = json.load(response)
            row.update(score_records(body['records'], c['expected_clause_ids'], version, args.top_k))
            row['status'] = 'version_leak' if row['foreign_version_ids'] else 'ok'
        except HTTPError as exc:
            row['error'] = f'HTTP {exc.code}'
        except (URLError, TimeoutError, ValueError, KeyError, TypeError, AttributeError) as exc:
            row['error'] = type(exc).__name__
        row['latency_seconds'] = round(time.monotonic()-started, 3)
        rows.append(row)
    good = [r for r in rows if r['status'] == 'ok']
    report = {'mode': 'live_dify_retrieval', 'scope': 'dev retrieval cases only; not answer quality',
        'review_status': sorted({c.get('review_status', 'unknown') for c in cases}), 'top_k': args.top_k,
        'cases_sha256': hashlib.sha256(case_bytes).hexdigest(),
        'policy_sha256': hashlib.sha256((ROOT/'data/policies/travel.json').read_bytes()).hexdigest(),
        'dataset_ids': dataset_map,
        'retrieval_model': {'search_method': 'semantic_search', 'reranking_enable': False,
                            'score_threshold_enabled': False, 'top_k': args.top_k},
        'query_variant': args.query_variant,
        'requested': len(rows), 'successful': len(good), 'failed': len(rows)-len(good),
        'mean_clause_recall_on_success': sum(r['clause_recall_at_k'] for r in good)/len(good) if good else None,
        'rows': rows}
    folder = ROOT/'.local/evaluations'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/f'retrieval-{time.time_ns()}.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'report': str(path), 'requested': len(rows), 'successful': len(good), 'failed': len(rows)-len(good)}))
    return 0 if len(good) == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
