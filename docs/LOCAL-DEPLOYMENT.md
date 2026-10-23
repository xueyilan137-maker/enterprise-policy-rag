# 本地 Dify 开发环境

## 当前部署配置

- 官方源码 tag：1.17.1；完整源码位于 `.local/vendor/dify-1.17.1/`，不作为本项目源码提交Git。
- 独立Compose项目：`policy-rag`。启动前必须确认旧项目是否应运行，工具不自动停止其它项目。
- 页面入口：`http://127.0.0.1:18080`；首次创建管理员使用 `/install`，应用未健康前不能认为页面可用。
- Nginx仅绑定127.0.0.1；不开放插件调试端口。
- 一名API worker、一名Celery worker；禁用多人协作profile，暂不修改Windows/WSL全局资源。
- 使用远程模型API；本机不部署LLM。模型Key须在本地Dify重新配置，云端凭据不会自动同步。
- 环境配置和随机内部Key只保存在忽略的`.local`；不会输出到报告。
- 插件运行目录改用独立Linux命名卷`policy-rag_plugin_runtime`，依赖初始化上限600秒；旧D盘插件目录保留作回退。首次直接Compose启动前需`docker volume create policy-rag_plugin_runtime`，Start脚本会自动确保卷存在。卷数据物理位置沿用Docker配置，不保证在D盘。

## 启停与配置

从项目根目录运行：

```powershell
& .\tools\dify_local.ps1 -Action Status
& .\tools\dify_local.ps1 -Action Start
& .\tools\dify_local.ps1 -Action Stop
```

脚本只针对`policy-rag`，Stop不删除数据。不要使用`docker compose down -v`或prune来排查。

新机器需从官方获取完整1.17.1源码压缩包解压到上述位置，执行`python tools/setup_dify.py`；脚本已有`.env`时拒绝覆盖。具体Compose/插件兼容与镜像digest待首次健康验收后记录，不把拉取镜像等同可运行验收。

本轮Docker引擎自动恢复的13个旧容器，用户已授权全部停止，名称清单保存于`.local/running-before-dify.txt`。恢复前先停止Dify，并由用户明确选择是否恢复旧项目，不能自动全部启动。

## 存储位置说明

源码与Compose绑定的数据目录在D盘本项目`.local`内。Docker镜像层、命名卷及引擎VHDX仍取决于Docker Desktop现有配置，尚未迁移，不能宣称所有Docker数据都在D盘。性能验收后才决定是否有必要调整存储位置。

## 健康验收

1. Compose核心容器正常，数据库健康；init_permissions一次性退出0是预期。
2. Nginx页面、API `/health`和管理员初始化入口可访问。
3. 配置模型插件后，真实模型和embedding成功；导入语料并执行有来源的检索。
4. 启停本项目后记录数据仍存在，并检查内存/CPU及OOM情况。

当前核心服务、API、真实embedding/检索/模型问答已验收；本轮用户关机重启后再次完成18次真实检索及发布页问答，数据保留。长期稳定性仍未验证。项目Chatflow/Workflow和Dify Cloud现有应用彼此独立，不能以云端截图替代本地验收。
