"""Two real development retrieval calls; never reruns the reserve ledger."""
import json
import re
import sys
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.intent_query import intent_query


def main():
    config = json.loads((ROOT/'.local/dataset-api.json').read_text(encoding='utf-8'))
    knowledge = json.loads((ROOT/'.local/knowledge-state.json').read_text(encoding='utf-8'))
    target = ROOT/'.local/evaluations'/('post-eval-intent-retrieval-'+str(time.time_ns())+'.json')
    query = intent_query('商务舱缺批准但住宿合规，能认定申请通过吗？')
    report = dict(split='post-evaluation development', query=query, rows=[])
    with target.open('x', encoding='utf-8') as out:
        json.dump(report, out)
    with httpx.Client(trust_env=False, timeout=45, headers={'Authorization':'Bearer '+config['DIFY_DATASET_API_KEY']}) as client:
        for version in ('v1', 'v2'):
            response = client.post('http://127.0.0.1:18080/v1/datasets/'+knowledge['versions'][version]['dataset_id']+'/retrieve',
                json=dict(query=query, retrieval_model=dict(search_method='semantic_search', reranking_enable=False,
                    top_k=3, score_threshold_enabled=False)))
            response.raise_for_status()
            records = response.json()['records']
            ids = sorted(set(re.findall(r'TRAVEL-v\d+-[A-Z]+', ' '.join(r['segment']['content'] for r in records))))
            report['rows'].append(dict(version=version, ids=ids, records=records))
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            print(version, ids, flush=True)
            if version == 'v1':
                time.sleep(7)
    print('Saved', target)


if __name__ == '__main__':
    main()
