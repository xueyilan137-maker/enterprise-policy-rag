"""Post-evaluation development candidate; leaves the frozen v4 builder/template intact."""
import argparse
import json
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_chatflow import build
from src.intent_query import intent_query
from src.answer_evidence import consultation_evidence
from src.followup_question import normalized_followup


ANSWERABILITY = '''
区分“不能执行用户操作”和“不能解释制度”：问题要求批准、付款、验真、缺材料仍通过，或给出了不符合制度的前提时，只要检索条款明确规定限制，就回答该限制，supported=true；不执行该操作，不承诺具体审批结果。
问题中的假设不是事实依据。城市未被制度覆盖时，解释制度覆盖边界并要求人工判断，不自行分类；不需要先获得一个可适用的城市等级才能解释“不在覆盖范围”。
当用户问某项费用能否套用另一类标准、只有总额是否足以核对、能否验真或自动付款，逐项对照本轮实际条款解释；只对检索缺失的事实保留不确定性，不将“无法执行”误写成“无依据回答”。
只输出规定JSON，不添加新的处理流程、证明要求或例外。不得把用户提供的金额当作已核定报销额。
'''


def candidate(dataset_ids, transport_routing=False, evidence_fallback=False):
    result = build(dataset_ids, query_variant='city-hint', related_review=True)
    for node in result['workflow']['graph']['nodes']:
        data = node['data']
        if data['type'] == 'llm':
            data['prompt_template'][0]['text'] += ANSWERABILITY
        if transport_routing and node['id'] == 'route':
            data['code'] = data['code'].replace('\ndef main(query, pending):',
                '\n'+inspect.getsource(intent_query)+'\ndef main(query, pending):')
            data['code'] = data['code'].replace('= retrieval_query(result["question"],',
                '= intent_query(result["question"],')
        if evidence_fallback and node['id'] == 'route':
            data['code'] = data['code'].replace('\ndef main(query, pending):',
                '\n'+inspect.getsource(normalized_followup)+'\ndef main(query, pending):')
            data['code'] = data['code'].replace('    result["retrieval_query"] =',
                '    result = normalized_followup(result, query, pending)\n    result["retrieval_query"] =')
        if evidence_fallback and node['id'] in ('guardv1', 'guardv2'):
            version = node['id'][-2:]
            data['code'] = data['code'].replace('\ndef main(text, records, question):',
                '\n'+inspect.getsource(consultation_evidence)+'\ndef main(text, records, question):')
            data['code'] = data['code'].replace('    return guard(text, records,',
                '    if not required:\n        required = consultation_evidence(question, '+repr(version)+')\n    return guard(text, records,')
            data['code'] = data['code'].replace('source_only=review_needed(question)',
                'source_only=(review_needed(question) or ("TRAVEL-'+version+'-DOCS" in required and "TRAVEL-'+version+'-MEAL" in required))')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', action='store_true')
    parser.add_argument('--transport-routing', action='store_true')
    parser.add_argument('--evidence-fallback', action='store_true')
    args = parser.parse_args()
    ids = {v: 'REPLACE_DATASET_'+v.upper() for v in ('v1', 'v2')}
    name = 'intent-candidate' if args.transport_routing else 'answerability-candidate'
    if args.evidence_fallback:
        name = 'evidence-candidate'
    target = ROOT/('dify/policy-chatflow.'+name+'.template.yml')
    if args.bind:
        state = json.loads((ROOT/'.local/knowledge-state.json').read_text(encoding='utf-8'))
        ids = {v: state['versions'][v]['dataset_id'] for v in ids}
        target = ROOT/('.local/policy-chatflow.'+name+'.bound.yml')
    target.write_text(json.dumps(candidate(ids, args.transport_routing, args.evidence_fallback), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Generated', target)
