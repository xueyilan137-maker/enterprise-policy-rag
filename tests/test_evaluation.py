import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.evaluation import (EvaluationGate,compare_findings,score_material,summarize,snapshot,verify_snapshot,
                            label_digest,require_human_reviews,load_pack,digest)
from tools.evaluate_system import evaluate_materials
from tools.evaluate_qa import score_observations
from tools.evaluate_reserved_retrieval import main as retrieval_main


class EvaluationTests(unittest.TestCase):
    def test_findings_use_code_item_and_clause_not_just_code(self):
        one=dict(code='X',item_ids=['a'],clause_ids=['TRAVEL-v2-DOCS'])
        other=dict(one,item_ids=['b'])
        self.assertEqual(compare_findings([other],[one]),dict(tp=0,fp=1,fn=1,exact=False))
        duplicate=compare_findings([one,one],[one])
        self.assertEqual((duplicate['tp'],duplicate['fp'],duplicate['fn']),(1,1,0))

    def test_empty_metrics_remain_undefined(self):
        empty=summarize([],2)
        self.assertEqual(empty['case_pass_fraction'],0);self.assertEqual(empty['missing_or_not_run'],2)
        self.assertIsNone(empty['finding_precision']);self.assertIsNone(empty['finding_recall'])

    def test_failure_stays_in_case_denominator_and_expected_findings_are_missing(self):
        expected=dict(findings=[dict(code='X',item_ids=['a'],clause_ids=[])])
        row=dict(score=score_material({'execution':'error'},expected))
        result=summarize([row],2)
        self.assertEqual(result['case_pass_fraction'],0);self.assertEqual(result['execution_errors'],1)
        self.assertEqual(result['finding_fn'],1)

    def test_blocked_input_requires_actual_creation_rejection(self):
        record=dict(execution='completed',extraction={'result':{'validation':dict(status='needs_materials',issues=[{'code':'MISSING_FIELD'}])}},creation_http_status=422)
        expected=dict(validation_status='needs_materials',required_issue_codes=['MISSING_FIELD'],application_created=False)
        self.assertTrue(score_material(record,expected)['case_pass'])
        record['creation_http_status']=201
        self.assertFalse(score_material(record,expected)['case_pass'])

    def test_snapshot_changes_and_path_escape_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'a.txt').write_text('first')
            frozen=snapshot(root,['a.txt']);verify_snapshot(root,frozen)
            (root/'a.txt').write_text('changed')
            with self.assertRaises(EvaluationGate):verify_snapshot(root,frozen)
            with self.assertRaises(EvaluationGate):verify_snapshot(root,{'../outside':'x'})

    def test_human_review_binds_both_labels_and_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.local').mkdir();(root/'.local/review.txt').write_text('Explicit test fixture; not actual human approval')
            pack=dict(folder=root,qa=[dict(id='Q',scenario_group='g')],materials=[],gold={'Q':{'answer':'x'}})
            target=root/'human-reviews.json';target.write_text('{"reviews":[]}')
            with self.assertRaises(EvaluationGate):require_human_reviews(pack,['Q'],root)
            record=dict(id='Q',decision='approved',source='human_user',reviewer='fixture',reviewed_at='fixture',
                        evidence_file='.local/review.txt',evidence_sha256=digest(root/'.local/review.txt'),label_sha256=label_digest(pack,'Q'))
            target.write_text(json.dumps({'reviews':[record]}));require_human_reviews(pack,['Q'],root)
            pack['gold']['Q']['answer']='changed'
            with self.assertRaises(EvaluationGate):require_human_reviews(pack,['Q'],root)

    def test_actual_candidate_review_gate_stops_before_http(self):
        pack=load_pack('reserve-v1')
        with patch('tools.evaluate_system.assert_frozen',return_value={}),patch('src.evaluation.read',return_value={'reviews':[]}),patch('tools.evaluate_system.httpx.Client') as client:
            with self.assertRaises(EvaluationGate):evaluate_materials(pack,'reserve')
            client.assert_not_called()

    def test_qa_cannot_substitute_clauses_for_semantic_accuracy(self):
        pack=dict(qa=[dict(id='Q',turns=['question'])],gold={'Q':dict(clause_ids=['TRAVEL-v2-MEAL'],final_policy_version='v2')})
        with self.assertRaises(EvaluationGate):score_observations(pack,[dict(id='Q',questions=['different'],answers=['TRAVEL-v2-MEAL'])])
        with self.assertRaises(EvaluationGate):score_observations(pack,[dict(id='Q',questions=['question'],answers=['TRAVEL-v2-MEAL'],evidence_file='')])

    def test_actual_retrieval_gate_stops_before_network(self):
        pack=load_pack('reserve-v1')
        with patch('tools.evaluate_reserved_retrieval.load_pack',return_value=pack),patch('src.evaluation.read',return_value={'reviews':[]}),patch('tools.evaluate_reserved_retrieval.assert_frozen',return_value={}),patch('tools.evaluate_reserved_retrieval.httpx.Client') as client:
            with self.assertRaises(EvaluationGate):retrieval_main()
            client.assert_not_called()

    def test_clause_mention_has_no_automatic_answer_accuracy(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.local').mkdir();proof=root/'.local/ui.txt';proof.write_text('Fixture UI evidence')
            pack=dict(qa=[dict(id='Q',turns=['question'])],gold={'Q':dict(clause_ids=['TRAVEL-v2-MEAL'],final_policy_version='v2')})
            row=dict(id='Q',questions=['question'],answers=['TRAVEL-v2-MEAL'],evidence_file='.local/ui.txt',evidence_sha256=digest(proof))
            with patch('tools.evaluate_qa.ROOT',root):result=score_observations(pack,[row])
            self.assertEqual(result['rows'][0]['expected_clause_mention_coverage'],1)
            self.assertIsNone(result['human_semantic_fraction']);self.assertEqual(result['human_answer_pending'],1)

    def test_prospective_packs_and_pilot_are_disjoint_by_id_and_exact_input(self):
        reserve=load_pack('reserve-v1');pilot=load_pack('pilot-v1')
        self.assertEqual((len(reserve['qa']),len(reserve['materials'])),(8,8))
        self.assertFalse(set(reserve['gold'])&set(pilot['gold']))
        self.assertFalse({c['narrative'] for c in reserve['materials']}&{c['narrative'] for c in pilot['materials']})
        # This proves exact separation only, not semantic family independence.
