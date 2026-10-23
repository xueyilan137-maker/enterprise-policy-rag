# CSV材料解析与服务端验证

2026-10-22。本轮接入真实UTF-8 CSV费用明细文件，使用服务端确定性解析，未调用提取模型。适用于本项目合成差旅演示；Markdown/PDF自由文本提取、扫描件/OCR和发票验真尚未实现，不能把本轮称作完整票据识别。

## 文件与接口

样例为`data/examples/expense-items-001.csv`。`POST /v1/materials?filename=expenses.csv`以文件原始字节作为HTTP请求体，Content-Type为`text/csv`（可带charset），沿用本机业务Bearer认证。不是multipart表单，也不是客户端提交解析后的JSON。支持UTF-8及UTF-8 BOM；文件最大256 KiB、200条非空明细、单元格1000字符。只忽略真正的空行，不忽略分隔符构成的缺字段行。

CSV英文列名大小写敏感：

| 列 | 契约 |
|---|---|
| item_id、category、amount | 必须存在且有值，ID唯一；category为meal/lodging/transit；金额为非负两位小数字符串，不转换成float |
| expense_date、receipt_id、receipt_present | 必须存在这些列；空值保留为缺项，交规则报告；非空日期须合法YYYY-MM-DD，布尔须true/false |
| meal_provided、prior_approval_present | 可选；非空须true/false，空值不擅自补false |
| check_in、check_out、nights | 可选；日期须合法；夜数非空为1至999整数，真实夜数/区间交规则核对 |
| route、seat_class | 可选文本，不执行内容；未知席别交规则转人工 |

单元格仅去掉首尾空白，保留票据编号前导零和金额字符串。逗号/换行引号遵循CSV语法，行号为记录结束的物理行，带引号换行时不能当作记录序号。任何行错误使整份材料invalid，items/row_locations为空，不接收部分成功。最多返回前30个问题，包含固定错误码、行号和已知字段名，不回显非法金额等原始错误值。

身份/角色/历史票据等未知列、重复表头、缺必需列、坏引号、列数不符、非法编码/控制字符、重复明细ID均拒绝。文件名不能包含路径/冒号/控制字符，仅作显示元数据；不用于磁盘路径。

## 保存、查询和创建申请

原始字节以BLOB保存于`.local/business/applications.sqlite3`材料表，同时保存SHA256、解析版本`expense-csv-1.0.0`、结果/错误、行定位、上传员工及时间。没有原始文件下载接口。`GET /v1/materials/{id}`仅本人可查，越权/不存在404；返回解析数据和元数据，不返回raw BLOB。

有效首次上传201；同员工相同原始字节/解析版本去重200，重命名也复用原记录，保留首次source_name。小型非法CSV保存invalid记录并返回422，方便本人查错；超限413、未支持文件类型415在保存前拒绝。当前只有每文件限制，没有总存储配额/自动清理，仍是本机合成演示边界。

`POST /v1/applications/from-material`提交差旅行程字段、声明总额和material_id，沿用Idempotency-Key。服务端读取本人parsed材料，重新用Pydantic验证并组装expense_items，客户端不能覆盖items或身份。行程日期非空须合法ISO日期，金额契约与既有API一致；数学合计、供餐、区间等业务判断由已有代码规则执行。原始文件与已解析内容均不充当系统指令。

申请保存材料ID/哈希/解析版本关联，报告item_ids可追溯至材料行定位。幂等比较包括材料ID，避免相同解析内容不同原始来源被静默替换；已有纯JSON申请哈希算法不变。解析有效只说明格式/字段可接受；receipt_present、供餐和审批布尔值仍是提交者声明，不是实际凭证、审批或发票验证。

创建后仍用既有`POST /v1/applications/{id}/precheck`及任务查询，Dify只收到服务端验证后的申请JSON。Chatflow第4版、预审Workflow第1版、服务凭据均未改动。

## 数据库与验收

Schema v1→v2为新增materials/application_materials两表，未改旧列；升级前确认零活动任务，停止本项目业务进程并用SQLite backup保存私有快照，再启动升级。备份位置记录`.local/evidence/material-migration-backup.json`，一致性证据`.local/evidence/material-migration-check.json`。旧申请、任务和事件逐行保持，完整性ok、外键零异常、raw与哈希一致。没有演练回滚，不在运行中覆盖数据库。

73项工程测试通过（原59+7项解析+7项接口/迁移），包括UTF-8 BOM、前导零、类型/金额/日期/表头错误、引号换行、体积/行数/列宽边界、归属与拒绝覆盖、并发去重及旧schema兼容。首次测试有夹具未关闭SQLite连接导致Windows清理报错，关闭连接后通过；不是忽略失败或改应用验证换通过。

18项真实HTTP检查通过，保存于`.local/evaluations/material-api-live-1792641565131847000.json`：有效上传/本人查询/重复去重/越权404、非法金额/UTF-8/身份列422、超限413、不支持PDF415、非法材料不能创建申请、客户端覆盖和非法行程日期422、有效创建/重复复用、越权申请404、异步任务及报告来源关联。真实CSV两笔60.00合计120.00，v2 MEAL/REVIEW转人工；未生成核定报销金额。

旧报告在升级后仍逐字段一致，查询证据`.local/evaluations/business-api-live-1792641651616040900.json`。不是独立材料识别准确率评测、模型提取成绩或正式企业材料测试。

运行：

```powershell
.venv/Scripts/python tools/verify_material_api.py
.venv/Scripts/python -m unittest discover -s tests -v
```

下一步扩展申请说明的自由文本提取和服务端核验，再接业务网页与人工复核；CSV部分继续作为确定性费用明细输入。
