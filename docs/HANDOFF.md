# 交接摘要

公开发布副本说明：本仓库为经白名单与凭据检查的源码交付，MIT许可证；运行凭据、数据库与原审核证据不分发，human-reviews在分发副本为空。下文保留开发阶段历史，历史“未建库/未发布”的阶段状态不代表本次公开仓库当前状态。仓库地址：https://github.com/xueyilan137-maker/enterprise-policy-rag 。

仓库选择最新结论：用户已确认`enterprise-policy-rag`、公开、MIT；根LICENSE使用项目contributors署名，未擅自填个人身份。打包包含LICENSE，最新版候选为.local/releases/enterprise-policy-rag-mit-candidate-002.zip。旧文中“名称/可见性/许可证未选”已由本条取代；只剩GitHub账户与同名仓库核对、独立Git初始化/远程发布未做。不得复用售后仓库。

更新：2026-10-23（Asia/Shanghai）。最新：Chatflow已在同一本地应用发布第5版，见CHATFLOW-005；预审Workflow仍第4版。

最新交付轮：已新增INSTALL/DEMO/DELIVERY-001及config占位样例、prepare_release.py/verify_release.py和.dockerignore。白名单生成.local/releases/source-*.zip，人工审批只在交付副本置空，原审核/冻结源不改。独立解压测试不依赖原.local，使用已有Python依赖，不代表新pip安装或第二套Docker重装。最终包与检查路径记录在本轮收尾条目。下一步确定独立GitHub仓库目标与原创代码许可证，再做新环境端到端复现/实际录屏/远程发布；尚未初始化Git，不推售后仓库。不要按INSTALL新机步骤重建当前正常环境。

交付验收收尾：143文件候选独立目录118项工程测试、离线规则和仅入库计划均通过，报告.local/releases/unpacked-1792736558285626800-check.json；最终仅文档收尾包.local/releases/policy-rag-source-candidate-001.zip，经清单/哈希核对且非Markdown逐文件与已测包一致。最终摘要.local/releases/delivery-001.json。原.local和40冻结文件保持，未运行模型/重装Dify/启停旧服务。README已更新测试数；本机历史问答112测试摘要仍作为旧轮证据保留。

第5版优先交接：Q05交通批准查询现优先检索交通/预审；限定咨询缺生成回答时只回退完整同版本真实片段，材料供餐问题强制原文；日期单独更正时清除被替代旧日期。112项工程测试及分阶段真实预览/两次发布页验收已完成，不是新保留成绩。所有已见Q01–Q08登记为post-eval-dev-v1，原reserve-v1首轮与40文件冻结源完整保留。当前生成命令为`python tools/build_chatflow_candidate.py --transport-routing --evidence-fallback`（加--bind输出私有ID）；旧build_chatflow.py/默认模板是冻结第4版，不能误覆盖现版。下一步整理独立仓库的脱敏/安装复现交付清单，仓库目标未选，不推到原售后仓库；正式认证、跨申请查重/复核更正审计及严格独立数据仍待做。

## 当前状态

