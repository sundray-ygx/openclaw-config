# ECS 备份机制审计 · 可行性评估与优化建议（2026-11-10）

> 依据：NAS 下发任务文档 nas-audit-ecs-task-20261110.md（sha256 8eefa205…）
> 阶段：只读核实已完成 → 本报告 = 评估 + 决策点，**未执行任何变更**
> 后续：Boss 批准后执行采集 → 结果回写 WebDAV `nas-audit-ecs-result-20261110.md`

## 一、文档声称 vs 实测核对

| # | 文档声称 | 实测结果 | 判定 |
|---|---------|---------|------|
| 1 | 每日 02:00 v5.0 脚本打 tar 上传 WebDAV | crontab `0 2 * * * nas_backup.sh` ✓；今晨 02:00:01 启动、02:01:50 上传成功（HTTP 201）、远程验证 200、41,952,191 bytes | ✅ 一致 |
| 2 | backup-info.json 自证 v5.0 | 脚本第 302-312 行生成，backup_version="5.0" | ✅ 一致 |
| 3 | server-backup/ 下 20261026 起连续每日目录 | PROPFIND 实测：20261026~20261110 共 16 个目录无断档 | ✅ 一致 |
| 4 | 3 个历史散目录 20260322/20260509/20260512「若是手动残留请确认」 | **非手动残留**——是清理代码 bug 的假删除产物（见二.1） | ⚠️ 修正结论 |
| 5 | A2 链已部署（2026-11-05 指引） | /etc/cron.d/hermes-config-pull 在跑，今晨 03:40 拉取成功，副本新鲜度 OK（最新提交 0 天前） | ✅ 一致 |

补充核实：
- nas-backup.log 今日 03:48 清零 = logrotate（daily/rotate14/delaycompress/copytruncate）正常轮转，昨晨日志完整存于 nas-backup.log-20261110（1747B）及历史 .gz。**非异常**。
- ECS 无 frpc 进程；5005 端口 = ECS frps（PID 2343043，自 6 月稳定运行）承载的 NAS webdav 代理回环。frps API 实测 14 条 NAS 代理全部 online。

## 二、审计新发现（任务文档未覆盖）

### 1. 🔴 高：保留策略「假删除」bug（与 NAS 今晨修复的同步链同族）
- **证据**：今晨日志 `02:01:51 删除过期备份: 20260322 / 20260509 / 20260512 / 20261025` → `清理完成: 删除 4 个`，但 PROPFIND 实测三散目录至今存在。11-09 及更早日志同样天天喊删。
- **根因**：nas_backup.sh 第 402 行 `grep -oP "(?<=<href>)[^<]+"` —— DSM WebDAV 返回 `<D:href>`（命名空间前缀），lookbehind 匹配不到 → `files` 恒空 → 跳过文件级 DELETE → 直接 DELETE 非空目录被 DSM 拒（405）→ 目录留存。curl `-s -o /dev/null` 吞掉状态码，`deleted_count` 只数循环次数，日志假绿。
- **矛盾点待实测收口**：每日目录（如 20261024/20261025）同代码路径却删掉了（NAS 观察与本轮 PROPFIND 均证实不在）——单文件目录 vs 多子项目录的 DELETE 行为差异，执行阶段用只读手段收口（PROPFIND `#recycle/` 回收站 + 11-05~11-08 历史 .gz 日志交叉）。skill 已记载 DSM PROPFIND 解析必须用 `(?<=href>)`，此处是同一坑的第二现场。
- **影响**：目前危害=NAS 空间慢性泄漏（散目录 ~百MB 级，暂可控）；**修复后需注意**：滚动清理一旦修好，>15 天备份将真正消失（设计行为，需 Boss 知悉）。

### 2. 🟡 高：default profile state.db（55M）不在任何备份项
- v5.0 第 9 项只备 `.hermes` 的 config.yaml/auth.json/.env/cron/skills；第 10 项只备 **scheduler** profile（含其 state.db）。
- `/root/.hermes/state.db`（default=aliyun助手 主力对话 profile 的全部会话历史，55M）**零备份**——ECS 整机丢失即全灭。修法现成：第 10 项同款 `sqlite3 .backup` 模式加一个源即可。

### 3. 🟡 中：恢复物料缺口（任务第 4 项的预答案）
无恢复文档/脚本。缺：镜像清单（docker images 无导出；new-api 有 container-meta.json，sing-box 无）、docker run/compose 参数记录、node/hermes 运行时（.nvm、.hermes/tools 1.6G、installs 478M、/usr/lib/node_modules/hermes-agent 4.1G 均不在备份——可重装但版本钉死 0.22.4 有 npm 壳覆盖风险）、acme 证书（.acme.sh）、/root/.ssh（id_rsa=GitHub 拉取凭据，丢失则 A2 链断）、/etc/cron.d/hermes-config-pull（crontab -l 不含 cron.d）、frps/bill-import/notion-bill-import/openclaw-gateway-daily-restart 四个 systemd unit（只备了 2 个）、/etc/nginx/nginx.conf 主文件、/etc/docker/daemon.json、/root/.backup-creds.env（WebDAV 凭据自身不在备份——恢复时需从 NAS 本地取，非死锁但需记录）。

