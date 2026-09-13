# MEMORY.md - 核心记忆索引

## 系统状态

### 定时任务运行状况
- **状态**: 🟢 正常（2026-08-13 升级后复检）
- **任务数量**: crontab 5 个 + OpenClaw cron 1 个
- **OpenClaw 版本**: 2026.7.1-2（2026-08-13 升级，含 openclaw-lark 2026.7.16）
- **模型链**: primary=zai/glm-5.3，fallbacks=[deepseek/deepseek-v4-pro, volcengine/doubao-seed-2-1-turbo-260628]
- **火山引擎欠费是误判**: 标准端点(/api/v3)欠费，但 Coding Plan 端点(/api/coding/v3)正常可用，现有配置用的就是 Coding Plan
- **2026-09-02 模型列表更新**: deepseek 3个 / zai 7个 / volcengine 12个，全部实测可用；glm-5v-turbo 和 glm-4.7-flashx 套餐不支持已移除
- **最近巡检**: 2026-08-13 深度巡检，修复 2 个 P0 静默故障 + 升级 + systemd 管理修复

### 2026-08-13 巡检修复要点
- 🔴 GitHub 每日同步失效 12 天（systemEvent 假阳性）→ 改 isolated 模式 + 失败告警
- 🔴 简报 AI 摘要失败 108 天（PATH + 火山引擎欠费）→ 绝对路径 + summarize 双 provider（volcengine→deepseek 自动切换）
- 🟡 journald 3.0G → 限 200M + logrotate
- ⚠️ ~~火山引擎账户欠费~~（2026-09-02 证实为误判，Coding Plan 端点正常）

### 自动化流程（优化后）
| 任务 | 时间 | 状态 |
|------|------|------|
| 早间简报 | 每日 08:00 | ✅ 正常（AI摘要已验证） |
| NAS 自动备份 | 每日 02:00 | ✅ 正常 |
| 安全配置巡检 | 每周一 09:00 | ✅ 正常 |
| 租金账单提醒 | 每月 25/27 日 | ✅ 正常 |
| 磁盘清理 | 每周一 10:00 | ✅ 正常 |
| GLM 渠道健康检查 | 每日 09:30 | ✅ 纯脚本零LLM，正常静默、异常才推送（09-13 静默模式） |
| Memory Dreaming | 每日 03:00 | ✅ 内置 |

### 已删除的定时任务（2026-06-03）
| 任务 | 原因 |
|------|------|
| 每日反思（daily_reflection） | 已迁移到其他 AI Agent，持续空跑 |
| 自动归档 inbox | 依赖不满足（无日报内容）|
| SSL 证书续期 | acme.sh 无证书管理，任务无用 |

### 已迁移到其他 AI Agent
| 任务 | 说明 |
|------|------|
| 每日工作日报 | 已从 crontab 移除 |
| 周复盘 | 已从 crontab 移除 |
| 周反思报告 | 已从 crontab 移除 |
| 月反思报告 | 已从 crontab 移除 |

## 本周概览 (第 16 周：4/14-4/20)

### 关键事项
- **周一 4/14**: 定时任务优化方案 C 执行完成
- 删除 6 个冗余任务，清理 11 个冗余脚本文件
- 预期 token 节省：35-45%
- **周四 5/8**: 系统性切换至 zai/glm-5
- 删除 bailian provider 配置，所有 AI 调用统一使用 zai/glm-5
- 更新 daily_reflection.py 和 weekly_review.py

### 待办
- [ ] 观察反思 V3 效果（关注是否有重复反思点）

## 最近日志
- `memory/2026-09-13.md` - 定时任务 LLM 消耗优化（方案B：GLM 检查 agentTurn→command 零LLM，GitHub 保留 agent）
- `memory/2026-09-08.md` - new-api 网关部署+ECS 三平台灰度切换完成（Claude Code/Hermes/OpenClaw→api.ygxpro.online），OpenClaw 接线三处对齐要点见 deployment 文档
- `memory/2026-08-13.md` - 业务巡检 + 2 个 P0 故障修复（GitHub同步/AI摘要）
- `memory/2026-05-08.md` - 系统性切换至 zai/glm-5
- `memory/2026-04-14.md` - 定时任务优化方案 C 执行记录
- `memory/2026-04-05.md` - 旧 API 配置问题分析（已解决）
- `memory/2026-04-03.md` - 周反思质量改进、cron 冗余清理
- `memory/2026-04-01.md` - 定时任务评估清理
- `memory/2026-03-31.md` - Claude Code 预算提醒重复执行修复