- 项目是企业制度RAG与报销预审，补初级AI应用岗位能力；不复用售后仓库发布，不重做工单Agent。
- 本轮Dify核心服务健康，旧服务未启动。Dify1.17.1入口http://127.0.0.1:18080，policy-rag；通义0.2.23、codex凭据、text-embedding-v3与qwen3.7-flash真实可用。未重建环境/插件/知识库，不要重复安装或生成部署密钥。
- 两版知识库各10片段，ID/哈希在.local/knowledge-state.json，Key在.local/dataset-api.json；禁止输出/提交/发前端，不重复建库。
- 同一Chatflow当前本地第5版：交通批准意图优先查询，其他city-hint主检索3条→需要时同版本REVIEW补检索1条→合并最多4条；限定意图增加完整证据回退，见顶部与CHATFLOW-005。前四版DSL保留，应用ID/URL在.local/chatflow-state.json，不重复创建应用。
- D03关联依据覆盖与原问法回答闭环已真实验证，见RETRIEVAL-EXPERIMENT-003/CHATFLOW-003。9条配对检索共10次请求均成功、无跨版；仅D03补1次，主Recall@3仍0.9444，合并上下文覆盖1.0（最多4条），不能称Recall@3提升到100%或答案正确率。
- 第4版完成八轮真实预览及发布页简短问法补日期验收，见CHATFLOW-004。修复的是限定输出策略，不是模型推理根治或答案正确率；失败记录保留。
- 随后已实现离线规则模块src/expense_rules.py、合成输入data/examples/expense-001.json和CLI tools/precheck_example.py，见RULES-001。Decimal合计、每日餐费、住宿/交通、期限、缺项、疑似重复均有规则；无自动核定金额。城市配置与正文共源，渲染哈希与现有入库一致，不重复入库。
- 规则API和预审Workflow当前第4版已本地发布（第1版规则链路保持兼容），见WORKFLOW-001及EXTRACTION-002。服务项目policy-rag-rules，主机127.0.0.1:18081，内部policy-rules:8000；仅精确域名放行，凭据.local/rules.env。应用状态.local/precheck-workflow-state.json，不重复创建。
- 用户已明确授权；Workflow后端密钥已通过页面创建一次，只存.local/precheck-app-api.json，不打印/提交/下发前端，不重复创建。新增src/workflow_client.py和tools/verify_workflow_api.py；正式发布版七项真实HTTP验收通过，51项工程测试通过，见WORKFLOW-002。HTTP200可能内部failed，适配器必须检查执行状态及报告，不把失败转成功。
- 本机业务API/网页127.0.0.1:18082：不可修改申请/幂等创建、异步任务与SQLite结果/本人查询；网页见WEB-001。旧Bearer凭据.local/business-auth.json不下发网页；DEMO-002保留作隔离测试。浏览器开放演示员工DEMO-001/财务FINANCE-DEMO视角，任何本机访客可切换，不是正式登录。DB .local/business/applications.sqlite3不得提交。
- 原业务正常/故障/重启验收见BUSINESS-001；本轮新增UTF-8 CSV原始上传、严格解析、材料保存/本人查询、服务端从材料创建申请与来源关联，见MATERIALS-001。73项工程测试、18项真实材料HTTP检查通过，真实CSV→Workflow→规则报告完成。随后已扩展Markdown/可提取文本PDF，见EXTRACTION-001；OCR仍未实现。
- SQLite当前schema v4，最新只新增reviews，v3备份.local/business/before-web-v4.sqlite3；web-migration-backup/check.json记录旧七表逐行保持、完整性ok及外键零异常。旧v1/v2材料/提取备份也保留。业务与规则服务健康。
- Markdown/文本PDF模型候选→服务端引用/字段/CSV核验→申请→规则报告已真实跑通。提取修复阶段87项工程测试，第4版travel-extract-1.0.2七个新真实任务及原规则API七用例回归通过，见EXTRACTION-002。两处原格式偏离已定向改善；中间第3版新增围栏失败也保留，不能声称通用提取准确率。正常MD/PDFvalidated，负例均未建申请；服务端证据/日期/金额校验未放宽。
- 本机网页/独立复核记录已完成合成联调：94项工程测试；浏览器一个新模型任务→申请→规则报告→模拟财务复核→下载JSON，复核前23/后27及受控重启后27项真实HTTP通过，原报告和提取结果不变。记录见WEB-001，不把自动化模拟复核当财务真人审核。每报告仅保存一次，暂无更正/撤销入口。
- 首轮前瞻性评测已完成收集，用户确认16项参考标签并对8条实际回答作统一批量三维评分；更严格的新家族独立集/逐题理由、OCR、正式认证/复核更正审计、跨申请历史查重和GitHub交付未完成。Git未初始化，手机视口未实际验收。

## 紧接着做

当前首轮见EVALUATION-002：105工程测试；16项参考标签由用户从“6”更正为“16项已逐条审核无需更正”，已绑定私有证据与哈希。8份新真实材料流程/问题预期均满足，6问题单元TP6/FP0/FN0；8条检索Recall@3=0.875、无跨版，Q05缺TRANSIT/REVIEW。发布页8例9轮完整保留，Q01/Q04/Q05/Q06/Q08统一拒答；不能把同批检索诊断当作该次发布上下文证据。数据与开发家族重叠，不是盲测或客观业务准确率。原准备及2份开发pilot记录仍在EVALUATION-001。

用户随后对全部8实际回答确认三个维度“是/否/是”：all_key_points_supported=true、no_unsupported_claim=false、appropriate_refusal_or_clarification=true。三项全true规则下全项通过0/8，仅统一批量声明且无逐题理由，不能称客观准确率；第二项不能反向解释为通过。副本qa-observations.human-reviewed-v1.json、新报告qa-semantic-reserve-v1-first-review.json和原话在.local。原未审qa-observations.json/qa-score.json保留，不覆盖。

