# 城市查询提示接入验收

当前发布版已由CHATFLOW-003取代；本文保留第2版历史验收。

日期：2026-10-21。取代CHATFLOW-001中“现有发布版仍用原查询”的状态；其首版证据继续保留。

## 实现

沿用同一应用、同一模型/提示词/温度、同一版本知识库，先导出原版到`.local/policy-chatflow.original.export.yml`，再通过现有应用菜单“导入DSL→覆盖并导入”更新草稿，未创建重复应用/知识库。

路由节点新增`retrieval_query`输出：原`question`保持不变供LLM使用，仅检索节点改读追加城市提示的查询。转换函数`src/retrieval_query.py`同时用于评测和DSL生成，工程测试执行DSL内嵌代码确认与评测转换一致。仍只追加此前实验中的城市等级关键词，不加入城市映射/金额答案；原来的日期路由、会话pending、引用校验均沿用。

默认`python tools/build_chatflow.py`生成当前city-hint公开模板；`--bind`写私有绑定文件；`--query-variant original`可生成原查询版本。原查询公开模板另存`dify/policy-chatflow.original.template.yml`。公开两模板均检查无实际dataset ID、鉴权Header、URL或环境秘密；通义插件需预先配置，不自动重装。

## 实际生成回归

候选草稿通过配置检查清单后完成七轮真实Dify运行：

| 场景 | 实际观察 |
|---|---|
| 2026-08-01成都住两晚住宿标准 | B类、每晚400.00元；v2-CITY/LODGE。未显式输出800元合计，不把此用例记为金额汇总验收 |
| 2026-03-01上海每晚住宿上限 | A类、500.00元；v1-CITY/LODGE |
| 2026-09-01住宿材料清单 | 基础字段、费用明细/凭证、住宿日期与夜数；v2-DOCS |
| 2026-08-01婚假天数 | 依据不足拒答 |
| 深圳住宿每晚限额，未给日期 | 追问完整开始日期 |
| 同会话补2026-08-01 | 保留深圳问题，A类600.00元；v2-CITY/LODGE |
| 2026-08-01餐费每日限额 | 100.00元；v2-MEAL |

已在本地发布第2版，页面明确显示“#2 / 已发布”；同一聊天URL刷新后另跑成都住宿问题，真实生成B类每晚400.00元与v2-CITY/LODGE引用。未发布到Marketplace或公网。

私有回归证据：`.local/evaluations/chatflow-regression-002.json`、`chatflow-published-002.txt`；截图`.local/evidence/chatflow-published-002.png`。现有应用ID/URL和query_variant记于`.local/chatflow-state.json`。

## 保留边界

这只是七轮开发回归及一轮发布页冒烟，不是正式正确率或独立测试。首版原生来源卡片的拒答展示问题未根治；本轮发布页没有显示原生卡片，以正文条款ID为依据。完整日期限制、真实上游失败和广泛注入测试仍未完成。D03的REVIEW漏召回仍见RETRIEVAL-EXPERIMENT-002；引用成员校验不能证明语义蕴含。独立保留集与人工审核仍待完成。

导入后预览/发布页不再显示原开场白，核心问答已验收；本轮没有修改业务权限或追问正文，开场白展示可后续在业务网页统一处理，不当作检索效果变化。
