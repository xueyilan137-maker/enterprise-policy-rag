import json
import unittest

from src.chatflow_nodes import guard


class GuardExcerptTests(unittest.TestCase):
    def setUp(self):
        self.required = ['TRAVEL-v2-MEAL', 'TRAVEL-v2-REVIEW']
        self.records = [dict(content='TRAVEL-v2-MEAL 餐费标准\n每天限额100元；同日合计检查。'),
                        dict(content='TRAVEL-v2-REVIEW 人工复核\n超标准不得自动认定通过。')]

    def draft(self, answer, refs=None):
        return json.dumps(dict(supported=True, answer=answer, clause_ids=refs or self.required))

    def test_retrieved_excerpt_does_not_repeat_unsafe_draft(self):
        text = self.draft('仅能报销限额内的金额，最终由财务复核。')
        strict = guard(text, self.records, 'v2', self.required)
        self.assertEqual(strict['validation_status'], 'refused')
        quoted = guard(text, self.records, 'v2', self.required, allow_excerpt=True)
        self.assertEqual(quoted['validation_status'], 'evidence_excerpt')
        self.assertEqual(quoted['validation_reason'], 'settlement_claim')
        self.assertNotIn('仅能报销', quoted['answer'])
        for record in self.records:
            self.assertIn(record['content'], quoted['answer'])

    def test_incomplete_or_foreign_evidence_never_gets_excerpt(self):
        for records in (self.records[:1], self.records+[dict(content='TRAVEL-v1-MEAL')], [None]):
            result = guard(self.draft('仅能报销100元'), records, 'v2', self.required, True)
            self.assertEqual(result['validation_status'], 'refused')

    def test_generated_and_excerpt_results_remain_distinct(self):
        valid = guard(self.draft('同日合计检查；超标准需人工复核，不自动批准。'), self.records, 'v2', self.required, True)
        self.assertEqual(valid['validation_status'], 'generated')
        missing_ref = guard(self.draft('转人工', self.required[:1]), self.records, 'v2', self.required, True)
        self.assertEqual(missing_ref['validation_status'], 'evidence_excerpt')
        self.assertEqual(missing_ref['validation_reason'], 'missing_required_citations')

    def test_source_only_disposition_never_renders_free_form_model_claim(self):
        for draft in (self.draft('需合并计算后按限额处理'), self.draft('可以报销全部金额'), 'not json'):
            result = guard(draft, self.records, 'v2', self.required, True, True)
            self.assertEqual(result['validation_status'], 'evidence_excerpt')
            self.assertEqual(result['validation_reason'], 'review_policy_source_only')
            self.assertNotIn('按限额处理', result['answer'])
            self.assertNotIn('可以报销全部金额', result['answer'])
