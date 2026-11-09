# ECS WebDAV(5005/5006) 依赖审计报告 — 完整版（原脚本 + 补三段增强）

执行：2026-11-05 · 模式：方案 R（Boss 批复）· 性质：纯只读审计，零变更

## 一、实时状态（原脚本段 1/2）

- **活动连接**：ECS 上**无任何进程**连 5005/5006（ss -tnp 空）
- **本地监听**：5005 与 5006 均由 **frps**（pid 2343043，Jun 11 起）监听——frp 隧道服务端在 ECS，端口空闲等 NAS 侧 frpc 连入
- **阿里云盘客户端**：无 aDrive 等同步进程（仅有 aliyun-assist/aegis 系统组件，与阿里云盘无关）

## 二、frps 配置（增强段 6，真实路径 /root/frp_0.60.0_linux_amd64/frps.toml）

- bindPort=7000 / vhostHTTPPort=8080 / 管理台 7500（admin/qwer1234，弱口令，建议顺带整改）
- **frps.toml 里没有 5005/5006 的 proxy 定义**——这两个端口是 NAS 侧 frpc 配置的 remotePort（ECS 只被动监听），符合「隧道服务端」角色

## 三、挂载点（增强段 7）

/proc/mounts **无 davfs/webdav 挂载**——WebDAV 访问全部走 curl/脚本层，无文件系统级依赖。

## 四、脚本引用面（增强段 8，核心发现）

**长期运行依赖（cron 驱动，每日 02:00）**：
- `nas_backup.sh`（root crontab）→ 硬编码 `WEBDAV_URL=http://127.0.0.1:5005` + source `/root/.backup-creds.env`（WebDAV 凭据，600 权限）→ **这是 5005 的唯一常态消费者**
- nas-backup.log 为空 → 该任务近期可能未成功执行（或日志轮转清了），建议 NAS 侧核对备份产物

**一次性/应急工具（无调度）**：
- `newapi-cutover-ecs.sh` / `newapi-cutover-nas.sh`（网关切换应急包，含 20261023 旧版快照）——按需手动跑，不算常态依赖

**恢复域物料（历史归档）**：nas-recovery/ 目录 6+ 文件（本次审计脚本自身 + 此前 S1-S9 恢复物料）——历史证据链，建议保留但可归档

**配置层**：hermes/gateway config 无 5005/5006 引用；无 systemd 单元引用

## 五、审计结论

| 维度 | 结论 |
|------|------|
| 进程连接 | 零活动连接（5005/5006 纯监听等入） |
| cron/脚本引用 | **1 个常态依赖**：nas_backup.sh（02:00 daily）经 .backup-creds.env 用 5005 |
| 挂载点 | 无 davfs，无文件系统级依赖 |
| 应急工具 | newapi-cutover 两个脚本按需手动 |
| 停用影响评估 | 若停 5005：**只伤 nas_backup.sh 每日备份**；5006 无任何消费者，可停 |

## 六、建议（供 NAS 侧决策参考，ECS 侧无需动作）

1. nas_backup.sh 是 5005 唯一常态消费者——停用前先确认 NAS 备份链路替代方案
2. nas-backup.log 为空值得排查（备份是否真的在跑）
3. frps 管理台 7500 弱口令（admin/qwer1234）顺带整改
4. 5006 零消费者，可随 NAS 侧决策直接回收
