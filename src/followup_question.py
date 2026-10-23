"""Remove superseded date text only when a date-only turn completes a pending question."""
import re


def normalized_followup(result, query, pending):
    if result['version'] and pending and result['question'] != query.strip() and result['question'].startswith(pending+'\n出差开始日期：'):
        cleaned = re.sub(r'(?<!\d)\d{4}[-年/]\d{1,2}[-月/]\d{1,2}日?(?!\d)', '', pending)
        result['question'] = cleaned.strip() + result['question'][len(pending):]
    return result
