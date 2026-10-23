"""Create a local service credential once; never print it or rotate implicitly."""
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    target = ROOT / '.local/rules.env'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text('RULES_API_TOKEN='+secrets.token_urlsafe(48)+'\n', encoding='utf-8')
        print('Created private rules credential')
    else:
        print('Preserved existing rules credential')
