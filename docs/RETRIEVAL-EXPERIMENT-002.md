# 全调试检索对照与标注初核

日期：2026-10-21。本轮包含关机重启后的恢复核查；Dify及知识库数据保留，未重复入库或安装插件。

## 协议

先按合成源文初核12条调试草稿，保留原dev.jsonl，新增dev.source-reviewed.jsonl。初核由Codex完成，**没有人类审核**；D03新增REVIEW必要依据，理由见EVAL-ANNOTATION-REVIEW-001。因此本报告与BASELINE-001不是同一标注/样本口径。

两组使用同一初核文件（SHA256 `dcd1dda273a5e295f318deeee8a51bf13044e9bc9f0842ebe6608a22c327bf6e`）的全部9条retrieve，按同一开始日期选择既有隔离知识库。text-embedding-v3、向量检索top_k=3、无重排/阈值；只改变城市查询提示。先original后city-hint，各组内请求间隔7秒；没有修改源文或重新入库。

## 实际结果

| 样本 | original Recall@3 | city-hint Recall@3 | 观察 |
|---|---:|---:|---|
| D01 | 0.5 | 1.0 | 提示后补齐CITY |
| D02 | 0.5 | 1.0 | 提示后补齐CITY |
| D03 | 0.5 | 0.5 | 两组都漏REVIEW，保留失败点 |
| D04 | 1.0 | 1.0 | 未变 |
| D05 | 1.0 | 1.0 | DOCS保留；提示引入CITY，取代TRANSIT噪声，不能称所有结果完全不变 |
| D06 | 1.0 | 1.0 | 未变 |
| D07 | 1.0 | 1.0 | 未变 |
| D08 | 1.0 | 1.0 | 未变 |
| D12 | 1.0 | 1.0 | 未变；检索命中不等于注入抵抗通过 |
| 均值 | 0.8333 | 0.9444 | 仅此9条调试检索，不是回答准确率 |

18次请求全部成功，两组都没有跨版本条款。比较工具逐条检查2条改善、7条召回率不变、0条下降、0条错误。该门槛不代表独立测试/人类审核通过，也未评估全部噪声和排名影响。

私有证据：`.local/evaluations/retrieval-1792568453805564700.json`（original）、`retrieval-1792568513800015900.json`（city-hint）、`retrieval-comparison-002.json`。报告新增cases/policy哈希、检索参数与实际数据集ID（仅.local）；比较时哈希/参数/样本不匹配直接报错，不能用整体均值掩盖逐条回归。

## 复现

按RAG-BASELINE配置进程环境变量后分别运行：

```powershell
python tools/evaluate_retrieval.py --limit 9 --cases data/eval/dev.source-reviewed.jsonl --query-variant original
python tools/evaluate_retrieval.py --limit 9 --cases data/eval/dev.source-reviewed.jsonl --query-variant city-hint
python tools/compare_retrieval.py <original报告> <candidate报告> --output .local/evaluations/comparison.json
```

## 后续边界

开发集回归允许进入Chatflow真实生成回归；保留原版DSL和原基线，独立保留集仍未建立。D03“超标准转人工”所需REVIEW漏召回未解决，本轮不同时加入补充检索/重排，以免混淆单因素结论。完整年月日和结构化日期条件不同，不能将检索输入等同端到端Chatflow输入。


后续D03采用有界同版本补检索，见RETRIEVAL-EXPERIMENT-003；该方案没有改变本报告主Recall@3结果，新增最多四条上下文覆盖指标。
