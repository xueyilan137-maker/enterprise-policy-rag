"""Rebuild version-isolated Dify knowledge bases from original synthetic policies.

Default is a no-network plan. --apply requires an explicitly selected private
JSON credentials file; API keys are never included in the persisted run state.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.policy_data import ROOT, load_policy, render_document

RETRIEVAL = dict(search_method='semantic_search', reranking_enable=False,
                 top_k=3, score_threshold_enabled=False)


def import_plan(model, provider):
    policy = load_policy()
    return [dict(version=v['version'], name=f"星桥差旅制度-{v['version']}",
                 text=render_document(policy, v), embedding_model=model,
                 embedding_model_provider=provider) for v in policy['versions']]


def run(config, state_path, model, provider):
    base = config['DIFY_API_BASE'].rstrip('/')
    url = urlparse(base)
    if url.username or url.password or url.query or url.fragment or not (
        url.scheme == 'https' or url.scheme == 'http' and url.hostname in ('127.0.0.1', 'localhost')
    ):
        raise ValueError('Use HTTPS or local HTTP, without URL credentials')
    key = config['DIFY_DATASET_API_KEY']
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    if state and state.get('api_base') != base:
        raise ValueError('State belongs to a different Dify instance')
    state.setdefault('api_base', base)
    state.setdefault('versions', {})

    def call(path, payload=None):
        req = Request(base+path, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'})
        with urlopen(req, timeout=90) as response:
            return json.load(response)

    def save():
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = state_path.with_suffix('.tmp')
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        temp.replace(state_path)

    for item in import_plan(model, provider):
        version = item['version']
        digest = hashlib.sha256(item['text'].encode()).hexdigest()
        record = state['versions'].get(version)
        if record and (record['sha256'] != digest or record['embedding_model'] != model
                       or record['embedding_model_provider'] != provider):
            raise ValueError('Source/model changed: use a new state file for an explicit rebuild')
        if not record:
            result = call('/datasets', dict(name=item['name'], description='原创合成演示制度，按版本隔离',
                permission='only_me', indexing_technique='high_quality',
                embedding_model=model, embedding_model_provider=provider, retrieval_model=RETRIEVAL))
            record = dict(dataset_id=result['id'], sha256=digest,
                          embedding_model=model, embedding_model_provider=provider)
            state['versions'][version] = record
            save()
        if record.get('upload_pending'):
            raise ValueError('Previous upload outcome unknown; inspect Dify documents before retrying')
        if not record.get('document_id'):
            record['upload_pending'] = True
            save()
            result = call(f"/datasets/{record['dataset_id']}/document/create-by-text", dict(
                name=f'TRAVEL-{version}.md', text=item['text'], indexing_technique='high_quality',
                doc_form='text_model', doc_language='Chinese', embedding_model=model,
                embedding_model_provider=provider, retrieval_model=RETRIEVAL,
                process_rule={'mode': 'custom', 'rules': {'pre_processing_rules': [],
                    'segmentation': {'separator': '\n## ', 'max_tokens': 700, 'chunk_overlap': 0}}}))
            record.update(document_id=result['document']['id'], batch=result['batch'], upload_pending=False)
            save()
        status = call(f"/datasets/{record['dataset_id']}/documents/{record['batch']}/indexing-status")
        record['indexing_status'] = status
        save()
        print(version, json.dumps(status, ensure_ascii=False))
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--config', type=Path, default=ROOT/'.local/dataset-api.json')
    parser.add_argument('--state', type=Path, default=ROOT/'.local/knowledge-state.json')
    parser.add_argument('--model', default='text-embedding-v3')
    parser.add_argument('--provider', default='langgenius/tongyi/tongyi')
    args = parser.parse_args()
    if not args.apply:
        for item in import_plan(args.model, args.provider):
            print(item['version'], item['name'], len(item['text']), 'characters', args.model)
        return
    try:
        run(json.loads(args.config.read_text(encoding='utf-8')), args.state, args.model, args.provider)
    except Exception as exc:
        # HTTP response bodies may include provider diagnostics: do not print secrets.
        print(f'Import stopped: {type(exc).__name__}: {str(exc) if isinstance(exc, ValueError) else "inspect private configuration or Dify logs"}', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
