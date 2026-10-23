import copy
import unittest

from src.retrieval_query import retrieval_query
from tools.compare_retrieval import compare
from tools.build_chatflow import build


class ExperimentTests(unittest.TestCase):
    def report(self):
        return dict(cases_sha256='cases', policy_sha256='policy', dataset_ids={'v1': 'id'},
            retrieval_model={'top_k': 3}, top_k=3, query_variant='original', mean_clause_recall_on_success=1.0,
            rows=[dict(id='D01', version='v1', query='住宿', status='ok', clause_recall_at_k=1.0,
                foreign_version_ids=[], retrieved_clause_ids=['TRAVEL-v1-CITY'])])

    def test_average_cannot_hide_regression(self):
        old = self.report()
        new = copy.deepcopy(old)
        new['query_variant'] = 'city-hint'
        new['rows'][0]['clause_recall_at_k'] = 0.5
        result = compare(old, new)
        self.assertFalse(result['regression_gate_passed'])
        self.assertEqual(result['counts']['regressed'], 1)

    def test_mismatched_gold_and_failed_calls_rejected(self):
        old = self.report()
        new = copy.deepcopy(old)
        new['cases_sha256'] = 'different'
        with self.assertRaises(ValueError):
            compare(old, new)
        new = copy.deepcopy(old)
        new['rows'][0]['status'] = 'error'
        self.assertFalse(compare(old, new)['regression_gate_passed'])

    def test_query_variant_does_not_add_answer(self):
        self.assertEqual(retrieval_query('餐费标准？', 'city-hint'), '餐费标准？')
        query = retrieval_query('上海住宿上限？', 'city-hint')
        self.assertIn('城市等级', query)
        self.assertNotIn('500', query)
        self.assertNotIn('上海属于', query)

    def test_dsl_query_code_matches_evaluator_and_preserves_user_question(self):
        graph = build({'v1': 'one', 'v2': 'two'}, query_variant='city-hint')['workflow']['graph']
        nodes = {n['id']: n['data'] for n in graph['nodes']}
        scope = {}
        exec(nodes['route']['code'], scope)
        result = scope['main']('2026-08-01成都住宿标准？', '')
        self.assertEqual(result['question'], '2026-08-01成都住宿标准？')
        self.assertEqual(result['retrieval_query'], retrieval_query(result['question'], 'city-hint'))
        self.assertEqual(nodes['retrievev2']['query_variable_selector'], ['route', 'retrieval_query'])
        self.assertIn('{{#route.question#}}', str(nodes['llmv2']['prompt_template']))
