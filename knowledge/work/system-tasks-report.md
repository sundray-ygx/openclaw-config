# 系统任务汇总报告

> 生成时间: 2026-03-17  
> 涵盖范围: 定时任务、自动化脚本、系统服务

---

## 一、定时任务清单（17个）

### 每日任务（6个）

| 序号 | 任务名 | 执行时间 | 功能描述 | 脚本路径 | 配置位置 | 数据存储 | 可迁移性 |
|:---:|--------|:-------:|----------|----------|----------|----------|:-------:|
| 1 | 早间简报 | 8:00 | 推送天气、邮件、资讯汇总 | `/root/scripts/morning_briefing.py` | `cron/jobs.json` | `daily-reports/`, 飞书 | ✅ 完整 |
| 2 | OpenClaw资讯 | 8:00 | 推送GitHub最新动态 | `/root/scripts/openclaw_news.py` | `cron/jobs.json` | 飞书卡片 | ✅ 完整 |
| 3 | 每日工作日报 | 8:30 | 生成昨日工作日报 | `/root/scripts/daily_report.py` | `cron/jobs.json` | `daily-reports/`, `memory/`, 飞书 | ✅ 完整 |
| 4 | NAS备份通知 | 8:35 | 发送备份完成通知 | `cat /tmp/backup-notification-*.txt` | `cron/jobs.json` | `/tmp/backup-notification-*.txt` | ✅ 完整 |
| 5 | NAS自动备份 | 2:00 | 备份配置到NAS | `/root/scripts/nas_backup.sh` | `cron/jobs.json` | NAS: `/aliyun_backup/server-backup/` | ✅ 完整 |
| 6 | 每日归档 | 23:00 | 归档日报到月份目录 | `/root/.openclaw/workspace/growth/multi-agents/xiaomi/cron/daily_archive.py` | `cron/jobs.json` | `archive/` | ✅ 完整 |

### 每周任务（5个）

| 序号 | 任务名 | 执行时间 | 功能描述 | 脚本路径 | 配置位置 | 可迁移性 |
|:---:|--------|:-------:|----------|----------|----------|:-------:|
| 7 | 周复盘 | 周五 18:30 | 生成本周复盘 | 待实现 | `cron/jobs.json` | ⚠️ 需开发 |
| 8 | 周报提醒 | 周五 17:00 | 提醒写周报 | 待实现 | `cron/jobs.json` | ⚠️ 需开发 |
| 9 | 周计划制定 | 周日 20:00 | 生成下周计划 | 待实现 | `cron/jobs.json` | ⚠️ 需开发 |
| 10 | 周计划提醒 | 周日 20:00 | 提醒做周计划 | 待实现 | `cron/jobs.json` | ⚠️ 需开发 |
| 11 | 日计划生成 | 周一 8:30 | 生成本周日计划 | 待实现 | `cron/jobs.json` | ⚠️ 需开发 |

### 单次/临时任务（6个）

| 序号 | 任务名 | 执行时间 | 状态 | 说明 |
|:---:|--------|:-------:|:----:|------|
| 12 | 年度OKR对齐提醒 | 3月18日 | 启用 | 一次性提醒 |
| 13 | AI-native考试提醒-周三 | 3月18日 | 启用 | 一次性提醒 |
| 14 | AI-native考试提醒-周四 | 3月19日 | 启用 | 一次性提醒 |
| 15 | 体系管理周会提醒 | 3月17日 18:00 | 启用 | 一次性提醒 |
| 16 | 产线周会提醒-交换机 | 3月19日 | 启用 | 一次性提醒 |
| 17 | 产线周会提醒-无线 | 3月21日 | 启用 | 一次性提醒 |

---

## 二、核心脚本详解

### 1. 早间简报脚本

```
路径: /root/scripts/morning_briefing.py
功能: 每天早上8点推送天气、邮件、海外资讯、国内AI资讯
依赖: 
  - 飞书API (FEISHU_APP_ID, FEISHU_APP_SECRET)
  - 邮箱IMAP (163/QQ/企业邮箱)
  - RSS订阅源 (量子位、36氪、钛媒体等)
  - sing-box代理 (访问海外RSS)
输出: 飞书卡片消息
数据存储: 无本地存储，直接发送飞书
```

**可迁移性**: ✅ 完整
- 脚本独立，配置在代码中
- 依赖外部服务（飞书、邮箱、RSS）
- 迁移需重新配置API密钥

---

### 2. OpenClaw资讯脚本

