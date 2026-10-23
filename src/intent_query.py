"""Development retrieval variant: prioritize the disputed expense category.

Contains search terms only. Does not supply policy content or decisions.
"""
from src.retrieval_query import retrieval_query


def intent_query(question, variant='city-hint'):
    transport = any(word in question for word in ('高铁', '车票', '商务舱', '经济舱', '交通费'))
    approval = any(word in question for word in ('批准', '通过', '审批'))
    if transport and approval:
        return '交通费用 席别 事前批准证明 预审与人工复核'
    return retrieval_query(question, variant)
