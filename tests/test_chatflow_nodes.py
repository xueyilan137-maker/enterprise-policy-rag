import unittest

from src.chatflow_nodes import route, guard
from src.policy_data import load_policy


class ChatflowTests(unittest.TestCase):
    def test_date_followup_and_new_question(self):
        versions = load_policy()['versions']
        first = route('深圳住宿上限？', '', versions)
        self.assertEqual(first['version'], '')
        second = route('2026-08-01', first['pending'], versions)
        self.assertEqual(second['version'], 'v2')
        self.assertIn('深圳住宿', second['question'])
        new = route('2026-03-01 餐费标准？', first['pending'], versions)
        self.assertNotIn('深圳', new['question'])

    def test_dates_fail_closed(self):
        versions = load_policy()['versions']
        for query in ('2026-02-30', '2027-01-01', '2026-06-30至2026-07-02', '明天出差'):
            self.assertEqual(route(query, '', versions)['version'], '')
        self.assertEqual(route('2026年6月30日', '', versions)['version'], 'v1')
        self.assertEqual(route('2026/7/1', '', versions)['version'], 'v2')

    def test_citation_and_schema_fail_closed(self):
        records = [{'content': 'TRAVEL-v2-MEAL 餐费每天100元'}]
        import json
        valid = dict(supported=True, answer='每天100元', clause_ids=['TRAVEL-v2-MEAL'])
        self.assertIn('每天100元', guard(json.dumps(valid), records, 'v2')['answer'])
        for changed in (dict(valid, clause_ids=['TRAVEL-v1-MEAL']), dict(valid, supported=False),
                        dict(valid, clause_ids=[]), dict(valid, answer='TRAVEL-v2-LODGE')):
            self.assertIn('依据不足', guard(json.dumps(changed), records, 'v2')['answer'])
        self.assertIn('依据不足', guard('not json', records, 'v2')['answer'])
        self.assertIn('依据不足', guard(json.dumps(valid), [{'content': 'TRAVEL-v1-MEAL'}], 'v2')['answer'])
