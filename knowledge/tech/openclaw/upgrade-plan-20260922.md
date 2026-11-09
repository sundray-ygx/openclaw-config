# OpenClaw 升级执行方案 — 2026.9.3 → 2026.9.5

> 版本：2026.9.3 → 2026.9.5（stable latest）
> 日期：2026-09-22
> 执行人：小助（systemd-run 自愈脚本模式）
> 前置条件：Boss 确认执行 + TUI 退出方式决策
> 停机窗口：约 5 分钟（pnpm 安装 39s + 重启 + 自动验证）
> 状态：**待 Boss 决策，未执行**

---

## 一、升级动机

- v2026.9.5：Atomic Updates（升级前自动验证新版本，失败不切换——以后升级更安全）、插件热安装不重启网关、专项 agent 团队、会话归档
- v2026.9.4：插件与 skill 发现增强、cloud-worker 控制、GPT Image 2.5
- 4179 个 PR，含大量可靠性修复

## 二、停机期间各端影响声明

| 端 | 影响 | 恢复方式 |
|----|------|----------|
| TUI（Boss 窗口） | 断连，进程保留或被 kill（见决策点3） | 网关恢复后手动 `openclaw tui --session agent:main:main` 重开 |
| WebChat | 断连 | 网关恢复后刷新页面 |
| 飞书三通道 | WS 断开，消息延迟投递 | 网关恢复自动重连（历史多次重启无丢消息） |
| 小助（本会话） | exec 死亡，会话历史保留 | 网关恢复后自动继续验收 |
| cron 定时任务 | 窗口内延迟 | 自动恢复，无损害 |

**为什么必须脚本闭环**：exec/TUI 都是网关子进程，停机即失联，无人能人工逐步操作；systemd-run transient unit 独立 cgroup，已实战验证（9-11 升级、doctor 修复、多次重启）。

## 三、执行架构

```
阶段A 预备（不停机）          阶段B 升级脚本（systemd-run，停机）         阶段C 验证（自动+人工）
├─ 备份轻量件                 ├─ stop 网关（腾 473M）                    ├─ 版本/端口/网关 active
├─ 修回滚脚本 bug             ├─ kill TUI（若决策选脚本杀）              ├─ lark 补丁存活 grep
├─ DRY_RUN 预演→Boss 过目     ├─ pnpm add -g openclaw@2026.9.5          ├─ 飞书三通道 + 0 报错
└─ Boss 下令执行              │   --dangerously-allow-all-builds        ├─ cron 9 任务健康
                              ├─ sed unit ExecStart 9.3→9.5             ├─ 模型链路实测（new-api）
                              ├─ 同步改 /usr/bin/openclaw wrapper       └─ doctor 只读
                              ├─ daemon-reload + start
                              ├─ 健康检查（端口/版本/插件）
                              └─ 任一步失败 → 自动回滚 9.3（装回+路径改回+start）
```

脚本全程日志：`/tmp/openclaw-upgrade-20260922.log`；无论成败，最后一步必拉回网关。

## 四、阶段A 预备清单（不停机）

| # | 动作 | 依据 |
|---|------|------|
| A1 | 全量备份 → `/root/.openclaw/backup-pre-upgrade-20260922_*/`：openclaw.json、agents/、plugins/、**state/openclaw.sqlite**（9-11 漏备教训）、workspace/memory、version.txt、unit 文件、wrapper、lark 补丁 3 文件 | 回滚预案 + 9-11 盲区 |
| A2 | 修 `scripts/utils/openclaw_rollback.sh`：4 处 `systemctl --user`→系统级、`npm install`→`pnpm add -g`（9-11 记录确认带病） | 回滚脚本必须先修才能当安全网 |
| A3 | 备份 lark 补丁 3 文件副本（`PATCH 2026-09-11` 标记：lark-client.js setRuntime shim、monitor.js cfg getter、getResolvedConfig） | R2 风险兜底 |
| A4 | 脚本编写 + `bash -n` + DRY_RUN 预演 → 输出给 Boss 过目 | 脚本正确性是闭环前提 |
| A5 | ★ Boss 退出 TUI（或决策点3选脚本 kill） | 腾 263M 防 OOM |

## 五、阶段B 升级脚本伪码（实际脚本 A4 产出后归档同目录）

