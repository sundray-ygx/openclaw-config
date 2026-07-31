# HEARTBEAT.md - 定时任务处理

## Cron 健康检查（每天一次，9:00 后执行）

检查 `lastCronHealthCheck` 是否为今天。如果不是：
```bash
python3 /root/.openclaw/workspace/scripts/utils/cron_health_monitor.py
```
如果有报错任务，分析原因并提醒用户。执行后更新 `lastCronHealthCheck`。

## 记忆维护（每周一次）

读取 `memory/heartbeat-state.json`，检查 `lastMemoryMaintenance` 字段。
如果距今 >= 7 天：
1. 读最近 7 天的 `memory/YYYY-MM-DD.md` 日志
2. 提炼有价值的信息到对应文件（projects.md / lessons.md）
3. 压缩已完成一次性任务的日志为一行结论
4. 删除过期信息
5. 更新 `heartbeat-state.json` 的 `lastMemoryMaintenance` 为今天

## 工作区整洁检查（每周一次）

读取 `memory/heartbeat-state.json`，检查 `lastWorkspaceCheck` 字段。
如果距今 >= 7 天：
1. 运行检查脚本：`sh scripts/utils/check_workspace_root.sh`
2. 如发现散落文件，提醒用户归档
3. 更新 `heartbeat-state.json` 的 `lastWorkspaceCheck` 为今天

## 待办提醒检查

读取 `/root/.openclaw/workspace/memory/todo-state.json`，检查是否有需要提醒的待办事项。
检查逻辑：
1. 解析 JSON 中的 reminders 数组，提取 remind_time 和 status
2. 如果当前时间 >= remind_time，且 status 为 "⏳ 待提醒"，则提醒用户
3. 提醒后，将 status 更新为 "📋 已提醒"

## 系统健康检查（每日一次）

检查以下系统指标，如发现异常在 heartbeat 中直接提醒：

### 磁盘使用率告警（每日检查）
```bash
df -h / | grep vda3 | awk '{print $5}' | tr -d '%'
```
- **> 85%**: 立即告警，列出占用大户并建议清理
- **> 75%**: 提醒关注，提供清理建议
- **< 75%**: 正常，无需操作

### 其他检查项
- 内存使用（> 90% 告警）
- 僵尸进程（> 0 告警）
- Cron 任务状态（是否有连续失败）
