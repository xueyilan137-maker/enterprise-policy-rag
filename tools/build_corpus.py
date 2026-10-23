import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.policy_data import ROOT, build

if __name__ == '__main__':
    result = build(ROOT / 'data/corpus')
    print(f"Built {len(result['documents'])} synthetic documents; no model calls")
