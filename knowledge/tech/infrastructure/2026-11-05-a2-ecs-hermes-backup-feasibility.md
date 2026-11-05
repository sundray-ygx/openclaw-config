# A2 ECS hermes-config 备份部署 — 可行性评估报告

日期：2026-11-05 · 评估对象：README-ecs-hermes-backup.md（A2 定版）· 状态：**待 Boss 决策**

## 一、需求理解

A2 目标：ECS 增加 GitHub 私仓 `sundray-ygx/hermes-config` 的**只读全量副本**（/opt/backups/hermes-config），形成「NAS rootfs → /volume1 快照 → GitHub → ECS」四层备份。ECS 侧部署 = ①只读 deploy key ②跑 setup 脚本（克隆+cron 03:40）③验证。`nas-restore-hermes.sh` 为 NAS 全丢恢复入口（NAS 侧执行，不在本次范围）。

## 二、核实结论（全部只读实证）

| # | 核实项 | 结果 |
|---|--------|------|
| 1 | 与现有 05:00 同步任务冲突 | **无调度冲突**：现有任务在 root crontab（/root/scripts/hermes-sync/pull.sh，sparse 副本+技能传播），新任务注册 /etc/cron.d/hermes-config-pull（**该文件现不存在，无覆盖风险**）。03:40 与 05:00 错峰合理（NAS 03:00 push 后） |
| 2 | **日志文件冲突（实锤）** | 两任务同写 `/var/log/hermes-config-pull.log`——现有 pull.sh 的告警上下文会被新脚本日志交叉污染，排障时取证困难。**需修** |
| 3 | SSH 凭据现状 | ~/.ssh 无 github.com 专属路由；id_rsa（1月）支撑现有每日拉取=对私仓**有读权限（可能读写）**。README 的 deploy key 按其脚本默认地址（git@github.com 直连）**不会被使用**——直连走 id_rsa；要走新 key 必须改用 `github.com-nasrepo` 别名（README 注意事项第 1 条自己也提到了）。**需 Boss 在 GitHub 加 key 或决策复用 id_rsa** |
| 4 | 磁盘 | / 可用 8.2G；全量克隆 ≈ .git 415M + 工作树 ~600M（含 knowledge/ 555M）。充足 |
| 5 | 仓库分支 | 现有副本 HEAD=de915be（11-05 03:00 push），`pull --ff-only origin main` 与现有 pull.sh 同款假设，一致 |
| 6 | 3 天陈旧度告警 | **价值真实**：现有链路 NAS 停推只会静默「无新提交」，新脚本的 exit 2 是唯一断链探测器。**但告警只写日志无人看**（cron exit 2 无邮件/推送）。建议接飞书直推（复用 pull.sh alert_fail 模式，app cli_a93c6b1e） |
| 7 | 脚本安全性 | 两脚本无破坏性命令、无密钥明文；setup 幂等（.git 存在检测 + cron.d 条件写）；restore 仅 NAS 侧。通过 |
| 8 | state.db 不入备份 | README 已声明由 NAS btrfs 快照兜底，符合既定架构 |

## 三、增量价值判定（值不值得做）

**值得**：①knowledge/ 工作树本地化（现有 sparse 副本没有）②独立于技能传播管线的纯备份副本（pull.sh 出错不殃及）③断链探测（现有链路盲区）。成本 ≈1G 磁盘 + 40 分钟时差延迟，可控。

## 四、执行方案（批后动作）

1. **D1 key 路线**（二选一）：
   - A=README 原案：我生成新 key + 改脚本 REPO_SSH 用别名 + **你把 .pub 贴到 GitHub Deploy keys（勾只读）**，隔离最强
   - B=复用现有 id_rsa：零 GitHub 操作即刻可跑，但备份副本持读写 key 且与主管线同生共死
2. **D2 三处补丁**（建议全批）：日志分离（LOG 改 /var/log/hermes-config-pull-a2.log）｜陈旧度 🟡 接飞书直推｜cron.d 里脚本路径用绝对路径钉死（防 nas-recovery 目录清理后断链）
3. 执行顺序：补丁 → 部署 → 首跑验证（log tail + ls config/ + 03:40 次日观察）→ 报告

## 五、回滚

删 /etc/cron.d/hermes-config-pull + rm -rf /opt/backups/hermes-config 即全量回滚；不动现有 05:00 管线任何一处。
