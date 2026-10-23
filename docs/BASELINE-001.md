# 首次真实检索基线

日期：2026-10-21。Dify1.17.1，通义插件0.2.23，text-embedding-v3，provider langgenius/tongyi/tongyi。两个独立版本知识库；高质量索引、semantic_search、top_k=3，无rerank，无分数阈值。

每版1份合成制度文档，10个片段（1个文档说明+9个条款）。已通过segments API确认18条款完整且按版本分离。实际embedding维度尚未单独读取，不作假定。

三条真实检索 D01/D02/D03 请求均成功，条款Recall@3依次0.5/0.5/1.0，均值0.6667，三条未发现跨版本条款。首次请求4.172秒，后两条0.406/0.391秒；不是稳定性能基准。未测生成回答，没有模型回答准确率或账单金额结论。标注仍为待人工审核的调试草稿，不能用作正式简历效果指标。

D01/D02漏召回CITY：问题需同时知道城市分类及住宿限额。当前单条款向量检索能召回LODGE，不能确保关联条款完整。后续先建立带引用问答闭环，再用固定调试集比较查询改写/补充检索与混合检索；保留当前基线，不先改top_k掩盖问题。

复现：运行tools/import_knowledge.py --apply；从私有knowledge-state.json中取得两个dataset ID，配置检索脚本的环境变量，运行tools/evaluate_retrieval.py --limit 3。密钥留在.local，不进入仓库。原始报告在.local/evaluations。
