# NAS Cron 点火方案 — S10

日期：2026-11-02 · 状态：**已暂停（Boss 2026-11-02 拍板：剩余优化转 NAS 侧 hermes 会话执行）** · 前置：S1-S9 全部完成

## 一、点火机制核实结论（只读源码，0.19.0）

1. `hermes cron resume <job_id>` = resume_job()（cron/jobs.py:1450）：无条件置 `enabled=true` + `state=scheduled` + **从现在重算 next_run_at**——对 S6 重建的 disabled 任务完全适用
2. 网关 tick 每轮 `load_jobs()` 重读 jobs.json（jobs.py:1827），文件锁互斥（scheduler.py:tick 用 flock）——**运行中网关无需重启**，CLI 改完下一 tick 即生效
3. 错过窗口不补发（fast-forward 折叠，jobs.py:1809 注释）——点火晚于今晚时间点的任务，下次触发顺延至下一周期，无双跑风险

## 二、风险盘点

| 风险 | 影响 | 对策 |
|------|------|------|
| R1 Notion 键缺失（.env） | 全部 13 任务数据读写失败 | S10 A 段硬门槛探测（只查键名存在性，不打印值）；❌ 则中止点火先补键 |
| R2 scripts/ 域脚本丢失 | 早报第一步 notion_daily_fetch.py 报缺失 | prompt 已内置「缺失时如实报告勿编造」；脚本重建是 S11 独立事项 |
| R3 今晚即真实运行（今天周日） | 21:30 提醒→22:00 日反思→22:15 周复盘完整版→22:30 日安排修正连环跑 | 这正是全链压力测试；分批策略见决策点 |
| R4 gateway 只活了 1.5 天 | 若再崩任务不跑（不补发） | S10 A 段查进程 uptime；月度巡检 cron 在 ECS 侧有独立告警 |

## 三、S10 脚本三段式

- **A 探测（只读）**：`hermes cron list --all` 核对 13 任务在库且 disabled；gateway 进程+uptime；.env 键名探测 `grep -c '^NOTION_API_KEY=' .env` 等（输出 ✅/❌ 布尔）
- **B 点火（已批批次）**：对指定 job_id 逐个 `hermes cron resume`，输出每个的 next_run_at
- **C 验证**：`hermes cron list` 全绿 + gateway journal 尾部 20 行；输出回传 WebDAV
- 主机守卫 + 幂等（resume 已 enabled 的任务无害）

## 四、决策点

- **D1 点火批次**：
  - A=全点 13 个（月末/年链有 guard，实际本周触发的就 5 个）
  - **B=今晚链 5 个**（周末提醒/日反思/周复盘完整版/日安排修正/明早早报）**，周五链+月末链+年链观察今晚后点火**（推荐）
  - C=只点最低风险 2 个（周末提醒+早报）
- **D2 Notion 键缺失时的处置**（若 A 段探测到 ❌）：暂停点火，我把键名清单发你，你从 ECS .env 取值手填 NAS（值不经我手）

## 五、回滚

`hermes cron pause <job_id>` 逐个可逆；不动 jobs.json 其他字段。

## 六、后续路线（点火后）

S11 scripts 域脚本重建（notion_daily_fetch.py 等，从 ECS 任务库+知识库规格反推）→ S12 console-api 修复（缺 /app/data/cache.mjs）→ S13 vaultwarden bw session 重录 → 全案卷归档 + 备份盲区修补（Phase 3）
