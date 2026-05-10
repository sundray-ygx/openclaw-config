# HEARTBEAT.md - 定时任务处理

## 每日反思生成（每天一次，8:45 后执行）

检查 `memory/heartbeat-state.json` 的 `lastDailyReflection` 字段。
如果今天尚未执行：
```bash
python3 /root/.openclaw/workspace/scripts/daily/daily_reflection.py
```
执行后更新 `lastDailyReflection` 为今天日期。

## 每周复盘（周五 18:30 后执行）

检查当前是否为周五且 `lastWeeklyReview` 不是本周：
```bash
python3 /root/.openclaw/workspace/scripts/daily/weekly_review.py
```
执行后更新 `lastWeeklyReview` 为本周日期。

## 每周磁盘清理（周一执行）

检查当前是否为周一且 `lastDiskCleanup` 不是本周：
```bash
rm -rf /tmp/pip-* && find /root/.openclaw/workspace -name '__pycache__' -exec rm -rf {} + 2>/dev/null && df -h /
```
如果磁盘使用 > 85%，额外清理日志和临时文件。执行后更新 `lastDiskCleanup`。

## Cron 健康检查（每天一次，9:00 后执行）

检查 `lastCronHealthCheck` 是否为今天。如果不是：
```bash
python3 /root/.openclaw/workspace/scripts/utils/cron_health_monitor.py
```
如果有报错任务，分析原因并提醒用户。执行后更新 `lastCronHealthCheck`。

## 租金提醒（每月 25 日/27 日执行）

### 13B402 租金提醒
如果今天是 25 号且 `lastRentReminder13B` 不是本月：
发送 13B402 租金账单提醒消息给用户，内容包括水费/电费/燃气费账单收集。
执行后更新 `lastRentReminder13B`。

### 16A503 租金提醒
如果今天是 27 号且 `lastRentReminder16A` 不是本月：
```bash
python3 /root/.openclaw/workspace/scripts/rent/rent_expense_remind.py
```
执行后更新 `lastRentReminder16A`。

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

运行 `weekly_health_checklist.py` 脚本检查系统健康状态：
- 磁盘空间
- 内存使用
- 僵尸进程
- 过期文件
- Cron 任务状态

如果发现问题，在 heartbeat 中直接提醒。
