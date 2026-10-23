import json
import unittest

from src.related_evidence import review_needed, review_plan, merge_review
from src.chatflow_nodes import guard
from tools.build_chatflow import build


class RelatedEvidenceTests(unittest.TestCase):
    def test_query_routing_has_no_case_id_or_gold_dependency(self):
        self.assertTrue(review_needed('同一天两张餐费凭证各60元，可以分别不超标准报销吗？'))
        self.assertTrue(review_needed('餐费超标怎么办？'))
        self.assertFalse(review_needed('住宿报销需要什么材料？'))
        self.assertFalse(review_needed('餐费每天上限是多少？'))
        self.assertFalse(review_needed('婚假几天？'))

    def test_budget_no_duplicate_and_real_miss_stays_missing(self):
        primary = [dict(content='TRAVEL-v2-MEAL'), dict(content='TRAVEL-v2-LODGE'), dict(content='TRAVEL-v2-TRANSIT')]
        self.assertEqual(review_plan('餐费能否报销？', primary, 'v2')['needed'], 'yes')
        self.assertEqual(len(merge_review(primary, [dict(content='TRAVEL-v2-REVIEW')], 'v2')['result']), 4)
        self.assertEqual(merge_review(primary, [dict(content='TRAVEL-v2-DOCS')], 'v2')['result'], primary)
        merged = merge_review(primary, [dict(content='TRAVEL-v2-REVIEW')], 'v2')['result']
        self.assertEqual(review_plan('餐费能否报销？', merged, 'v2')['needed'], 'no')

    def test_foreign_version_is_rejected(self):
        with self.assertRaises(ValueError):
            merge_review([dict(content='TRAVEL-v2-MEAL')], [dict(content='TRAVEL-v1-REVIEW')], 'v2')

    def test_missing_review_or_unreferenced_review_refuses(self):
        needed = ['TRAVEL-v2-MEAL', 'TRAVEL-v2-REVIEW']
        text = json.dumps(dict(supported=True, answer='超标准需人工复核', clause_ids=needed))
        primary = [dict(content='TRAVEL-v2-MEAL')]
        self.assertIn('依据不足', guard(text, primary, 'v2', needed)['answer'])
        records = primary+[dict(content='TRAVEL-v2-REVIEW')]
        self.assertIn('人工复核', guard(text, records, 'v2', needed)['answer'])
        partial = json.dumps(dict(supported=True, answer='需人工复核', clause_ids=['TRAVEL-v2-MEAL']))
        self.assertIn('依据不足', guard(partial, records, 'v2', needed)['answer'])
        for invalid in (None, [None], [dict(content=None)]):
            self.assertIn('依据不足', guard(text, invalid, 'v2', needed)['answer'])

    def test_valid_citations_do_not_authorize_settlement_amount(self):
        needed = ['TRAVEL-v2-MEAL', 'TRAVEL-v2-REVIEW']
        records = [dict(content=id) for id in needed]
        for answer in ('仅能报销100元，转人工复核', '可报销金额为100.00元', '最终支付120元'):
            text = json.dumps(dict(supported=True, answer=answer, clause_ids=needed))
            self.assertIn('依据不足', guard(text, records, 'v2', needed)['answer'])
        text = json.dumps(dict(supported=True, answer='每日限额100元；同日合计120元超标准，不自动认定通过，需人工复核。', clause_ids=needed))
        self.assertIn('每日限额100元', guard(text, records, 'v2', needed)['answer'])

    def test_dsl_embedded_plan_merge_and_guard_match_python(self):
        nodes = {n['id']: n['data'] for n in build({'v1': 'one', 'v2': 'two'}, query_variant='city-hint', related_review=True)['workflow']['graph']['nodes']}
        scope = {}
        exec(nodes['planv2']['code'], scope)
        self.assertEqual(scope['main']('餐费超标怎么办？', [dict(content='TRAVEL-v2-MEAL')])['needed'], 'yes')
        exec(nodes['mergev2']['code'], scope)
        self.assertEqual(len(scope['main']([dict(content='TRAVEL-v2-MEAL')], [dict(content='TRAVEL-v2-REVIEW')])['result']), 2)
        exec(nodes['guardv2']['code'], scope)
        text = json.dumps(dict(supported=True, answer='人工复核', clause_ids=['TRAVEL-v2-MEAL']))
        self.assertIn('依据不足', scope['main'](text, [dict(content='TRAVEL-v2-MEAL')], '餐费超标怎么办？')['answer'])
