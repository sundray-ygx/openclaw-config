# MEMORY.md - 核心记忆索引

## 系统状态

### 定时任务运行状况
- **状态**: 🟢 正常（2026-08-13 升级后复检）
- **任务数量**: crontab 5 个 + OpenClaw cron 1 个
- **OpenClaw 版本**: 2026.7.1-2（2026-08-13 升级，含 openclaw-lark 2026.7.16）
- **模型链**: primary=zai/glm-5，fallbacks=[deepseek, volcengine（欠费待充值）]
- **最近巡检**: 2026-08-13 深度巡检，修复 2 个 P0 静默故障 + 升级 + systemd 管理修复

### 2026-08-13 巡检修复要点
- 🔴 GitHub 每日同步失效 12 天（systemEvent 假阳性）→ 改 isolated 模式 + 失败告警
- 🔴 简报 AI 摘要失败 108 天（PATH + 火山引擎欠费）→ 绝对路径 + summarize 双 provider（volcengine→deepseek 自动切换）
- 🟡 journald 3.0G → 限 200M + logrotate
- ⚠️ 火山引擎账户欠费（影响所有 volcengine API，已由 deepseek 兑底）

### 自动化流程（优化后）
| 任务 | 时间 | 状态 |
|------|------|------|
| 早间简报 | 每日 08:00 | ✅ 正常（AI摘要已验证） |
| NAS 自动备份 | 每日 02:00 | ✅ 正常 |
| 安全配置巡检 | 每周一 09:00 | ✅ 正常 |
| 租金账单提醒 | 每月 25/27 日 | ✅ 正常 |
| 磁盘清理 | 每周一 10:00 | ✅ 正常 |
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
