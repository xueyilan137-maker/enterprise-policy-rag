"""Offline structured rule precheck; synthetic examples only, no model or service call."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.expense_rules import precheck

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('application', type=Path)
    args = parser.parse_args()
    try:
        report = precheck(json.loads(args.application.read_text(encoding='utf-8')))
    except (ValueError, KeyError, TypeError):
        parser.error('Invalid structured application; check the documented schema')
    print(json.dumps(report, ensure_ascii=False, indent=2))
