# NAS DSM 升级后 root 环境与 Docker 容器丢失 — 备份资产盘点与恢复评估报告

> 生成：2026-10-31 00:40（ECS 侧，小群）
> 性质：**只读评估，未做任何变更**。执行须 Boss 逐项批准决策点。
> 方法：全部结论来自本次实测命令输出；记忆/文档中的声称均标注「待核实」。

---

## 0. 结论速览

- **NAS 本体活着，volume1 数据面大概率无损**：DSM Web 返回 200、WebDAV 服务正常、frpc 14 条隧道全部 online、`/docker` 共享下 13 个容器数据目录健在（newapi 数据 **10-30 21:38** 仍有写入，即升级当晚仍在用）。
- **丢失的是"系统层"**：10 个容器后端端口全部连接失败（容器全灭），Boss 报告 root 环境 hermes 不见了——指向 DSM 升级重置了系统分区上的 `/root`、自定义 systemd/crontab、Docker 容器注册表。
- **恢复可行性：高**。知识库/记忆/技能/主配置在 GitHub 私有仓库有 **10-30 03:00 全量副本**（距升级不到 19 小时）；容器数据在 volume1；LLM 密钥在 ECS 有副本。
- **两个真实缺口**：① NAS `.env`（飞书 App secret）无备份——需重置或从 Vaultwarden 取；② cron 任务定义、`projects/` 代码（console/bill-to-notion/model-proxy）、kanban.db 不在备份范围。
- **先别动手**：H1（服务只是没自启，数据都在）与 H2（/root 真被清）的恢复动作完全不同，Phase 0 十分钟探测定分晓。

---

## 1. 事故时间线（实测拼出的证据链）

| 时间 | 事件 | 证据 |
|------|------|------|
| 10-30 02:00 | ECS→NAS 每日备份成功（33MB 上传+验证） | nas-backup.log-20261030 |
| 10-30 03:00 | NAS push-config 最后一次成功推送（+16 文件） | hermes-config git log `234180b` |
| 10-30 05:00 | ECS pull 正常拉取并传播 8 个技能更新 | hermes-config-pull.log |
| 10-30 21:38 | newapi 容器数据目录最后写入（升级前最后活动） | WebDAV PROPFIND last-modified |
| 10-30 21:38 后 | **DSM 升级执行（在 NAS hermes 会话中）**，此后 NAS 侧静默 | 推断：此后无任何 NAS 推送/写入 |
| 10-31 00:10~00:25 | ECS 侧实测：隧道 online 但后端全灭 | 本报告 §2 |

## 2. 现状实测（2026-10-31 00:10-00:35，ECS 视角）

| 探测项 | 结果 | 判读 |
|--------|------|------|
| frps 管理口 7500 | 14 条隧道全部 `online` | frpc（/volume1/Frp）活着，volume1 挂载正常 |
| DSM Web（5000 隧道） | HTTP 200，标题 `enjoysynology - Synology NAS` | DSM 起来了 |
| WebDAV（5005 隧道） | PROPFIND 207，目录可列举 | WebDAV 包正常，volume1 可读 |
| 容器后端 3011/3012/3100/3200/3300/3346/8001/8096/8648/9080 | **全部连接失败**（0.01s 即拒） | 隧道在、后端死：Docker 容器全灭 |
| SSH（7023 隧道） | banner `SSH-2.0-OpenSSH_8.2`，但 ECS 公钥 `Permission denied` | sshd 活着；ECS 依旧无授权（与记忆一致） |
| 飞书 NAS 机器人（cli_a9700b52…） | 今日无任何推送（3:00 备份、9:30 检查均静默） | NAS hermes 网关确认死 |

**判读**：这是典型的"系统层被重置、数据层健在"形态。DSM 升级（尤其跨大版本或带分区变更的更新）会重建系统分区 overlay——`/root`、`/etc/crontab` 自定义行、`/etc/systemd/system` 自定义单元、Docker 套件的容器注册表都可能被清；而 volume1/volume2 的共享数据不受影响。frpc 还在线是个待解释项（可能其自启机制恰好幸存，或 DSM 任务计划的 @reboot 任务未被清）——Phase 0 会查清。