准备阶段摘要.local/evidence/evaluation-final-check.json记录当时候选提交0、两份pilot报告token1692；这是首轮前历史证据，不代表当前仍未运行。不要再以.local/final_web_check.py生成新轮总结，它会覆盖旧固定网页摘要且测试数写死94；见I032。

1. 本地源码交付候选已完成，按顶部交付轮继续；Q05/5拒答修复见CHATFLOW-005，不再按未修复重做。参考标签和首轮批量评分无需重复索要，也不能迁移为第5版通过。reserve-v1不复跑挑好成绩，另建严格独立版本尚未开始。
2. 正式认证/权限配置、跨申请历史票据查重、复核更正/审计仍待做。当前开放角色选择只可本机演示，不能公开部署为有身份保护的应用。
3. 补真实429/超时边界；已有规则不可用真实失败落库，超时/中断恢复仅夹具。I021的Dify 403展示问题仍在，不扩大私网放行。之后准备独立GitHub脱敏与复现交付。

## 验证与证据

- `.venv/Scripts/python -m unittest discover -s tests -v`：最新112项工程测试；`node --check web/app.js`；PDF测试还需requirements-dev.txt。受限环境TestClient可能挂起，同一命令主机运行通过。第5版摘要.local/evaluations/chatflow-v5-final-check.json记录40冻结文件/副本哈希匹配、108公开范围文件扫描无现有凭据值、18个开发回答节点摘要（另有2次无效日期追问）。
- `python tools/evaluate_system.py plan --pack reserve-v1`无网络显示审核已全记录；两个包已freeze，不覆盖生成。材料/检索首轮标记已存在，不再次运行reserve/retrieval；qa-score为只读首轮，勿覆盖。冻结仍逐项一致，生产/主评测代码未改；仅门禁单测改为独立待审夹具，不依赖真实审核状态。未新增Chatflow API密钥。
- 首轮材料.local/evaluations/system-reserve-v1-1792649548306771400.json（提取报告token6771，不含QA/embedding/费用）；检索reserve-retrieval-1792649575896082000.json；发布首轮qa-observations.json和qa-score.json在.local/eval-ledger/reserve-v1。reserve-first-pass-final-check.json为人审前摘要，reserve-answer-review-final-check.json是随后用户批量评分摘要，不混作同一时间状态。
- `python tools/build_chatflow.py`默认city-hint+关联补检索，`--bind`读私有ID；`--no-related-review`重建第2版结构，另加`--query-variant original`重建原查询结构。只生成文件，不联网、不新建应用。
- `python tools/evaluate_related.py`需RAG-BASELINE环境变量，默认全9条及请求间隔7秒；只检索，不发布应用，不加载.env，不打印Key。
- 实验.local/evaluations/related-1792573434265353500.json；指标与协议RETRIEVAL-EXPERIMENT-003。原BASELINE-001/EXPERIMENT-001/002及原dev.jsonl均保留。dev.source-reviewed.jsonl是初核副本，不是保留集。
- 当前最终回归.local/evaluations/chatflow-final-regression-004.json，八轮真实预览；此前失败记录保留，不把原文回退统计为生成正确。
- 发布页真实证据.local/evaluations/chatflow-published-004.txt；截图.local/evidence/chatflow-published-004.png。
- 离线规则示例报告.local/prechecks/expense-001.json；两版正文兼容证据.local/evidence/policy-render-compatibility-004.json。
- 第3版真实导出.local/policy-chatflow.v3.export.yml；原第2版真实导出.local/policy-chatflow.v2.export.yml；原版.local/policy-chatflow.original.export.yml；公开original/city-hint模板均保留。私有bound/export DSL不能直接提交。

- `python tools/verify_rules_api.py`：七项真实HTTP；.local/evaluations/rules-api-live-001.json。
- `docker compose -p policy-rag-rules -f deploy/rules.compose.yml up -d --build`启动规则服务；Dify启动见tools/dify_local.ps1，已加载精确域名override。
- Workflow五轮预览.local/evaluations/precheck-workflow-preview-001.json；发布页.local/evaluations/precheck-workflow-published-001.txt及.local/evidence/precheck-workflow-published-001.jpg。
- `python tools/build_precheck_workflow.py`生成无密钥模板；--bind输出私有DSL（含内部凭据，不可提交）。tools/setup_rules.py保留已有凭据，不重复生成。

