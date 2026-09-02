# OpenClaw 升级方案：2026.7.1-2 → 2026.8.1（OpenClaw 2.0）

> **版本**: 1.0
> **日期**: 2026-09-01
> **状态**: ⏳ 待决策（未执行）
> **依据**: `openclaw-upgrade-guide.md`（v1.0，含 2026-03-11 OOM 历史教训）+ 官方 2026.8.1 release notes + 环境实测

---

## 一、环境预检（对照升级指导文档清单）

| 检查项 | 文档要求 | 当前实测 | 状态 |
|--------|---------|---------|------|
| 物理内存 | ≥2GB（低于极易 OOM） | 1.8G，可用约 742M | ⚠️ 不达标 → 必须走内存受限流程 |
| Swap | ≥2GB（推荐 4GB） | 6.0G（swapfile2 4G + swapfile3 2G） | ✅ |
| 磁盘 | ≥1GB 空闲 | 14G 空闲（65%） | ✅ |
| Node.js | ≥18（推荐 20 LTS） | v22.23.2 | ✅（8.1 要求 Node 22） |
| Gateway 服务 | 正常 | 运行中（systemd user） | ✅ |
| 上次备份 | 保留 | /root/openclaw-backups/（8-13，242M×2） | ✅ 本次需新备份 |

**结论**：内存是唯一短板。2026-03-11 曾因 1.8G 内存 OOM 升级失败 3 次，本次沿用"停服务 + 限 Node 内存"组合方案（Swap 6G 已满足）。

---

## 二、升级风险清单

| # | 风险 | 等级 | 应对 |
|---|------|------|------|
| 1 | 会话存储迁移 SQLite（不可逆） | 🔴 高 | 升级前完整备份；回滚需用 8.1 CLI 导出归档 |
| 2 | 内存不足 OOM | 🔴 高 | 停 Gateway + TUI 释放 ~600M；`NODE_OPTIONS=--max-old-space-size=1024` |
| 3 | 飞书插件兼容性（openclaw-lark 2026.7.16 < 8.1） | 🟡 中 | 升级后测试飞书收发；失效则更新插件或装官方 `@openclaw/feishu` |
| 4 | Provider 包独立化（zai/volcengine） | 🟡 中 | 升级后 `openclaw doctor --fix` 补齐缺失包 |
| 5 | 插件 SDK deprecation（2026-09-01 生效） | 🟡 中 | 仅警告不阻断；openclaw-lark 报错则同步升级 |
| 6 | Gateway 重启中断当前会话 | 🟢 低 | 已知现象（SIGTERM 正常，systemd 自动拉起） |

**业务影响评估**：早间简报、NAS 备份、安全巡检、磁盘清理均为 crontab 独立脚本，不受影响；受影响仅 GitHub 同步（23:30）与 Memory Dreaming（03:00）两个 OpenClaw cron，避开该窗口即可。

---

## 三、升级流程（内存受限组合方案）

### 阶段 0：备份
```bash
tar -czf /root/openclaw-backups/openclaw-20260901_$(date +%H%M%S).tar.gz -C /root .openclaw
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup.20260901
# 校验 tar 完整性（官方要求 verified backup）
```

### 阶段 1：释放内存（关键）
```bash
systemctl --user stop openclaw-gateway
# 确认 inactive (dead)，释放约 600M
```

### 阶段 2：清缓存 + 升级
```bash
npm cache clean --force
NODE_OPTIONS="--max-old-space-size=1024" npm install -g openclaw@latest
```

### 阶段 3：启动 + 修复
```bash
systemctl --user start openclaw-gateway
sleep 5
openclaw doctor --fix
openclaw plugins list
```

### 阶段 4：功能验证
| 验证项 | 方法 |
|--------|------|
| 版本 | `openclaw --version` = 2026.8.1 |
| 会话完整 | 历史会话可读（SQLite 迁移成功） |
| 飞书收发 | 发测试消息，确认机器人回复 |
| GitHub 同步 cron | `openclaw cron list` 任务在、投递目标未变 |
| Memory Dreaming | 03:00 定时任务存在 |
| 模型调用 | 跑一次 GLM 对话验证 zai provider |
| 磁盘/内存 | 无异常增长 |

### 阶段 5：收尾
- 重启 TUI
- 写日志 `memory/2026-09-01.md`
- 同步更新本目录相关文档

---

## 四、执行方式（TUI 不可用时的替代）

⚠️ **关键约束**：Gateway 停止后，本 agent（运行于 Gateway 内）与 TUI 均不可用，无法继续执行命令。

**方案：预写一键脚本 + 终端手动执行**

1. 升级脚本预置：`/root/openclaw-backups/upgrade-openclaw-20260901.sh`（含备份→停服→清缓存→升级→启动→doctor）
2. 终端手动执行：
   ```bash
   bash /root/openclaw-backups/upgrade-openclaw-20260901.sh
   ```
3. 脚本完成、Gateway 重启后，TUI 自动重连，agent 恢复，再执行验证清单

**备选**：不预写脚本，用户在终端按阶段逐条执行（可控性更强，但步骤多）。

---

## 五、回滚预案

| 场景 | 操作 |
|------|------|
| 升级失败/Gateway 起不来 | 恢复备份 tar → 重启服务（5 分钟，可逆） |
| 飞书插件失效 | 更新 `@larksuite/openclaw-lark`；或装官方 `@openclaw/feishu` |
| 降回 7.1.2（⚠️ 不可逆） | SQLite 迁移后旧版无法读新会话；降级前须用 8.1 CLI 导出归档。**除非灾难性故障，否则不降级，优先修复** |

---

## 六、执行计划

- 窗口：避开 08:00 简报 / 23:30 GitHub 同步 / 03:00 Dreaming
- 预计中断：Gateway 停机 5-10 分钟
- 总耗时：约 20-30 分钟

---

## 七、决策点

- [ ] A. 立即执行
- [ ] B. 指定时间执行
- [ ] C. 调整方案
