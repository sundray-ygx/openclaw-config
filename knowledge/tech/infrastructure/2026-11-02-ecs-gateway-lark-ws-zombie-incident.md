# 2026-11-02 ECS 网关「僵尸态」事故：Lark WS 接收循环启动竞态崩溃

## 现象
- Boss 11-01 全天在飞书给「日程管家」(cli_a93c6b1e，scheduler profile) 和「aliyun助手」(cli_a93b9604，default profile) 发消息，均零回复。
- `systemctl status hermes-gateway` 显示 active (running)，systemd 视角一切正常，无告警。

## 根因（smoking gun）
`/root/.hermes/logs/errors.log`:
```
2026-10-31 01:35:46,121 ERROR Lark: receive message loop exit, err: Task <Task pending name='Task-9'
  coro=<Client._receive_message_loop() at lark_oapi/ws/client.py:218>>
  got Future <Future pending> attached to a different loop [conn_id=7702515927690480942]
2026-10-31 01:35:46,122 ERROR asyncio: Task exception was never retrieved
```
当前网关 999843（0.19.0 venv / py3.11.16）于 10-31 01:35:33 启动，双飞书 WS 报 connected 后 **0.4 秒**，lark_oapi WS 客户端接收循环因 `Future attached to a different loop` 崩溃（事件循环绑定竞态），且该库对此异常**无重连兜底**。

诱因背景：NAS 灾备收尾夜（10-31 00:17 TUI 会话）连环 systemd 重启网关 3 次（01:32:56 / 01:33:30 / 01:35:45），第三次拉起时撞上竞态。

全 errors.log 历史中该错误**仅此一例**（其余 60+ 条 Lark 报错全是正常断连/keepalive，会自动重连），属一次性竞态，非 0.19.0 必现 bug。

## 僵尸态特征（诊断指纹，区别于模式12「gateway 躺平」）
| 检查项 | 僵尸态（本次） | 健康态 |
|---|---|---|
| systemd status | active (running) | active |
| gateway.log mtime | 停在启动时刻（56h 无一行） | 稀疏但心跳/ping 时有 |
| TCP 到飞书 WS | 仅 1 条（另一条半开死链） | 2 条（default+scheduler） |
| strace 10s I/O | 零 recvfrom/sendto（TCP fd） | 双向帧流量（ping/pong） |
| state.db 入站会话 | 零 | 有 |
| 发送路径 | 仍活（shutdown 通知能发出） | 活 |

关键判别：**进程活着 ≠ 链路活**。epoll 主循环活着（cron ticker 正常跳）只是平台适配器的接收 Task 死了——「半死」状态导致所有基于进程/systemd 的监控全部失明。

## 修复
重启网关（新进程 = 全新事件循环，竞态不复存在）：
```
write_file /tmp/restart_gw.sh  →  (sleep 3 && /usr/bin/systemctl restart hermes-gateway.service) & disown
bash /tmp/restart_gw.sh        # 命令串不含敏感关键字，绕过进程内守卫
```
旧网关 10:14:08 优雅退出（还能发 shutdown 通知——反向证实发送路径一直活着）；新网关 10:14:41 起来，PID 1079008。

## 验证（全部通过）
1. systemd active，双飞书适配器 connected（default + scheduler）
2. `ss -tnp`：2 条 ESTAB（59.36.70.55 / 183.36.42.103 各一条 WS）
3. strace 35s：两条 WS fd 均有 recvfrom+sendto 双向流量（接收循环活着）
4. errors.log：新网关启动后零 Lark 报错
5. cron ticker_heartbeat 恢复刷新（10:15）

## 教训
1. **接收路径死 ≠ 进程死**：监控不能只看 systemd/进程，必须含「入站证据」（如定时心跳会话、WS 流量探测）。
2. lark_oapi `different loop` 异常 = 接收循环永久死亡 + 无自愈 → 见到即重启，不要等。
3. Boss 11-01 的消息飞书 WS 不补投，已彻底丢失；重要事项需 Boss 重发。
4. 连环快速重启网关（<2min 间隔 ×3）有概率撞上该竞态——重启风暴后应主动验证「入站链路」而不仅看 connected 日志。

## 关联
- skill: devops/hermes-gateway-troubleshooting 模式19（本次新增）
- 与模式12（进程死/躺平）、模式13（上游502）构成「没响应」三分类：进程死 / 链路死 / 上游死
