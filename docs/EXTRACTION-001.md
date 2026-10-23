# 申请说明模型提取与服务端核验

本篇记录第2版首次接通的历史验收。当前格式修复、协议与发布状态见[EXTRACTION-002](EXTRACTION-002.md)，下述原始失败及用量保持不变。

2026-10-22。Markdown与可提取文本PDF已接通真实qwen3.7-flash提取，CSV仍确定性解析。复用同一预审应用及API密钥，本地发布Workflow第2版；问答Chatflow仍第4版。未创建新知识库、插件、应用或部署密钥，未改原检索基线。

## 流程与接口

1. POST `/v1/materials?filename=note.md`上传UTF-8原始Markdown字节（text/markdown或text/plain），或上传`.pdf`（application/pdf）。原文、提取文本、哈希、格式与页码范围保存在私有SQLite。
2. POST `/v1/extractions`，仅提交`narrative_material_id`和`csv_material_id`。服务端校验归属/材料可读性，创建异步提取任务，首次202；同员工、两份材料与提取协议版本一致时复用原任务200，不自动重试。
3. GET `/v1/extractions/{id}`查看执行状态、原始模型输出、候选核验、引用/行号/页码、问题、耗时/token和Dify运行ID；仅本人可查，越权404。
4. 仅任务completed且validation.status=validated时，POST `/v1/applications/from-extraction`，提交extraction_id及Idempotency-Key。服务端从保存的结果与CSV组装申请，不接受客户端字段覆盖，关联两份材料和提取记录。其它状态422。
5. 延用原异步precheck接口执行代码规则并查询报告。validated表示提取数据满足已实现核验，completed表示执行完成，都不是报销审批。

模型只提取出发/返程/提交日期、目的地、行程范围、事由、申请总额七字段，每字段必须有value/quote；缺失用两个null。日期只规范化明确完整年月日，不继承年份；预算、标准或限额不能替代申请总额。身份与费用明细不交给模型选择。

Workflow新增action=extract分支返回待核验model_json，原规则分支默认precheck；后台适配器提取请求同时传application_json="{}"保持旧必填接口兼容。Dify界面的候选输出本身未经服务端核验，不能直接作为业务报告。既有7项规则API回归通过。

## 核验与边界

Pydantic检查结构和字段集合，代码检查逐字quote确在提取文本且只出现一次；保存字符范围、行号及PDF实际页码。日期/金额须被quote支持；独立检查明确角色日期、多值日期冲突、明确申请总额、日期顺序、CSV费用/住宿日期范围以及Decimal合计。仅原文明示境内/中国大陆才接收CN-mainland，不用城市常识补范围。已识别的忽略规则/核定付款指令转人工，材料内容始终作数据。

这些是有限的类型、字面证据和一致性检查，不能证明所有语义蕴含或通用抗注入能力。日期角色和总额需符合当前已支持的明确表述；未支持/歧义表述停在人工核对，不以模型常识补齐。目的地/事由的字面引用也不能证明业务真实性；凭证/审批仍未验真。

任务执行状态与核验状态分开：completed内可为validated、needs_materials、needs_manual_review。格式异常转人工；网络结果不确定记indeterminate，不自动重跑。服务器重启对遗留任务保守标记，与原预审任务一致；单进程线程执行器仍不是独立持久队列。

Markdown最多256 KiB；PDF最多2 MiB、10页；提取文本最多20000字符。PDF加密、任一页无文本、提取失败或明显不可读时拒绝，不接OCR、不丢弃空页后假装完整。pypdf不执行脚本或访问材料中的链接，但本机解析并非隔离沙箱，不能将大小/页数限制说成完整资源耗尽防护；复杂表格/乱码等仍需人工核对。

解析身份包含格式：`narrative-text-1.0.1-md/pdf`，避免同一字节以不同格式上传时误用缓存。提取协议`travel-extract-1.0.0`；更新提示/校验协议时应显式变更版本，已有失败任务保留。`pypdf==6.16.1`为运行依赖；reportlab仅在requirements-dev.txt生成合成PDF，Windows存在simhei.ttf时内嵌字体，否则使用CID字体。本轮合成PDF已渲染目视核对，生成文件/预览留在.local，不作为公开语料发布。

## 真实验收与限制

85项工程测试通过（原73+7项文档/核验+3项提取接口/恢复+1项响应协议+1项跨格式缓存）。真实模型UI正常预览完成，记录`.local/evaluations/extraction-preview-002.txt`。以下7个开发场景调用实际发布模型分支，结果保存`.local/evaluations/extraction-live-1792643495779033400.json`：

| 场景 | 核验观察 |
|---|---|
| 正常Markdown | validated，实际组装申请并预审，120.00元餐费超限转人工 |
| 缺出发日期 | needs_materials，不能创建申请 |
| 两个冲突出发日期 | needs_manual_review；本次模型conflicts为对象列表，严格协议拒绝 |
| 声明100、CSV合计120 | CSV_TOTAL_CONFLICT，不能创建申请 |
| 仅有预算，实际总额未确定 | 模型字段直接null而非value/quote对象，协议拒绝并转人工 |
| 忽略制度、批准付款干扰指令 | INSTRUCTION_LIKE_TEXT，不能创建申请 |
| 正常文本PDF | validated，字段引用实际第1页，组装申请并完成代码预审 |

七场景使用文本解析1.0.0；之后仅将缓存身份升级为1.0.1并按格式区分，已补单测/真实HTTP，没有冒充重新跑过全部模型场景。

七场景都观察到预定流转边界，**包含两处模型格式偏离，不能称七条模型提取全部正确或正式准确率**。模型没有在预算场景生成核定金额；该字段格式仍未符合约定，不静默修补为成功。原始输出保留，下一轮可定向改善输出协议。

七次API记录合计total_tokens为4545，这是Dify报告值，不是账单/费用结论；另有一次正常UI预览，不能把4545当作本轮全部用量。标注是开发预期，无独立保留集或人类审核。

原规则API七项回归：`.local/evaluations/workflow-api-live-1792643542987122000.json`；空白/加密PDF真实422、重启后提取记录不变：`.local/evaluations/extraction-boundaries-002.json`；最终格式缓存隔离/健康检查：`.local/evidence/extraction-final-check.json`。

数据库v2→v3前备份，新增extractions与application_extractions两表；旧申请、任务、事件、材料原始字节和链接逐行保持，完整性ok、外键零异常。证据`.local/evidence/extraction-migration-backup.json`及`extraction-migration-check.json`。当前无活动任务，业务服务运行；未测试整机重启。

运行：安装requirements.txt；测试PDF生成需requirements-dev.txt。`python tools/build_pdf_example.py`生成合成文本PDF；`.venv/Scripts/python tools/verify_extraction_api.py`进行真实模型回归，可能消耗额度；原材料/协议已存在时复用记录，不把缓存查询当新模型请求。