```
路径: /root/scripts/openclaw_news.py
功能: 推送OpenClaw GitHub最新动态
依赖:
  - GitHub API
  - 飞书API
输出: 飞书卡片消息
```

**可迁移性**: ✅ 完整
- 无外部配置依赖
- 独立运行

---

### 3. 工作日报脚本

```
路径: /root/scripts/daily_report.py
功能: 生成昨日工作日报
依赖:
  - cron/jobs.json (读取定时任务执行记录)
  - agents/main/sessions/ (读取用户交互)
  - 飞书API
输出: 
  - 飞书卡片消息
  - daily-reports/daily-report-YYYY-MM-DD.md
  - memory/YYYY-MM-DD.md
```

**可迁移性**: ✅ 完整
- 依赖本地文件路径
- 迁移需同步目录结构

---

### 4. NAS备份脚本

```
路径: /root/scripts/nas_backup.sh
功能: 备份服务器配置到NAS
备份内容:
  - sing-box配置
  - FRP配置
  - 脚本目录
  - OpenClaw工作区核心文档
  - OpenClaw完整配置
依赖:
  - WebDAV (NAS)
  - curl
输出: 
  - NAS: /aliyun_backup/server-backup/YYYYMMDD/
  - /tmp/backup-notification-YYYYMMDD.txt
```

**可迁移性**: ✅ 完整
- 配置在脚本中（WebDAV地址、账号密码）
- 需更新NAS地址和凭据

---

### 5. 每日归档脚本

```
路径: /root/.openclaw/workspace/growth/multi-agents/xiaomi/cron/daily_archive.py
功能: 归档日报到月份目录
输入: daily-reports/
输出: archive/YYYY-MM/
```

**可迁移性**: ✅ 完整

---

## 三、系统服务

| 服务 | 类型 | 状态 | 用途 | 管理命令 |
|------|:----:|:----:|------|----------|
| sing-box | Docker | 运行中 | 代理服务 | `docker restart sing-box` |
| SearXNG | Docker | 运行中 | 搜索引擎 | `docker restart searxng` |
| FRP | systemd | 运行中 | 内网穿透 | `systemctl restart frps` |
| OpenClaw Gateway | Node.js | 运行中 | 消息网关 | `openclaw gateway restart` |

---

## 四、配置文件清单

| 文件 | 路径 | 用途 | 可迁移性 |
|------|------|------|:-------:|
| 定时任务配置 | `/root/.openclaw/cron/jobs.json` | 所有定时任务 | ✅ 完整 |
| sing-box配置 | `/etc/sing-box/config.json` | 代理节点 | ✅ 完整 |
| FRP服务端配置 | `/root/frp_0.60.0_linux_amd64/frps.toml` | 内网穿透服务端 | ✅ 完整 |
| FRP客户端配置 | `/root/frp_0.60.0_linux_amd64/frpc.toml` | 内网穿透客户端 | ✅ 完整 |
| OpenClaw配置 | `/root/.openclaw/openclaw.json` | 网关配置 | ✅ 完整 |

---

## 五、数据存储位置

```
/root/.openclaw/workspace/
├── daily-reports/          # 日报文件
├── memory/                 # 每日记忆
├── archive/                # 归档数据
│   ├── 2026-03/           # 按月归档
│   ├── daily/             # 日报归档
│   └── weekly/            # 周报归档
├── agents/scheduler/       # 调度器配置
└── skills/                 # 技能目录

/tmp/
└── backup-notification-*.txt  # 备份通知

/root/scripts/              # 自动化脚本
```

---

## 六、迁移指南

### 迁移到新OpenClaw环境

1. **复制脚本**
   ```bash
   scp /root/scripts/*.py /root/scripts/*.sh new-server:/root/scripts/
   ```

2. **复制配置**
   ```bash
   scp /root/.openclaw/cron/jobs.json new-server:/root/.openclaw/cron/
   scp -r /root/.openclaw/workspace/memory new-server:/root/.openclaw/workspace/
   ```

3. **更新配置**
   - 修改脚本中的API密钥
   - 更新NAS地址和凭据
   - 重新配置邮箱

4. **测试运行**
   ```bash
   python3 /root/scripts/daily_report.py
   ```

---

## 七、待完善项

| 任务 | 状态 | 优先级 |
|------|:----:|:------:|
| 周复盘脚本 | 未实现 | P2 |
| 周报生成脚本 | 未实现 | P2 |
| 周计划脚本 | 未实现 | P2 |
| 日计划脚本 | 未实现 | P2 |

---

*报告生成完成*