## 3. 两个假设（Phase 0 用 10 分钟区分）

- **H1（乐观，概率中）**：`/root` 和 @docker 注册表其实都在，只是 Docker 套件与 hermes systemd --user 服务升级后**没有自启**。恢复 = 起服务，分钟级。
- **H2（悲观，概率中偏高）**：系统分区被重置，`/root/.hermes` 与容器注册表真被清。恢复 = 走 §5 完整方案，小时到半天级。
- 两者的探测脚本相同，输出会直接给出答案（见 §6 Phase 0）。

## 4. 备份资产矩阵（全部已核实）

### 4.1 在手的（可恢复）

| # | 资产 | 位置 | 最后快照 | 完整度 |
|---|------|------|----------|--------|
| A1 | NAS knowledge/ 知识库全树 | GitHub `sundray-ygx/hermes-config` + ECS clone（/root/hermes-config） | **10-30 03:00** | ✅ 全量（14 个一级子目录都在库） |
| A2 | NAS memory/（每日日志/lessons/projects/system-baseline） | 同上 | 10-30 03:00 | ✅ 全量（state.db* 按设计排除） |
| A3 | NAS skills/（14MB 全部自创技能，65 个目录） | 同上 + 已传播到 ECS `/root/.hermes/skills` | 10-30 03:00 | ✅ 全量 |
| A4 | NAS config.yaml（16KB）+ AGENTS/SOUL/MEMORY.md | 同上 config/ | 10-24 05:00 | ✅（密钥均为 `${VAR}` 引用，无明文） |
| A5 | 容器数据（vaultwarden/jellyfin/newapi/iptv-api 等 13 个 `/docker/*` 目录） | **NAS volume1 本体**（WebDAV 可见） | 10-30 21:38 | ✅ 健在（volume1 未受升级影响） |
| A6 | state.db 会话库（869MB） | **/volume1**（10-29 刚从根分区迁出，见 memory/2026-10-29） | 10-29 | ⏳ 待核实——若在，全部会话史无损 |
| A7 | LLM 密钥（ZAI/VOLCENGINE/DEEPSEEK） | ECS `/root/.hermes/.env` | 现行 | ✅ 可直接复用（NAS config.yaml 的 fallback 直连 zai 用的就是这类 key） |
| A8 | 容器重建 runbook | ECS knowledge：newapi 迁移四件套、vaultwarden 部署文档、frp-config 等 | 现行 | ✅ 关键参数（端口/bind/镜像）大都在文档里 |
| A9 | ECS 自身配置 15 天滚动备份 | NAS WebDAV `/aliyun_backup/server-backup/`（10-15~10-30 共 18 份） | 10-30 02:00 | ✅（本次事故不涉及，但证明通道健康） |

### 4.2 缺口（无备份，需重建/补救）

