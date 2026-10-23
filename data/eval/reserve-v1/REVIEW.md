# 候选保留集人工审核单

8条问答 + 8份申请，均为助手原创合成、来源初核，尚未经人类审核。不是盲测或独立第三方数据。
请逐项核对输入、参考答案和引用条款。不要运行应用来决定标签；请直接对照制度原文。
同一制度的知识点会重叠；新增组合/业务场景不代表所有语义家族完全独立，详见EVALUATION-001。

## Q01 · rail_vs_lodging_cap

对话：
1. 2026-02-18出发，高铁二等座车票620元，能按住宿每晚500元的标准压减车票金额吗？

参考标签：
```json
{
  "kind": "qa",
  "clause_ids": [
    "TRAVEL-v1-TRANSIT",
    "TRAVEL-v1-LODGE"
  ],
  "key_points": [
    "二等座交通费用与住宿上限分开；不按住宿限额核定车票金额。"
  ],
  "first_turn_requires_clarification": false,
  "final_policy_version": "v1",
  "prohibit": [
    "自动批准或核定付款",
    "伪造来源或跨版本依据"
  ]
}
```

**TRAVEL-v1-TRANSIT 交通费用**
普通员工可报销有对应行程的高铁二等座及经济舱实际费用。高铁一等座、商务座及商务舱等需事前批准证明，缺失时需补材料并转人工。交通费不适用住宿或餐费上限。

**TRAVEL-v1-LODGE 住宿标准**
住宿按实际住宿夜数计算，不按出差天数计算；A类每人每晚限额500.00元，B类每人每晚限额350.00元。限额内据实预审，超限部分标记人工复核，不自动批准或扣减。

人工结论：待填写；如需更正，请写出ID及更正依据。

## Q02 · provided_meal_missing_evidence

对话：
1. 2026-09-14出发，单位已经提供午餐，另外申报当天餐费但没有凭证，还需要补充什么说明和材料？

参考标签：
```json
{
  "kind": "qa",
  "clause_ids": [
    "TRAVEL-v2-MEAL",
    "TRAVEL-v2-DOCS"
  ],
  "key_points": [
    "已供餐日期不重复报该日餐费，需供餐说明；费用凭证缺失需补材料。"
  ],
  "first_turn_requires_clarification": false,
  "final_policy_version": "v2",
  "prohibit": [
    "自动批准或核定付款",
    "伪造来源或跨版本依据"
  ]
}
```

**TRAVEL-v2-MEAL 餐费标准**
餐费按自然日汇总，每人每天限额100.00元；同日多张餐费凭证合计检查，不得逐张单独享受限额。单位已提供餐食的日期不重复报销该日餐费，需补充供餐说明。

**TRAVEL-v2-DOCS 材料清单**
申请须提供员工编号、出差事由、开始/结束日期、目的地、费用明细与凭证。住宿须有住宿日期和夜数，交通须有路线及席别，餐费须有发生日期和供餐说明。凭证缺失时标记需补材料；本系统不验证发票真伪。

人工结论：待填写；如需更正，请写出ID及更正依据。

## Q03 · actual_nights_and_submission

对话：
1. 2026-04-16出发的行程，住宿应按实际夜数还是差旅天数算？行程结束后最迟多少个自然日提交？

参考标签：
```json
{
  "kind": "qa",
  "clause_ids": [
    "TRAVEL-v1-LODGE",
    "TRAVEL-v1-DEADLINE"
  ],
  "key_points": [
    "按实际住宿夜数；行程结束后30个自然日，等于30天仍在期限内。"
  ],
  "first_turn_requires_clarification": false,
  "final_policy_version": "v1",
  "prohibit": [
    "自动批准或核定付款",
    "伪造来源或跨版本依据"
  ]
}
```

**TRAVEL-v1-LODGE 住宿标准**
住宿按实际住宿夜数计算，不按出差天数计算；A类每人每晚限额500.00元，B类每人每晚限额350.00元。限额内据实预审，超限部分标记人工复核，不自动批准或扣减。

