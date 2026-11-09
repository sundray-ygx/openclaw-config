# OpenClaw → Hermes Agent 切换方案报告

> 日期: 2026-09-05 | 环境: 阿里云 ECS 2C/1.8G/40G | 决策人: Boss

## 一、资源评估结论

| 资源 | 现状 | 切换后预算 | 结论 |
|------|------|-----------|------|
| 内存 | 1066M/1870M 已用（含 openclaw gateway 394M + tui 252M） | 停 openclaw 释放 ~650M，hermes 预算 ~800M-1G | ✅ 串行运行可行 |
| 磁盘 | 25G/40G (67%)，余 13G | hermes 安装 ~1G（uv 隔离运行时+git checkout） | ✅ 无压力 |
| CPU | 2 核，load ≈ 0 | Python 系 agent 常驻 ~5-10% 单核 | ✅ 无压力 |

**红线：两套 gateway 不可同时常驻**（内存不够 + 飞书 websocket 事件会分流）。

## 二、现状清单（切换涉及项）

### 2.1 OpenClaw 侧
- systemd: `openclaw-gateway.service`（port 18789，MemoryMax=450M，OPENCLAW_NO_RESPAWN=1）
- 数据: `/root/.openclaw`（591M，含 workspace 180M）—— **不删除，仅停服务**
- 配置: `/root/.openclaw/openclaw.json`

### 2.2 飞书通道（hermes 复用同一通道）
- 模式: websocket 长连接
- 主应用: `cli_a93b96047e7a5bc3`（secret 在 openclaw.json channels.feishu）
- 调度应用: `cli_a93c6b1e1ff89bd4`（secret 同上 + env.FEISHU_APP_SECRET）
- 允许的用户: ou_c2edzslc01a87fc09ba756176d8606
- ⚠️ 同一 app 的 websocket 不能两个 agent 同时连（事件分流/抢占），必须先停 openclaw 再起 hermes
- ⚠️ 待安装时验证：Hermes 是否有原生飞书 channel。若无原生支持，备选：
  - 方案 i: hermes 用 webchat/local，飞书侧由轻量 webhook 转发脚本桥接
  - 方案 ii: hermes 保留 openclaw 的飞书插件包（同为 npm 生态，理论可移植，需实测）

### 2.3 定时任务接管清单
| 任务 | 现位置 | 切换后 | 动作 |
|------|--------|--------|------|
| 早间简报 08:00 | 系统 crontab → python 脚本 | 不依赖 openclaw gateway | 无需迁移，继续跑 ✅ |
| NAS 备份 02:00 | 系统 crontab → bash 脚本 | 同上 | 继续 ✅ |
| 安全巡检 周一 09:00 | 系统 crontab | 同上 | 继续 ✅ |
| 磁盘清理 周一 10:00 | 系统 crontab | 同上 | 继续 ✅ |
| acme 续期 22:06 | 系统 crontab | 同上 | 继续 ✅ |
| **GitHub 每日同步 23:30** | **OpenClaw 内部 cron（sqlite）** | 随 gateway 停止而失效 | **需迁移到 hermes cron** 🔴 |

结论：系统 crontab 5 项与 openclaw gateway 解耦，切换零影响；唯一需迁移的是 OpenClaw 内部的 GitHub 同步任务。

### 2.4 Hermes Agent 安装信息（已核实）
- 上游: github.com/NousResearch/hermes-agent（Python 系，uv 管理运行时）
- 推荐安装: `npm install --global hermes-agent`（npm bridge 0.21.0，2026-08-31 更新，运行时包内隔离，不污染 host Python）
- 依赖: Node 20+（本机 v22.23.2 ✅）、git（本机有 ✅）
- 更新: `hermes update` / 回滚: `npm uninstall -g hermes-agent`

## 三、执行步骤（方案 A，已确认 1-5 + 6 接管）

```
阶段1 备份    tar 打包 /root/.openclaw → /root/openclaw-backups/（排除 logs/cache）
阶段2 安装    npm i -g hermes-agent → hermes --version 验证 → hermes 初始化配置
              → 此时装飞书凭据、验证 channel 支持
阶段3 停 OC   systemctl stop openclaw-gateway && systemctl disable（防重启双跑）
              + 退出 tui（当前会话中断，预期行为）
阶段4 起 HG   配置 hermes gateway systemd 单元 → 启动 → 飞书连通性验证（发测试消息）
              + 迁移 GitHub 同步 cron 到 hermes
阶段5 观察    监控 24h：内存/swap/飞书响应/cron 执行（重点看明早 08:00 简报）
回滚          systemctl start openclaw-gateway 即恢复（数据未动）
```

## 四、脚本清单

- `scripts/migration-hermes/01-backup-openclaw.sh` — 备份
- `scripts/migration-hermes/02-install-hermes.sh` — 安装+验证
- `scripts/migration-hermes/03-stop-openclaw.sh` — 停 openclaw（含确认提示）
- `scripts/migration-hermes/04-start-hermes.sh` — systemd 单元+启动+验证
- `scripts/migration-hermes/05-rollback.sh` — 一键回滚
- `scripts/migration-hermes/monitor.sh` — 24h 观察期监控（内存/swap/进程）

## 五、风险与决策点

1. **飞书 channel 支持待实测**（最大不确定性）：阶段2 安装后第一时间验证，若不支持原生飞书，暂停并向 Boss 汇报选桥接方案
2. **tui 会话中断**：阶段3 后当前对话通道消失，需提前约定 hermes 侧验证方式（webchat 或 SSH）
3. **openclaw disable vs stop**：建议 disable，防止服务器重启后双 gateway 抢飞书连接
4. **回滚成本**：极低，数据未删，服务可秒级拉起
