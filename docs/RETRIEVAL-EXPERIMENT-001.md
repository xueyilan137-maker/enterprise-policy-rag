# CITY查询提示单因素探索

后续全调试回归与接入结论见RETRIEVAL-EXPERIMENT-002、CHATFLOW-002；本文保持首轮探索原记录。

日期：2026-10-21。保留BASELINE-001及原始报告；本实验不修改知识库或已发布Chatflow。

使用相同D01/D02/D03、相同版本知识库、text-embedding-v3、semantic_search、top_k=3、不重排、不设阈值。唯一改变：住宿类查询末尾增加` 城市等级：A类城市、B类城市。住宿标准。`，不包含城市映射或金额答案。D03不追加提示，作为未修改查询的对照。

| 查询 | 原查询同期复跑 Recall@3 | city-hint Recall@3 |
|---|---:|---:|
| D01 | 0.5 | 1.0 |
| D02 | 0.5 | 1.0 |
| D03 | 1.0 | 1.0 |
| 均值 | 0.6667 | 1.0 |

两组各3次真实请求均成功，均无跨版本条款；提示组D01/D02同时召回CITY与LODGE。原查询复跑仍漏CITY，与BASELINE-001一致。执行顺序为提示组后原查询同期复跑，每组内间隔7秒；不是随机化性能实验，不把耗时差异归因于优化。

私有原始报告：提示组`.local/evaluations/retrieval-1792566619887708000.json`；同期原查询`.local/evaluations/retrieval-1792566716864991800.json`。报告包含原始/实际查询、逐条召回与错误状态，不含凭据。

复现：沿用RAG-BASELINE环境变量，运行`python tools/evaluate_retrieval.py --limit 3 --query-variant city-hint`，原查询为`--query-variant original`（默认）。参数只作用于评测，不更改已发布Chatflow或入库配置。

结论仅为三条调试草稿上的候选策略；标注未人工审核，尚未在全部9条检索草稿、独立保留集及Chatflow回答上验证，不能称检索整体达到100%或回答准确率100%。下一步扩大调试回归并审核标注，确认无回归后再接入Chatflow。
