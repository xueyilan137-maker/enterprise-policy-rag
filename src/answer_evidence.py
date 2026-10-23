"""Bounded evidence requirements for development consultation intents.

The output contains identifiers only, never fabricated policy excerpts.
"""
def consultation_evidence(question, version):
    clauses = []
    transport = any(w in question for w in ('高铁', '车票', '商务舱', '经济舱', '交通费'))
    if '餐费' in question and any(w in question for w in ('凭证', '供餐', '提供午餐', '说明', '材料')):
        clauses = ['MEAL', 'DOCS']
    elif transport and any(w in question for w in ('批准', '通过', '审批')):
        clauses = ['TRANSIT', 'REVIEW']
    elif transport and any(w in question for w in ('住宿', '餐费')):
        clauses = ['TRANSIT']
    elif any(w in question for w in ('城市', 'A类', 'B类')) and any(w in question for w in ('名单', '境外', '港澳台', '直接套')):
        clauses = ['CITY']
    elif '总额' in question and any(w in question for w in ('明细', '合计', '核对')):
        clauses = ['DOCS', 'DUPLICATE']
    elif any(w in question for w in ('验真', '真伪', '付款')):
        clauses = ['DOCS', 'REVIEW']
    return ['TRAVEL-'+version+'-'+c for c in clauses]
