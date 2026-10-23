import copy
import unittest
from src.expense_rules import money, precheck


def application(amounts=('60.00', '60.00')):
    return dict(employee_id='DEMO-001', employee_type='ordinary', reason='合成差旅示例', destination='成都',
        destination_region='CN-mainland', trip_start_date='2026-08-01', trip_end_date='2026-08-02',
        submitted_date='2026-08-22', total_amount='120.00', expense_items=[dict(item_id=str(i),
            category='meal', amount=value, expense_date='2026-08-01', receipt_id='SYN-'+str(i),
            receipt_present=True, meal_provided=False) for i, value in enumerate(amounts)])


def codes(report):
    return {f['code'] for f in report['findings']}


class ExpenseRuleTests(unittest.TestCase):
    def test_meal_is_summed_by_day_and_has_no_approved_amount(self):
        result = precheck(application())
        self.assertEqual(result['status'], 'needs_manual_review')
        finding = next(f for f in result['findings'] if f['code'] == 'MEAL_DAILY_OVER_LIMIT')
        self.assertEqual(finding['facts']['actual'], '120.00')
        self.assertEqual(finding['facts']['limit'], '100.00')
        self.assertEqual(finding['clause_ids'], ['TRAVEL-v2-MEAL', 'TRAVEL-v2-REVIEW'])
        self.assertNotIn('approved_amount', result)

    def test_decimal_sum_and_total_mismatch(self):
        case = application(('0.10', '0.20'))
        case['total_amount'] = '0.30'
        self.assertEqual(precheck(case)['status'], 'no_issues_found')
        case['total_amount'] = '0.31'
        self.assertIn('TOTAL_MISMATCH', codes(precheck(case)))

    def test_invalid_money_does_not_produce_partial_sum(self):
        for value in (0.1, 'NaN', 'Infinity', '-1.00', '1.001', '1e2', True):
            with self.assertRaises(ValueError):
                money(value)
        case = application()
        case['expense_items'][0]['amount'] = 'NaN'
        result = precheck(case)
        self.assertIn('INVALID_MONEY', codes(result))
        self.assertIsNone(result['facts']['item_sum'])

    def test_deadline_equal_and_one_day_late(self):
        case = application()
        self.assertNotIn('LATE_SUBMISSION', codes(precheck(case)))
        case['submitted_date'] = '2026-08-23'
        self.assertIn('LATE_SUBMISSION', codes(precheck(case)))
        case.update(trip_start_date='2026-06-30', trip_end_date='2026-07-02', submitted_date='2026-08-01')
        for item in case['expense_items']:
            item['expense_date'] = '2026-07-01'
        result = precheck(case)
        self.assertEqual(result['policy_version'], 'v1')
        self.assertNotIn('LATE_SUBMISSION', codes(result))
        self.assertEqual(next(f for f in result['findings'] if f['code']=='MEAL_DAILY_OVER_LIMIT')['facts']['limit'], '80.00')

    def test_duplicates_within_and_trusted_history(self):
        case = application()
        case['expense_items'][1]['receipt_id'] = 'SYN-0'
        self.assertIn('SUSPECTED_DUPLICATE_RECEIPT', codes(precheck(case)))
        result = precheck(application(), previous_receipt_ids=['SYN-0'])
        self.assertTrue(next(f for f in result['findings'] if f['code']=='SUSPECTED_DUPLICATE_RECEIPT')['facts']['cross_application'])

    def test_missing_materials_and_unsupported_scope(self):
        case = application(('10.00',))
        case['total_amount'] = '10.00'
        case['expense_items'][0]['receipt_present'] = False
        self.assertEqual(precheck(case)['status'], 'needs_materials')
        case['destination_region'] = 'overseas'
        self.assertEqual(precheck(case)['status'], 'needs_manual_review')

    def test_meal_provision_is_a_daily_fact_not_a_per_receipt_override(self):
        case = application(('0.00', '60.00'))
        case['total_amount'] = '60.00'
        case['expense_items'][0]['meal_provided'] = True
        result = precheck(case)
        self.assertIn('MEAL_ALREADY_PROVIDED', codes(result))
        self.assertIn('CONFLICTING_MEAL_PROVISION', codes(result))

    def test_city_tier_and_rendered_clause_share_one_source(self):
        from src.policy_data import load_policy, render_clauses
        policy = load_policy()
        policy['city_tiers']['A'].append('成都')
        text = next(c['text'] for c in render_clauses(policy, policy['versions'][1]) if c['clause_id'].endswith('-CITY'))
        self.assertIn('深圳、成都', text)
        case = application()
        case['expense_items'] = [dict(item_id='h', category='lodging', amount='500.00', expense_date='2026-08-01',
            receipt_present=True, receipt_id='H', check_in='2026-08-01', check_out='2026-08-02', nights=1)]
        case['total_amount'] = '500.00'
        self.assertIn('LODGING_OVER_LIMIT', codes(precheck(case)))
        self.assertNotIn('LODGING_OVER_LIMIT', codes(precheck(case, policy=policy)))

    def test_lodging_nights_limit_and_overlap(self):
        case = application()
        case.update(trip_end_date='2026-08-03', total_amount='800.00')
        item = dict(item_id='hotel', category='lodging', amount='800.00', expense_date='2026-08-01',
            receipt_present=True, receipt_id='HOTEL-1', check_in='2026-08-01', check_out='2026-08-03', nights=2)
        case['expense_items'] = [item]
        self.assertEqual(precheck(case)['status'], 'no_issues_found')
        item['amount'] = '800.01'; case['total_amount'] = '800.01'
        self.assertIn('LODGING_OVER_LIMIT', codes(precheck(case)))
        item['nights'] = 3
        self.assertIn('LODGING_NIGHT_MISMATCH', codes(precheck(case)))
        other = copy.deepcopy(item); other.update(item_id='hotel2', receipt_id='HOTEL-2')
        case['expense_items'].append(other)
        self.assertIn('OVERLAPPING_LODGING', codes(precheck(case)))

    def test_unknown_version_and_invalid_structure_never_pass(self):
        case = application()
        case.update(trip_start_date='2027-01-01', trip_end_date='2027-01-02', submitted_date='2027-01-03')
        result = precheck(case)
        self.assertIsNone(result['policy_version'])
        self.assertIn('NO_APPLICABLE_POLICY', codes(result))
        self.assertTrue(all(not f['clause_ids'] for f in result['findings']))
        case['expense_items'] = []
        with self.assertRaises(ValueError):
            precheck(case)

    def test_transit_prior_approval_missing(self):
        case = application()
        case['total_amount']='200.00'
        case['expense_items']=[dict(item_id='train', category='transit', amount='200.00',
            expense_date='2026-08-01', route='成都-上海', seat_class='高铁一等座', receipt_id='TRAIN', receipt_present=True)]
        result=precheck(case)
        self.assertIn('MISSING_PRIOR_APPROVAL', codes(result))
        self.assertEqual(result['status'], 'needs_manual_review')