- `.venv/Scripts/python tools/verify_workflow_api.py`：正式发布版七项真实HTTP，保存新时间戳报告；本轮.local/evaluations/workflow-api-live-1792639342415358000.json。
- 正式API验收见WORKFLOW-002，密钥存在即复用，配置含api_base/app_id/api_key。Workflow当前第4版、Chatflow第5版；历史DSL备份不删。

- `python tools/setup_business.py`保留本机演示身份；`./tools/business_local.ps1 -Action Start/Status/Stop`管理唯一业务进程，不手工启动第二个worker。
- `.venv/Scripts/python tools/verify_business_api.py`新增合成申请并真实调用；`--check-saved <报告>`验证重启后原记录，不重新发起Workflow。
- 当前业务DB不能多进程并行运行；重启遗留running→indeterminate、pending→failed，不自动重跑；每申请一任务，暂无人工确认重试/编辑入口。

- 网页GET /；`POST /web/session`选择employee/finance，Cookie HttpOnly/SameSite严格、8小时内存会话，重启需重选；Cookie写请求要求同源Origin。财务接口/v1/review-queue、/v1/review-applications/{id}及/reviews，服务端角色校验；员工仍不能跨人读取。
- `.venv/Scripts/python tools/verify_web_api.py 7a262213-14c1-4b40-8280-e93141e5d786`只查询/负例校验、不调用模型或提交复核；复核前快照已存在，不再加--snapshot覆盖。重启后报告web-api-live-1792646697189222900.json；独立复核为模拟记录，申请/原报告/模型结果保持。
- 截图business-web-upload/review-001.jpg、原文行号/缺项/无效CSV页面文本与下载JSON在.local/evidence或evaluations；详见WEB-001。网页制度正文按报告源快照匹配，不是新RAG调用。Dify界面与旧标签保持。

- `.venv/Scripts/python tools/verify_material_api.py`：18项真实CSV材料HTTP，报告.local/evaluations/material-api-live-1792641565131847000.json；输入样例data/examples/expense-items-001.csv。
- 新接口POST /v1/materials（text/csv原始字节）、GET /v1/materials/{id}、POST /v1/applications/from-material；格式/边界见MATERIALS-001。invalid材料不能进入申请，不接受客户端expense_items覆盖。
- 原始字节存私有SQLite BLOB；同员工/字节哈希/解析版本去重；不要公开DB或把声明布尔值当附件验真。

- POST /v1/materials现支持text/markdown和application/pdf；POST/GET /v1/extractions、POST /v1/applications/from-extraction见EXTRACTION-001，只有validation=validated可建申请。
- `.venv/Scripts/python tools/verify_extraction_api.py`会真实消耗模型调用，已有材料+协议会复用记录，fresh_model_task显式区分；当前7个新任务报告.local/evaluations/extraction-live-1792645093393579400.json（5895报告token，非本轮总用量），规则API回归workflow-api-live-1792645158552852500.json。原失败1792643495779033400及中间围栏失败1792644874119539700保留；详见EXTRACTION-002。
- 预审第1版公开/私有DSL备份precheck-workflow.v1.*保留；真实导出.local/precheck-workflow.v1.export.yml不含Secret值。
- PDF示例生成与渲染在.local/evidence/trip-note-001.pdf及preview.png；无OCR。解析版本按md/pdf区分，提取协议travel-extract-1.0.2，改提示/协议须显式变版本避免缓存误用。

## 避免重走

- 当前官方浏览器组件browser/26.1016.51333/scripts/browser-client.mjs；先发现当前版本并读官方docs，setupBrowserRuntime()返回agent，不会自动注入globalThis.agent。旧setupAtlasRuntime/26.1013.40934入口不能用。
- 已有iab问答/安装入口与预审编排/发布页标签；复用并保留。导出有两层确认（含Secret窗口），不勾Secret值；窗口会显示凭据，必须脱敏读取，禁止打印原始快照。更新同一应用走“更多操作→导入DSL→覆盖并导入”，先备份；导入后刷新服务器草稿再验收。
- Docker沙箱pipe permission denied不等于引擎停机。确有I007故障再按记录恢复，不prune/清卷/恢复出厂。
- 不启动旧售后/Hadoop服务，Edge保留。重启可能自动恢复旧容器，已有用户授权暂停全部旧容器；恢复清单.local/running-before-dify.txt。
- Dify生成API/聊天链接仍可能缺18080端口，本机按实际端口使用，不重开隧道作为业务入口。
- 原生来源卡片不是语义引用验证；拒答也可能显示检索文件。正文条款校验不能证明每句话都被条款蕴含。