**TRAVEL-v1-DEADLINE 提交期限**
行程结束后30个自然日内提交，以提交日期减结束日期计算；等于30天仍在期限内。超过期限转人工；提交日期早于行程结束日期为数据异常。

人工结论：待填写；如需更正，请写出ID及更正依据。

## Q04 · foreign_city_default_exclusion

对话：
1. 2026-11-02出发去巴黎，不在A类城市名单，就能直接套B类住宿标准吗？

参考标签：
```json
{
  "kind": "qa",
  "clause_ids": [
    "TRAVEL-v2-CITY",
    "TRAVEL-v2-SCOPE"
  ],
  "key_points": [
    "不能；境外不在此境内制度范围，需人工判断。"
  ],
  "first_turn_requires_clarification": false,
  "final_policy_version": "v2",
  "prohibit": [
    "自动批准或核定付款",
    "伪造来源或跨版本依据"
  ]
}
```

**TRAVEL-v2-CITY 城市等级**
A类城市为北京、上海、广州、深圳；其他中国境内城市为B类。境外和港澳台差旅不在本制度范围，需人工判断。

**TRAVEL-v2-SCOPE 适用范围与版本**
仅适用于星桥示例科技普通员工的中国境内差旅。以出差开始日期选择唯一制度版本；跨生效日的同一行程不拆换版本。日期缺失时先补充；没有适用版本或版本冲突时转人工，不自动套用最新版。

人工结论：待填写；如需更正，请写出ID及更正依据。

## Q05 · cabin_and_review_path

对话：
1. 2026-05-19出发，商务舱缺事前批准证明，但住宿在标准以内，能因此直接认定整份申请通过吗？

参考标签：
```json
{
  "kind": "qa",
  "clause_ids": [
    "TRAVEL-v1-TRANSIT",
    "TRAVEL-v1-REVIEW"
  ],
  "key_points": [
    "商务舱仍需事前批准证明，缺失补材料并转人工；住宿合规不代表整份通过或批准付款。"
  ],
  "first_turn_requires_clarification": false,
  "final_policy_version": "v1",
  "prohibit": [
    "自动批准或核定付款",
    "伪造来源或跨版本依据"
  ]
}
```

**TRAVEL-v1-TRANSIT 交通费用**
普通员工可报销有对应行程的高铁二等座及经济舱实际费用。高铁一等座、商务座及商务舱等需事前批准证明，缺失时需补材料并转人工。交通费不适用住宿或餐费上限。

**TRAVEL-v1-REVIEW 预审与人工复核**
预审输出仅为未发现问题、需补材料或需人工复核。制度冲突、异常金额、超标准或无法解析材料不得自动认定通过；财务人员独立记录最终复核意见。本项目不执行付款。

人工结论：待填写；如需更正，请写出ID及更正依据。

## Q06 · missing_items_prevents_sum_check

对话：
1. 2026-10-13出发，只给申请总额，不交费用明细和凭证，是否已足够核对各项合计？

参考标签：
```json
{
  "kind": "qa",
  "clause_ids": [
    "TRAVEL-v2-DOCS",
    "TRAVEL-v2-DUPLICATE"
  ],
  "key_points": [
    "不够，需明细和凭证；明细金额之和须与申请总额一致，不能凭总额声称已核对。"
  ],
  "first_turn_requires_clarification": false,
  "final_policy_version": "v2",
  "prohibit": [
    "自动批准或核定付款",
    "伪造来源或跨版本依据"
  ]
}
```

**TRAVEL-v2-DOCS 材料清单**
申请须提供员工编号、出差事由、开始/结束日期、目的地、费用明细与凭证。住宿须有住宿日期和夜数，交通须有路线及席别，餐费须有发生日期和供餐说明。凭证缺失时标记需补材料；本系统不验证发票真伪。

**TRAVEL-v2-DUPLICATE 重复与金额检查**
同一员工已提交申请中的相同凭证编号须标记疑似重复，跨申请再次检查；同一申请内重复凭证也须标记。各明细金额之和须等于申请总额；金额使用人民币元、保留两位小数，不使用浮点近似判定。

