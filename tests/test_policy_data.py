import copy
import json
import tempfile
import unittest
from pathlib import Path
from src.policy_data import ROOT, build, load_policy, render_document, select_version


class PolicyDataTests(unittest.TestCase):
    def test_effective_boundary(self):
        p = load_policy()
        self.assertEqual(select_version(p, '2026-06-30')['version'], 'v1')
        self.assertEqual(select_version(p, '2026-07-01')['version'], 'v2')

    def test_missing_and_uncovered_dates_fail(self):
        for day in (None, '2027-01-01', '2026-02-30'):
            with self.subTest(day=day), self.assertRaises(ValueError):
                select_version(load_policy(), day)

    def test_overlapping_versions_rejected(self):
        p = copy.deepcopy(load_policy())
        p['versions'][1]['effective_from'] = '2026-06-30'
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'bad.json'
            f.write_text(json.dumps(p), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'overlapping'):
                load_policy(f)

    def test_nonfinite_money_rejected(self):
        for bad in ('NaN', 'Infinity', '-1.00', '100.001', 100.0):
            p = copy.deepcopy(load_policy())
            p['versions'][0]['meal_per_day'] = bad
            with tempfile.TemporaryDirectory() as tmp:
                f = Path(tmp) / 'bad.json'
                f.write_text(json.dumps(p), encoding='utf-8')
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    load_policy(f)

    def test_rendered_rules_and_ids_match(self):
        p = load_policy()
        for v in p['versions']:
            text = render_document(p, v)
            self.assertIn(v['lodging_per_night']['A']+'元', text)
            self.assertIn(v['meal_per_day']+'元', text)
            self.assertIn(f"TRAVEL-{v['version']}-LODGE", text)
            self.assertNotIn('{days}', text)

    def test_build_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = build(tmp)
            self.assertEqual(first, build(tmp))

    def test_dev_citations_exist_in_applicable_version(self):
        p = load_policy()
        cases = [json.loads(line) for line in (ROOT/'data/eval/dev.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len({c['id'] for c in cases}), len(cases))
        for c in cases:
            if c['action'] == 'retrieve':
                text = render_document(p, select_version(p, c['trip_start_date']))
                for clause in c['expected_clause_ids']:
                    self.assertIn(clause, text)


if __name__ == '__main__':
    unittest.main()
