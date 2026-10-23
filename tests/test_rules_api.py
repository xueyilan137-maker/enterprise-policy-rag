import json
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from src.rules_api import create_app


class RulesApiTests(unittest.TestCase):
    def setUp(self):
        self.token = 'test-only-'+'x'*40
        self.client = TestClient(create_app(self.token))
        self.headers = {'Authorization': 'Bearer '+self.token}
        self.case = json.loads(Path('data/examples/expense-001.json').read_text(encoding='utf-8'))

    def test_authentication_and_scope(self):
        self.assertEqual(self.client.post('/v1/prechecks', json=self.case).status_code, 401)
        self.assertEqual(self.client.post('/v1/prechecks', json=self.case, headers={'Authorization': 'Bearer wrong'}).status_code, 401)
        self.case['employee_id'] = 'other'
        self.assertEqual(self.client.post('/v1/prechecks', json=self.case, headers=self.headers).status_code, 403)

    def test_strict_money_and_no_client_history(self):
        for field, value in [('total_amount', 120.0), ('previous_receipt_ids', []), ('admin', True)]:
            case = dict(self.case, **{field: value})
            response = self.client.post('/v1/prechecks', json=case, headers=self.headers)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {'detail': 'Invalid structured application'})

    def test_real_rule_result_and_unique_request_id(self):
        first = self.client.post('/v1/prechecks', json=self.case, headers=self.headers).json()
        second = self.client.post('/v1/prechecks', json=self.case, headers=self.headers).json()
        self.assertEqual(first['status'], 'needs_manual_review')
        self.assertNotEqual(first['request_id'], second['request_id'])
        self.assertEqual(first['findings'][0]['facts']['actual'], '120.00')
        self.assertNotIn('approved_amount', first)

    def test_duplicate_item_ids_and_malformed_json(self):
        self.case['expense_items'][1]['item_id'] = self.case['expense_items'][0]['item_id']
        self.assertEqual(self.client.post('/v1/prechecks', json=self.case, headers=self.headers).status_code, 422)
        self.assertEqual(self.client.post('/v1/prechecks', content='{', headers=self.headers).status_code, 422)

    def test_missing_materials_is_business_result(self):
        self.case['expense_items'] = self.case['expense_items'][:1]
        self.case['total_amount'] = '60.00'
        self.case['expense_items'][0]['receipt_present'] = False
        response = self.client.post('/v1/prechecks', json=self.case, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'needs_materials')