人工结论：待填写；如需更正，请写出ID及更正依据。

## Q07 · invalid_date_repair_to_approval

对话：
1. 2026-02-30出发，高铁一等座没有事前批准材料，需要怎么处理？
2. 2026-02-28

参考标签：
```json
{
  "kind": "qa",
  "clause_ids": [
    "TRAVEL-v1-TRANSIT"
  ],
  "key_points": [
    "先要求有效完整开始日期；补日期后，一等座缺批准证明需补材料并转人工。"
  ],
  "first_turn_requires_clarification": true,
  "final_policy_version": "v1",
  "prohibit": [
    "自动批准或核定付款",
    "伪造来源或跨版本依据"
  ]
}
```

**TRAVEL-v1-TRANSIT 交通费用**
普通员工可报销有对应行程的高铁二等座及经济舱实际费用。高铁一等座、商务座及商务舱等需事前批准证明，缺失时需补材料并转人工。交通费不适用住宿或餐费上限。

人工结论：待填写；如需更正，请写出ID及更正依据。

## Q08 · invoice_verification_and_payment_boundary

对话：
1. 2026-12-06出发，能替我验证发票真伪，并把预审结果直接当付款批准吗？

参考标签：
```json
{
  "kind": "qa",
  "clause_ids": [
    "TRAVEL-v2-DOCS",
    "TRAVEL-v2-REVIEW"
  ],
  "key_points": [
    "本系统不验证发票真伪，预审不是付款批准，财务独立复核，不执行付款。"
  ],
  "first_turn_requires_clarification": false,
  "final_policy_version": "v2",
  "prohibit": [
    "自动批准或核定付款",
    "伪造来源或跨版本依据"
  ]
}
```

**TRAVEL-v2-DOCS 材料清单**
申请须提供员工编号、出差事由、开始/结束日期、目的地、费用明细与凭证。住宿须有住宿日期和夜数，交通须有路线及席别，餐费须有发生日期和供餐说明。凭证缺失时标记需补材料；本系统不验证发票真伪。

**TRAVEL-v2-REVIEW 预审与人工复核**
预审输出仅为未发现问题、需补材料或需人工复核。制度冲突、异常金额、超标准或无法解析材料不得自动认定通过；财务人员独立记录最终复核意见。本项目不执行付款。

人工结论：待填写；如需更正，请写出ID及更正依据。

## A01 · mixed_lodging_rail_v1

申请说明：
```text
# 原创合成申请 A01

出发日期：2026-02-10。
返程日期：2026-02-12。
提交日期：2026-02-20。
目的地：广州。
事由：项目现场交接。
申请总额：1360.00元。
行程范围为中国大陆。
```
费用明细：
```csv
item_id,category,amount,expense_date,receipt_id,receipt_present,meal_provided,check_in,check_out,nights,route,seat_class,prior_approval_present
A01-H,lodging,1000.00,2026-02-10,SYN-A01-H,true,,2026-02-10,2026-02-12,2,,,
A01-T,transit,360.00,2026-02-10,SYN-A01-T,true,,,,,佛山至广州,高铁二等座,
```

参考标签：
```json
{
  "kind": "material",
  "validation_status": "validated",
  "required_issue_codes": [],
  "policy_version": "v1",
  "report_status": "no_issues_found",
  "findings": [],
  "item_sum": "1360.00",
  "application_created": true
}
```

**TRAVEL-v1-LODGE 住宿标准**
住宿按实际住宿夜数计算，不按出差天数计算；A类每人每晚限额500.00元，B类每人每晚限额350.00元。限额内据实预审，超限部分标记人工复核，不自动批准或扣减。

**TRAVEL-v1-CITY 城市等级**
A类城市为北京、上海、广州、深圳；其他中国境内城市为B类。境外和港澳台差旅不在本制度范围，需人工判断。

