# hermes 0.22.4→0.19.0 降级后"会话记录找不到"诊断报告

> 日期：2026-10-30 11:35　诊断人：小群（ECS hermes 0.19.0 TUI）　状态：只读诊断完成，修复项待 Boss 决策
> 关联：`openclaw-gateway-cutover-hermes-downgrade-plan-20261029.md`（其 八-C-1 校验项的衍生问题）

## 一、结论（一句话）

**会话数据零丢失**——state.db 完整保有 45 个会话 / 4145+ 条消息（含昨日 395 条的切换评估大会话），0.19 对 0.22.4 写的库读写正常（本诊断会话的写入即证明）。"找不到"是**入口层标签不匹配**：0.22.4 时期 TUI 会话用新标签 `source='local'` + `local-<hash>` ID；0.19 只认 `source='tui'` + 时间戳 ID（0.19 代码里根本没有 `agent/session_source.py` 这个标签体系）。裸 `hermes -c`（继续上次会话）按 `source='tui'` 查 → 查不到 → 开了全新会话。**用 `--resume <id>` 或 `-c "标题"` 立即可恢复，不改任何东西。**

## 二、只读核实结果（全部实证）

| # | 项目 | 实测值 | 手段 |
|---|------|--------|------|
| 1 | state.db 数据量 | 45 sessions / 4145+ messages（本会话期间数字持续增长 → 0.19 写入链路正常） | sqlite 只读连接 |
| 2 | 昨日大会话 | `local-ead3f461…`（评估ECS上openclaw升级可行性，395 msgs）行完好，end_reason=tui_shutdown@10-30 11:14（切换前正常收尾，非异常终止） | 同上 |
| 3 | 0.19 读 0.22.4 的库 | 库 schema_version=32（0.22.4 写），0.19 代码 SCHEMA_VERSION=22。0.19 不回滚不报错——迁移逻辑只在 `当前<22` 时动作，读写按列名进行（32 版多出的 6 列被忽略）。实测列表查询返回全部 40 条 | 0.19 venv 真跑 `list_sessions_rich` |
| 4 | CLI 列表 | `hermes sessions list`（0.19）完整列出所有会话，含昨日大会话 | 实跑 |
| 5 | TUI 会话面板数据源 | 前端 = `session.active_list`（网关进程内活会话，重启后只剩当前）+ `session.list`（DB 历史，deny-list 仅排除 'tool'，**无 source 过滤**）→ 面板历史区应能看到全部 | entry.js 反查 + tui_gateway/server.py 源码 |
| 6 | 裸 `hermes -c` 失效根因 | `main.py` 2434：`_resolve_last_session(source='tui')` → `search_sessions` SQL `WHERE source='tui'` 精确等值 → 0.22.4 的 `source='local'` 行全部不命中 → "No previous TUI session found" → 开新会话（今天 11:16 的 "Hello and Work Task Assistance" 即此来路）。现有回退链只兜 `tui→cli`，不含 `local` | main.py + hermes_state.py 源码 |
| 7 | 会话内 `/sessions` | 按调用方 platform scope 过滤 `source='local'` → 恰好显示 0.22.4 时期的 12 个 local 会话（含昨日大会话），可 `/resume <序号>`；但会隐藏 source='tui' 的会话（含今天新会话） | slash_commands.py 3987-4030 |
| 8 | 路由索引"剪除"真相 | 今早 11:15:45 0.19 网关启动时，把 sessions.json **文件镜像**里 12 条 end_reason 非空的条目剪掉（日志措辞 "left by a crashed gateway" 吓人，实为对"已结束会话"的正常清理设计）。**gateway_routing 表（scope=''）18 条完好**——那是 0.22.4 的主存储，sessions.json 在 0.22.4 里只是镜像。被剪条目均指向已结束会话 + TUI peer hash 每次启动都换 → 剪除无实际影响 | journal + 表/文件逐条 diff |
| 9 | 0.22.4 关停状态 | 干净 SIGTERM，"Previous gateway exited cleanly — skipping session suspension"；并非崩溃 | gateway.log |
| 10 | 标签体系差异 | `agent/session_source.py`（local 标签定义处）0.22.4 有、0.19 无——版本间 source 语义断层的代码级证据 | 双目录 find |

## 三、根因链

```
10-29 定版机制：0.22.4 ↔ 0.19.0 软链切换，共享同一 /root/.hermes（含 state.db）
    ↓
0.22.4 运行期：TUI 会话改用新标签 source='local' + local-<hash> ID 体系
    ↓
10-30 11:15 切到 0.19.0：0.19 只认 source='tui' + 时间戳 ID（无 local 概念）
    ↓
Boss 重开 TUI 期望续昨日会话 → 裸 -c 按 source='tui' 查 → 落空 → 起全新会话
    ↓
体感 = "之前的 session 会话记录找不到了"（实际全部在库）
```

## 四、修复选项（决策点）

**A. 零变更，立即可用（建议先验证）**
- 续昨日会话：`hermes --resume local-ead3f46114436692cf2c4caba44f292799ce7f6f5bdffb7290c5025aa070ff48`
- 或按标题：`hermes -c "评估ECS上openclaw升级可行性"`（标题解析走 `resolve_session_by_title`，无 source 过滤）
- 或当前 TUI 内：会话面板历史区 / `/sessions` → `/resume <序号>`
- 验证：resume 后由我复核该会话 message_count 增长即闭环。

**B. 修裸 `hermes -c` 的跨版本语义（改 0.19 venv 源码，小补丁）**
- 位置：`hermes_cli/main.py` ~2434。现状只查单一 source（tui 查空仅回退 cli）。
- 改法：bare `-c` 改为在 {tui, local, cli} 各取最近一条、按 last_active 取最新（`search_sessions` 本就返回 last_active 富化列，~10 行）。仅影响裸 `-c`，`-c "标题"` 与 `--resume` 路径不动。
- 风险：改的是 0.19 独立 venv 的包文件；该 venv 不归 pm 管、不会被自动升级，但若日后重建 venv 需重打。先 cp .bak，可秒回滚。
- 注意：今天 11:16 已产生新的 source='tui' 会话，**不打补丁的话裸 -c 今后只会续到 0.19 自己的会话**，跨版本边界仍要靠 A。

**C. 回填 sessions.json 被剪的 12 条（不推荐，建议不动）**
- 数据在 gateway_routing 表可回填，但条目指向已结束会话、TUI peer hash 每次启动都换 → 无实际收益纯扰动；0.22.4 切回时自会从表读。

**D. 防再发（随本报告自动完成）**
- 本报告归档 + 教训同步 agent-gateway-cutover skill + hermes 记忆。
- 边界提醒：0.19 在 32 版库上读写已实证兼容，但**勿对共享 state.db 跑 0.19 的 `hermes sessions prune/optimize/repair`**（按 22 版逻辑动 32 版库，无必要风险）。

## 五、影响面

| 对象 | 影响 |
|------|------|
| 数据 | 零丢失（messages 计数持续增长证明写入正常） |
| 飞书通道/日程管家 | 零影响（feishu 路由 oc_cc41… 未被剪，网关 11:15 起正常） |
| 0.22.4 回切能力 | 完好（gateway_routing 表 18 条全在 + 现役目录未动） |
| 待 Boss 目验 | TUI 会话面板历史区是否正常**显示**（数据源已验证返回全部；渲染层乱码是降级动机本身，需目测确认 0.19 下是否好转） |
