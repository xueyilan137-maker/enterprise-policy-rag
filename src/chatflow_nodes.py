"""Original sandbox-compatible Chatflow code; no network or credentials."""
import json
import re
from datetime import date


def route(query, pending, intervals):
    query = query.strip()
    matches = re.findall(r'(?<!\d)(\d{4})[-年/](\d{1,2})[-月/](\d{1,2})日?(?!\d)', query)
    result = dict(version='', question=query, pending='', message='')
    if not matches:
        result.update(pending=query, message='请补充出差开始日期（YYYY-MM-DD），以确定适用制度。请使用完整年月日。')
        return result
    try:
        days = {date(*map(int, parts)).isoformat() for parts in matches}
    except ValueError:
        result.update(pending=pending or query, message='日期无效，请提供有效的出差开始日期（YYYY-MM-DD）。')
        return result
    if len(days) != 1:
        result.update(pending=query, message='检测到多个日期，请单独确认出差开始日期（YYYY-MM-DD）；本版暂不自动区分起止日期。')
        return result
    day = days.pop()
    # A date-only reply completes the pending question; a new question replaces it.
    remainder = re.sub(r'(?<!\d)\d{4}[-年/]\d{1,2}[-月/]\d{1,2}日?(?!\d)', '', query)
    if pending and not re.sub(r'[\s，。,:：；！!是的为出差开始日期时间号]+', '', remainder):
        result['question'] = pending + '\n出差开始日期：' + day
    versions = [v['version'] for v in intervals if v['effective_from'] <= day <= v['effective_until']]
    if len(versions) != 1:
        result['message'] = '该出差开始日期没有唯一适用制度，需人工确认；不能自动套用最新版。'
    else:
        result['version'] = versions[0]
    return result


def guard(text, records, version, required_clause_ids=None, allow_excerpt=False, source_only=False):
    """Validate citations and known boundaries; separately label retrieved excerpts."""
    refusal = '现有检索依据不足，无法可靠回答，请补充信息或联系人工复核。'
    required = set(required_clause_ids or [])
    allowed = set()
    excerpts = {}

    def reject(reason, can_quote=False):
        if allow_excerpt and can_quote and required and required.issubset(excerpts):
            quoted = '\n\n'.join(excerpts[id] for id in required_clause_ids)
            return dict(answer='以下为适用制度原文，供核对；不构成报销金额核定：\n\n'+quoted+
                        '\n\n依据：'+'、'.join(required_clause_ids)+'（原创合成制度，仅供演示）',
                        validation_status='evidence_excerpt', validation_reason=reason)
        return dict(answer=refusal, validation_status='refused', validation_reason=reason)

    if not isinstance(records, list):
        return reject('invalid_evidence')
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get('content'), str):
            return reject('invalid_evidence')
        content = record['content']
        ids = set(re.findall(r'\bTRAVEL-v\d+-[A-Z]+\b', content))
        if any(not item.startswith('TRAVEL-' + version + '-') for item in ids):
            return reject('foreign_version')
        allowed.update(ids)
        if len(ids) == 1 and ids.issubset(required):
            excerpts[next(iter(ids))] = content
    if not required.issubset(allowed):
        return reject('missing_required_evidence')
    if source_only and required:
        return reject('review_policy_source_only', True)
    try:
        raw = text.strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw)
        obj = json.loads(raw)
        refs = obj['clause_ids']
        answer = obj['answer']
        if obj['supported'] is not True or not isinstance(answer, str) or not answer.strip():
            return reject('model_unsupported', True)
        if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or r not in allowed for r in refs):
            return reject('invalid_citations', True)
        if not required.issubset(set(refs)):
            return reject('missing_required_citations', True)
        settlement = (
            r'(?:报销|支付|付款|可报|能报|只报|仅报)(?:金额)?(?:为|是|至多|最多|不超过)?\s*[￥¥]?\d[\d,.]*\s*元'
            r'|(?:仅能|只能|仅可|只可|最多|允许|可予|准予)(?:报销|支付|付款)[^。；\n]{0,16}(?:金额|费用|限额|部分)'
            r'|(?:整笔|全部|一律|全额)[^。；\n]{0,8}(?:不予报销|不能报销|不得报销)'
        )
        if required and re.search(settlement, answer):
            return reject('settlement_claim', True)
        mentioned = set(re.findall(r'\bTRAVEL-v\d+-[A-Z]+\b', answer))
        if not mentioned.issubset(set(refs)):
            return reject('unlisted_citation', True)
        return dict(answer=answer+'\n\n依据：'+'、'.join(refs)+'（原创合成制度，仅供演示）',
                    validation_status='generated', validation_reason='ok')
    except (ValueError, KeyError, TypeError, AttributeError):
        return reject('invalid_model_schema', True)