```bash
# systemd-run --unit=claw-upgrade-0922 --collect bash upgrade-20260922.sh
set -e; shift捕获每步失败 → rollback()
1. systemctl stop openclaw-gateway; 等 18789 释放
2. kill TUI（按决策）
3. pnpm add -g openclaw@2026.9.5 --dangerously-allow-all-builds   # 9-11 实测 39s，npm 会 OOM/半态
4. sed -i 's|openclaw@2026.9.3|openclaw@2026.9.5|' /etc/systemd/system/openclaw-gateway.service
5. sed -i 同步 /usr/bin/openclaw wrapper 路径
6. systemctl daemon-reload && start
7. 验证: 端口 18789 / openclaw --version=2026.9.5 / 插件加载日志无 fail
8. 失败任一步 → rollback(): pnpm add -g openclaw@2026.9.3 + 两个路径文件 sed 改回 + start
9. 尾部: 无论成败 start + PORT 检查 + DONE 时间戳
```

## 六、阶段C 验证清单（升级后逐项）

**基础**：版本=2026.9.5、端口监听、网关 active、wrapper CLI 正常
**插件**：lark 补丁存活（`grep -c "PATCH 2026-09-11"` ≥3）、飞书三通道 running、`error handling message` 计数=0
**功能**：模型链路实测（glm-5.3 经 new-api）、cron 9 任务健康、doctor 只读无新增错误
**已知问题预案**（9-11 同款处置）：
- 启动 78/CONFIG → 日志提示的过时 key 清理
- state schema 迁移报错 → `OPENCLAW_SERVICE_REPAIR_POLICY=external doctor --fix --yes`（路径已打通）
- lark 消息处理崩 → 按新 API 迭代 shim（备份可回退）

## 七、回滚预案（自动 + 手动兜底）

**触发条件**（任一即回滚，先回滚再排查）：
🔴 网关起不来/端口不监听 🔴 飞书完全不可收发 🔴 全模型调用失败
🟡 核心异常 30 分钟内无法修复

**自动**：脚本内置 rollback()。
**手动兜底**（脚本也挂时）：
```bash
systemctl stop openclaw-gateway
pnpm add -g openclaw@2026.9.3 --dangerously-allow-all-builds
sed -i 's|openclaw@2026.9.5|openclaw@2026.9.3|g' /etc/systemd/system/openclaw-gateway.service /usr/bin/openclaw
systemctl daemon-reload && systemctl start openclaw-gateway
# 若 state schema 不兼容致旧版起不来：恢复备份 state/openclaw.sqlite 后再 start
```

## 八、风险表

| # | 风险 | 概率 | 对策 |
|---|------|------|------|
| R1 | pnpm 安装内存峰值 | 低（停网关后 avail ~1.4G，9-11 pnpm 峰值远低于 npm） | 停网关 + swap 5.7G 兜底 |
| R2 | 9.5 插件 API 变更致 lark 补丁失效 | 中 | 补丁独立于网关包不被覆盖；验证+迭代 shim；备份可回退；9-11 全套排障经验 |
| R3 | unit/wrapper 路径漏改 | 低（脚本自动化） | sed 双文件 + 验证步骤 |
| R4 | state schema 迁移单向 | 中 | A1 已备份 sqlite；doctor --fix 路径已验证 |
| R5 | 脚本自身 bug | 低 | A4 DRY_RUN 预演 + bash -n + Boss 过目 |

## 九、观察期（24h）

- [ ] 今晚 23:30 GitHub cron 正常
- [ ] 明晨 03:00 Memory Dreaming 正常
- [ ] 飞书消息收发（Boss 发条消息测试）
- [ ] 24h 无新增 ERROR、内存稳定
- [ ] 稳定后：更新 MEMORY.md 版本信息、memory 日志、清理旧版本残留（可选）

## 十、待决策点

1. 是否执行本方案
2. 执行时间（现在 / 指定时间）
3. TUI：Boss 手动退出，还是脚本 kill（脚本 kill 则升级完需手动重开 TUI）
4. DRY_RUN 预演输出是否需要 Boss 过目后再执行（推荐是）

---

## 执行记录（执行后填写）

- [ ] 阶段A 完成
- [ ] 阶段B 完成 / 回滚（原因：____）
- [ ] 阶段C 验证全过
- [ ] 观察期通过，归档收尾