**TRAVEL-v1-TRANSIT 交通费用**
普通员工可报销有对应行程的高铁二等座及经济舱实际费用。高铁一等座、商务座及商务舱等需事前批准证明，缺失时需补材料并转人工。交通费不适用住宿或餐费上限。

人工结论：待填写；如需更正，请写出ID及更正依据。

## A02 · B_lodging_cent_over_three_nights

申请说明：
```text
# 原创合成申请 A02

出发日期：2026-11-03。
返程日期：2026-11-06。
提交日期：2026-11-12。
目的地：武汉。
事由：项目现场交接。
申请总额：1200.01元。
行程范围为中国大陆。
```
费用明细：
```csv
item_id,category,amount,expense_date,receipt_id,receipt_present,meal_provided,check_in,check_out,nights,route,seat_class,prior_approval_present
A02-H,lodging,1200.01,2026-11-03,SYN-A02-H,true,,2026-11-03,2026-11-06,3,,,
```

参考标签：
```json
{
  "kind": "material",
  "validation_status": "validated",
  "required_issue_codes": [],
  "policy_version": "v2",
  "report_status": "needs_manual_review",
  "findings": [
    {
      "code": "LODGING_OVER_LIMIT",
      "item_ids": [
        "A02-H"
      ],
      "clause_ids": [
        "TRAVEL-v2-LODGE",
        "TRAVEL-v2-REVIEW"
      ]
    }
  ],
  "item_sum": "1200.01",
  "application_created": true
}
```

**TRAVEL-v2-LODGE 住宿标准**
住宿按实际住宿夜数计算，不按出差天数计算；A类每人每晚限额600.00元，B类每人每晚限额400.00元。限额内据实预审，超限部分标记人工复核，不自动批准或扣减。

**TRAVEL-v2-REVIEW 预审与人工复核**
预审输出仅为未发现问题、需补材料或需人工复核。制度冲突、异常金额、超标准或无法解析材料不得自动认定通过；财务人员独立记录最终复核意见。本项目不执行付款。

人工结论：待填写；如需更正，请写出ID及更正依据。

## A03 · rail_upgrade_missing_approval

申请说明：
```text
# 原创合成申请 A03

出发日期：2026-11-10。
返程日期：2026-11-11。
提交日期：2026-11-15。
目的地：南京。
事由：项目现场交接。
申请总额：880.00元。
行程范围为中国大陆。
```
费用明细：
```csv
item_id,category,amount,expense_date,receipt_id,receipt_present,meal_provided,check_in,check_out,nights,route,seat_class,prior_approval_present
A03-T,transit,880.00,2026-11-10,SYN-A03-T,true,,,,,苏州至南京,高铁一等座,false
```

参考标签：
```json
{
  "kind": "material",
  "validation_status": "validated",
  "required_issue_codes": [],
  "policy_version": "v2",
  "report_status": "needs_manual_review",
  "findings": [
    {
      "code": "MISSING_PRIOR_APPROVAL",
      "item_ids": [
        "A03-T"
      ],
      "clause_ids": [
        "TRAVEL-v2-TRANSIT"
      ]
    },
    {
      "code": "TRANSIT_REQUIRES_REVIEW",
      "item_ids": [
        "A03-T"
      ],
      "clause_ids": [
        "TRAVEL-v2-TRANSIT",
        "TRAVEL-v2-REVIEW"
      ]
    }
  ],
  "item_sum": "880.00",
  "application_created": true
}
```

**TRAVEL-v2-REVIEW 预审与人工复核**
预审输出仅为未发现问题、需补材料或需人工复核。制度冲突、异常金额、超标准或无法解析材料不得自动认定通过；财务人员独立记录最终复核意见。本项目不执行付款。

**TRAVEL-v2-TRANSIT 交通费用**
普通员工可报销有对应行程的高铁二等座及经济舱实际费用。高铁一等座、商务座及商务舱等需事前批准证明，缺失时需补材料并转人工。交通费不适用住宿或餐费上限。

人工结论：待填写；如需更正，请写出ID及更正依据。

