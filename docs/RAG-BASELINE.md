# RAG 基线准备与运行

当前完成：合成数据、版本路由、Markdown 与来源哈希、检索评测脚本和无网络契约测试。
已完成首次真实 Dify 知识库/embedding与三条检索基线，见BASELINE-001；最小Chatflow真实生成冒烟已完成（CHATFLOW-001），正式答案效果评测尚未完成。

## 数据

`data/policies/travel.json` 是规则及制度正文的共同来源。运行 `python tools/build_corpus.py` 生成 `data/corpus/TRAVEL-v1.md`、`TRAVEL-v2.md` 与 manifest。共18个带稳定ID的条款。都为本项目原创合成数据，不是真实企业标准。

`data/eval/dev.jsonl` 仅12个调试草稿（9个检索，另3个分别为追问、无版本、无答案场景）；答案尚未人工核对。不是设计中已完成的100条评测集。保留集尚未建立，不从这些问题机械改写凑数。当前自动检索评测只测 retrieve 行，其余用于后续 Chatflow 评测。

## Dify 配置基线（已真实建立）

第一阶段每个版本使用独立知识库，前置代码按出差开始日期选择版本，避免基线依赖尚未验证的元数据过滤行为。分别导入对应 Markdown，不把两个版本放同一知识库。后续元数据过滤需单独验证越界用例再比较。

高质量索引、向量检索、top_k=3、不启用 rerank、不设分数阈值；以 `## ` 标题作为分段边界，并在导入预览检查条款完整性。模型/提供商/维度与分段实际参数必须记入运行记录，在首次入库前选定并记录，不能直接宣称当前已锁定。

需要真实知识库 API Key（不同于百炼 Key 与应用 app Key），以及两个知识库 ID。根据实际实例「访问 API」文档核对接口。脚本使用 `POST /v1/datasets/{id}/retrieve`，解析 `records[].segment.content`，不符合时显式报错，不能默默认为检索成功。

## 命令

无网络工程回归：`python -m unittest discover -s tests -v`。

在当前 PowerShell 设置环境变量 `DIFY_API_BASE`、`DIFY_DATASET_API_KEY`、`DIFY_DATASET_V1`、`DIFY_DATASET_V2` 后运行 `python tools/evaluate_retrieval.py --limit 3`。示例键名见 `.env.example`，脚本不会自动加载 `.env`，不在聊天中发送密钥。

默认最多3次真实检索、间隔7秒；每次可能消耗 embedding 调用，运行前确认供应商与额度。无凭据直接停止，不启用 mock 回退。结果位于 `.local/evaluations/`，不会提交公开仓库。

指标是条款 Recall@K，不是模型回答准确率。接口错误/版本泄漏单列，不混入成功平均值。未设分数阈值不能用空结果判断无答案；拒答需后续答案层实验。检索中包含条款ID只是召回证据，不代表回答内容正确。

## 参考与限制

Dify API文档入口：https://docs.dify.ai/en/api-reference/guides/get-started 。版本/接口契约在真实联调后记录；当前真实API验收取代早期仅响应夹具阶段，见BASELINE-001；夹具测试仍不代表模型效果。


## 可复现入库工具（已真实验证）

`python tools/import_knowledge.py`默认只显示计划，不联网；`--apply`读取`.local/dataset-api.json`，创建按版本隔离的知识库并导入，记录哈希、模型、dataset/document/batch和索引状态到`.local/knowledge-state.json`，不在状态中存Key。重复运行查询索引，不重复上传；源内容或模型变更要求显式新状态重建，上传结果不确定时停止并人工核对，不盲目重试。

已验证官方1.17.1接口：POST /v1/datasets、POST /v1/datasets/{id}/document/create-by-text、GET /v1/datasets/{id}/documents/{batch}/indexing-status、GET segments以及retrieve。两版均completed，各10片段；结果见BASELINE-001。页面服务API显示的URL遗漏18080端口，本机实际使用http://127.0.0.1:18080/v1，暂未修改部署URL配置。


最小问答首版见CHATFLOW-001，当前city-hint第2版见CHATFLOW-002。三条探索见RETRIEVAL-EXPERIMENT-001，全9条初核副本对照见RETRIEVAL-EXPERIMENT-002。评测默认original保持原基线；DSL生成默认city-hint。dev.source-reviewed.jsonl只是Codex源文初核副本，仍待人类审核，不能充当保留集。


## 第3版关联依据

当前默认DSL为city-hint+有界REVIEW补检索，见CHATFLOW-003；`--no-related-review`生成原先city-hint结构。主检索参数不变，补检索一次top1、合并最多4条；独立工具`python tools/evaluate_related.py`的配对实验见RETRIEVAL-EXPERIMENT-003。主Recall@3与合并覆盖率分开，后者不能写成Recall@3或回答准确率。保留简短餐费问法补日期后保守拒答及开发时无依据核定金额失败记录。


## 第4版输出策略与规则共源

当前问答见CHATFLOW-004：限定餐费处理分支展示本轮真实依据原文，非检索参数实验，不重算或覆盖上述历史基线。规则模块见RULES-001；城市列表结构化后两版正文渲染哈希与现有入库一致，无需重建知识库。JSON源哈希改变，历史实验仍按当时快照解释。
