"""Explicit retrieval-only query variants. Never add monetary or city mapping answers."""


def retrieval_query(query, variant='original'):
    if variant not in ('original', 'city-hint'):
        raise ValueError('Unknown retrieval query variant')
    if variant == 'city-hint' and any(word in query for word in ('住宿', '住两晚', '住一晚')):
        return query + ' 城市等级：A类城市、B类城市。住宿标准。'
    return query