| # | 资产 | 影响 | 补救路径 |
|---|------|------|----------|
| G1 | NAS `/root/.hermes/.env`（飞书 App `cli_a9700b52…` 的 secret、模型 key） | hermes 网关起不来 | 飞书开放后台重置 secret（最快），或 Vaultwarden（数据在 volume1，恢复容器后可查）|
| G2 | NAS cron/jobs.json（9+ 个 hermes 定时任务：早间简报/日反思/周复盘/知识归档…） | 定时任务全停 | 按知识库 cron 架构文档 + memory 日志重建（定义散在日志里，可恢复 90% 语义） |
| G3 | platforms/ 飞书配对（feishu-approved.json） | 机器人不听指令 | `hermes pairing approve` 重新配对，分钟级 |
| G4 | `projects/` 代码（console 前端、console-api、bill-to-notion、model-proxy） | 个人项目代码 | ❌ 高危——git 仓库不含；待 Phase 0 确认是否真丢；console 或有本地 clone 可救 |
| G5 | kanban.db、/root/.hermes/scripts/（daily/plan 等自建脚本） | 运维脚本丢失 | 部分在知识库/记忆有描述；scripts/drafts 归档过一部分 |
| G6 | /etc/crontab 自定义行、systemd units（bill-to-notion、frpc 等） | 自启链断 | 知识库有 systemd 文档 + 本报告附重建清单 |
| G7 | Docker 容器"注册表"（容器名/启动参数）——数据卷健在但容器定义可能没了 | `docker ps -a` 空 | 按 A8 的 runbook 逐个重建，bind mount 回 /volume1/docker/* |

## 5. 恢复方案（三阶段，均待批准）

### Phase 0 — 只读探测（10 分钟，零风险）
目的：区分 H1/H2，摸清幸存资产。两种执行方式见决策点 D2。
脚本动作全部只读：`cat /etc/VERSION`、`ls -la /root/.hermes /volume1/@docker`、`docker ps -a`/`docker images`、`ls /usr/local/lib/hermes-agent-*`、`systemctl list-units`、`cat /etc/crontab`、检查 state.db 软链目标、`du -sh /volume1/docker/*`。

### Phase 1 — hermes 网关恢复（1-2 小时）
1. 重装 hermes（版本选择见 D3；知识库有 NAS 侧升级流程文档）
2. `git clone sundray-ygx/hermes-config` → 恢复 knowledge/memory/skills/config 四目录
3. 重建 `.env`：LLM key 从 ECS 安全通道传（frp ssh scp 直传，禁走 git）；飞书 secret 走 D4
4. `hermes pairing approve feishu <code>` 重新配对
5. 重建 cron 任务（按文档+日志，逐个与 Boss 确认语义）
6. `systemd --user` 重挂 hermes-gateway 单元 + 04:00 重启 timer（文档在库）

### Phase 2 — 容器恢复（半天，按优先级）
优先级建议：vaultwarden（密码库，全家要用的凭据都在里面）→ newapi-failover → jellyfin/iptv → 其余。
每个容器：按 runbook `docker run`（禁 latest，钉 digest）→ bind mount 回 `/volume1/docker/<name>` → frpc 隧道已在（frps 侧无需动）→ 验证。

### Phase 3 — 防再犯（本次事故暴露的备份盲区）
把 push-config.sh 的 rsync 范围扩大：+ `cron/jobs.json`、+ `platforms/`（配对清单）、+ `projects/` tar 包（排除 node_modules/.venv）、+ `/etc/crontab` 快照、+ systemd 单元快照。密钥仍不入 git，改入每日 33MB 的 WebDAV 备份包（该包已含 ECS .env，通道私有）。

## 6. 风险表

| # | 风险 | 级别 | 缓解 |
|---|------|------|------|
| R1 | 盲目重启/重装 Docker 套件导致 @docker 里幸存的镜像/容器定义被覆盖 | 高 | Phase 0 先盘点，任何套件操作前先 `tar` 备份 `/volume1/@docker` 的元数据目录 |
| R2 | DSM 升级其实没完成（处于半升级态），乱动导致更糟 | 高 | Phase 0 查 `/etc/VERSION`、`/usr/syno/synoman/webapi/` 版本与升级日志 `/var/log/synoupdate.log` |
| R3 | projects/ 代码（G4）确认丢失且无本地副本 | 中 | Phase 0 先确认；console 若有 Boss 本机/GitHub 副本可回传 |
| R4 | 飞书 secret 重置后，旧 token 缓存导致网关反复重启 | 低 | 重置后清 cache 再起网关 |
| R5 | 恢复期间 NAS WebDAV 暴露面（5005 已在公网）被扫 | 低 | 通道一直如此（Boss 已知悉接受），恢复后建议纳入 Phase 3 加固 |

## 7. 决策点（请 Boss 批复）

- **D1**：先执行 Phase 0 只读探测？（推荐：批准，零风险）
- **D2**：探测执行方式——(a) 我生成探测脚本，你 SSH 到 NAS 手动贴入运行、输出回传（不动 NAS 任何状态，**推荐**）；(b) 你在 NAS 的 authorized_keys 里加 ECS 公钥（`/root/.ssh/id_rsa.pub` 我可以给出），我远程只读探测
- **D3**：hermes 重装版本——按知识库记录的原版本，还是升到当前最新？（Phase 0 探明原版本后再定）
- **D4**：飞书 secret——(a) 你到飞书开放后台重置后发我（快）；(b) 先恢复 vaultwarden 容器再从密码库取（顺，但多等半天）
- **D5**：Phase 3 备份盲区修补是否授权（改 push-config.sh，先出 diff 再执行）

## 8. 直说建议

1. **数据没全丢，不用慌**。最坏情况下知识资产的账面损失≈0（git 有 10-30 03:00 快照）；真正的肉痛项只有 projects/ 代码和 cron 定义，且都要等 Phase 0 确认。
2. **顺序别乱**：先探测（H1 的话什么都别重装，起服务就完事）→ 再恢复 → 最后补盲区。跳过探测直接重装 = 主动销毁可能幸存的现场。
3. **值得反思的一条**：这次 869MB state.db 能活下来纯属侥幸（10-29 刚迁去 /volume1）。备份盲区（cron/projects/.env）是系统性问题，Phase 3 必须补上，否则下次没这么走运。

---

## 9. Phase 0 探测结论（2026-10-31 00:50 实测，判定 H2 成立 + 三大幸存意外）

### 9.1 事故定性
- 升级动作：**DSM 7.2.2-72806 Update 10**（小版本安全更新），10-30 21:43:34 完成
- 灾害范围：**rootfs（/dev/md0）用户层被重置**——/root 清回出厂态（仅剩 .profile/.ssh/.bash_history/.viminfo），用量 55%→29%（约 2.1G 用户数据消失，即 /root/.hermes 全部 + /root/scripts）
- /root/.hermes 八项资产确认全失：.env、config.yaml、cron/jobs.json、platforms/、scripts/、skills/、memory/、projects/（console/bill-to-notion/model-proxy 代码）、logs/

### 9.2 幸存资产（比预期好得多）
| 资产 | 位置 | 状态 |
|------|------|------|
| **state.db 会话库 845MB** | `/volume1/hermes-data/state.db`（mtime 10-30 21:40 升级前最后写入） | ✅ 完好，等软链回接 |
| **git 备份仓库本体** | `/volume1/hermes-config/`（cron.d 仍指向它的 push-config.sh） | ✅ 在 volume1，10-30 03:00 后有活动 |
| **hermes 安装本体** | `/usr/local/lib/hermes-agent` + 0.19/0.21.0/0.21.6/0.22.4 四版本 + /usr/local/bin/hermes | ✅ 未被清（只丢了 /root），但 `hermes --version` 失败待查（疑似 venv/依赖在 /root 下的部分丢失） |
| **容器注册表+镜像+卷** | `/volume1/@docker/`（containers 10-29 23:31、volumes 10-23） | ✅ 完整 |
| **容器 bind 数据** | `/volume1/docker/` 13 目录 | ✅ 完整 |
| **ContainerManager 套件** | synopkg 状态 **stop（已安装未启动）** | ✅ 只需 start，无需重装 |
| **frpc** | systemd frpc.service enabled，运行中 | ✅ 自启幸存 |
| **/etc/crontab + cron.d** | 全部保留（含 ransomware-guard、hermes-config-backup） | ✅ 但 3 条指向已丢路径会空跑失败 |
| user systemd 总线 | root/ygx 的 systemd --user 进程在 | ✅ 只缺单元文件 |

### 9.3 恢复路径修订（比原方案轻一个量级）
1. `synopkg start ContainerManager` → 大概率容器全量回归（@docker 注册表在）
2. 重建 `/root/.hermes` 骨架 + 从 `/volume1/hermes-config` rsync 四目录 + state.db 软链回接
3. 修 hermes 启动链（查 --version 失败根因）
4. .env 重建（D4）+ 飞书重配对 + systemd user 单元重建
5. cron 任务反推重建（从 ECS git 历史 + memory 日志）
