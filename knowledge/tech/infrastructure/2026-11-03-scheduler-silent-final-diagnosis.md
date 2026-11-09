# 日程管家失聪二次诊断（2026-11-03 11:50 定稿）

## 一、最终时间线（API 实测，非日志推断）
| 时间 | 事件 | 证据 |
|---|---|---|
| 10-29 | scheduler 在 v0.22.4 multiplex 网关下正常收发（最后正常日） | scheduler/gateway.log 有完整 Inbound/response |
| 10-30 11:15 | 网关切 0.19.0-venv（版本切换）→ **scheduler 当天起零 Inbound** | scheduler log 停滞 |
| 11-01~11-02 | 双通道失聪（第一轮诊断，修了 ECS 网关竞态） | 11-02 修复后 aliyun助手 恢复 |
| 11-03 08:19/09:45/11:00/11:13 | 你发的 4 条测试消息全部到达飞书服务端，ECS 网关静默丢弃 | API 直查 + dedup 文件记录 3 个 message_id（08:19 撤回的没记） |
| 11-03 11:32 | **修复执行**：两 .env 白名单交叉补齐 + 网关重启（PID 1103689） | .env.bak-20261103-allowlist |
| 11-03 11:43 | aliyun助手 正常收发（你发指令，网关 2 秒收到处理） | 主 gateway.log Inbound |
| 11-03 11:33~11:47 | **日程管家私聊零新消息**——修复后你尚未测试 | API 直查返回 0 |

## 二、根因（源码级实锤）
v0.19.0 multiplex 网关的 **allowlist 跨 profile 泄漏**（0.22.4 修复 issue #72348，源码注释原文："a scoped miss returns default instead of falling through to os.environ, which may hold ANOTHER profile's first-writer bridged value — allowlist leak"）。

因果链：multiplex 下 default profile 的 `FEISHU_ALLOWED_USERS=ou_c2cde251...`（你在 aliyun助手 下的 open_id）被 YAML→env 桥接进 os.environ（first-writer-wins）→ scheduler 适配器 `_admit()` 用 `os.getenv` 读到 default 的白名单 → 你在日程管家 app 下的 open_id 是 ou_d8ae71cd（open_id 按 app 隔离）→ 不在名单 → `dm_policy_rejected` → 仅 DEBUG 级日志 → **静默丢弃**。

三重证据吻合：
1. dedup 文件记录了消息 ID（死点在 dedup 之后、_admit 处）但主 log/scheduler log 均无该消息 ID 痕迹
2. 断连时间点 = 10-30 11:15 切 0.19.0 的精确时刻（v0.22.4 下 10-29 还正常）
3. default profile 一直正常（它读到的白名单恰好是自己的 ID，泄漏对它无感）

## 三、已执行的修复（11:32，已生效）
两个 .env 的 `FEISHU_ALLOWED_USERS` 交叉补齐（互相包含对方 app 下的 open_id；open_id 按 app 隔离，交叉加入只是扩白名单，无安全副作用）：
- `/root/.hermes/.env`：`ou_c2cde251...,ou_d8ae71cd...`
- `/root/.hermes/profiles/scheduler/.env`：`ou_d8ae71cd...,ou_c2cde251...`
备份：`.env.bak-20261103-allowlist` × 2；网关已重启生效（PID 1103689，双 WS 正常）。

**⚠️ 尚未完成：修复后零测试**——你在日程管家发一条消息即完成闭环验证。11:43 aliyun助手 正常回复已证明网关整体健康、修复无副作用。

## 四、中期建议（待决策，不急）
1. **升级回 0.22.4**：根治 #72348（本修复是 workaround，白名单交叉后即使 0.19.0 的泄漏存在也读到正确值）。NAS 灾备期结束、版本切换脚本就绪（hermes-version-switch.sh）时可做
2. **失聪告警缺口**：本次故障 5 天（10-30~11-03）无人发现——`_admit` 静默丢弃设计使然。可在 heartbeat_syscheck（每小时）加一条“飞书双通道 WS 连接数=2”探活，或给 scheduler profile 建一个每日 no_agent 心跳 cron 推送测试卡片
3. 0.19.0 的 `_admit` 拒绝日志是 DEBUG 级——排障时临时加 `-v -v` 启动可见，已记入 skill
