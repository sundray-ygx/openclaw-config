# ECS 备份机制审计结果（NAS 任务 nas-audit-ecs-task-20261110.md · 2026-11-10）

> 执行方：ECS Hermes（小群 ECS 侧）。全程只读，未做任何变更。
> 任务文档 sha256 8eefa205…，采集时间 2026-11-10 上午。所有密钥/密码值不出现（标 [REDACTED]）。
> 关联评估：knowledge/tech/infrastructure/2026-11-10-ecs-backup-audit-assessment.md（ECS 本地）

## 1. ECS 备份脚本与调度

**证据**：`crontab -l` → `0 2 * * * bash /root/.openclaw/workspace/scripts/backup/nas_backup.sh >> /var/log/nas-backup.log`；`/etc/cron.d/` 仅 1 个自定义文件 hermes-config-pull（A2 链，见第 3 项）。
- **脚本路径**：`/root/.openclaw/workspace/scripts/backup/nas_backup.sh`（411 行，v5.0；凭据外置 `/root/.backup-creds.env` chmod 600 不入 git）
- **备份范围**（12 项打包进每日 tar）：01-sing-box(/etc/sing-box/config.json)、02-frp(frps/frpc toml+二进制)、03-scripts(本脚本+crontab 快照)、04-workspace(顶层 7 个 md)、05-openclaw-config(workspace 全量 tar，exclude .git/node_modules/.venv/pyc)、06-安全脚本(/root/.openclaw/scripts/*.sh)、07-nginx(conf.d/*.conf)、08-new-api(one-api.db 经宿主 sqlite3 .backup 一致性快照+admin-credentials+container-meta.json)、09-hermes-config(config.yaml/auth.json/.env/cron/skills)、10-hermes-profile(**scheduler** profile：state.db sqlite3 .backup + cron/skills/plans/memories/sessions/workspace/platforms 等 tar)、11-systemd(hermes-gateway+openclaw-gateway 两个 unit)、backup-info.json(v5.0 自证 ✓——已下载今日 tar 解包核实)
- **上传目标**：WebDAV `http://127.0.0.1:5005/aliyun_backup/server-backup/YYYYMMDD/server-backup-YYYYMMDD.tar.gz`（即 NAS /volume1/aliyun_backup）。今日实测：HTTP 201 上传成功、HEAD 200、41,952,191 bytes（41M），全程 1m49s
- **保留策略**：RETAIN_DAYS=15 滚动删除（详见第 7 项——**该删除逻辑有 bug，实际未按设计执行**）
- **可靠性配套**：flock 防并发、网络预检 3 次、上传重试 5 次×600s、远程 HEAD 验证、logrotate daily/rotate14、失败必推飞书卡片（cli_a93c6b1e→Boss）✓ 非静默

## 2. 每日 tar 范围核对与缺口

INCLUDE/EXCLUDE 原文见上（脚本 L184-298）。EXCLUDE：.git、__pycache__、*.pyc、node_modules、.venv、cache/audio_cache/desktop/locks/feishu_seen 等。

**✅ 覆盖**：workspace 全部（含 knowledge/memory/scripts/skills）、hermes config+scheduler profile（含其 state.db）、crontab、2 个 systemd unit、new-api DB 一致性快照、sing-box/frp 配置+二进制、nginx conf.d。

**❌ ECS 上存在但不在备份范围**（按恢复影响排序）：
| 缺项 | 大小/性质 | 丢失影响 |
|------|----------|---------|
| `/root/.hermes/state.db`（**default profile**，aliyun助手主力对话） | 55M | 🔴 全部会话历史灭失（v5.0 只备 scheduler 的） |
| `/root/.ssh`（id_rsa 等） | 28K | 🔴 GitHub 拉取凭据丢→A2 链断，需重配 key |
| `/root/.acme.sh`（证书+account key） | 4M | 🟡 证书可重签但 account/部署配置丢 |
| `/etc/cron.d/hermes-config-pull` | 1 行 | 🟡 crontab -l 不含 cron.d，A2 调度丢失 |
| systemd：frps / bill-import / notion-bill-import / openclaw-gateway-daily-restart 4 个 unit | - | 🟡 11-systemd 只备了 2 个 |
| `/etc/nginx/nginx.conf` 主文件 | - | 🟡 只备了 conf.d/*.conf |
| `/etc/docker/daemon.json` | - | 🟢 低 |
| `/root/.nvm`（node v24.22.2）+ hermes 运行时（.hermes/tools 1.6G、installs 478M、/usr/lib/node_modules/hermes-agent 4.1G） | ~6G | 🟢 可重装，但版本钉死（0.22.4 有 npm 壳覆盖坑）且无文档 |
| `/root/.backup-creds.env`（WebDAV 凭据自身） | 400B | 🟢 NAS 本地有份（凭据不随 tar 走 frp 链，v5.0 设计如此，恢复时从 NAS 取） |
| docker 镜像（new-api:latest / sing-box:latest） | 3 镜像 | 🟡 无导出，靠 dockerhub 重拉；latest tag 版本漂移风险（本机存有 sing-box v1.11.3 备胎镜像但未导出） |
| `/opt/new-api` 的 original-upstream-keys.json / price-options-backup.json / 2 个手工 .bak db | ~10M | 🟢 低 |

## 3. ECS→GitHub 三链状态

- **workspace 仓**（`/root/.openclaw/workspace` → github sundray-ygx/openclaw-config）：23:30 github-sync-cron.sh 每日跑。**🟡 发现假绿 bug**：内层 sync-to-github.sh 用 `git diff --quiet && git diff --cached --quiet` 判变更——**只认已跟踪文件的修改，新建文件（git status ??）完全不可见**。11-07/08/09 连续报「没有变更需要同步」，实际工作区躺着 5 个未提交新文件（v0.23.0 升级评估、NAS v0230 TUI 故障诊断、security-config-check-2026-11-09、exec-P3.sh、ecs-backup-audit-assessment）。最新提交仍是 11-06 9002a0f。影响：仅新增文件的日期 GitHub 副本滞后（这些文件同时在每日 tar 的 05 项里，有 NAS 副本兜底，非裸奔）。修法：变更检测改 `git status --porcelain`（未批，仅报告）。
- **A2 链**（/opt/backups/hermes-config ← GitHub sundray-ygx/hermes-config）：✅ 已部署在跑。`/etc/cron.d/hermes-config-pull` → 03:40 ecs-hermes-config-pull.sh --pull-only → /var/log/hermes-config-pull-a2.log。今晨尾 3 行：`✅ 副本新鲜度 OK（最新提交 0 天前）/ ===== 本次拉取完成 =====（×2）`。副本 558M 含 knowledge。
- **05:00 主同步**（/root/hermes-config，sparse 不含 knowledge 工作树）：/var/log/hermes-config-pull.log 尾 3 行：`更新: unattended-failover-probes / ✅ 完成: cbd06b8 sync: 2026-11-10 03:00 备份 (+1 ~12 -0) | 技能 新增 3 / 更新 16 / 官方保护跳过 14 / 飞书通知已发送`。✅ 正常。

## 4. 恢复演练可行性

**结论：无任何配套恢复文档/脚本**（knowledge 全库检索 server-backup/恢复演练/整机恢复/ecs restore = 0 命中）。凭每日 tar 可恢复：workspace、crontab、脚本、hermes scheduler profile+其 state.db、hermes config(.env 含密钥)、new-api DB、sing-box/frp/nginx conf.d、2 个 unit。**整机丢失时缺**：
1. **镜像清单无记录**（docker images：calciumion/new-api:latest 224M、ghcr.io/sagernet/sing-box:latest 105M、sing-box:v1.11.3 51.5M——凭记忆重拉，latest 漂移风险）
2. **容器重建参数无完整记录**（new-api 有 container-meta.json{Env+Binds} ✓；sing-box 无）
3. **无 docker-compose**（容器是 docker run 起的，参数散落）
4. **node/hermes 运行时重建无文档**（nvm v24.22.2 + hermes-agent 0.22.4 tarball 安装纪律——npm 壳覆盖坑有 knowledge 案底但无 runbook 串联）
5. .ssh/acme/4 unit/cron.d/nginx.conf/daemon.json（见第 2 项表）
6. **pip/npm 依赖冻结清单无**（workspace package.json 随 tar 走算部分覆盖；系统 python 脚本全 stdlib+少量 site-packages，未冻结）
7. 密钥恢复顺序无文档（.env 在 tar 内 ✓，但 WebDAV 凭据/SSH key 需从 NAS/本地另取）
→ 建议：补 ecs-restore runbook（评估报告 O3，未批）。

## 5. ECS 关键数据盘点

**docker ps -a**：sing-box(Up 2d)、new-api(Up 6w)、sing-box-v1113-rollback(Exited 12d)。Bind：new-api=/opt/new-api/data:/data(Restart=always)；sing-box=/etc/sing-box/{config.json(ro),cache.db}(unless-stopped)。

**大目录分布（du）与备份状态**：
| 路径 | 大小 | 备份状态 |
|------|------|---------|
| /usr/lib/node_modules/hermes-agent | 4.1G | ❌（可重装） |
| /root/.hermes（tools 1.6G/installs 478M/state.db 55M/profiles 76M/skills 28M/lsp 56M） | 2.4G | 部分：config/cron/skills+scheduler profile ✓；**default state.db ❌**；运行时 ❌(可重装) |
| /root/.openclaw/workspace | 927M(node_modules 53M+extensions 52M+git 52M) | ✅ 每日 tar + GitHub（新文件有滞后，见第 3 项） |
| /opt/backups/hermes-config | 558M | A2 副本本体（不备合理，可由 GitHub 重生） |
| /opt/alibabacloud | 549M | ❌ 阿里云助手系统组件（不需要） |
| /root/hermes-config | 523M(.git 430M) | 05:00 副本本体（可由 GitHub 重生） |
| /root/hermes-backup-20261022-0813.tar.gz | 426M | 手工快照（.hermes 含 skills），在 /root ❌ 未入每日 tar |
| /opt/rh | 202M | 系统编译工具链（不需要） |
| /opt/new-api | 83M | DB ✓（.bak×2 和 2 个 json ❌） |
| /root/frp_0.60.0 | 32M+tar 12M | ✅ 02-frp |
| /root/.acme.sh | 4M | ❌ |
| /root/.ssh | 28K | ❌ |
| /etc/sing-box | 1.2M | ✅ 01 |

## 6. WebDAV 服务自身（47.119.177.194:5005）

**非 docker 部署**。ECS 侧：frps（`/root/frp_0.60.0_linux_amd64/frps -c frps.toml`，systemd frps.service，PID 2343043 自 6 月稳定）监听 7000，5005 = NAS frpc 上线的 `webdav`/`webdav-http` 两条 tcp 代理回环映射到 NAS DSM WebDAV 套件。frps API 实测 **14 条 NAS 代理全 online**（nas/ssh2/webdav/webdav-http/newapi/hermes-studio/hermes-mobile/jellyfin/vaultwarden×2/bill-web/console-web/console-api/aliyunpan）——**整个 NAS 对外服务面压在这一个 frps 进程上**，其单点影响面远超备份链。
**它自己在备份范围吗**：frps.toml（含 dashboard 密码/auth token，此处 [REDACTED]）+ frps/frpc 二进制 ✅ 在每日 tar 02-frp 项；**frps.service unit ❌ 不在**（11-systemd 只备 2 个 hermes unit）。
**单点评估**：写入链 = nas_backup.sh → 127.0.0.1:5005 → frps 隧道 → NAS frpc → DSM WebDAV → /volume1/aliyun_backup。任一环断 = 上传失败 → 飞书卡片告警（实测有告警链，非静默）。**数据落地单点 = NAS 单地**：每日 tar 只存 NAS /volume1，无异地副本；异地只有 GitHub（文本类）。DB 类资产（default state.db 除外未备）仅有 NAS 单份。

## 7. 保留策略核对

**设计**：RETAIN_DAYS=15，按 PROPFIND 列目录、日期比较、逐文件 DELETE + 目录 DELETE。
**实际**：
- 每日目录（单文件，v5.0 后格式）✅ 正常滚动：现存 20261026~20261110 共 16 个 = 恰好 15 天 + 今日，昨日日志「删除 20261025」与今日 PROPFIND（1025 不在）吻合。
- **3 个历史散目录 20260322/20260509/20260512 ❌ 假删除滞留**——非手动残留。今晨 02:01:51 日志再次打印「删除过期备份: 20260322/20260509/20260512」但 PROPFIND 实测三者至今存在（连续多日同模式）。**根因**：脚本 L402 `grep -oP "(?<=<href>)[^<]+"` 匹配不到 DSM 返回的 `<D:href>`（命名空间前缀）→ 文件列表恒空 → 直接 DELETE 含子目录的非空集合被 DSM 拒（405）→ 滞留；单文件目录恰能被 DSM 直接 DELETE 成功，故每日目录不受影响。curl `-s -o /dev/null` 吞掉状态码 + deleted_count 只数循环次数 → **日志假绿**。与 NAS 今晨修复的阿里云同步链 PROPFIND bug 同族（DSM D: 前缀）。
- 20260322 为 v1/v2 时代多子项目录（9 项含子目录），0509/0512 为单 tar 目录但内含？——0509/0512 实测仅含 1 个 tar，理论上应能被 DELETE……与 20261025（同样单 tar）命运不同，差异点待修 bug 时一并验证（不影响结论：三者均滞留 + 日志均假绿）。#recycle 经 WebDAV 探测为空（DSM 回收站不暴露给该 share 视图）。
- 修法已评估未批：L402 改 `(?<=href>)` + DELETE 后校验 HTTP 码（评估报告 O1/D2）。修好后三散目录次日自动清除。

### 7.1 追加（2026-11-10 下午，D2 执行中实证）：双因结论修正

修复后一次性清理实测：**解析 bug 只是因素一；因素二 = DSM 对 3 个散目录内全部文件的 DELETE 返回 403 Forbidden**（含 Depth:infinity 目录删除亦 403，36 项 DELETE 全失败）。对照实验：同账号 PUT+DELETE 自己新建的文件 = 204 正常（含每日目录内探针）→ 排除账号全局禁删，锁定为**这批老文件的属主/ACL 差异**（疑为 DSM 侧历史迁移或快照继承所致）。
推论修正：①假删除根因=解析 bug（文件列表恒空→DSM 拒删非空目录）+老文件 403 权限锁，双因叠加 ②每日目录滚动不受影响（其 tar 为现账号所传，DELETE 权限正常）③3 个散目录 ECS 侧永远删不掉，需 **NAS 侧本地删除**（DSM File Station 或 SSH rm，1 分钟）④v5.1 修复后若散目录仍在，每晚清理会如实报失败并推飞书告警——是诚实遥测非噪声，NAS 侧清理后自愈。


---

## ECS 侧备份机制一页总结

**体系**：①每日 02:00 nas_backup.sh v5.0 打 12 项 tar（41M/1m49s）→ WebDAV→NAS 单地，15 天滚动（清理有 bug），失败飞书告警 ②workspace 23:30 → GitHub openclaw-config（变更检测有新文件盲区 bug）③NAS hermes-config 03:00 push GitHub → ECS 03:40 A2 拉全量副本 + 05:00 sparse 副本，断链告警 ✓ ④手工快照若干（10-22 tar 426M 在本地未入链）。

**健康面**：上传/验证/告警链完整非静默；12 项范围覆盖主要配置资产；A2 双时间位冗余；logrotate 齐。核心配置类资产恢复可能性中上。

**缺陷按严重度**：🔴 ①default profile state.db（55M 主力会话库）零备份 ②保留清理假删除（D:href 解析 bug，日志假绿）🟡 ③github-sync 未跟踪文件静默跳过（GitHub 副本滞后 3 天+）④恢复 runbook/镜像清单/compose 参数全缺 ⑤DB 类资产 NAS 单地无异地 ⑥.ssh/acme/4 unit/cron.d/nginx.conf 缺备 🟢 ⑦latest 镜像漂移风险 ⑧散目录滞留占 NAS 空间。

**修复建议**（详见评估报告 O1-O4，均未批）：O1 修假删除（一行 grep + DELETE 校验，当日 git 入仓）；O2 v5.1 扩范围（default state.db 用 sqlite3 .backup 模式最优先）；O3 恢复 runbook；O4 tar 异地化。
