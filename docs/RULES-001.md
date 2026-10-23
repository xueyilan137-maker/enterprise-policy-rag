# 结构化报销规则模块 v0.1

2026-10-21。`src/expense_rules.py`为离线纯Python实现，`tools/precheck_example.py`调用真实规则函数，无模型、HTTP或mock回退。尚未接入API、Dify Workflow、材料解析、数据库或权限。

## 输入与输出

示例：`data/examples/expense-001.json`。运行：

```powershell
python tools/precheck_example.py data/examples/expense-001.json
python -m unittest discover -s tests -v
```

| 字段 | 当前契约 |
|---|---|
| employee_id / employee_type | 非空员工标识；当前仅ordinary范围，身份尚未验证 |
| destination / destination_region / reason | 非空目的地、事由；仅显式CN-mainland范围，不做地理推断 |
| trip_start_date / trip_end_date / submitted_date | ISO年月日，按出差开始日选版本，提交期限含最后一天 |
| total_amount / 明细amount | 非负两位小数字符串；拒绝浮点、科学计数、NaN及负数 |
| expense_items | 1至200项对象，item_id非空且唯一 |
| 各明细公共字段 | category为meal/lodging/transit；expense_date、receipt_id、receipt_present |
| meal | meal_provided布尔，按日期聚合餐费及供餐事实 |
| lodging | check_in、check_out、正整数nights，校验真实夜数、区间、重叠及城市限额 |
| transit | route、seat_class；超标准席别检查prior_approval_present |

包络结构非法抛ValueError；业务缺项/异常生成findings。报告含status、policy_version、rule_engine_version、规范化制度快照SHA256、逐项事实及条款ID。状态优先级：needs_manual_review > needs_materials > no_issues_found；最后一个仅表示所提供字段未触发已实现规则，不等于批准。无approved_amount或付款结果。任何明细金额非法时item_sum为null，不给部分合计。

同申请票据ID重复及服务端传入的历史ID仅作疑似重复。previous_receipt_ids必须由后续可信后端按员工查询，不能将客户端历史当作授权或真实性证明。receipt_present等布尔值目前只是结构化声明，不是附件审查、发票验真或审批核验。

## 验证与边界

离线示例两张同日60.00元，实际合计120.00，v2限额100.00，报告needs_manual_review，关联MEAL与REVIEW；未自动截断金额。保存结果`.local/prechecks/expense-001.json`。

新增11项规则测试覆盖Decimal合计/不符、非法金额、同日聚合、期限边界及跨生效日出差、重复票据、材料缺失/范围、供餐事实冲突、住宿夜数/超限/重叠、交通审批缺失、无适用版本和共同城市配置。连同既有工程测试共39项通过，不是40份申请评测或实际业务运行。

制度正文与规则共享`data/policies/travel.json`。本轮将原有城市列表提取为结构化city_tiers并用于正文模板，渲染的两版文档哈希均与现有入库状态一致，未改制度语义或重复入库；原始JSON源哈希改变，历史实验源哈希仍保留。兼容证据`.local/evidence/policy-render-compatibility-004.json`。

下一步先明确本地Dify到规则服务的双向网络与鉴权，再以Pydantic定义HTTP契约并联调Workflow。可信员工范围/历史、附件解析、持久化、人工复核与独立申请评测仍待实现。