## A04 · economy_missing_receipt

申请说明：
```text
# 原创合成申请 A04

出发日期：2026-03-12。
返程日期：2026-03-13。
提交日期：2026-03-18。
目的地：青岛。
事由：项目现场交接。
申请总额：710.00元。
行程范围为中国大陆。
```
费用明细：
```csv
item_id,category,amount,expense_date,receipt_id,receipt_present,meal_provided,check_in,check_out,nights,route,seat_class,prior_approval_present
A04-T,transit,710.00,2026-03-12,,false,,,,,济南至青岛,经济舱,
```

参考标签：
```json
{
  "kind": "material",
  "validation_status": "validated",
  "required_issue_codes": [],
  "policy_version": "v1",
  "report_status": "needs_materials",
  "findings": [
    {
      "code": "MISSING_RECEIPT",
      "item_ids": [
        "A04-T"
      ],
      "clause_ids": [
        "TRAVEL-v1-DOCS"
      ]
    }
  ],
  "item_sum": "710.00",
  "application_created": true
}
```

**TRAVEL-v1-DOCS 材料清单**
申请须提供员工编号、出差事由、开始/结束日期、目的地、费用明细与凭证。住宿须有住宿日期和夜数，交通须有路线及席别，餐费须有发生日期和供餐说明。凭证缺失时标记需补材料；本系统不验证发票真伪。

人工结论：待填写；如需更正，请写出ID及更正依据。

## A05 · submission_before_end_extraction_gate

申请说明：
```text
# 原创合成申请 A05

出发日期：2026-09-07。
返程日期：2026-09-09。
提交日期：2026-09-08。
目的地：厦门。
事由：项目现场交接。
申请总额：260.00元。
行程范围为中国大陆。
```
费用明细：
```csv
item_id,category,amount,expense_date,receipt_id,receipt_present,meal_provided,check_in,check_out,nights,route,seat_class,prior_approval_present
A05-T,transit,260.00,2026-09-07,SYN-A05-T,true,,,,,泉州至厦门,高铁二等座,
```

参考标签：
```json
{
  "kind": "material",
  "validation_status": "needs_manual_review",
  "required_issue_codes": [
    "DATE_ORDER_CONFLICT"
  ],
  "application_created": false
}
```

**TRAVEL-v2-DOCS 材料清单**
申请须提供员工编号、出差事由、开始/结束日期、目的地、费用明细与凭证。住宿须有住宿日期和夜数，交通须有路线及席别，餐费须有发生日期和供餐说明。凭证缺失时标记需补材料；本系统不验证发票真伪。

**TRAVEL-v2-REVIEW 预审与人工复核**
预审输出仅为未发现问题、需补材料或需人工复核。制度冲突、异常金额、超标准或无法解析材料不得自动认定通过；财务人员独立记录最终复核意见。本项目不执行付款。

人工结论：待填写；如需更正，请写出ID及更正依据。

## A06 · same_receipt_across_categories

申请说明：
```text
# 原创合成申请 A06

出发日期：2026-10-05。
返程日期：2026-10-06。
提交日期：2026-10-10。
目的地：合肥。
事由：项目现场交接。
申请总额：270.00元。
行程范围为中国大陆。
```
费用明细：
```csv
item_id,category,amount,expense_date,receipt_id,receipt_present,meal_provided,check_in,check_out,nights,route,seat_class,prior_approval_present
A06-T,transit,200.00,2026-10-05,SYN-A06-SAME,true,,,,,芜湖至合肥,高铁二等座,
A06-M,meal,70.00,2026-10-05,SYN-A06-SAME,true,false,,,,,,
```

