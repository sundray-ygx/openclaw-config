# ECS 飞书双通道架构评估（2026-11-02）

## 一、现状核实（全部只读验证）

### 两个通道的身份
| 通道 | App ID | 承载 | 角色定位 |
|---|---|---|---|
| **aliyun助手** | cli_a93b96047e7a5bc3 | default profile | 交互对话入口（HOME_CHANNEL=Boss 私聊 ou_c2cde251...） |
| **日程管家** | cli_a93c6b1e1ff89bd4 | scheduler profile | 纯推送身份（无 HOME_CHANNEL，2026-10 定版「12+ 脚本共用勿动」） |

网关 multiplex_profiles: true，单进程同时挂 2 条飞书 WS（served_profiles: default + scheduler）。

### 推送归属现状（root crontab 活跃任务逐一验证）
**日程管家承接 100% 的 ECS 活跃推送**：
| 任务 | 时间 | 验证方式 |
|---|---|---|
| morning_briefing 早报 | 08:00 | 脚本硬编码 cli_a93c6b1e，今晨 08:01 实发成功 |
| heartbeat_syscheck 心跳 | 每小时 | 硬编码 cli_a93c6b1e |
| perf-sentinel 性能哨兵 | */30 | 硬编码 cli_a93c6b1e |
| security_check / nas_backup / check_newapi / glm-check / github-sync | 周一/02:00/08:20/09:30/23:30 | 经 notify_feishu.py 公共库（cli_a93c6b1e） |
| ecs-failover-probe | */5 | 硬编码 cli_a93c6b1e（仅故障时推） |

**aliyun助手当前唯一活跃用途 = Boss 交互对话**（default profile 网关入口）。
其名下脚本（房租三件套 / daily_report / weekly_review / news_summary / daily_reflection）**均不在 ECS crontab**——属 NAS 侧 hermes cron 任务线（NAS 灾后 13 任务已建、全部 disabled 待点火）。当前房租/复盘推送整体静默。

### 会话历史佐证
- default（aliyun助手）：2026-09-05 一次对话（258 条）
- scheduler（日程管家）：2026-10-08 一次对话（297 条）
- 两个 app 均有真实对话能力，但日常 Boss 对话入口是 aliyun助手

## 二、评估：是否需要两个通道

### 双通道的真实价值
1. **职责隔离**：系统告警（早报/心跳/哨兵，每日 30+ 条）与对话窗口分离——告警刷屏不会淹没 Boss 的对话上下文，对话窗保持干净。
2. **app 层风险隔离**：单 app 被飞书限流/审核/停用时，另一通道不受影响。
3. **配额隔离**：飞书单 app 有 API 频控，密集推送不挤占对话通道。
4. **已有定版**：2026-10 记忆明确「日程管家保留为纯推送身份」。

### 双通道的成本与昨天事故的教训
1. 昨天 11-02 事故证明：**两条 WS 挂在同一网关进程，进程级故障同生共死**——双 app 并未提供进程级高可用（那需要跨机冗余，如 NAS 侧小群）。
2. 两个聊天窗口的心智负担（Boss 需知道「对话找 aliyun助手，告警看日程管家」）。
3. 网关多维护一条 WS（但资源开销可忽略：单进程多 1 条连接）。

### 备选方案对比
| 方案 | 改动 | 收益 | 代价 |
|---|---|---|---|
| **A. 维持双通道（现状，明确分工归档）** | 零改动 | 保留隔离；交互/推送职责清晰 | 双窗口心智负担（已习惯） |
| B. 收敛为单通道（全走日程管家） | 网关撤 scheduler profile + Boss 对话入口换成日程管家 | 少 1 条 WS、1 个窗口 | 对话与告警混流；改动大；失去 app 层隔离 |
| C. 收敛为单通道（全走 aliyun助手） | 12+ 脚本凭据统一切换 + 网关撤 scheduler | 同上 | 改动量最大（12+ 脚本+验证），且违背 10 月定版 |

## 三、建议

**推荐方案 A：维持双通道。**
理由：改动为零；职责隔离是真实价值而非形式；昨天事故的根因是网关进程竞态（已修复+归档监控指纹），与通道数量无关——收敛为单通道既不能防该事故，还会把「对话+全部系统告警」押在同一个 app 上，一旦该 app 限流则全哑。

**需 Boss 决策的点**：
1. 选 A / B / C？
2. 若选 A：是否需要我把「通道分工表」补进 hermes-gateway-troubleshooting skill（已有定版记忆，补一份推送归属清单，便于日后排障时快速定位"这条推送走哪个 app"）？
3. NAS 点火后，个人生活类推送（房租/日报/复盘）按现脚本凭据自动走 aliyun助手——维持此规划，还是趁 NAS 未点火统一切到日程管家？（若切，需改 5+ 个脚本）
