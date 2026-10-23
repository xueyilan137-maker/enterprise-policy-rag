"""Pure deterministic precheck of structured synthetic travel applications.

No authorization, persistence, model extraction, payment, or invoice verification.
Receipt history must be supplied by a trusted server, never treated as user proof.
"""
import re
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from src.policy_data import load_policy, select_version


def money(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:0|[1-9]\d{0,11})\.\d{2}', value):
        raise ValueError('Money requires a nonnegative decimal string with two places')
    return Decimal(value)


def precheck(application, previous_receipt_ids=(), policy=None):
    if not isinstance(application, dict):
        raise ValueError('Application must be an object')
    items = application.get('expense_items')
    if not isinstance(items, list) or not 1 <= len(items) <= 200 or any(not isinstance(i, dict) for i in items):
        raise ValueError('Provide 1..200 structured expense items')
    ids = [i.get('item_id') for i in items]
    if any(not isinstance(id, str) or not id.strip() for id in ids) or len(ids) != len(set(ids)):
        raise ValueError('Item IDs must be unique nonempty strings')
    if not isinstance(previous_receipt_ids, (list, tuple, set)) or any(not isinstance(x, str) for x in previous_receipt_ids):
        raise ValueError('Trusted receipt history must contain strings')
    policy = policy or load_policy()
    findings, version = [], None

    def add(code, severity, clause, item_ids=(), **facts):
        findings.append(dict(code=code, severity=severity, clause=clause, item_ids=list(item_ids), facts=facts))

    def day(value, field, item_ids=()):
        if not value:
            add('MISSING_FIELD', 'needs_materials', 'DOCS', item_ids, field=field)
            return None
        try:
            if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError()
            return date.fromisoformat(value)
        except ValueError:
            add('INVALID_DATE', 'needs_manual_review', 'REVIEW', item_ids, field=field)
            return None

    def amount(value, field, item_ids=()):
        try:
            return money(value)
        except ValueError:
            add('INVALID_MONEY', 'needs_manual_review', 'DUPLICATE', item_ids, field=field)
            return None

    for field in ('employee_id', 'reason', 'destination'):
        if not isinstance(application.get(field), str) or not application[field].strip():
            add('MISSING_FIELD', 'needs_materials', 'DOCS', field=field)
    start = day(application.get('trip_start_date'), 'trip_start_date')
    end = day(application.get('trip_end_date'), 'trip_end_date')
    submitted = day(application.get('submitted_date'), 'submitted_date')
    if start:
        try:
            version = select_version(policy, start.isoformat())
        except ValueError:
            add('NO_APPLICABLE_POLICY', 'needs_manual_review', 'SCOPE')
    trip_valid = start is not None and end is not None and start <= end
    if start and end and not trip_valid:
        add('INVALID_TRIP_INTERVAL', 'needs_manual_review', 'REVIEW')
    scope_valid = application.get('destination_region') == 'CN-mainland' and application.get('employee_type') == 'ordinary'
    if not scope_valid:
        add('UNSUPPORTED_SCOPE', 'needs_manual_review', 'SCOPE')
    if submitted and end:
        elapsed = (submitted-end).days
        if elapsed < 0:
            add('SUBMITTED_BEFORE_TRIP_END', 'needs_manual_review', 'DEADLINE', elapsed_days=elapsed)
        elif version and elapsed > version['submission_days']:
            add('LATE_SUBMISSION', 'needs_manual_review', 'DEADLINE', elapsed_days=elapsed, limit_days=version['submission_days'])
    total = amount(application.get('total_amount'), 'total_amount')
    values, meals, provided, stays = [], defaultdict(list), defaultdict(set), []
    receipts = [i.get('receipt_id', '').strip() if isinstance(i.get('receipt_id'), str) else '' for i in items]
    counts, previous = Counter(r for r in receipts if r), {x.strip() for x in previous_receipt_ids}
    for item, receipt in zip(items, receipts):
        id = item['item_id']
        value = amount(item.get('amount'), 'amount', [id])
        values.append(value)
        if item.get('receipt_present') is not True or not receipt:
            add('MISSING_RECEIPT', 'needs_materials', 'DOCS', [id])
        if receipt and (counts[receipt] > 1 or receipt in previous):
            add('SUSPECTED_DUPLICATE_RECEIPT', 'needs_manual_review', 'DUPLICATE', [id], cross_application=receipt in previous)
        category = item.get('category')
        if category not in ('meal', 'lodging', 'transit'):
            add('UNSUPPORTED_CATEGORY', 'needs_manual_review', 'REVIEW', [id])
            continue
        happened = day(item.get('expense_date'), 'expense_date', [id])
        if happened and trip_valid and not start <= happened <= end:
            add('EXPENSE_OUTSIDE_TRIP', 'needs_manual_review', 'REVIEW', [id])
        if category == 'meal':
            if happened and value is not None:
                meals[happened].append((id, value))
            if not isinstance(item.get('meal_provided'), bool):
                add('MISSING_MEAL_PROVISION', 'needs_materials', 'MEAL', [id])
            elif happened:
                provided[happened].add(item['meal_provided'])
        elif category == 'lodging':
            check_in = day(item.get('check_in'), 'check_in', [id])
            check_out = day(item.get('check_out'), 'check_out', [id])
            nights = item.get('nights')
            if not isinstance(nights, int) or isinstance(nights, bool) or nights <= 0:
                add('INVALID_NIGHTS', 'needs_manual_review', 'LODGE', [id])
            if check_in and check_out:
                actual = (check_out-check_in).days
                if actual <= 0 or nights != actual:
                    add('LODGING_NIGHT_MISMATCH', 'needs_manual_review', 'LODGE', [id], actual_nights=actual)
                if trip_valid and (check_in < start or check_out > end):
                    add('LODGING_OUTSIDE_TRIP', 'needs_manual_review', 'REVIEW', [id])
                for old_in, old_out, old_id in stays:
                    if check_in < old_out and old_in < check_out:
                        add('OVERLAPPING_LODGING', 'needs_manual_review', 'LODGE', [old_id, id])
                stays.append((check_in, check_out, id))
                city = application.get('destination')
                if actual > 0 and value is not None and version and scope_valid and isinstance(city, str) and city.strip():
                    tier = 'A' if city.strip() in policy['city_tiers']['A'] else policy['city_tiers']['domestic_default']
                    limit = money(version['lodging_per_night'][tier])*actual
                    if value > limit:
                        add('LODGING_OVER_LIMIT', 'needs_manual_review', 'LODGE', [id], actual=str(value), limit=str(limit), city_tier=tier)
        elif category == 'transit':
            if not isinstance(item.get('route'), str) or not item['route'].strip() or not item.get('seat_class'):
                add('MISSING_TRANSIT_DETAILS', 'needs_materials', 'TRANSIT', [id])
            elif item['seat_class'] in ('高铁二等座', '经济舱'):
                pass
            elif item['seat_class'] in ('高铁一等座', '商务座', '商务舱'):
                if item.get('prior_approval_present') is not True:
                    add('MISSING_PRIOR_APPROVAL', 'needs_materials', 'TRANSIT', [id])
                    add('TRANSIT_REQUIRES_REVIEW', 'needs_manual_review', 'TRANSIT', [id])
            else:
                add('UNKNOWN_SEAT_CLASS', 'needs_manual_review', 'TRANSIT', [id])
    summed = sum(values, Decimal('0.00')) if all(v is not None for v in values) else None
    if total is not None and summed is not None and total != summed:
        add('TOTAL_MISMATCH', 'needs_manual_review', 'DUPLICATE', actual=str(summed), declared=str(total))
    for happened, entries in sorted(meals.items()):
        daily = sum((v for _, v in entries), Decimal('0.00'))
        if provided[happened] == {True, False}:
            add('CONFLICTING_MEAL_PROVISION', 'needs_manual_review', 'MEAL', [id for id, _ in entries])
        if True in provided[happened] and daily > 0:
            add('MEAL_ALREADY_PROVIDED', 'needs_manual_review', 'MEAL', [id for id, _ in entries], expense_date=happened.isoformat())
        if version and scope_valid and daily > money(version['meal_per_day']):
            add('MEAL_DAILY_OVER_LIMIT', 'needs_manual_review', 'MEAL', [id for id, _ in entries], expense_date=happened.isoformat(), actual=str(daily), limit=version['meal_per_day'])
    for finding in findings:
        suffix = finding.pop('clause')
        finding['clause_ids'] = [policy['policy_id']+'-'+version['version']+'-'+suffix] if version else []
        if version and finding['severity'] == 'needs_manual_review' and suffix != 'REVIEW':
            finding['clause_ids'].append(policy['policy_id']+'-'+version['version']+'-REVIEW')
    severities = {f['severity'] for f in findings}
    status = 'needs_manual_review' if 'needs_manual_review' in severities else 'needs_materials' if findings else 'no_issues_found'
    snapshot = hashlib.sha256(json.dumps(policy, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
    return dict(status=status, is_precheck=True, policy_version=version['version'] if version else None,
        rule_engine_version='0.1.0', policy_snapshot_sha256=snapshot,
        findings=findings, facts=dict(item_sum=str(summed) if summed is not None else None),
        notice='仅为结构化数据规则预审，不是审批、核定报销金额、发票验真或付款。')
