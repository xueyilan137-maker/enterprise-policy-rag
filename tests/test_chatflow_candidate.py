import unittest
from tools.build_chatflow import build
from tools.build_chatflow_candidate import candidate
from src.intent_query import intent_query
from src.retrieval_query import retrieval_query
from src.answer_evidence import consultation_evidence


class CandidateTests(unittest.TestCase):
    def test_prompt_only_preserves_every_non_llm_node(self):
        ids = dict(v1='test-v1', v2='test-v2')
        original = build(ids, query_variant='city-hint', related_review=True)
        changed = candidate(ids)
        for old, new in zip(original['workflow']['graph']['nodes'], changed['workflow']['graph']['nodes']):
            if old['id'] == 'branch':
                # The original builder randomizes condition identifiers.
                for case in old['data']['cases']:
                    case['conditions'][0]['id'] = ''
                for case in new['data']['cases']:
                    case['conditions'][0]['id'] = ''
            if old['data']['type'] == 'llm':
                self.assertTrue(new['data']['prompt_template'][0]['text'].startswith(old['data']['prompt_template'][0]['text']))
                new['data']['prompt_template'] = old['data']['prompt_template']
            self.assertEqual(old, new)

    def test_transport_dispute_prioritizes_transport_over_lodging(self):
        query = intent_query('商务舱缺批准，但住宿未超标，申请能通过吗？')
        self.assertIn('交通费用', query)
        self.assertIn('预审', query)
        self.assertNotIn('住宿', query)

    def test_other_queries_keep_prior_behavior(self):
        for query in ('住宿标准？', '餐费可以报销吗？', '高铁二等座多少钱？', '婚假几天？'):
            self.assertEqual(intent_query(query), retrieval_query(query, 'city-hint'))

    def test_embedded_code_matches_local_routing(self):
        flow = candidate(dict(v1='test-v1', v2='test-v2'), True)
        route = next(n for n in flow['workflow']['graph']['nodes'] if n['id'] == 'route')
        namespace = {}
        exec(route['data']['code'], namespace)
        q = '2026-05-19商务舱缺事前批准，但住宿合规，能通过吗？'
        self.assertEqual(namespace['main'](q, '')['retrieval_query'], intent_query(q))

    def test_excerpt_fallback_requires_real_complete_same_version_evidence(self):
        flow = candidate(dict(v1='test-v1', v2='test-v2'), True, True)
        code = next(n['data']['code'] for n in flow['workflow']['graph']['nodes'] if n['id'] == 'guardv2')
        namespace = {}
        exec(code, namespace)
        q = '只有总额没有明细能核对吗？'
        records = [{'content':'TRAVEL-v2-DOCS 材料清单\n真实材料要求'},
                   {'content':'TRAVEL-v2-DUPLICATE 金额检查\n真实金额要求'}]
        run = namespace['main']
        result = run('{"supported":false,"answer":"","clause_ids":[]}', records, q)
        self.assertEqual(result['validation_status'], 'evidence_excerpt')
        self.assertIn(records[0]['content'], result['answer'])
        self.assertEqual(run('{}', records[:1], q)['validation_reason'], 'missing_required_evidence')
        self.assertEqual(run('{}', records+[{'content':'TRAVEL-v1-DOCS 错版本'}], q)['validation_reason'], 'foreign_version')
        self.assertEqual(run('{}', records, '婚假有几天？')['validation_status'], 'refused')
        meal = [{'content':'TRAVEL-v2-MEAL 餐费\n供餐条款原文'}, {'content':'TRAVEL-v2-DOCS 材料\n凭证条款原文'}]
        unsafe = '{"supported":true,"answer":"若坚持申报可例外批准","clause_ids":["TRAVEL-v2-MEAL","TRAVEL-v2-DOCS"]}'
        fixed = run(unsafe, meal, '单位提供午餐，申报餐费但无凭证要补什么材料？')
        self.assertEqual(fixed['validation_status'], 'evidence_excerpt')
        self.assertNotIn('例外批准', fixed['answer'])

    def test_bounded_intents_are_version_specific(self):
        self.assertEqual(consultation_evidence('商务舱缺批准能通过吗？', 'v1'),
                         ['TRAVEL-v1-TRANSIT', 'TRAVEL-v1-REVIEW'])
        self.assertEqual(consultation_evidence('没有名单里的城市能直接套B类吗？','v2'), ['TRAVEL-v2-CITY'])

    def test_corrected_date_does_not_keep_superseded_invalid_date(self):
        flow = candidate(dict(v1='test-v1', v2='test-v2'), True, True)
        namespace = {}
        exec(next(n['data']['code'] for n in flow['workflow']['graph']['nodes'] if n['id']=='route'), namespace)
        run = namespace['main']
        pending = '2026-02-30出发，高铁一等座缺批准怎么办？'
        result = run('2026-02-28', pending)
        self.assertEqual(result['version'], 'v1')
        self.assertNotIn('2026-02-30', result['question'])
        self.assertIn('高铁一等座缺批准', result['question'])
        self.assertIn('2026-02-28', result['question'])
        self.assertEqual(run('2026-07-10住宿标准？', pending)['question'], '2026-07-10住宿标准？')
        self.assertFalse(run('2026-02-31', pending)['version'])


if __name__ == '__main__':
    unittest.main()
