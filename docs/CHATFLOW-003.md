# D03关联依据接入与回答边界

日期：2026-10-21。当前版本取代CHATFLOW-002的“只有city-hint”状态；首版与第2版证据保留。

## 实现与发布

同一应用增加条件补检索：同版本主检索前三条 → 检查餐费处理类问题是否缺REVIEW → 缺少则一次top1补检索 → 合并最多四条 → 变量聚合选择已执行分支 → LLM → 必要依据校验。非触发问题走原上下文，已有REVIEW不追加。评测与DSL共用`src/related_evidence.py`，无本地源文填充、无样本ID分支。

查询条件与检索效果见RETRIEVAL-EXPERIMENT-003。金额规则/持久化/预审API并未因此实现；问答中的120元简单算术来自模型，本轮仅核对该具体例子，不能当确定性金额校验已通过。后续业务预审仍须使用Decimal规则API。

回答层另外明确：supported指“回答有条款依据”，不是“允许报销”；餐费处理问题须回答费用规则与预审处理路径，实际引用同版本MEAL与REVIEW。guard强制两条引用均属于本轮上下文，不满足就拒答；另外拦截已识别的“报销/支付/付款具体金额”表述，不能自动把超限费用截断为某个核定金额。该词形规则只覆盖已识别模式，不代表完整语义安全证明。

已导出第2版真实DSL到`.local/policy-chatflow.v2.export.yml`后更新同一应用，配置清单无错误，本地发布第3版；知识库、插件、模型和应用ID不变。发布后问答证据另存，不以预览替代发布页验收。

## 真实调试与失败记录

不能只统计工作流SUCCESS：最初补检索、合并和LLM输入已含四条依据，模型仍返回supported=false。明确咨询边界与supported含义后，模型能作否定解释但只引用MEAL，被guard拦截。再明确“费用规则+处理路径”完整回答契约后，D03开始同时引用MEAL/REVIEW。

随后补日期变体出现“仅能报销100元”，虽然两条引用存在，结论仍越过制度边界。该候选未发布；保留失败记录，补上禁止核定金额的提示与代码拦截，再回归。不是简单将拒答条件放宽，也不把补检索命中当回答正确。

最终候选七轮实际观察：

| 场景 | 最终观察 |
|---|---|
| 餐费问题缺日期 | 追问完整开始日期 |
| 简短问法补2026-08-01 | 保守拒答，未生成核定金额；**可用性仍未通过** |
| D03原问法带完整2026-08-01 | 每日100元、同日合计检查、超标准不自动通过并转人工；v2-MEAL/REVIEW |
| 同问法2026-03-01 | 每日80元，引用v1-MEAL/REVIEW，没有混入v2 |
| 成都住宿 | 每晚400元、两晚800元限额；v2-CITY/LODGE |
| 婚假 | 无依据拒答 |
| 普通餐费每日限额 | 100元，引用v2-MEAL，无需处理路径 |

这不是“七轮全部通过”或正式答案正确率：有一个已知保守拒答，模型对“异常金额或超标准”的措辞也仍较宽泛，不能代替人工审核。当前D03原问题的生成闭环已验证，相关自然语言表达的泛化仍有限。

## 文件与验证

- `python tools/build_chatflow.py`现在默认city-hint+关联补检索；`--no-related-review`生成此前无补检索结构，`--query-variant original --no-related-review`生成原查询结构。
- `.local/policy-chatflow.bound.yml`为私有ID绑定文件；公开模板仅占位dataset ID，检查不含实际ID、Header、环境URL或秘密。`dify/policy-chatflow.city-hint.template.yml`保留第2版结构，原查询模板继续保留。
- `python -m unittest discover -s tests -v`：24项无模型测试通过，涵盖预算/去重、外版拒绝、缺REVIEW/缺引用拒答、已识别核定金额拦截、DSL内嵌函数一致性。缺依据/错误版本/非法结构是工程夹具验收，**未做真实知识库删除或上游故障注入**。
- 早期候选回归与失败：`.local/evaluations/chatflow-regression-003.json`、`related-initial-llm-trace.json`、`related-supported-incomplete-output.json`。
- 最终候选：`.local/evaluations/chatflow-final-regression-003.json`，记录保守拒答；发布页证据`chatflow-published-003.txt`、截图`.local/evidence/chatflow-published-003.png`。

## 未决边界

修复的是D03关联依据覆盖及其原问法解释闭环，不是所有餐费问题根治。保守拒答、词形拦截覆盖有限、金额确定性计算、独立保留集、人类标注审核、真实上游失败与广泛注入测试仍待完成。下一步优先用明确记录的补日期变体定位输出契约与保守拒答，避免依靠放松校验换表面可答率。