### 4. 🟢 低：workspace GitHub 链 11-07 起无新提交
`/root/.openclaw/workspace`（remote=sundray-ygx/openclaw-config）最新提交 9002a0f=11-06 23:30 auto-sync，11-07/08/09 无提交。23:30 github-sync-cron.sh 在 crontab 中，待查 /var/log/github-sync.log 判定是「三天无变更」还是「链断了」——执行阶段补证。

### 5. 备份体系真实风险面（任务第 6 项的预答案）
WebDAV 链路：ECS nas_backup.sh → 127.0.0.1:5005（ECS frps 代理）→ NAS frpc → NAS WebDAV（存储于 NAS /volume1/aliyun_backup）。**每日 tar 只存 NAS 单地**；异地副本仅 GitHub（覆盖 workspace 文本 + hermes-config，不含 state.db/one-api.db 数据库类）。NAS 整机灾难时：tar 全灭 + GitHub 剩文本资产，数据库类资产最多回退到「最后手工备份」。frps 自身：frps.toml+二进制已备（02-frp 项），frps.service unit 未备。

## 三、7 项任务可行性评估

| # | 任务 | 可行性 | 证据就绪度 |
|---|------|--------|-----------|
| 1 | 备份脚本与调度 | ✅ 纯只读 | 100%（crontab/cron.d/脚本全文已读） |
| 2 | tar 范围核对+缺口清单 | ✅ 纯只读 | 100%（INCLUDE 12 项/EXCLUDE 已提取，缺口清单见二.3） |
| 3 | ECS→GitHub 三链 | ✅ 纯只读 | 90%（差 github-sync.log 尾部，执行补） |
| 4 | 恢复演练可行性 | ✅ 纯只读 | 100%（结论=部分可恢复，缺口如上） |
| 5 | 关键数据盘点 | ✅ 纯只读 | 100%（docker ps/du 已采） |
| 6 | WebDAV 部署与单点 | ✅ 纯只读 | 95%（frps 代理表已取，NAS 侧 WebDAV 服务本身由 NAS 审计覆盖） |
| 7 | 保留策略核对 | ✅ 纯只读 | 95%（假删除已实锤，根因细节待 #recycle 探测） |

**总评：全部 7 项可执行，零破坏性（全程 cat/ls/du/PROPFIND/HEAD/log 读取），无决策风险。**

## 四、优化建议（供决策）

- **O1（高）修假删除 bug**：nas_backup.sh L402 `(?<=<href>)` → `(?<=href>)`；DELETE 后校验 HTTP 码、失败如实计数入日志。修好后 3 个散目录次日自动清掉。⚠️ 副作用：>15 天备份此后会真删（设计行为）。
- **O2（高）备份范围 v5.1**：①default profile state.db（sqlite3 .backup 模式）②/etc/cron.d/ 快照 ③frps 等 4 个 systemd unit 补进 11-systemd ④/etc/nginx/nginx.conf ⑤.acme.sh ⑥.docker/daemon.json。.ssh/.backup-creds.env 是否入包（密钥入 tar 走 frp 明文链）需单独权衡。
- **O3（中）恢复 runbook**：ecs-restore.md 落 knowledge/tech/infrastructure/——镜像清单、容器重建参数（meta 已有）、hermes 0.22.4 重装纪律（npm 壳覆盖坑）、密钥恢复顺序。
- **O4（低）每日 tar 异地化**：现状 DB 类资产单存 NAS；可选周度 tar 转存 OSS/阿里云盘（增量成本，Boss 拍板）。

## 五、决策点

| # | 决策 | 性质 | 建议 |
|---|------|------|------|
| D1 | 执行 7 项采集，结果回写 WebDAV nas-audit-ecs-result-20261110.md（含 #recycle/github-sync.log 补证） | 只读+写一个结果文件 | ✅ 建议批准 |
| D2 | O1：修 nas_backup.sh 清理 bug（当日 git 入仓防 05:00 覆盖） | 变更 | 建议批准 |
| D3 | O2：v5.1 扩备份范围 | 变更 | 建议批准（.ssh/creds 入包问题可先跳过） |
| D4 | O3：编写恢复 runbook | 新增文档 | 可与 D1 并行或后置 |
| D5 | O4：tar 异地化 | 方案设计 | 可后置 |
