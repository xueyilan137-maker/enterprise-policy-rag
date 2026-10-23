# 单申请业务后端、身份绑定与持久化

2026-10-22。已有正式Workflow调用上增加本机业务API，真实链路为：员工演示凭据 → 申请保存 → 异步预审任务 → Dify发布版Workflow → 规则服务 → SQLite结果/事件 → 查询。问答第4版、预审Workflow第1版保持，没有新增模型或材料提取节点。

## 运行和身份边界

业务API在Windows主机`127.0.0.1:18082`，独立于规则容器18081和Dify18080。继续复用已获授权的`.local/precheck-app-api.json`，不复制到前端或创建新Dify密钥。SQLite为`.local/business/applications.sqlite3`（含WAL/SHM），身份文件`.local/business-auth.json`，进程记录/日志亦在`.local/`。

本轮是本机演示Bearer身份映射，不是密码登录、SSO或企业认证。两个合成员工凭据在服务端映射，身份/员工类型不从申请接收；当前规则服务仅允许DEMO-001，所以DEMO-002创建申请返回403，仅用于隔离验收。不得据此宣称多员工业务已全部实现。没有财务角色、人工复核入口或业务网页；前端会话方案后续实现。

主机运行：

```powershell
python tools/setup_business.py
./tools/business_local.ps1 -Action Start
./tools/business_local.ps1 -Action Status
.venv/Scripts/python tools/verify_business_api.py
.venv/Scripts/python -m unittest discover -s tests -v
```

`setup_business.py`保留已有身份，不打印凭据。启动脚本后台隐藏启动一个uvicorn进程，仅监听回环，禁用访问日志，进程启动不等于健康验收。`-Action Stop`只操作记录且核验过命令行的业务启动器及Python子进程，不操作旧项目或其它服务。Windows虚拟环境的启动器/实际Python可能是两个PID，系统conhost不被主动停止。重启仅用于本项目验收，不是系统重启；尚未配置Windows自动启动。

## HTTP契约

| 接口 | 行为 |
|---|---|
| GET /health | 公开最小健康状态，无人员/凭据 |
| GET /v1/me | 已认证演示员工ID与固定ordinary类型 |
| POST /v1/applications | 创建不可修改申请；必须Idempotency-Key；新建201、同键同内容200、同键不同内容409 |
| GET /v1/applications/{id} | 仅本人可查，含申请与已有预审结果；不存在/越权均404 |
| POST /v1/applications/{id}/precheck | 仅本人发起；新任务202、已有任务200，始终复用同一job_id |
| GET /v1/prechecks/{job_id} | 本人查询状态、报告、错误码、Workflow运行ID及状态事件；越权404 |

申请体为原合成示例移除employee_id/employee_type后的TravelDetails，额外身份/权限/历史字段、浮点金额和重复明细ID在业务边界拒绝422。服务端补入员工上下文后保存。幂等键按员工隔离，比较规范化校验后payload哈希；键不能取代身份认证。申请不可修改，修正材料需新申请/新键，编辑流程尚未实现。

应用ID、业务job_id、Dify workflow_run_id、规则request_id分别保留。数据库使用唯一约束、写事务和条件更新，保证并发相同请求只建一个申请/任务、一个worker领取。没有声称跨远端调用的exactly-once；报告与事件保存后GET可回查。

## 任务与失败语义

任务依次pending → running → completed/failed/indeterminate。completed只表示调用完成且报告通过校验，业务报告仍可能needs_manual_review或needs_materials，绝非批准付款。已确认Dify失败或明确拒绝保存failed、错误码及可取得的运行ID，报告为空；网络超时或无法确认结果保存indeterminate，不自动重跑。不把未知结果伪装成已完成或可安全重试。

队列执行器为单API进程内的两条线程；SQLite保存任务事实，不是独立持久消息队列。必须单进程单worker运行同一数据库。重启将遗留running记为indeterminate、遗留pending记为failed/service_interrupted，不恢复执行；该恢复规则通过工程夹具测试，本轮没有杀死真实正在调用的任务。关闭脚本可能强制终止进程，因此此边界必须保留。人工确认后重试接口尚未实现。

跨申请票据历史尚未从业务数据库传给规则服务；不能把保存申请说成跨申请查重已接通。材料布尔值仍是声明，未验真。

## 验收证据

- 59项工程测试通过：原51+8项业务测试；包含8线程并发创建/领取、所有权/身份注入、幂等冲突、失败/超时状态、恢复及重新打开数据库。超时和中断恢复为夹具，不是线上故障注入。
- 正常真实业务HTTP验收14个检查：`.local/evaluations/business-api-live-1792640142480415000.json`。真实Workflow完成，餐费120.00超限，报告转人工；重复提交/重复发起复用ID，另一员工读取/发起均404。
- 仅停止本项目规则容器做真实不可用故障注入，业务任务落库failed、报告null并保留Dify运行ID；14个检查通过：`.local/evaluations/business-api-live-1792640261605281600.json`。finally恢复规则服务，当前healthy；不代表已验证真实429或超时分类。
- 只重启本项目业务进程后，已保存任务与报告逐字段一致，查询200：`.local/evaluations/business-api-live-1792640595617040900.json`。没有重启整机或Dify。

下一步接材料解析与服务端验证，随后业务网页、人工复核和独立评测。当前是合成JSON输入的应用后端，不是完整材料预审系统或生产登录方案。
