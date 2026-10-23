# 源码交付候选与复现检查

公开发布副本说明：本仓库为经白名单与凭据检查的源码交付，MIT许可证；运行凭据、数据库与原审核证据不分发，human-reviews在分发副本为空。下文保留开发阶段历史，历史“未建库/未发布”的阶段状态不代表本次公开仓库当前状态。仓库地址：https://github.com/xueyilan137-maker/enterprise-policy-rag 。

2026-10-23。本轮完成本地源码交付包与无私有状态复现检查，未创建Git仓库或推送GitHub。当前运行服务未重装、未启停，Chatflow第5版和Workflow第4版保持。

## 交付内容

- INSTALL.md：无模型离线检查、新机器Dify/插件/知识库、当前两个DSL、规则容器与业务网页的连接步骤。
- DEMO.md：合成数据演示路线、技术职责与未完成范围。
- config/*.example.json：仅占位符的私有配置样例，不提供可运行Key。
- tools/prepare_release.py：从固定源码目录与扩展名白名单生成新的`.local/releases/source-*.zip`，不依赖.gitignore决定内容。含源码、测试、文档、原创合成数据、脱敏DSL及逐文件SHA256清单，不包含.local、vendor、模型凭据、DB、原始上传、日志或私有证据。
- tools/verify_release.py：核对归档成员/哈希/路径后解压到新目录，运行归档内工程测试、离线规则示例、无网络入库计划，日志与摘要留在.local。已有目录/已有ZIP不覆盖。
- .dockerignore：排除私有运行状态与环境，减少规则镜像构建上下文；Dockerfile的COPY范围保持原样。

human-reviews.json仅在交付副本里写为空，原用户审核记录和证据保持不变。公开标签已接触，不可再称未见测试；首次实测及用户评分仍见EVALUATION-002。交付副本没有原人工证据，不能把历史审核自动带到新安装。

## 可重复执行

```powershell
.\.venv\Scripts\python tools/prepare_release.py
# 使用上一步输出的ZIP路径：
.\.venv\Scripts\python tools/verify_release.py .local/releases/source-<运行标识>.zip
```

打包会检查本机已知私有Key/Token/知识库ID、常见Key格式，以及全部DSL中的环境变量值、知识库绑定、HTTP认证Header与临时端点。发现问题只输出文件名和问题类型，不输出秘密值。此扫描不能证明不存在任意未知秘密，发布前仍应人工核对归档目录和配置。

首次候选为142文件，独立解压后115工程测试及两个离线命令通过；随后补充归档篡改/路径逃逸/内嵌Header测试及交付文档，143文件候选独立解压后118测试、离线规则与入库计划均通过。报告`.local/releases/unpacked-1792736558285626800-check.json`绑定当时归档SHA256。最后仅补齐文档中的验收数/交接指针；最终候选再次核验归档哈希与成员，并逐文件证明非Markdown内容和已通过的包一致，避免为文档收尾重复跑模型或工程测试。摘要见`.local/releases/delivery-001.json`，原候选证据不覆盖。

验证边界：使用现有Python解释器与已安装依赖，验证源码不依赖原.local，**没有重新pip安装依赖，也没有在第二套空Docker中重装Dify**。安装说明中的联网依赖、插件获取、模型凭据和新实例GUI绑定仍需真实新机器验收。未为这次打包重复消耗模型或复跑保留集。

## 上游与版本

运行底座Dify 1.17.1，插件通义0.2.23，本机Python 3.11；规则镜像基础Python3.12.10固定digest见deploy/rules.Dockerfile。依赖版本锁在requirements*.txt。并非所有Dify镜像都固定内容digest，不能声称完全位级可复现。

本机保存的官方完整Dify 1.17.1源码ZIP SHA256：`ddac31cac40410ef266aab2610e2b1402849808ae2457747bb08981d678fe9f4`。本轮已重新计算与部署记录一致；这是本机历史档案指纹，不是新下载文件的签名证明。

已读取本机该版本LICENSE，其标题为Open Source License，说明基于修改后的Apache License 2.0及附加条件。交付包不再分发Dify源代码，保留其原生品牌展示；来源和范围见REFERENCES。具体分发/商业使用仍以所选版本原许可证为准，不将Dify简单标成普通Apache-2.0，也不把第三方依赖归为本项目自研。

## GitHub前未决事项

用户已确定独立仓库名`enterprise-policy-rag`、公开、原创代码MIT。根LICENSE已添加，打包白名单包含许可证；第三方依赖不改许可。GitHub所有者和同名仓库是否存在尚未核对，未创建远程或推送，不复用售后仓库。下一步核对当前登录账户与目标，再初始化独立Git、检查暂存内容并推送。私有历史审核/截图/数据库不进入Git；真实录屏尚未制作，DEMO仅是脚本。

完整交付尚有：新环境端到端复现、实际演示录屏、远程发布。正式认证、OCR、跨申请查重接线和复核更正审计属于功能缺口，不用文档或打包冒充实现。
