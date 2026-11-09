# Agent-Reach × 现有 Cron 任务增强评估报告

日期：2026-10-28 · 状态：Boss 已批准 D1-D5，当日执行完毕（P0 GitHub 走 Reach / P1 摘要兜底 / P2 B站板块 / 附带修复海外源 socks5→socks5-hostname DNS 污染问题），干跑+单测冒烟全部通过 · 性质：只读评估，未做任何变更

## 一、需求理解

给"拉取外部信息"的定时任务补上 agent-reach 的渠道能力，提升：
- **完整度**：覆盖原本够不着的来源（登录墙、视频、中文社区）
- **准确度**：拿到结构化正文/评论，而非搜索摘要

评估标准沿用 agent-reach skill 自身选路原则——**自带工具优先，Reach 补缺口**，不为用而用。

## 二、盘点结果（只读核实）

ECS 侧 cron 共 13 条，其中信息拉取类只有早报一条主线；其余 12 条为运维类（备份/安全巡检/磁盘清理/acme/失败探测/心跳/性能哨兵/同步），不拉外部内容，不适用本次增强。

- Hermes 侧 cron 任务：0 条（本 profile）
- openclaw scheduler 任务库读取被审批拦截未完成（不影响主结论）

**早报主线（morning_briefing.py，每日 08:00）现有数据源：**

1. RSS × 7~9 个源（量子位、36氪、钛媒体、人人都是产品经理、BBC中文、大纪元、阿波罗网；v2 版另有虎嗅、少数派）
   - 痛点：RSS 只给摘要；部分源在国内直连不稳或已死（BBC中文/大纪元/阿波罗网需代理，脚本里有 use_proxy 开关佐证）
2. GitHub API 直连 curl（openclaw issues / releases / hermes+AI agent 仓库搜索）
   - 痛点：无鉴权有速率限制（60次/小时）；拿的是列表不是讨论正文
3. 163 邮箱拉取（IMAP）
4. 飞书推送（只推不拉）

**其余脚本（未挂 cron 但属同族）：** ai_agent_news.py / news_summary_v2.py / rss_news_fetch.py，数据源与早报高度重叠。

## 三、Agent-Reach 能补什么（逐渠道对照）

| 渠道 | 对早报的价值 | 状态 | 成本 |
|---|---|---|---|
| github | 替换裸 curl：读 issue/PR 全部评论正文、README，结构化 JSON | ✅ 已装已验证 | 零（无登录） |
| web (read) | RSS 死链/摘要不全时按链接取正文（Jina 后端走代理可用） | ✅ 已装 | 零 |
| youtube | AI 领域视频资讯（字幕即正文）——早报当前完全无视频维度 | ✅ 已装 | 零（字幕免登录） |
| bilibili | 中文 AI 社区内容（搜索/视频信息）——36氪等 RSS 覆盖不到的社区视角 | ✅ 已装已验证 | 零 |
| v2ex | 技术社区热帖（走 1080 代理实测可用） | ✅ 已装已验证 | 零 |
| xueqiu | 财经/个股行情快照（行情免登录） | 可选未加 | 一条 add 命令 |
| twitter/reddit/xiaohongshu | 海外 AI 圈动态/社区讨论 | 可选/实验 | 需登录，本机无头不建议 |

## 四、增强方案（按优先级）

### P0 — GitHub 维度升级（收益最高、零成本、零风险）
morning_briefing.py 里 5 处裸 `curl api.github.com` 换成 `agent-reach github ...`：
- 收益：issue/PR 含完整评论正文（现在只有标题列表）；输出统一 JSON 解析更稳；内置错误码处理（RATE_LIMITED 不再产生静默空段落）
- 改动面：纯函数级替换，飞书推送结构不变

### P1 — RSS 失败兜底（提升准确度）
fetch_rss 失败或正文过短（<200 字）的条目，fallback 调 `agent-reach read <链接>` 补正文：
- 收益：死链/摘要源不再直接丢条目；境外 RSS 源（BBC中文等）走 1080 代理通道
- 前提：脚本内引入 socks 代理 env（早报脚本已有 use_proxy 机制，可直接复用）

### P2 — 新增社区/视频维度（提升完整度）
早报新增两个板块，各取 3~5 条：
- B站 AI 热门（bilibili search "大模型/AI Agent"，取标题+简介+链接）
- V2EX 热帖（v2ex hot，技术圈动态；走代理）
- 可选：YouTube 字幕维度（AI 发布会/教程，量少质高）

### P3 — 暂不建议
- twitter/reddit/xiaohongshu 渠道：需登录态，无头服务器维护成本高，收益不确定
- 雪球行情：早报没有财经板块定位，加了也没人看；除非你想要

## 五、风险与前置条件

1. **代理依赖**：v2ex/BBC/部分 web read 走 1080 代理。sing-box 已 `--restart unless-stopped`，但订阅失效会级联影响早报 → 方案：脚本对 Reach 失败做静默降级（跳过该板块，不影响其余推送）
2. **代理 env 注入**：agent-reach 命令需 `ALL_PROXY=socks5h://127.0.0.1:1080` 前缀（github/bilibili 不需要，加了也无害——mixed 入站国内直连域名走 direct 规则）
3. **执行时长**：Reach 每命令 2~10s，新增 2 板块 + 兜底预计增加 1~2 分钟，早报 08:00 无竞争任务，可接受
4. **回滚**：所有改动 git 级可回退（脚本在 /root/scripts/，有 .bak 惯例）

## 六、决策点（请逐项拍板）

- [ ] D1：是否执行 P0（GitHub 维度升级）？建议：是
- [ ] D2：是否执行 P1（RSS 失败兜底）？建议：是
- [ ] D3：是否执行 P2（B站/V2EX 新板块）？建议：先加 B站，V2EX 你定
- [ ] D4：P3 雪球/需登录渠道是否要？建议：暂不
- [ ] D5：改完是否立即手动触发一次早报做冒烟验证？建议：是

完整报告文件：/root/.openclaw/workspace/knowledge/inbox/agent-reach-cron-enhancement-eval.md
