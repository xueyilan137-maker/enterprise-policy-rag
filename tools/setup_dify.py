"""Prepare this project's private, version-pinned Dify deployment; never touch old stacks."""
import hashlib
import json
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.17.1'
DOCKER = ROOT / '.local/vendor' / f'dify-{VERSION}' / 'docker'


def main():
    template = DOCKER / '.env.example'
    if not template.exists() or not (DOCKER/'nginx').is_dir():
        raise SystemExit('Extract the complete official Dify 1.17.1 archive first')
    env = DOCKER / '.env'
    if env.exists():
        raise SystemExit('Existing .env preserved; inspect rather than overwrite')
    text = template.read_text(encoding='utf-8')
    changes = {
        'EXPOSE_NGINX_PORT': '18080', 'EXPOSE_NGINX_SSL_PORT': '18443',
        'EXPOSE_PLUGIN_DEBUGGING_PORT': '15003',
        'COMPOSE_PROFILES': 'weaviate,postgresql',
        'ENABLE_COLLABORATION_MODE': 'false', 'CELERY_WORKER_AMOUNT': '1',
        'PLUGIN_PYTHON_ENV_INIT_TIMEOUT': '600',
        'SERVER_WORKER_AMOUNT': '1', 'SECRET_KEY': secrets.token_urlsafe(42),
        'PLUGIN_DAEMON_KEY': secrets.token_hex(32),
        'PLUGIN_DIFY_INNER_API_KEY': secrets.token_hex(32),
        'DIFY_AGENT_API_TOKEN': secrets.token_hex(32),
        'TRIGGER_URL': 'http://localhost:18080',
        'ENDPOINT_URL_TEMPLATE': 'http://localhost:18080/e/{hook_id}',
        'NEXT_PUBLIC_SOCKET_URL': 'ws://localhost:18080',
    }
    for key, value in changes.items():
        pattern = rf'(?m)^{re.escape(key)}=.*$'
        if re.search(pattern, text):
            text = re.sub(pattern, lambda _: key+'='+value, text)
        else:
            text += '\n'+key+'='+value+'\n'
    env.write_text(text, encoding='utf-8')
    (DOCKER/'project.override.yaml').write_text('''services:
  nginx:
    ports: !override
      - "127.0.0.1:18080:80"
  plugin_daemon:
    ports: !override []
    volumes:
      - plugin_runtime:/app/storage
volumes:
  plugin_runtime:
    name: policy-rag_plugin_runtime
    external: true
''', encoding='utf-8')
    archive = ROOT/'.local'/f'dify-{VERSION}.zip'
    lock = {'upstream': 'https://github.com/langgenius/dify', 'tag': VERSION,
            'project': 'policy-rag', 'console': 'http://127.0.0.1:18080',
            'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest() if archive.exists() else None,
            'secret_values_in_report': False}
    (ROOT/'.local/dify-deployment.json').write_text(json.dumps(lock, indent=2)+'\n', encoding='utf-8')
    print('Prepared isolated policy-rag deployment; secrets are not printed')


if __name__ == '__main__':
    main()