参考标签：
```json
{
  "kind": "material",
  "validation_status": "validated",
  "required_issue_codes": [],
  "policy_version": "v2",
  "report_status": "needs_manual_review",
  "findings": [
    {
      "code": "SUSPECTED_DUPLICATE_RECEIPT",
      "item_ids": [
        "A06-T"
      ],
      "clause_ids": [
        "TRAVEL-v2-DUPLICATE",
        "TRAVEL-v2-REVIEW"
      ]
    },
    {
      "code": "SUSPECTED_DUPLICATE_RECEIPT",
      "item_ids": [
        "A06-M"
      ],
      "clause_ids": [
        "TRAVEL-v2-DUPLICATE",
        "TRAVEL-v2-REVIEW"
      ]
    }
  ],
  "item_sum": "270.00",
  "application_created": true
}
```

**TRAVEL-v2-DUPLICATE 重复与金额检查**
同一员工已提交申请中的相同凭证编号须标记疑似重复，跨申请再次检查；同一申请内重复凭证也须标记。各明细金额之和须等于申请总额；金额使用人民币元、保留两位小数，不使用浮点近似判定。

**TRAVEL-v2-REVIEW 预审与人工复核**
预审输出仅为未发现问题、需补材料或需人工复核。制度冲突、异常金额、超标准或无法解析材料不得自动认定通过；财务人员独立记录最终复核意见。本项目不执行付款。

人工结论：待填写；如需更正，请写出ID及更正依据。

## A07 · city_not_proof_of_region

申请说明：
```text
# 原创合成申请 A07

出发日期：2026-12-15。
返程日期：2026-12-16。
提交日期：2026-12-20。
目的地：杭州。
事由：项目现场交接。
申请总额：300.00元。
```
费用明细：
```csv
item_id,category,amount,expense_date,receipt_id,receipt_present,meal_provided,check_in,check_out,nights,route,seat_class,prior_approval_present
A07-T,transit,300.00,2026-12-15,SYN-A07-T,true,,,,,湖州至杭州,高铁二等座,
```

参考标签：
```json
{
  "kind": "material",
  "validation_status": "needs_materials",
  "required_issue_codes": [
    "MISSING_FIELD"
  ],
  "application_created": false
}
```

**TRAVEL-v2-DOCS 材料清单**
申请须提供员工编号、出差事由、开始/结束日期、目的地、费用明细与凭证。住宿须有住宿日期和夜数，交通须有路线及席别，餐费须有发生日期和供餐说明。凭证缺失时标记需补材料；本系统不验证发票真伪。

**TRAVEL-v2-REVIEW 预审与人工复核**
预审输出仅为未发现问题、需补材料或需人工复核。制度冲突、异常金额、超标准或无法解析材料不得自动认定通过；财务人员独立记录最终复核意见。本项目不执行付款。

人工结论：待填写；如需更正，请写出ID及更正依据。

## A08 · two_explicit_totals_conflict

申请说明：
```text
# 原创合成申请 A08

出发日期：2026-08-18。
返程日期：2026-08-19。
提交日期：2026-08-22。
目的地：福州。
事由：项目现场交接。
申请总额：370.00元。
行程范围为中国大陆。
申报总额：380.00元。
```
费用明细：
```csv
item_id,category,amount,expense_date,receipt_id,receipt_present,meal_provided,check_in,check_out,nights,route,seat_class,prior_approval_present
A08-T,transit,380.00,2026-08-18,SYN-A08-T,true,,,,,宁德至福州,高铁二等座,
```

参考标签：
```json
{
  "kind": "material",
  "validation_status": "needs_manual_review",
  "required_issue_codes": [
    "SOURCE_TOTAL_CONFLICT"
  ],
  "application_created": false
}
```

**TRAVEL-v2-DOCS 材料清单**
申请须提供员工编号、出差事由、开始/结束日期、目的地、费用明细与凭证。住宿须有住宿日期和夜数，交通须有路线及席别，餐费须有发生日期和供餐说明。凭证缺失时标记需补材料；本系统不验证发票真伪。

**TRAVEL-v2-REVIEW 预审与人工复核**
预审输出仅为未发现问题、需补材料或需人工复核。制度冲突、异常金额、超标准或无法解析材料不得自动认定通过；财务人员独立记录最终复核意见。本项目不执行付款。

人工结论：待填写；如需更正，请写出ID及更正依据。

