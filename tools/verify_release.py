"""Verify and smoke-test an unpacked source delivery using the current Python dependencies."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def unpack(archive, target):
    if target.exists():
        raise ValueError('Use a fresh verification directory')
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive members')
        manifest = json.loads(source.read('DELIVERY-MANIFEST.json'))
        if set(names) != set(manifest['files']) | {'DELIVERY-MANIFEST.json'}:
            raise ValueError('Unexpected archive members')
        bodies = {}
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or '.local' in path.parts:
                raise ValueError('Unsafe archive path')
            body = source.read(name)
            if name != 'DELIVERY-MANIFEST.json' and hashlib.sha256(body).hexdigest() != manifest['files'][name]:
                raise ValueError('Archive hash mismatch')
            bodies[name] = body
    target.mkdir(parents=True, exist_ok=False)
    for name, body in bodies.items():
        path=target/name;path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(body)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    args=parser.parse_args()
    target=ROOT/'.local/releases'/('unpacked-'+str(time.time_ns()))
    manifest=unpack(args.archive,target)
    checks=[]
    for name, command in [
        ('engineering', [sys.executable,'-m','unittest','discover','-s','tests','-v']),
        ('offline_rule', [sys.executable,'tools/precheck_example.py','data/examples/expense-001.json']),
        ('knowledge_plan', [sys.executable,'tools/import_knowledge.py'])]:
        run=subprocess.run(command,cwd=target,capture_output=True,timeout=120)
        (target.parent/(target.name+'-'+name+'.log')).write_bytes(run.stdout+b'\n'+run.stderr)
        checks.append(dict(name=name,exit_code=run.returncode))
        print(name,run.returncode,flush=True)
        if run.returncode:
            break
    report=dict(archive_sha256=hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        unpacked=str(target),source_files=len(manifest['files']),checks=checks,
        clean_source_without_private_state=True,
        dependency_environment='existing Python environment; not a fresh dependency installation',
        docker_reinstalled=False,model_calls=False)
    path=target.parent/(target.name+'-check.json')
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved',path)
    if len(checks)!=3 or any(c['exit_code'] for c in checks):
        raise SystemExit(1)


if __name__=='__main__':
    main()
