# 提取输出格式定向修复与回归

日期：2026-10-22。当前同一预审Workflow本地第4版，提取协议`travel-extract-1.0.2`，qwen3.7-flash、temperature=0.1；解析器与服务端证据/日期/金额校验未放宽。业务网页仍待开发。

## 问题与修改

EXTRACTION-001保留的两个失败分别为conflicts输出对象数组、缺失total_amount直接为null。提示词明确每个字段始终为value/quote对象，缺失或冲突时两值为null；conflicts只能包含七字段中的名称字符串，冲突值不自行取舍。协议升级使相同材料产生新的提取任务，旧记录保持。

中间候选第3版（travel-extract-1.0.1）冲突日期真实UI预览符合协议，但发布API首个正常样例出现Markdown代码围栏。严格解析拒绝、未创建申请；没有剥围栏或修补候选冒充成功。失败原始输出保留在`.local/evaluations/extraction-live-1792644874119539700.json`，UI记录在`extraction-format-preview-003.txt`。

随后补充首字符/末字符、禁止围栏/标签/解释的原始JSON约束，升级1.0.2并发布第4版。原第2、3版公开模板及私有绑定DSL分别保存为precheck-workflow.v2/v3.*；不删除原第1版备份，不新建应用或密钥。

## 验收证据

87项工程测试通过，新增两项分别验证历史错误结构仍被拒绝、正确的空值对象/字符串冲突列表进入业务核验路径。测试是夹具，不算模型成绩。

发布版真实报告：`.local/evaluations/extraction-live-1792645093393579400.json`。七项均为新任务/新运行ID；脚本独立解析原始JSON及严格Candidate，检查字段全集/冲突名单，并检查两个目标负例的原始值与问题码，没有复用旧缓存冒充新调用。

| 场景 | 本次观察 |
|---|---|
| 正常Markdown | validated；组装申请，真实规则预审餐费120.00超限转人工 |
| 缺出发日期 | needs_materials / MISSING_FIELD，创建申请422 |
| 冲突出发日期 | 字符串数组报告trip_start_date；MODEL_REPORTED_CONFLICT及SOURCE_DATE_CONFLICT，转人工，创建422 |
| 声明100而CSV合计120 | CSV_TOTAL_CONFLICT，转人工，创建422 |
| 预算120，实际申请总额不确定 | total_amount为value/quote空值对象；needs_materials / MISSING_FIELD，创建422 |
| 干扰付款指令 | INSTRUCTION_LIKE_TEXT，转人工，创建422 |
| 正常文本PDF | validated；所有引用定位实际第1页，组装申请并完成规则预审 |

七次API报告total_tokens合计5895，仅为Dify报告用量。另有一次第3版UI预览和一次第3版失败API调用，不包含在5895中；不是本轮总账单或费用结论。无独立保留集/人类审核，不称通用格式稳定性、提取准确率或抗注入能力已证明。

原规则分支七项真实HTTP回归通过：`.local/evaluations/workflow-api-live-1792645158552852500.json`。状态仍区分Workflow失败、HTTP错误及业务转人工。发布截图`.local/evidence/extraction-workflow-published-004.jpg`。业务进程已受控重启加载1.0.2；未修改数据库结构、知识库或规则服务。

最终检查`.local/evidence/extraction-format-final-check.json`：原规则分支节点数据逐项未变，七个提取运行ID互异，89个公开源文件/文档/模板未包含已知内部规则、应用及演示身份凭据。该扫描针对当前文件，不能代替未来Git发布前的全量审查。

## 下一步

开发业务网页及人工复核入口：上传说明/CSV、查看提取状态与问题、预审依据和报告，再记录具有服务端角色权限的人工复核结果。复核记录独立保存，不能覆写原报告或表示付款批准。正式认证、OCR、跨申请历史查重、独立保留集与GitHub交付仍未完成。
