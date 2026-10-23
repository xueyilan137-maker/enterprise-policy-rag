"""Record explicit human label-review assertions after the human has read the packet. Never auto-approves labels."""
import argparse
import json
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.evaluation import EvaluationGate,load_pack,assert_frozen,label_digest,digest,read


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids',required=True,help='Explicit comma-separated case IDs actually reviewed by the human')
    parser.add_argument('--reviewer',required=True)
    parser.add_argument('--evidence-file',required=True,type=Path,help='Private file containing the actual human statement; not an assistant simulation')
    args=parser.parse_args();pack=load_pack('reserve-v1');assert_frozen(pack)
    evidence=args.evidence_file.resolve();local=(ROOT/'.local').resolve()
    if not evidence.is_relative_to(local) or not evidence.is_file():raise EvaluationGate('Existing private human evidence file required')
    if not args.reviewer.strip() or not evidence.read_text(encoding='utf-8').strip():raise EvaluationGate('Human reviewer and statement required')
    ids=args.ids.split(',')
    if len(set(ids))!=len(ids) or not set(ids)<=set(pack['gold']):raise EvaluationGate('Unknown or duplicate IDs')
    path=pack['folder']/'human-reviews.json';records=read(path)
    if set(ids)&{r['id'] for r in records['reviews']}:raise EvaluationGate('Human review already recorded; preserve original evidence')
    for id in ids:
        records['reviews'].append(dict(id=id,decision='approved',source='human_user',reviewer=args.reviewer,
            reviewed_at=datetime.now(timezone.utc).isoformat(),evidence_file=str(evidence.relative_to(ROOT)).replace('\\','/'),
            evidence_sha256=digest(evidence),label_sha256=label_digest(pack,id)))
    path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Recorded',len(ids),'explicit human label-review assertions. No model calls; no financial approval.')


if __name__=='__main__':
    try:main()
    except EvaluationGate as exc:raise SystemExit(str(exc)) from None
