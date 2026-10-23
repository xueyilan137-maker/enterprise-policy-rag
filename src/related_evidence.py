"""Bounded related evidence retrieval; query routing contains no policy answers."""
import re


def review_needed(question):
    return '餐费' in question and any(word in question for word in
        ('报销', '可以', '能否', '超', '分别', '怎么办', '处理'))


def evidence_ids(records, version):
    if not isinstance(records, list):
        raise ValueError('Evidence must be a list')
    ids = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get('content'), str):
            raise ValueError('Evidence requires string content')
        found = set(re.findall(r'\bTRAVEL-v\d+-[A-Z]+\b', record['content']))
        if any(not item.startswith('TRAVEL-' + version + '-') for item in found):
            raise ValueError('Foreign policy version in evidence')
        ids.update(found)
    return ids


def review_plan(question, records, version):
    ids = evidence_ids(records, version)
    needed = review_needed(question) and 'TRAVEL-' + version + '-REVIEW' not in ids
    return dict(needed='yes' if needed else 'no', query='预审与人工复核')


def merge_review(primary, supplemental, version):
    evidence_ids(primary, version)
    evidence_ids(supplemental, version)
    target = 'TRAVEL-' + version + '-REVIEW'
    if target in evidence_ids(primary, version):
        return {'result': primary[:3]}
    matches = [r for r in supplemental if target in evidence_ids([r], version)]
    # A real retrieval miss remains missing evidence, never insert source text locally.
    return {'result': primary[:3] + matches[:1]}
