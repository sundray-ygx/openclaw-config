# Weekly Review Skill

自动从 Notion 日复盘生成周复盘并推送飞书通知。

## 功能

- 每周五 18:30 自动执行
- 读取本周（周一到周五）日复盘数据
- AI 分析总结生成周复盘（摘要 + 详细版）
- 更新 Notion 周复盘数据库
- 飞书推送复盘摘要（使用自建应用）

## 配置

### 环境变量（必需）

所有敏感配置必须通过环境变量设置，禁止硬编码：

```bash
# Notion 配置（必需）
export NOTION_API_KEY="your_notion_api_key"
export NOTION_DAILY_REVIEW_DB_ID="your_daily_review_database_id"
export NOTION_WEEKLY_REVIEW_DB_ID="your_weekly_review_database_id"

# 飞书应用配置（必需）
export FEISHU_APP_ID="your_feishu_app_id"
export FEISHU_APP_SECRET="your_feishu_app_secret"
export FEISHU_USER_ID="your_feishu_user_id"
```

### 配置检查

运行前请确认环境变量已设置：
```bash
echo $NOTION_API_KEY
echo $FEISHU_APP_ID
```

### 定时任务

```cron
# 每周五 18:30 执行
30 18 * * 5 cd /root/.openclaw/workspace && python3 skills/weekly-review/weekly_review.py >> /var/log/weekly-review.log 2>&1
```

## 使用方法

### 自动执行

无需操作，每周五自动运行。

### 手动执行

```bash
python3 /root/.openclaw/workspace/skills/weekly-review/weekly_review.py
```

### 强制指定周

```bash
python3 weekly_review.py --week 2026-03-10
```

## 输出格式

### 飞书通知（摘要）

```
📋 第11周复盘摘要（3月10日 至 3月14日）

【核心成果】
✅ AI研发流程融合：完成OpenClaw多环境部署，完整实践AI-Native Spec流程
✅ 项目推进：集群1.0版本持续跟进，零中断2.0-ROF项目信息整理完成
✅ 知识分享：NMC高可用团队内部分享AI Coding使用经验
✅ 工具应用：打通Apple Watch健康数据管线方案，完成Notion数据库对接

【主要问题】
⚠️ 客户拜访记录查看和行业资讯跟进不够系统化
⚠️ 日复盘填写质量需提升（反思部分多为模板）

【下周重点】
📌 持续跟进集群1.0和ROF项目
📌 完善OpenClaw与Notion自动化流程
📌 建立客户拜访和行业资讯的系统化机制

📄 详细复盘：https://www.notion.so/xxx

---
💡 本消息由 OpenClaw Weekly Review Skill 自动生成
```

## 数据库字段映射

### 日复盘数据库
- `日期` - date
- `今日复盘` - rich_text
- `今日反思` - rich_text
- `今天安排` - rich_text
- `星期` - rich_text

### 周复盘数据库
- `周` - title
- `开始日期` - date
- `周计划` - rich_text
- `周复盘` - rich_text
- `对应日` - relation

## 依赖

- Python 3.7+
- requests

## 版本

v1.0.0 - 基础功能：自动周复盘 + 飞书通知
