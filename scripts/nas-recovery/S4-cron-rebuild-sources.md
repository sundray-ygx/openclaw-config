# S4 — NAS Hermes cron 任务重建素材清单

> 2026-10-31 由 ECS 侧从幸存 git 仓库（10-30 03:00 快照，与 NAS 丢失前同源）反推
> 用途：S3 完成后在 NAS 上重建 hermes cronjob。每条含定义来源，重建后逐条与 Boss 确认语义。

## 1. 任务清单（按 daily-cron-architecture.md 2026-05-31 定版 + memory 日志补正）

| # | 任务名 | 调度 | deliver | 语义 | 定义来源 |
|---|--------|------|---------|------|----------|
| 1 | morning-briefing | 08:00 daily | feishu | 今日计划+系统+会话回顾（6 板块，无任务看板） | daily-cron-architecture.md |
| 2 | daily-reflection | 23:45 daily | feishu | 昨日复盘生成+写入 Notion | daily-cron-architecture.md |
| 3 | weekly-review | 周五 18:30 | feishu | 周复盘（GRAI 框架） | synology-nas SKILL + crontab 注释 |
| 4 | weekly-reminder | 周五 17:00 | feishu | 周提醒 | crontab 注释 |
| 5 | 知识库自动归档 | 01:00 daily | local | inbox/ ≤3d 自动归档（脚本 utils/knowledge_auto_archive.py，注意 workdir 陷阱） | SKILL pitfall #66 |
| 6 | periodic-planning 系列 | 多个 | feishu | 周计划/月计划草稿+推卡（10 月新增，含阶段B日安排滚动） | memory/2026-10-29.md |
| 7 | daily-report | ~~08:30~~ | — | **已删除**（2026-05-31 与简报重叠），勿重建 | daily-cron-architecture.md |

## 2. 重建时必守的坑（全部来自 SKILL pitfalls）

1. **workdir 必须显式设 `/root/.hermes`**——null 会写到 /volume1/homes/ygx/（pitfall #30）
2. **deliver=local 是静默的**——要推飞书必须 `feishu:<chat_id>`（pitfall #20）
3. **prompt 引用脚本路径必须与实际一致**：`scripts/daily/notion_daily_fetch.py`（非 scripts/notion/...）（pitfall #62）
4. **enabled_toolsets 必须覆盖 prompt 引用的工具**（session_search 常漏）（pitfall #66）
5. **cronjob 先 list 查重再建**（pitfall #24）

## 3. 系统级 cron 修复项（/etc/crontab + cron.d，幸存但引用断链）

| 条目 | 状态 | 修复动作 |
|------|------|----------|
| `0 */6 * * * /root/.hermes/scripts/utils/ransomware_snapshot.sh both` | 脚本本体已丢 | S2 恢复 skills 后从 git 历史找；找不到则暂时注释（防每 6h 空跑） |
| `/etc/cron.d/sync-aliyun-backup` → `/root/.hermes/scripts/backup/sync-aliyun-backup.sh` | 脚本本体已丢 | 同上；恢复后先跑一次校验（注意 pitfall #76 恢复已删文件的坑） |
| `/etc/cron.d/hermes-config-backup` → `/volume1/hermes-config/scripts/push-config.sh` | ✅ 源在 volume1 | 无需修，03:00 自动恢复推送链 |
| `/etc/crontab` sync-frpc-ssh-port / tmp-cleanup | 脚本在 /root/scripts（已丢） | 低优先，按需重建 |

## 4. Notion 数据库 ID 速查（重建 prompt 用）

- 任务 cbe3188c（title=任务, status=状态）/ 待办 5c0f7915（title=待办事项）
- 日复盘 2bd7772a（title 字段是 rich_text「日」）/ 周复盘 345f5210（同）
- status 过滤不支持 and 多 does_not_equal（400），用单条 does_not_equal:"Done"
