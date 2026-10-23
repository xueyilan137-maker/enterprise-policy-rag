"""Isolated, authenticated connectivity probe; no model or business data."""
import hmac
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / '.local' / 'tunnel-probe'
ROOT.mkdir(parents=True, exist_ok=True)
TOKEN_FILE = ROOT / 'token.txt'
TOKEN = secrets.token_urlsafe(32)
TOKEN_FILE.write_text(TOKEN, encoding='utf-8')


class Probe(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/probe':
            self.respond(404, {'ok': False, 'error': 'not_found'})
        elif not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            self.respond(401, {'ok': False, 'error': 'unauthorized'})
        else:
            self.respond(200, {'ok': True, 'service': 'dify-local-probe', 'message': 'connection_success'})

    def respond(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == '__main__':
    print('Probe listening on 127.0.0.1:18765; token stored in .local/tunnel-probe/token.txt', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 18765), Probe).serve_forever()
