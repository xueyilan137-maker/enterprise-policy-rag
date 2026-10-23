"""Create isolated local demo identities once; never print their bearer tokens."""
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__=='__main__':
    path = ROOT/'.local/business-auth.json'
    if not path.exists():
        path.write_text(json.dumps({'mode':'synthetic_demo','users':[
            {'employee_id':id,'token':secrets.token_urlsafe(48)} for id in ('DEMO-001','DEMO-002')]},indent=2)+'\n',encoding='utf-8')
        print('Created private local demo identities')
    else:
        print('Preserved existing local demo identities')
