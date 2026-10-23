"""Synthetic policy source, deterministic versioning and clause rendering."""
import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/policies/travel.json'


def load_policy(path=SOURCE):
    policy = json.loads(Path(path).read_text(encoding='utf-8'))
    if policy['data_kind'] != 'synthetic_demo':
        raise ValueError('Only synthetic demo policies are supported')
    if policy['city_tiers']['domestic_default'] != 'B' or not policy['city_tiers']['A'] or any(
        not isinstance(city, str) or not city for city in policy['city_tiers']['A']
    ):
        raise ValueError('Invalid synthetic city tier configuration')
    ids = [c['id'] for c in policy['clauses']]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError('Clause IDs must be unique and nonempty')
    versions = sorted(policy['versions'], key=lambda v: v['effective_from'])
    if len({v['version'] for v in versions}) != len(versions):
        raise ValueError('Version IDs must be unique')
    for i, v in enumerate(versions):
        start, end = date.fromisoformat(v['effective_from']), date.fromisoformat(v['effective_until'])
        if start > end or (i and versions[i-1]['effective_until'] >= v['effective_from']):
            raise ValueError('Invalid or overlapping version intervals')
        if not isinstance(v['submission_days'], int) or v['submission_days'] < 0:
            raise ValueError('Invalid submission deadline')
        for amount in [*v['lodging_per_night'].values(), v['meal_per_day']]:
            if not isinstance(amount, str):
                raise ValueError('Money must use decimal strings')
            try:
                value = Decimal(amount)
                if not value.is_finite() or value < 0 or value.as_tuple().exponent != -2:
                    raise ValueError('Money must be finite, nonnegative and have two decimal places')
            except InvalidOperation as exc:
                raise ValueError('Invalid money') from exc
    return policy


def select_version(policy, trip_start_date):
    if not trip_start_date:
        raise ValueError('trip_start_date is required')
    day = date.fromisoformat(trip_start_date).isoformat()
    matches = [v for v in policy['versions'] if v['effective_from'] <= day <= v['effective_until']]
    if len(matches) != 1:
        raise ValueError('No unique applicable policy version')
    return matches[0]


def render_clauses(policy, version):
    values = dict(lodging_A=version['lodging_per_night']['A'],
                  lodging_B=version['lodging_per_night']['B'],
                  meal=version['meal_per_day'], days=version['submission_days'],
                  cities_A='、'.join(policy['city_tiers']['A']))
    return [dict(clause_id=f"{policy['policy_id']}-{version['version']}-{c['id']}",
                 title=c['title'], text=c['text'].format(**values)) for c in policy['clauses']]


def render_document(policy, version):
    header = (f"# {policy['organization']} 差旅制度 {version['version']}\n\n"
              f"合成演示数据，不是真实企业制度。\n\n"
              f"生效日期：{version['effective_from']} 至 {version['effective_until']}（含首尾日）。\n"
              f"版本选择依据：出差开始日期；币种：{policy['currency']}。\n\n")
    return header + '\n\n'.join(f"## {c['clause_id']} {c['title']}\n{c['text']}" for c in render_clauses(policy, version)) + '\n'


def build(output):
    policy = load_policy()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'documents': []}
    for v in policy['versions']:
        text = render_document(policy, v)
        name = f"TRAVEL-{v['version']}.md"
        (output / name).write_bytes(text.encode('utf-8'))
        manifest['documents'].append(dict(file=name, version=v['version'],
            effective_from=v['effective_from'], effective_until=v['effective_until'],
            sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
            clauses=[c['clause_id'] for c in render_clauses(policy, v)]))
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return manifest
