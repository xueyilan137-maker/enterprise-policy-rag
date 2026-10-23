# 规则 API 与最小预审 Workflow

2026-10-21。已实现真实HTTP闭环，使用原创合成结构化申请，无模型提取或模拟回退。制度问答仍为原Chatflow第4版；预审是另一业务入口，不是问答第5版。

## 拓扑和契约

规则服务为独立Compose项目`policy-rag-rules`，容器`policy-rag-rules-rules-1`，加入既有`policy-rag_default`网络，内部域名`policy-rules:8000`，主机仅暴露`127.0.0.1:18081`。Dify HTTP节点经官方SSRF代理，只放行精确服务名`policy-rules`，未放行私网网段、修改系统网络或启动旧项目。Docker基础镜像固定tag与实际digest，Python直接依赖见requirements.txt；完整实际解析版本保存在私有证据中，不宣称已做供应链审计。

`GET /health`不需凭据，仅返回演示运行状态。`POST /v1/prechecks`需Bearer服务凭据，输入Application、输出Report由Pydantic约束，OpenAPI见本机`http://127.0.0.1:18081/docs`。金额必须两位小数字符串，浮点/非法类型/额外字段返回422且不回显原始材料。与离线接口区别：非法金额在HTTP边界拒绝，不进入业务规则报告。

服务凭据仅绑定演示员工DEMO-001，服务端固定ordinary员工类型，其它员工返回403；客户端不能提交历史票据字段。当前历史为空，跨申请数据库查重、真实登录与权限尚未实现。服务凭据不是员工认证；目的地、供餐和材料布尔值仍是申请声明。request_id是每次调用标识，不是持久化作业、幂等键或Dify运行ID。

Workflow：申请JSON → HTTP规则调用 → 校验HTTP状态/报告 → 输出report_json、status、request_id。非200或非法响应显式失败，无默认成功报告。关闭节点自动重试，连接/读取/写入超时5/15/10秒。仅直接调用代码规则；条款ID来自同一制度配置，本阶段没有额外RAG检索或LLM解释，不将其称作材料理解完整链路。

## 重建与验证

先启动既有Dify并确认网络存在，再运行：

```powershell
python tools/setup_rules.py
docker compose -p policy-rag-rules -f deploy/rules.compose.yml up -d --build
# 在 .local/vendor/dify-1.17.1/docker 目录执行，只更新本项目代理
docker compose -p policy-rag -f docker-compose.yaml -f project.override.yaml -f "D:/dify workflow/deploy/dify.rules.override.yml" up -d --no-deps ssrf_proxy
python tools/build_precheck_workflow.py
python tools/build_precheck_workflow.py --bind
python tools/verify_rules_api.py
.venv/Scripts/python -m unittest discover -s tests -v
```

新开发环境先`python -m venv .venv`及`.venv/Scripts/python -m pip install -r requirements.txt`。`setup_rules.py`仅首次生成`.local/rules.env`，已有凭据保留。导入私有bound DSL一次创建Workflow；已有应用后覆盖更新，不重复创建。公开模板的服务URL为占位符、密钥为空，需在本地绑定；私有DSL含凭据，不得提交或放业务前端。Dify管理员可查看编排及运行信息，因此后台权限也是凭据边界。

当前Workflow应用ID/入口在`.local/precheck-workflow-state.json`。本地发布第1版，未上架Marketplace或公网。Dify生成入口仍遗漏18080，使用实际映射端口。历史创建动作曾被自动审批拒绝；用户已明确授权，2026-10-22正常页面创建一次并完成正式API验收，当前见WORKFLOW-002。

## 实际验收

- 47项工程测试通过：原39项+5项API契约/鉴权测试+3项Workflow响应门测试。TestClient为进程内测试，不能替代真实HTTP。
- 主机真实HTTP七项通过：同日60+60转人工、缺凭证需材料、无规则问题、浮点金额422、错误凭据401、其它员工403、客户端历史字段422。证据`.local/evaluations/rules-api-live-001.json`。
- Dify API容器经SSRF代理访问规则服务health真实200，确认网络可达。
- 五轮真实Workflow预览：三种业务状态正确保留，非法金额显式失败；其它员工被拒，但403被Dify错误描述成SSRF拦截。原始页面记录`.local/evaluations/precheck-workflow-preview-001.json`。不是五轮无错误，也不隐去失败展示问题。
- 发布页同日60+60真实验收，报告120.00超过100.00，关联MEAL/REVIEW且无核定金额。截图与页面记录在`.local/evidence/precheck-workflow-published-001.jpg`、`.local/evaluations/precheck-workflow-published-001.txt`。

尚未真实故障注入超时/429，正式Dify后端服务API调用现已验收（WORKFLOW-002）；仍未完成异步作业/幂等、材料解析、持久化、人工复核或独立申请评测。不把无问题状态当作审批，不把固定JSON输入当发票识别。
