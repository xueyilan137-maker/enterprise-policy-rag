# Chatflow 第5版：拒答诊断与限定证据回退

2026-10-23。本地同一应用发布第5版；预审Workflow仍第4版。本轮是已接触案例的开发回归，不更新reserve-v1首轮指标，不提供新回答准确率。

## 原始运行根因

通过Dify日志页面定位原始会话，再只读导出该应用指定节点输入输出，保存在`.local/evaluations/chatflow-first-pass-node-traces-20261023.jsonl`。Q01/Q04/Q05/Q06/Q08的guard均为`model_unsupported`，模型实际输出supported=false，不是结构或引用校验误拦。

Q01已召回TRANSIT明确禁止套住宿上限；Q04已有CITY/LODGE/SCOPE；Q06已有DOCS/DUPLICATE；Q08已有DOCS/REVIEW。Q05实际上下文为CITY/LODGE/DOCS，缺TRANSIT/REVIEW；交通批准问题夹带住宿触发city-hint，且餐费专用补检索不触发。只能证明该查询与漏召回有关，未做全部可能因素归因。

冻结清单40文件已逐项核验并复制到`.local/eval-ledger/post-eval-dev-v1/frozen-source/`，原清单、输入、标签、首轮结果及用户评分不覆盖。registry.json将已观察Q01–Q08全部登记为开发案例。

## 分阶段试验

1. 仅追加“解释限制不等于执行批准”的提示，检索与guard保持原样。真实预览Q01/Q08能解释制度，Q04/Q06仍拒答。保存post-eval-prompt-Q*-001.txt，不删失败记录。
2. 交通+批准/通过/审批意图优先使用“交通费用 席别 事前批准证明 预审与人工复核”检索词，其他查询保持原city-hint；仍主top3、无重排。两版各一次真实知识库请求均返回同版本TRANSIT/REVIEW/DOCS。报告post-eval-intent-retrieval-1792734449033203600.json。没有新建或改写知识库；这两次请求不作为整个集合Recall指标。
3. 限定咨询意图设置必要条款ID：交通批准TRANSIT/REVIEW、交通跨费用标准TRANSIT、城市分类边界CITY、总额核对DOCS/DUPLICATE、验真付款DOCS/REVIEW。模型拒答/格式/引用不满足时，只有本轮实际完整同版本片段才可原文回退；缺条款/跨版本仍拒答，不从本地源文补答案。生成与原文回退分别标记，提示不构成金额核定。

完整候选真实预览中，原5条拒答均返回依据：Q05/Q08生成，Q01/Q04/Q06原文回退。这是一次开发观察，不能推断模型稳定性或语义准确率。

## 回归发现与修正

完整候选的Q02仍出现拒答（post-eval-evidence-Q02-001.txt）；新增餐费材料意图的MEAL/DOCS必要条款，并强制展示真实原文，避免重复生成“坚持申报”等无依据例外。Q02新预览已展示两条完整原文，保存002后缀记录。

Q07补有效日期后，旧无效日期仍留在pending问题，实际模型解释了旧日期，见post-eval-evidence-Q07-turn2-001.txt。只在日期单独回复确实完成pending时移除被替代的日期字面量，保持原问题事实并附最终有效日期；不改新问题和多日期追问。修正后新预览有效路由v1、只展示TRANSIT/REVIEW原文，不再把旧日期当当前事实。婚假问题修正前后真实预览均拒答；Q03住宿夜数/30自然日真实预览保持正常。

## 发布与验证

- 112项工程测试通过，包括真实片段完整性/版本、无依据仍拒答、禁止将危险草稿混入原文、嵌入代码与本地逻辑一致、日期更正。它们不是模型准确率测试。
- 同一应用页面显示发布`#5`，证据`.local/evidence/chatflow-v5-publish.txt`；发布页新对话Q05验证生成、Q04验证原文回退，实际文本另存chatflow-v5-published-Q05/Q04.txt。
- 主top3、餐费REVIEW最多一次top1及最多4条上下文维持。新的交通意图只改主查询，没有增加补检索次数。
- 旧v4源文件与模板保持冻结不变。当前第5版复现命令：`python tools/build_chatflow_candidate.py --transport-routing --evidence-fallback`；加`--bind`只在.local输出实际ID。当前模板为`dify/policy-chatflow.evidence-candidate.template.yml`，candidate命名记录实验来源，已发布的是该最终配置。旧`tools/build_chatflow.py`仍复现第4版，不要误导入覆盖第5版。

限定关键词覆盖、生成分支的语义错误风险、原文回退阅读体验仍存在。新一轮严格独立数据及逐题回答审核尚未做；原用户“是/否/是”只绑定首轮，不能迁移为本轮通过。后续优先整理可复现交付，再按公开部署范围补正式认证与审计；公开前不能使用开放角色演示充当身份保护。