## 知识库文件
- 项目追踪：`memory/projects.md` - 记录各项目进展
- 经验教训：`memory/lessons.md` - 归类整理问题和教训

## 知识库位置
- 日日志：`memory/YYYY-MM-DD.md`
- 项目追踪：`memory/projects.md`
- 经验教训：`memory/lessons.md`

## Promoted From Short-Term Memory (2026-09-06)

<!-- openclaw-memory-promotion:memory:memory/2026-09-02.md:13:16 -->
- [PROJECT:OpenClaw系统] 模型列表全面更新 + 火山引擎"欠费"根因诊断: GLM-5.3/5.3-flash/5.1 强制思考模式（thinking.type 仅支持 enabled），OpenClaw 调用正常; 旧 MEMORY 里"系统性切换至 zai/glm-5"记录有误，实际此前默认是 volcengine/doubao-seed-2-0-pro; **教训**: 诊断 API 可用性必须区分端点（Coding Plan vs 标准端点），curl 测试时 shell 环境变量传参有坑（AuthHeader 假错误），用 python 直读环境变量才拿到真实错误; **标签**: #models #provider #volcengine #zai #deepseek [score=0.816 recalls=0 avg=0.620 source=memory/2026-09-02.md:13-16]
<!-- openclaw-memory-promotion:memory:memory/2026-09-02.md:5:8 -->
- [PROJECT:OpenClaw系统] 模型列表全面更新 + 火山引擎"欠费"根因诊断: 火山引擎"欠费"是误判：标准端点 `/api/v3` 欠费（AccountOverdueError），但 Coding Plan 端点 `/api/coding/v3` 完全正常，现有配置走的就是 Coding Plan，无需修复; 模型列表已更新：deepseek 3 个 / zai 7 个 / volcengine 12 个，共 22 个，全部实测可用; 默认模型切换：zai/glm-5.3（1M ctx），fallbacks=[deepseek/deepseek-v4-pro, volcengine/doubao-seed-2-1-turbo]; scheduler agent → zai/glm-4.7-flash；coding agent → zai/glm-5.3 [score=0.816 recalls=0 avg=0.620 source=memory/2026-09-02.md:5-8]
<!-- openclaw-memory-promotion:memory:memory/2026-09-02.md:9:12 -->
- [PROJECT:OpenClaw系统] 模型列表全面更新 + 火山引擎"欠费"根因诊断: **实测不可用已移除**: glm-5v-turbo（套餐未开放 1311）、glm-4.7-flashx（需单独计费 1113）、doubao-seed-2-1-pro-260628（不支持 coding plan 404）; **文件变更**: /root/.openclaw/openclaw.json（备份 openclaw.json.bak-20260902）、MEMORY.md; **关键发现**:; zai 的 apiKey 不在 openclaw.json/env，存在 auth_profile_store（SQLite: agents/main/agent/openclaw-agent.sqlite），profile 名 `zai:default` [score=0.816 recalls=0 avg=0.620 source=memory/2026-09-02.md:9-12]

## Promoted From Short-Term Memory (2026-09-07)

<!-- openclaw-memory-promotion:memory:memory/2026-09-02.md:19:21 -->
- [补记] TUI /model 看不到新增模型的根因: **根因**: `agents.defaults.models` 是 allowlist+目录，TUI /model 列表只展示其中条目。只加 providers 模型定义不加 allowlist，模型"存在但不可选"; **修复**: 8 个新模型全部加入 allowlist 并配别名（DS-Vision / GLM-5.3 / GLM-5.3-Flash / GLM-5.1 / Doubao-Evolving / Doubao-2.1-Turbo / Volc-DS-Pro-GA / Volc-DS-Flash-GA），已验证 configured+alias 标签齐全; **教训**: 加模型要同时改两处 — providers 定义 + agents.defaults.models allowlist [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-02.md:19-21]

## Promoted From Short-Term Memory (2026-09-08)

