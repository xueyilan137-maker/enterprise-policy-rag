import unittest
from tools.evaluate_retrieval import score_records


class RetrievalContractTests(unittest.TestCase):
    def test_partial_recall_is_not_counted_as_full(self):
        result = score_records([{'segment': {'content': 'TRAVEL-v1-LODGE'}}],
                               ['TRAVEL-v1-LODGE', 'TRAVEL-v1-CITY'], 'v1', 3)
        self.assertEqual(result['clause_recall_at_k'], 0.5)

    def test_version_leak_reported_even_when_expected_found(self):
        result = score_records([{'segment': {'content': 'TRAVEL-v1-LODGE TRAVEL-v2-LODGE'}}],
                               ['TRAVEL-v1-LODGE'], 'v1', 3)
        self.assertEqual(result['foreign_version_ids'], ['TRAVEL-v2-LODGE'])

    def test_schema_change_fails_instead_of_empty_success(self):
        with self.assertRaises(ValueError):
            score_records([{'content': 'wrong schema'}], ['TRAVEL-v1-CITY'], 'v1', 3)

    def test_top_k_and_duplicate_mentions(self):
        records = [{'segment': {'content': 'TRAVEL-v1-CITY TRAVEL-v1-CITY'}},
                   {'segment': {'content': 'TRAVEL-v1-LODGE'}}]
        self.assertEqual(score_records(records, ['TRAVEL-v1-LODGE'], 'v1', 1)['clause_recall_at_k'], 0)


if __name__ == '__main__':
    unittest.main()
