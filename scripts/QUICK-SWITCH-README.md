# quick-switch.sh 使用说明（ECS 网关/版本快速切换）

> 入口脚本：`/root/scripts/quick-switch.sh`（任何 shell 可直接跑：SSH / hermes TUI / openclaw TUI）
> 所有切换动作自动脱离会话进程树执行（systemd-run），不会连坐当前会话。
> 完整背景见：`/root/workspace/knowledge/tech/openclaw/openclaw-gateway-cutover-hermes-downgrade-plan-20261029.md`

## 一、命令速查

| 命令 | 作用 | 生效时机 | 中断影响 |
|------|------|---------|---------|
| `quick-switch.sh status` | 查看两网关状态+版本指向（无副作用） | — | 无 |
| `quick-switch.sh 0.19` | hermes 切到 v0.19.0 | 新进程立即；**gateway 需重启、TUI 需重开** | 零中断（运行中进程不受影响） |
| `quick-switch.sh 0.22` | hermes 切回 v0.22.4 | 同上 | 零中断 |
| `quick-switch.sh openclaw` | 网关切到 openclaw（停 hermes 网关→起 openclaw→doctor→channels status） | 立即 | 飞书收发中断 2-5 分钟；**hermes TUI 会话下线** |
| `quick-switch.sh hermes` | 网关切回 hermes | 立即 | openclaw 侧飞书中断 ~1 分钟 |

日志：每个动作写 `/var/log/quick-switch-*.log`（openclaw 切换明细在 `/var/log/openclaw-cutover-20261029.log`）。

## 二、场景操作流

### 场景 1：验证 0.19.0 修 TUI 乱码（≈2 分钟，可秒回滚）
```bash
quick-switch.sh 0.19          # 切换 CLI+unit 指向
# 退出当前 hermes TUI，重新打开：
hermes --tui --continue        # 或你平时的启动方式
# → 验证乱码是否消失（这是降级的最终验收标准）
# 不满意回滚：
quick-switch.sh 0.22           # 然后重开 TUI
```

### 场景 2：gateway 也降到 0.19（场景 1 验证满意后）
```bash
quick-switch.sh 0.19           # 若还没切
# 先退出所有 hermes TUI 会话（TUI 开着 restart 会卡），然后：
systemctl restart hermes-gateway
systemctl is-active hermes-gateway   # active 即可
# ⚠️ 风险提示：0.19 读 0.22.4 写过的 config/memories 有格式回读风险，异常时：
#   quick-switch.sh 0.22 && systemctl restart hermes-gateway   # 秒回
#   极端情况恢复备份：tar xzf /root/hermes-state-backup-pre-downgrade-20261029.tgz -C /
```

### 场景 3：应急切到 openclaw 网关（hermes 网关故障时）
```bash
quick-switch.sh openclaw
# 脚本自动：停 hermes-gateway → 起 openclaw-gateway → 轮询 /health → doctor --fix
#          → channels status；health 10 分钟不就绪自动回滚 hermes
# 验收：输出里 feishu 显示 enabled/configured/running 后，
#      飞书给小群 bot 发条消息确认能回复（channels running ≠ 消息能收发）
# ⚠️ 此时 hermes TUI 会话已下线（正常现象），后续操作走 SSH 或 openclaw TUI：
#      openclaw tui --session agent:main:main
```

### 场景 4：切回 hermes 网关
```bash
quick-switch.sh hermes
# 脚本自动：停 openclaw-gateway → enable+start hermes-gateway → 轮询确认 active
# 验收：hermes TUI / 飞书发消息实测
```

## 三、随时可查状态
```bash
quick-switch.sh status
# 输出：两网关 active/enabled、CLI 指向、unit venv 路径、两个版本目录真身、18789 端口
```

## 四、注意事项（坑，勿踩）
1. **版本切换零中断**但"gateway 重启"才让网关吃新版本；TUI 重开才让界面吃新版本——切换后感觉"没变"先确认重启了没有。
2. openclaw 切换**必须用本入口**（或直接 systemd-run），不要在 hermes 会话里手敲 `systemctl stop hermes-gateway`——hermes 的护栏会拦截/连坐。
3. 切 openclaw 期间 hermes TUI 下线是**预期行为**，不是故障；`quick-switch.sh hermes` 切回后即恢复。
4. 飞书两个 bot（小群 cli_a93b96…、日程管家 cli_a93c6b…）同一时刻只能一个网关持有——切换脚本已按"先停后起"保证不抢消息。
5. `/usr/lib/node_modules/hermes-agent` 现役目录**禁止改名/软链化**（pm 按路径登记依赖，改名触发 repair 死循环，2026-10-29 实测教训）。
6. **hermes 会话内部跑 `hermes --version` 可能显示旧版**：会话 PATH 被运行时注入了 `.hermes/bin/hermes` 垫片（无条件 exec 旧 runtime）。验证真实版本用绝对路径：`/usr/bin/hermes --version`（SSH 干净 shell 不受影响）。