<!-- openclaw-memory-promotion:memory:memory/2026-09-03-1620.md:15:15 -->
- 第 5 步：更新记忆文件: assistant: 全部完成。汇报： [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-03-1620.md:15-15]
<!-- openclaw-memory-promotion:memory:memory/2026-09-03-1620.md:22:23 -->
- 火山引擎"欠费"诊断（已破案）: **根因：误判**。之前测的是标准端点 `/api/v3`（该端点确实账户欠费），但你的配置走的是 **Coding Plan 端点 `/api/coding/v3`，完全正常可用**（实测 130 个模型可调）; 配置无需修复，直接拉取了最新模型列表 [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-03-1620.md:22-23]
<!-- openclaw-memory-promotion:memory:memory/2026-09-03-1620.md:27:30 -->
- 模型列表更新（共 22 个，全部实测验证）: | Provider | 数量 | 新增 | 移除（不可用） | |----------|------|------|--------------| | **zai 智谱** | 7 | 🆕 glm-5.3（旗舰）、glm-5.3-flash（多模态，1M ctx）、glm-5.1 | glm-5v-turbo（套餐未开放）、glm-4.7-flashx（需单独计费） | | **volcengine** | 12 | 🆕 doubao-seed-evolving、seed-2-1-turbo、deepseek-v4-pro-ga、deepseek-v4-flash-ga | seed-2-1-pro（不支持 coding plan） | [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-03-1620.md:27-30]
<!-- openclaw-memory-promotion:memory:memory/2026-09-03-1620.md:31:31 -->
- 模型列表更新（共 22 个，全部实测验证）: | **deepseek** | 3 | 🆕 v4-flash-vision-exp（视觉）；V4 系列上下文已更新为 1M | 无 | [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-03-1620.md:31-31]

## Promoted From Short-Term Memory (2026-09-09)

<!-- openclaw-memory-promotion:memory:memory/2026-09-01-0917.md:2:2 -->
- Session: 2026-09-01 hermes-config 同步脚本（已压缩）: 一次性任务，已提炼至 projects.md「Hermes 部署」。核心：Hermes 侧同步脚本完成并 push，路径2配置完成。 [score=0.815 recalls=0 avg=0.620 source=memory/2026-09-01-0917.md:2-2]
<!-- openclaw-memory-promotion:memory:memory/2026-09-01-0957.md:2:2 -->
- Session: 2026-09-01 SSH/git 排障（已压缩）: 一次性任务：客户端 git SSH 认证排障（PowerShell config 检查 / -F /dev/null 绕过）。无遗留。 [score=0.815 recalls=0 avg=0.620 source=memory/2026-09-01-0957.md:2-2]

## Promoted From Short-Term Memory (2026-09-10)

<!-- openclaw-memory-promotion:memory:memory/2026-09-02-2125.md:2:2 -->
- Session: 2026-09-02 模型列表更新规划（已压缩）: 规划会话，执行结果已完整记录在 2026-09-02.md 并提炼至 projects.md「模型体系大更新」。无新增信息。 [score=0.804 recalls=0 avg=0.620 source=memory/2026-09-02-2125.md:2-2]
<!-- openclaw-memory-promotion:memory:memory/2026-09-04-1112.md:2:2 -->
- Session: 2026-09-04（已压缩）: 空会话记录，无有效内容。 [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-04-1112.md:2-2]
<!-- openclaw-memory-promotion:memory:memory/2026-09-05-0914.md:15:18 -->
- 现状: **frps**：运行中（0.60.0，bindPort 7000），已有 NAS 上的 frpc 接入（如 nas 服务走本地 5000 端口的模式）。ECS 本地 8648 尚无监听——正常，等 frpc 配好 tcp 代理 remote_port=8648 后出现; **nginx**：1.24.0，conf.d 下已有 nas/pan/bill 等 6 个站点，套路统一（80 跳 443 + 反代 127.0.0.1 端口）; **证书**：`/etc/letsencrypt/live/ygxpro.online/` 是**泛域名证书**（`*.ygxpro.online`），hermes 子域名可直接复用，**无需新申请**; **DNS**：`hermes.ygxpro.online` **未解析**，nas.ygxpro.online 指向本机 47.119.177.194，需新增解析 [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-05-0914.md:15-18]
<!-- openclaw-memory-promotion:memory:memory/2026-09-05-0914.md:19:19 -->
- 现状: 文档里的配置可直接用，只需改证书路径 [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-05-0914.md:19-19]
<!-- openclaw-memory-promotion:memory:memory/2026-09-05-0914.md:23:23 -->
- 执行方案（待你决策）: **ECS 侧（我来做）：** [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-05-0914.md:23-23]
<!-- openclaw-memory-promotion:memory:memory/2026-09-05-0914.md:24:27 -->
- 执行方案（待你决策）: 写 `/etc/nginx/conf.d/hermes-studio.conf`，基于文档模板，改两处：; 证书路径 → `/etc/letsencrypt/live/ygxpro.online/{fullchain.pem,privkey.pem}`（复用泛域名证书）; 其余保留（WebSocket、SSE、3600s 超时、buffering off 都合理，Hermes Studio 是流式应用需要）; `nginx -t && nginx -s reload` [score=0.803 recalls=0 avg=0.620 source=memory/2026-09-05-0914.md:24-27]
