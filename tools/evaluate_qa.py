"""Collect published-UI observations without a new Chatflow key; structural and human semantic scores stay separate."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.evaluation import EvaluationGate,load_pack,assert_frozen,require_human_reviews,digest,read


def score_observations(pack,observations):
    cases={c['id']:c for c in pack['qa']}
    if len(observations)!=len(cases) or {r['id'] for r in observations}!=set(cases):
        raise EvaluationGate('Every QA ID must appear exactly once')
    rows=[]
    for observation in observations:
        id=observation['id'];case=cases[id];gold=pack['gold'][id]
        if observation.get('questions')!=case['turns']:raise EvaluationGate('Observed input turns differ from frozen case: '+id)
        answers=observation.get('answers',[])
        if len(answers)!=len(case['turns']) or any(not isinstance(a,str) or not a.strip() for a in answers):
            raise EvaluationGate('Missing actual answer turns: '+id)
        evidence=ROOT/observation.get('evidence_file','')
        if (not str(observation.get('evidence_file','')).startswith('.local/') or not evidence.is_file() or
                observation.get('evidence_sha256')!=digest(evidence)):
            raise EvaluationGate('Private UI trace evidence and hash required: '+id)
        refs=set(re.findall(r'\bTRAVEL-v\d+-[A-Z]+\b',answers[-1]))
        expected=set(gold['clause_ids']);foreign={r for r in refs if not r.startswith('TRAVEL-'+gold['final_policy_version']+'-')}
        human=observation.get('human_semantic_review')
        semantic=None
        if human:
            # This is a documented human assertion, not authenticated third-party review.
            checks=('all_key_points_supported','no_unsupported_claim','appropriate_refusal_or_clarification')
            proof=ROOT/human.get('evidence_file','')
            answer_hash=hashlib.sha256(json.dumps(answers,ensure_ascii=False).encode()).hexdigest()
            if (human.get('source')!='human_user' or not human.get('reviewer') or not proof.is_file() or
                    human.get('answers_sha256')!=answer_hash or human.get('evidence_sha256')!=digest(proof) or
                    any(type(human.get(k)) is not bool for k in checks)):
                raise EvaluationGate('Invalid human answer annotation: '+id)
            semantic=all(human[k] for k in checks)
        rows.append(dict(id=id,mentioned_clause_ids=sorted(refs),foreign_version_mentions=sorted(foreign),
            expected_clause_mention_coverage=len(expected&refs)/len(expected),semantic_pass=semantic,
            output_mode=observation.get('output_mode','unknown'),
            citation_entailment_verified=False,actual_retrieval_recall=None))
    reviewed=[r for r in rows if r['semantic_pass'] is not None]
    return dict(rows=rows,requested=len(cases),human_answer_reviewed=len(reviewed),human_answer_pending=len(cases)-len(reviewed),
        human_semantic_fraction=sum(r['semantic_pass'] for r in reviewed)/len(reviewed) if reviewed else None,
        notice='Clause mentions are not retrieval recall or entailment. Excerpts, generated text and refusal remain separate; human accuracy unavailable until reviewed.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('template','score'))
    parser.add_argument('--observations',type=Path)
    args=parser.parse_args();pack=load_pack('reserve-v1');manifest=assert_frozen(pack)
    require_human_reviews(pack,[c['id'] for c in pack['qa']])
    folder=ROOT/'.local/eval-ledger/reserve-v1';folder.mkdir(parents=True,exist_ok=True)
    if args.action=='template':
        target=folder/'qa-observations.json'
        try:
            with target.open('x',encoding='utf-8') as file:
                json.dump(dict(pack='reserve-v1',manifest_sha256=digest(pack['folder']/'manifest.json'),
                    source='published_dify_browser',rows=[dict(id=c['id'],questions=c['turns'],answers=[],
                    evidence_file='',evidence_sha256='',output_mode='unknown',human_semantic_review=None) for c in pack['qa']]),file,ensure_ascii=False,indent=2)
        except FileExistsError:raise EvaluationGate('QA observation template already exists; preserve original first-pass evidence') from None
        print('Created private first-pass QA observation sheet:',target)
    else:
        if args.observations is None:raise EvaluationGate('Provide actual published UI observations')
        observed=read(args.observations)
        if observed.get('manifest_sha256')!=digest(pack['folder']/'manifest.json') or observed.get('source')!='published_dify_browser':
            raise EvaluationGate('Frozen manifest or collection source mismatch')
        report=score_observations(pack,observed['rows']);report['manifest']=manifest
        # Exclusive output prevents overwriting a first-pass result.
        target=folder/'qa-score.json'
        with target.open('x',encoding='utf-8') as file:json.dump(report,file,ensure_ascii=False,indent=2)
        print(json.dumps({k:v for k,v in report.items() if k not in ('rows','manifest')},ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except EvaluationGate as exc:raise SystemExit(str(exc)) from None
