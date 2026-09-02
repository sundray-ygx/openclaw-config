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

## Promoted From Short-Term Memory (2026-08-18)

<!-- openclaw-memory-promotion:memory:memory/2026-08-13.md:8:11 -->
- [PROJECT:OpenClaw系统] 升级 2026.5.28 → 2026.7.1-2 + systemd 修复: 升级成功（含 openclaw-lark 2026.7.16、auth 迁 SQLite）；修复 systemd 双重管理冲突（user service 归档 .bak-20260813，加 OPENCLAW_NO_RESPAWN=1）; memorySearch 已按用户决策禁用；备份 /root/openclaw-backups/openclaw-20260813_153304.tar.gz (242M); 升级特性报告: archive/reports/2026-08-13-OpenClaw升级特性报告.md; 详情见 projects.md「OpenClaw 环境维护」 [score=0.830 recalls=0 avg=0.620 source=memory/2026-08-13.md:8-11]

## Promoted From Short-Term Memory (2026-08-21)

<!-- openclaw-memory-promotion:memory:memory/2026-08-13.md:4:5 -->
- [SYSTEM:业务巡检] 深度巡检 + 故障修复: 巡检发现 2 个 P0 静默故障（GitHub 同步失效 12 天、简报 AI 摘要失败 108 天），全部修复；summarize 改 volcengine/deepseek 双 provider；journald 限 200M；logrotate 补 5 个业务日志; 报告: archive/reports/2026-08-13-业务巡检报告.md [score=0.815 recalls=0 avg=0.620 source=memory/2026-08-13.md:4-5]
<!-- openclaw-memory-promotion:memory:memory/2026-08-14.md:4:4 -->
- [巡检优化] P1 GitHub同步投递 + P3 RSS源修复: GitHub cron 投递目标改为正确 open_id（ou_c2cde2***）；ai_agent_news.py 替换 6 个失效 RSS 源为可靠源 [score=0.815 recalls=0 avg=0.620 source=memory/2026-08-14.md:4-4]
<!-- openclaw-memory-promotion:memory:memory/2026-08-14.md:7:7 -->
- [PROJECT:OpenClaw环境] GLM 全链路切换（详情见 projects.md）: key 切换（6 处，硬链接同步）+ openclaw.json 添加 zai provider + 模型精简 12→4（glm-5.2/4.7/4.7-flash/4.6v）+ coding 套餐端点统一 + ANTHROPIC 死代码清除，全端点验证通过 [score=0.815 recalls=0 avg=0.620 source=memory/2026-08-14.md:7-7]

## Promoted From Short-Term Memory (2026-08-29)

<!-- openclaw-memory-promotion:memory:memory/2026-08-25.md:13:13 -->
- [SECURITY] SSH 暴力破解防护加固（方案 A）: **标签**: #security #ssh #fail2ban [score=0.850 recalls=0 avg=0.620 source=memory/2026-08-25.md:13-13]
<!-- openclaw-memory-promotion:memory:memory/2026-08-25.md:5:8 -->
- [SECURITY] SSH 暴力破解防护加固（方案 A）: **根因**: SSH 端口暴露在公网，持续遭受暴力破解攻击（7天133万次尝试）; **修复内容**:; fail2ban `maxretry: 3 → 2`（2次失败即封禁）; fail2ban `findtime: 600s → 3600s`（1小时窗口） [score=0.850 recalls=0 avg=0.620 source=memory/2026-08-25.md:5-8]
<!-- openclaw-memory-promotion:memory:memory/2026-08-25.md:9:12 -->
- [SECURITY] SSH 暴力破解防护加固（方案 A）: 开启 `bantime.increment` 递增封禁，最多 7 天; SSH `MaxAuthTries: 6 → 3`; **备份文件**: /etc/fail2ban/jail.local.bak-20260825, /etc/ssh/sshd_config.bak-20260825; **验证**: 配置语法通过，fail2ban 正常运行，当前被封 5 IP [score=0.850 recalls=0 avg=0.620 source=memory/2026-08-25.md:9-12]
<!-- openclaw-memory-promotion:memory:memory/2026-08-24-1642.md:19:19 -->
- 📋 系统巡检报告 | 2026-08-24 14:07: **总体状态：🟢 正常运行（135 天）** [score=0.803 recalls=0 avg=0.620 source=memory/2026-08-24-1642.md:19-19]
<!-- openclaw-memory-promotion:memory:memory/2026-08-24-1642.md:25:28 -->
- 1️⃣ 系统运行状态: | 指标 | 状态 | 详情 | |------|------|------| | 磁盘 | ✅ 正常 | 25G / 40G（65%），剩余 14G | | 内存 | ⚠️ 偏紧 | 已用 1.0G / 1.8G，可用 819M | [score=0.803 recalls=0 avg=0.620 source=memory/2026-08-24-1642.md:25-28]
<!-- openclaw-memory-promotion:memory:memory/2026-08-24-1642.md:29:32 -->
- 1️⃣ 系统运行状态: | Swap | ⚠️ 已用 | 381M / 6G 已使用 | | CPU 负载 | ✅ 正常 | 0.48 / 0.34 / 0.15 | | 僵尸进程 | ✅ 正常 | 0 | | inode | ✅ 正常 | 13% | [score=0.803 recalls=0 avg=0.620 source=memory/2026-08-24-1642.md:29-32]
<!-- openclaw-memory-promotion:memory:memory/2026-08-24-1642.md:33:33 -->
- 1️⃣ 系统运行状态: | Docker | ✅ 正常 | sing-box 运行 4 个月 | [score=0.803 recalls=0 avg=0.620 source=memory/2026-08-24-1642.md:33-33]
<!-- openclaw-memory-promotion:memory:memory/2026-08-24-1642.md:35:35 -->
- 1️⃣ 系统运行状态: **Top 内存占用：** [score=0.803 recalls=0 avg=0.620 source=memory/2026-08-24-1642.md:35-35]
<!-- openclaw-memory-promotion:memory:memory/2026-08-24-1642.md:36:38 -->
- 1️⃣ 系统运行状态: OpenClaw Gateway — 359M（18.7%）; openclaw-tui — 256M（13.3%）; 阿里云盾 — 42M（2.1%） [score=0.803 recalls=0 avg=0.620 source=memory/2026-08-24-1642.md:36-38]
<!-- openclaw-memory-promotion:memory:memory/2026-08-24-1642.md:44:47 -->
- 2️⃣ OpenClaw 运行状态: | 项目 | 状态 | 详情 | |------|------|------| | 版本 | ✅ | 2026.7.1-2 (0790d9f) | | Gateway 服务 | ✅ | 运行 1 天 20 小时，内存 410M/450M | [score=0.803 recalls=0 avg=0.620 source=memory/2026-08-24-1642.md:44-47]
