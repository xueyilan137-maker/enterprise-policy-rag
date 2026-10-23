# 参考仓库与复用边界

筛选日期：2026-10-20。均未端到端启动；目前没有第三方代码复制到业务实现中。未固定 commit，正式采用前必须补齐 commit、文件、许可证和用途。

| 来源 | 检查内容 / 结果 | 使用决定 |
|---|---|---|
| https://github.com/hdhsh125/contract-review-assistant | README、app.py、requirements.txt、实际 MIT LICENSE；文件上传/Workflow/API/导出；工作流需自行配置，版本兼容未验证 | 优先参考 API 适配思路；不采用其整套业务，不沿用 README 提效数字 |
| https://github.com/MARUCIE/dify-demo | README、package.json、src/app/api/audit/route.ts、src/lib/dify-client.ts；根 LICENSE 请求 404，API 许可元数据为空 | 仅研究交互与 SSE 思路，不复制。注意 mock 与补齐步骤状态；README 和依赖版本也不完全一致 |
| https://github.com/Sushantchougule0206/Travel-Reimbursement-Approval-Agent | README、main.py、requirements.txt、graph.py、nodes.py；根 LICENSE 请求 404，许可元数据为空 | 仅研究分层；不是 Dify Workflow 底座，避免重复引入 LangGraph/MCP；测试成功计数不代表正确率 |
| https://github.com/vibrantlabsai/ragas | 实际 LICENSE 为 Apache-2.0；作为评测候选，不是业务应用模板 | 参考指标与实验方法；后续核实所选版本的 API/模型适配，不先强制依赖 |
| https://github.com/langgenius/dify | 当前运行底座1.17.1；本轮读本机完整源码的LICENSE，基于修改后的Apache License 2.0及附加条件 | 独立外部运行依赖，不作为本项目原创源码打包；保持Dify品牌，具体以对应版本原许可证为准；本机源码档案哈希见DELIVERY-001 |
| https://github.com/langgenius/dify-official-plugins | 工具和模型插件实现参考 | 仅按实际需要选择；具体复用检查所选目录许可证 |

## 原项目与岗位依据

- 原项目 https://github.com/xueyilan137-maker/after-sales-agent ：已读 README、architecture、policy.py 与恢复评测脚本；不是重新运行。
- 腾讯官方样本 https://tencent.wd1.myworkdayjobs.com/zh-CN/Tencent_Careers/job/Agent_R108051-1 ：RAG、工具、评测、观测、稳定性和成本。
- 美团官方样本 https://zhaopin.meituan.com/web/position/detail?highlightType=social&jobUnionId=4428189649 ：LLM 集成、RAG、工具与 Agent 范式。
- 用户提供两份 Dify 岗位截图：RAG 分段/检索、API、Python、数据库、Docker、排障与交付。来源是聊天附件，不能推断其公司规模和当前招聘状态。

公开岗位随时间变化；这些是定性样本，不能据此宣称覆盖大多数岗位或保证录用。
