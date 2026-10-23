# 从源码到本机演示

本文适用于Windows PowerShell。应用源码不包含Dify、插件包、模型Key、知识库ID、数据库或历史审核证据。现有机器继续工作请按HANDOFF，不要按新机器步骤重建已有知识库或凭据。

## 1. 无模型离线检查

需要Python 3.11（本机已测）、Git可选。先在新目录解压交付ZIP，或取得未来独立仓库源码。进入包含README的项目根目录：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python tools/precheck_example.py data/examples/expense-001.json
.\.venv\Scripts\python tools/import_knowledge.py
```

requirements-dev包含运行依赖和PDF测试依赖。最后一个命令仅显示入库计划，不联网；离线规则结果不代表模型或业务Workflow实际运行。没有模型账户也可以查看规则实现、合成制度、测试及网页源码。

## 2. 新机器启动Dify

需要Docker Desktop Linux引擎/WSL2、Docker Compose支持`!override`，以及足够运行Dify的内存和磁盘。本机16GB曾需分时运行；资源条件不是长期稳定性保证。保持端口18080、18081、18082空闲，不擅自停止别人的服务。

1. 从[Dify 1.17.1发布源码](https://github.com/langgenius/dify/releases/tag/1.17.1)取得完整ZIP；保留为`.local/dify-1.17.1.zip`，完整源码解压为`.local/vendor/dify-1.17.1/`，确认包含`docker/docker-compose.yaml`、`docker/.env.example`和`docker/nginx/`。不只下载单个Compose文件。
2. 在项目根运行以下命令。setup仅用于新环境，已有`.env`时拒绝覆盖。启动脚本确保插件Linux命名卷存在，只管理policy-rag。

```powershell
New-Item -ItemType Directory -Force .local | Out-Null
.\.venv\Scripts\python tools/setup_dify.py
.\tools\dify_local.ps1 -Action Start
.\tools\dify_local.ps1 -Action Status
```

3. 等核心服务与API健康后访问`http://127.0.0.1:18080/install`创建管理员。正常退出0的init_permissions是一次性初始化；不要反复重启或删除卷处理冷启动。配置细节与历史排障见LOCAL-DEPLOYMENT/ISSUES。
4. 在Dify安装通义插件（本机验收版本0.2.23），用自己的模型凭据配置text-embedding-v3与qwen3.7-flash。DSL的dependencies为空，不能自动安装或证明插件齐全；需手动确认两个模型均可调用。版本不可取得时先验证替代版本，不能声称与本机完全一致。

本机历史完整源码ZIP的SHA256见DELIVERY-001；新下载文件应自行核验来源。上游镜像可能需联网拉取，插件/模型需要账户；本次交付包不分发上游源码、镜像或第三方Key。没有做第二套Dify空环境重装验收。

## 3. 建库并导入当前问答

在新实例创建知识库API Key（已有实例复用）。复制配置样例，在本机编辑占位字段；不要打印Key或提交`.local`：

```powershell
Copy-Item config/dataset-api.example.json .local/dataset-api.json
# 在本机编辑上面的私有文件后，先计划，再执行一次实际入库。
.\.venv\Scripts\python tools/import_knowledge.py
.\.venv\Scripts\python tools/import_knowledge.py --apply
```

该工具以`.local/knowledge-state.json`记住新实例两版知识库/文档/哈希。再次执行会保留状态；upload_pending表示上次结果不明，先核对Dify，不换状态文件反复上传。等待两版索引completed，在页面确认每版10个片段（说明1、条款9）。实际入库消耗embedding额度。

```powershell
.\.venv\Scripts\python tools/build_chatflow_candidate.py --transport-routing --evidence-fallback --bind
```

在工作室导入`.local/policy-chatflow.evidence-candidate.bound.yml`创建Chatflow；在新实例会有新ID，不应期待本机原链接有效。确认插件、模型和两版知识库绑定，预览日期缺失/无效、v1/v2问答、范围外拒答后发布。旧`build_chatflow.py`及默认模板是第4版历史冻结源，不代表当前第5版。

## 4. 规则服务与预审Workflow

先确认Dify已启动、policy-rag_default网络存在：

```powershell
.\.venv\Scripts\python tools/setup_rules.py
docker compose -p policy-rag-rules -f deploy/rules.compose.yml up -d --build
```

规则服务仅本机18081；Dify内走`http://policy-rules:8000`。dify_local.ps1已加载精确域名SSRF放行，不能扩大到整个私网。部署用独立Linux插件卷，不把运行环境绑定到Windows源码目录。

```powershell
.\.venv\Scripts\python tools/build_precheck_workflow.py --bind
```

导入`.local/precheck-workflow.bound.yml`作为Workflow，校对环境变量/内部地址/Secret，选择已配置通义模型，预览后发布。该私有DSL内含规则Token，不能放到公开仓库。当前提取协议travel-extract-1.0.2。发布后在该应用创建一次服务API Key，复制`config/precheck-app-api.example.json`到`.local/precheck-app-api.json`，填写新实例app_id/api_key，保留api_base的18080端口。

## 5. 业务API与网页

```powershell
.\.venv\Scripts\python tools/setup_business.py
.\tools\business_local.ps1 -Action Start
.\tools\business_local.ps1 -Action Status
Invoke-RestMethod http://127.0.0.1:18082/health
```

打开`http://127.0.0.1:18082/`，选择员工演示视角，上传`data/examples/trip-note-001.md`及`expense-items-001.csv`，发起提取与预审。用财务演示视角查看报告并保存一次模拟复核。完整路线见DEMO.md。

业务数据库首次自动创建在`.local/business/`。只能一个API worker；网页开放员工/财务切换，属于本机演示，不能公开暴露为正式登录系统。模型调用、内部执行失败、需补材料/需人工复核是不同状态；无资料验证发票真伪、无自动审批/付款。

## 6. 停止与再次运行

```powershell
.\tools\business_local.ps1 -Action Stop
docker compose -p policy-rag-rules -f deploy/rules.compose.yml stop
.\tools\dify_local.ps1 -Action Stop
```

再次运行依次启动Dify、规则服务、业务API。保留`.local`与Docker卷，不重建Key或库；不执行prune、down -v或清空数据库。Windows业务进程没有开机自启。完整机器冷启动/长期稳定性仍需单独验证。

评测样例已公开并用于开发，不能作为新的未见测试集。交付包里的human-reviews为空，历史首轮结论在EVALUATION-002；不要把新机器审核空状态改成已通过来跑旧成绩。
