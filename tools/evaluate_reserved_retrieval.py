"""Gated, frozen retrieval diagnostics for reviewed QA labels, separate from published Chatflow answer quality."""
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import httpx
from src.evaluation import EvaluationGate,load_pack,assert_frozen,require_human_reviews,read
from src.chatflow_nodes import route
from src.policy_data import load_policy
from src.retrieval_query import retrieval_query
from src.related_evidence import review_plan,merge_review
from tools.evaluate_retrieval import score_records


def main():
    pack=load_pack('reserve-v1');manifest=assert_frozen(pack)
    require_human_reviews(pack,[c['id'] for c in pack['qa']])
    config=read(ROOT/'.local/dataset-api.json');knowledge=read(ROOT/'.local/knowledge-state.json')
    if config['DIFY_API_BASE'].rstrip('/')!='http://127.0.0.1:18080/v1':raise EvaluationGate('Only current localhost deployment allowed')
    datasets={v:knowledge['versions'][v]['dataset_id'] for v in ('v1','v2')}
    if len(set(datasets.values()))!=2:raise EvaluationGate('Version-isolated datasets required')
    folder=ROOT/'.local/eval-ledger/reserve-v1';folder.mkdir(parents=True,exist_ok=True)
    target=ROOT/'.local/evaluations'/('reserve-retrieval-'+str(time.time_ns())+'.json')
    marker=folder/'retrieval-started.json'
    try:
        with marker.open('x',encoding='utf-8') as file:json.dump({'report':str(target.relative_to(ROOT))},file)
    except FileExistsError:raise EvaluationGate('Reserve retrieval already started; preserve first-pass evidence') from None
    report=dict(scope='live retrieval diagnostic using frozen code routing; not a published Chatflow answer run',manifest=manifest,
        rows=[],dataset_ids=datasets,primary_top_k=3,max_merged_context=4,rerank=False,query_variant='city-hint')
    last_call=None;requests=0
    with httpx.Client(base_url='http://127.0.0.1:18080',headers={'Authorization':'Bearer '+config['DIFY_DATASET_API_KEY']},
                      trust_env=False,follow_redirects=False,timeout=45) as client:
        def retrieve(version,query,k):
            nonlocal last_call,requests
            if last_call is not None:time.sleep(max(0,7-(time.monotonic()-last_call)))
            last_call=time.monotonic();requests+=1
            response=client.post('/v1/datasets/'+datasets[version]+'/retrieve',json=dict(query=query,retrieval_model=dict(
                search_method='semantic_search',reranking_enable=False,top_k=k,score_threshold_enabled=False)))
            if response.status_code!=200:raise EvaluationGate('HTTP '+str(response.status_code))
            records=response.json()['records'];score_records(records,['TRAVEL-'+version+'-REVIEW'],version,k)
            return records[:k]
        for case in pack['qa']:
            row=dict(id=case['id'],status='error');started=time.monotonic()
            try:
                pending='';r=None
                for question in case['turns']:
                    r=route(question,pending,load_policy()['versions']);pending=r['pending']
                if not r['version']:raise EvaluationGate('No unique route after frozen final turn')
                version=r['version'];gold=pack['gold'][case['id']]['clause_ids'];query=retrieval_query(r['question'],'city-hint')
                primary=retrieve(version,query,3);normalized=[{'content':p['segment']['content']} for p in primary]
                plan=review_plan(r['question'],normalized,version);merged=normalized
                if plan['needed']=='yes':
                    extra=retrieve(version,plan['query'],1)
                    merged=merge_review(normalized,[{'content':p['segment']['content']} for p in extra],version)['result']
                row.update(primary=score_records(primary,gold,version,3),
                    merged=score_records([{'segment':{'content':p['content']}} for p in merged],gold,version,4),
                    primary_records=primary,merged_records=merged,version=version,query=query,context_count=len(merged))
                row['status']='version_leak' if row['primary']['foreign_version_ids'] or row['merged']['foreign_version_ids'] else 'ok'
            except (httpx.RequestError,ValueError,KeyError,TypeError) as exc:
                row['error']=str(exc) if isinstance(exc,EvaluationGate) else type(exc).__name__
            row['latency_seconds']=round(time.monotonic()-started,3);report['rows'].append(row)
            successful=[r for r in report['rows'] if r['status']=='ok'];requested=len(pack['qa'])
            report['summary']=dict(requested=requested,observed=len(report['rows']),successful=len(successful),http_requests=requests,
                failed_or_not_run=requested-len(successful),
                primary_recall_over_requested=sum(r['primary']['clause_recall_at_k'] for r in successful)/requested,
                merged_coverage_over_requested=sum(r['merged']['clause_recall_at_k'] for r in successful)/requested,
                notice='Failures/not-run contribute zero to requested-case coverage; merged coverage is not Recall@3 or answer accuracy.')
            target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(case['id'],row['status'],flush=True)
    print('Saved private retrieval diagnostics:',target)


if __name__=='__main__':
    try:main()
    except EvaluationGate as exc:raise SystemExit(str(exc)) from None
