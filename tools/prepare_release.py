"""Build an allowlisted source ZIP; no Git, network, credentials or runtime data copied."""
import argparse
import hashlib
import json
import os
import re
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {'README.md', 'LICENSE', 'AGENTS.md', '.gitignore', '.dockerignore', 'requirements.txt', 'requirements-dev.txt'}
TREES = {'src': {'.py'}, 'tools': {'.py', '.ps1'}, 'tests': {'.py'}, 'docs': {'.md'},
         'web': {'.html', '.css', '.js'}, 'deploy': {'.yml', '.Dockerfile'},
         'dify': {'.yml'}, 'data': {'.json', '.jsonl', '.md', '.csv'}, 'config': {'.json'}}
SENSITIVE_PARTS = {'.local', '.git', '.venv', 'node_modules', '__pycache__'}


def selected(root):
    candidates = [root/name for name in ROOT_FILES if (root/name).is_file()]
    for tree in TREES:
        base = root/tree
        if not base.exists():
            continue
        if base.is_symlink() or getattr(base.stat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('Linked source tree rejected')
        for directory, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = [name for name in dirs if name not in SENSITIVE_PARTS and
                       not (Path(directory)/name).is_symlink() and
                       not getattr((Path(directory)/name).stat(), 'st_file_attributes', 0) & 0x400]
            candidates.extend(Path(directory)/name for name in files)
    result = []
    for path in sorted(candidates):
        relative = path.relative_to(root)
        # Do not traverse outside the source tree through links/junctions.
        if path.is_symlink() or any(part in SENSITIVE_PARTS for part in relative.parts):
            continue
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Source path escapes root')
        if len(relative.parts) == 1:
            include = relative.name in ROOT_FILES
        else:
            include = path.suffix in TREES.get(relative.parts[0], set())
        if include:
            if path.name.startswith('.env') or path.name.endswith(('.bound.yml', '.export.yml')):
                raise ValueError('Private configuration in public tree: '+relative.as_posix())
            result.append(relative)
    return result


def known_private_values(root):
    values = set()
    def visit(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and len(value) >= 12 and re.search(r'key|token|password|dataset_id', key, re.I):
                    values.add(value.encode())
                else:
                    visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)
    for name in ('dataset-api.json', 'precheck-app-api.json', 'business-auth.json', 'knowledge-state.json'):
        path = root/'.local'/name
        if path.exists():
            visit(json.loads(path.read_text(encoding='utf-8-sig')))
    path = root/'.local/rules.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('RULES_API_TOKEN='):
                values.add(line.split('=', 1)[1].encode())
    return values


def validate_dsl(name, content):
    obj = json.loads(content)
    workflow = obj['workflow']
    for var in workflow.get('environment_variables', []):
        value = var.get('value')
        if value and not (isinstance(value, str) and value.startswith('REPLACE_')):
            raise ValueError('Bound environment value in DSL: '+name)
    for node in workflow['graph']['nodes']:
        data = node['data']
        if any(not str(id).startswith('REPLACE_DATASET_') for id in data.get('dataset_ids', [])):
            raise ValueError('Bound dataset in DSL: '+name)
        if data.get('type') == 'http-request':
            if 'REPLACE_' not in data.get('url', ''):
                # Runtime URL variables are allowed; literal deployment endpoints are not.
                if not data.get('url', '').startswith('{{#env.'):
                    raise ValueError('Deployment URL in DSL: '+name)
            for header in str(data.get('headers', '')).splitlines():
                if re.match(r'(?i)\s*(authorization|x-api-key|api-key)\s*:', header):
                    value = header.split(':', 1)[1].strip()
                    if value and '{{#env.' not in value and not value.startswith('REPLACE_'):
                        raise ValueError('Embedded authentication header in DSL: '+name)
    if re.search(r'(?i)(?:https?://)[^\s"<>]*\.(?:trycloudflare\.com|loca\.lt|lhr\.life)', content):
        raise ValueError('Temporary endpoint in DSL: '+name)


def build(root, output):
    root = root.resolve()
    payload = {}
    private = known_private_values(root)
    for relative in selected(root):
        name = relative.as_posix()
        body = (root/relative).read_bytes()
        if name.endswith('/human-reviews.json'):
            # Do not export private evidence pointers or transfer human approval to a new installation.
            body = b'{"reviews": [], "notice": "Distribution copy: original approvals and evidence remain private."}\n'
        if any(value in body for value in private):
            raise ValueError('Known private value detected in '+name)
        text = body.decode('utf-8-sig')
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,})', text):
            raise ValueError('Credential pattern detected in '+name)
        if name.startswith('dify/'):
            validate_dsl(name, text)
        payload[name] = body
    manifest = dict(kind='source_delivery_candidate', private_runtime_included=False,
        human_approvals_transferred=False, dify_version='1.17.1', chatflow_version=5, workflow_version=4,
        notice='No model performance guarantee. Known-value and pattern scan is not a universal secret detector.',
        files={name:hashlib.sha256(body).hexdigest() for name,body in payload.items()})
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects earlier delivery evidence.
    with output.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, body in payload.items():
                archive.writestr(name, body)
            archive.writestr('DELIVERY-MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    return dict(archive=str(output), files=len(payload), sha256=hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(build(ROOT, args.output or ROOT/'.local/releases'/('source-'+str(time.time_ns())+'.zip')), ensure_ascii=False))
    except (ValueError, FileExistsError) as exc:
        raise SystemExit(str(exc)) from None
