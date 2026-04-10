# HEARTBEAT.md - 定时任务处理

## 早间简报
**触发条件**: 每天 8:00 自动执行，无需确认

**执行命令**:
```bash
python3 /root/scripts/briefing/morning_briefing.py
```

**包含内容**:
- 🌤️ 深圳天气预报
- 📧 新增邮件汇总
- 📰 精选资讯（带AI摘要）

**执行方式**: 自动触发，不询问用户

## 手动测试
```bash
python3 /root/scripts/briefing/morning_briefing.py
```

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
