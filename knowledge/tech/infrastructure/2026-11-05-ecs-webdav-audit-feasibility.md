# ECS WebDAV(5005/5006) 依赖审计 — 脚本可行性评估

日期：2026-11-05 · 对象：Boss 提供的 `ecs-webdav-audit.sh`（1139B/17行，已拉取）· 状态：**待 Boss 决策**

## 一、需求理解

背景：WebDAV 通道是 ECS↔NAS 的备用投递通道（NAS 阿里云盘 WebDAV 经 frp 5005/5006 隧道到 ECS 本地回环）。NAS 侧欲评估停用/回收该通道（清理 frp 端口、评估依赖面），需先在 ECS 侧摸清：谁在用 5005/5006——进程连接、cron/脚本引用、挂载点。

## 二、脚本判读（五段全只读）

①`ss -tnp` 连接扫描 ②`ss -tlnp` 监听扫描 ③frps 进程+配置（token 行已滤）④阿里云盘客户端进程 ⑤近30天 .log grep。**无写操作、无密钥泄露面**——安全性通过。

## 三、只读核实结论（已在 ECS 实测）

| # | 脚本段 | 覆盖度 | 缺口 |
|---|--------|--------|------|
| 1 | ss 连接/监听 | ✅ 实测：**5005+5006 均由 frps 监听**（pid 2343043，Jun11 起），当前**零活动连接** | — |
| 2 | frps 配置 | ⚠️ 候选路径不含本机真实路径 `/root/frp_0.60.0_linux_amd64/frps.toml`——脚本会静默漏报 | 需补路径 |
| 3 | 阿里云盘客户端 | ✅ | — |
| 4 | 日志 grep | ⚠️ 只扫 `~ /var/log` 的 `.log` 文件；而**真正的依赖大头是脚本与凭据文件**：`/root/.backup-creds.env`（396B，WebDAV 用户名/密码）+ 6 个引用 5005 的脚本（nas_backup.sh、newapi-cutover-ecs/nas.sh、nas-recovery 域全套）+ openclaw skill `nas-disaster-recovery`（webdav-relay-watch.sh） | cron/脚本引用段缺失（Boss 检测目标里的重点） |
| 5 | 挂载点 | ❌ **无此段**——需 `/proc/mounts` 查 davfs（实测当前无 davfs 挂载，但审计应记录在案） | 需补段 |

另注：crontab 无直接 5005 引用（凭据经 `.backup-creds.env` 间接引入），但 nas_backup.sh 由 root crontab 02:00 每日跑——**是隐性依赖链**（cron→脚本→creds→5005）。

## 四、执行方案

**方案 R（推荐）**：跑 Boss 原脚本（尊重原案取证格式）+ 我补三段增强（frps 真实路径、cron/脚本/凭据引用清单、/proc/mounts davfs 检查），输出合并成一份完整审计报告回传 NAS。

**方案 N**：仅跑原脚本——结果会漏掉最关键的脚本引用面与挂载点段，审计结论不完整。

## 五、决策点

- **D1**：R（原脚本+补三段，推荐）/ N（仅原脚本）

## 六、回滚

纯只读审计，零变更，无回滚需求。
