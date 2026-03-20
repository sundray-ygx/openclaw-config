# HEARTBEAT.md - 定时任务配置
# 迁移完成时间: 2026-03-17
# 原属: main (小助) → 现属: scheduler

## 每日任务

### 早间简报
- **时间**: 每天 8:00
- **任务**: 生成并发送早间简报
- **命令**: `python3 /root/scripts/morning_briefing.py`
- **内容**: 深圳天气 + 邮件汇总 + 精选资讯
- **发送目标**: 当前scheduler会话
- **状态**: ✅ 已修复，使用scheduler账号发送

### OpenClaw每日资讯推送
- **时间**: 每天 8:05
- **任务**: 运行OpenClaw资讯脚本
- **命令**: `python3 /root/scripts/openclaw_news.py`

### 每日工作日报
- **时间**: 每天 8:30
- **任务**: 运行日报脚本
- **命令**: `python3 /root/scripts/daily_report.py`

### NAS自动备份
- **时间**: 每天 2:00
- **任务**: 执行NAS备份
- **命令**: `/root/scripts/nas_backup.sh`

### NAS备份通知
- **时间**: 每天 8:35
- **任务**: 读取备份通知
- **命令**: `cat /tmp/backup-notification-$(date +%Y%m%d).txt`

### 每日归档
- **时间**: 每天 23:00
- **任务**: 执行每日归档
- **命令**: `python3 /root/.openclaw/workspace/knowledge/tech/automation/cron/daily_archive.py`

## 每周任务

### 周复盘
- **时间**: 周五 18:30
- **任务**: 运行周复盘脚本
- **命令**: `python3 /root/.openclaw/workspace/skills/weekly-review/weekly_review.py`

### 周报提醒
- **时间**: 周五 17:00
- **任务**: 运行周报提醒脚本
- **命令**: `python3 /root/.openclaw/workspace/knowledge/tech/automation/cron/weekly_reminder.py`

### 周计划制定
- **时间**: 周日 20:00
- **任务**: 生成下周周计划草稿

### 周计划提醒
- **时间**: 周日 20:00
- **任务**: 提醒用户做下周计划

### 日计划生成
- **时间**: 周一 8:30
- **任务**: 生成下周日计划
