# 发布版 Workflow 后端 API 验收

2026-10-22。用户已在2026-10-21明确允许创建该预审Workflow的后端调用密钥，指定只保存`.local/precheck-app-api.json`，不打印、不提交、不放业务前端；随后暂停，今日恢复执行。通过Dify正常页面创建一次，原应用、知识库、制度和Workflow第1版均未重建或更新发布。

## 实现

`src/workflow_client.py`提供本机后端调用适配器，使用`POST http://127.0.0.1:18080/v1/workflows/run`、blocking模式。application_json为结构化合成申请，Dify user固定演示标识，仅作调用归属，不替代业务鉴权。凭据读自私有配置，限制本地目标，不跟随重定向、不自动重试，连接5秒、其它操作30秒超时；不是严格整体耗时上限。暂未暴露业务API入口或实现异步作业。

适配器依次检查HTTP状态、Dify执行状态、workflow_run_id与data.id一致、Pydantic报告契约、输出status/request_id与报告一致。Dify返回HTTP200但内部failed时抛WorkflowCallError，不返回业务成功。网络与上游错误不回显原始材料、密钥或原始错误正文。workflow_run_id与规则request_id分开保存，二者均不是本项目已持久化的job_id。

`tools/verify_workflow_api.py`读取现有私有凭据并调用实际发布版本，无mock、无模型、无自动重试，每次报告用时间戳新文件保留。运行：

```powershell
.venv/Scripts/python tools/verify_workflow_api.py
.venv/Scripts/python -m unittest discover -s tests -v
```

## 真实HTTP验收

| 场景 | HTTP / 执行状态 | 结果 |
|---|---|---|
| 同日餐费60+60 | 200 / succeeded | needs_manual_review，合计120.00，v2限额100.00 |
| 一张60且材料声明齐全 | 200 / succeeded | no_issues_found，仅为已实现规则未发现问题 |
| 缺凭证 | 200 / succeeded | needs_materials |
| v1同日餐费60+60 | 200 / succeeded | v1限额80.00，转人工 |
| 浮点金额120.0 | 200 / failed | 适配器拒绝接收成功报告 |
| 其它员工 | 200 / failed | 越权被拒，I021的Dify错误说明问题仍在 |
| 错误Dify应用密钥 | 401 | 不执行Workflow |

七项均按预期验收，真实原始报告`.local/evaluations/workflow-api-live-1792639342415358000.json`。51项工程测试通过（原47+4项适配器测试）；其中超时测试为httpx响应夹具，不是真实超时故障注入。截图`.local/evidence/precheck-api-enabled-002.jpg`只显示密钥数量，不包含密钥管理弹窗。

本轮未消耗生成模型调用；固定JSON输入不等于材料提取。材料解析、业务登录/权限、数据库历史、作业幂等、人工复核、真实超时/429故障注入和独立保留集仍未完成。隔夜运行状态健康是一次观察，不是长期稳定性成绩。
