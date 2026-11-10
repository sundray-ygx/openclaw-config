# ECS 整机恢复 Runbook（v1 · 2026-11-10 · D4 决策产物）

> 适用：ECS（47.119.177.194）整机丢失/重置后的完整服务恢复。
> 数据源：每日 tar（NAS /volume1/aliyun_backup/server-backup/，15 天滚动，v5.1）+ GitHub 两仓 + NAS 本地。
> 配套阅读：`2026-11-10-ecs-backup-audit-result.md`（资产盘点）、`2026-11-10-ecs-backup-audit-assessment.md`。
> 铁律：**恢复顺序不可乱：frps → WebDAV 凭据 → 每日 tar → 其余一切**（frps 是备份链自举根）。

## 备份资产地图

| 层 | 资产 | 位置 |
|----|------|------|
| 每日 tar | 配置包 v5.1（01~11b + backup-info.json，41M） | NAS /volume1/aliyun_backup/server-backup/YYYYMMDD/ |
| GitHub 仓 A | workspace 全量文本 | sundray-ygx/openclaw-config（23:30 推） |
| GitHub 仓 B | NAS hermes-config（含 knowledge） | sundray-ygx/hermes-config（NAS 03:00 推） |
| NAS 本地 | WebDAV 凭据、frpc 配置 | NAS /root/、/volume1/Frp |

## Phase 0 新机基础（~15min）

1. 阿里云重置/新购（Alibaba Cloud Linux 8 系），**保留原公网 IP**（先解绑再重置）
2. 安全组：22/80/443/7000/7500/1080/9090 放行（3000/5005 仅本机，无需外放）
3. `dnf install -y git curl sqlite docker`
4. 密钥恢复（顺序）：
   - SSH key：原 id_rsa 未备份——从 NAS 取，或生成新 deploy key 加到 GitHub 两私仓
   - WebDAV 凭据：从 NAS 取 .backup-creds.env → 写入 `/root/.backup-creds.env`（chmod 600）
   - 其余密钥在每日 tar 09-hermes-config 内的 .env，Phase 2 取

## Phase 1 恢复 frps（自举根，~10min）

```bash
mkdir -p /root/frp_0.60.0_linux_amd64
# 从 GitHub 重下 frp_0.60.0_linux_amd64.tar.gz（或 NAS /root/frp_0.60.0 目录直传）
# frps.toml 从每日 tar 02-frp/ 恢复（含 auth token，须与 NAS frpc.toml 匹配，以 NAS 侧为准）
cp <02-frp>/frps.toml /root/frp_0.60.0_linux_amd64/
cp <tar>/11-systemd/frps.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now frps
ss -tlnp | grep -E "7000"          # ✓ frps 起来
# NAS frpc 重连后验证 WebDAV 回环（须 207）
source /root/.backup-creds.env
curl -s -u "$WEBDAV_USER:$WEBDAV_PASS" -X PROPFIND -H "Depth: 0" http://127.0.0.1:5005/ -o /dev/null -w "%{http_code}\n"
```
恢复后建议轮换 dashboard 密码/auth token（与 NAS 同步换）。

## Phase 2 拉取每日 tar + 核心配置（~15min）

```bash
source /root/.backup-creds.env
D=$(date +%Y%m%d)   # 若当日无 tar，PROPFIND 列目录取最近一天
curl -s -u "$WEBDAV_USER:$WEBDAV_PASS" "http://127.0.0.1:5005/aliyun_backup/server-backup/$D/server-backup-$D.tar.gz" -o /tmp/sb.tar.gz
tar -xzf /tmp/sb.tar.gz -C /tmp/sb && ls /tmp/sb   # backup-info.json 应为 5.1
R=/tmp/sb
cp $R/11-systemd/*.service /etc/systemd/system/ && systemctl daemon-reload
crontab $R/03-scripts/crontab.bak
tar -xzf $R/11b-ecs-misc/etc-cron-d.tar.gz -C /etc cron.d 2>/dev/null || tar -xzf $R/11b-ecs-misc/etc-cron-d.tar.gz -C /
cp $R/07-nginx/*.conf /etc/nginx/conf.d/ && cp $R/11b-ecs-misc/nginx.conf /etc/nginx/
mkdir -p /etc/docker && cp $R/11b-ecs-misc/daemon.json /etc/docker/ 2>/dev/null; systemctl enable --now docker
mkdir -p /etc/sing-box && cp $R/01-sing-box/config.json /etc/sing-box/
tar -xzf $R/11b-ecs-misc/acme.sh.tar.gz -C /root/     # 恢复 .acme.sh
git clone git@github.com:sundray-ygx/openclaw-config.git /root/.openclaw/workspace
mkdir -p /root/.hermes && tar -xzf $R/09-hermes-config/hermes-config.tar.gz -C /root/.hermes/   # config/cron/skills/.env
cp $R/10b-hermes-default/state.db /root/.hermes/       # default profile 会话库（v5.1 起）
mkdir -p /root/.hermes/profiles/scheduler
cp $R/10-hermes-profile/state.db /root/.hermes/profiles/scheduler/
tar -xzf $R/10-hermes-profile/hermes-profile.tar.gz -C /root/.hermes/profiles/scheduler/
```

## Phase 3 服务重建（~30min）

**容器**（重建参数已在 tar 11b-ecs-misc/：docker-images.txt + container-meta-{sing-box,new-api}.json）：
```bash
mkdir -p /opt/new-api/data && cp $R/08-new-api/one-api.db /opt/new-api/data/
cp $R/08-new-api/admin-credentials.txt /opt/new-api/   # original-upstream-keys.json 等手工回填（若需要）
docker run -d --name new-api --restart always -p 127.0.0.1:3000:3000 -v /opt/new-api/data:/data calciumion/new-api:latest
docker run -d --name sing-box --restart unless-stopped -p 1080:1080 -p 9090:9090 \
  -v /etc/sing-box/config.json:/etc/sing-box/config.json:ro \
  -v /etc/sing-box/cache.db:/etc/sing-box/cache.db ghcr.io/sagernet/sing-box:latest
```
镜像版本以 container-meta json 的 `Labels["org.opencontainers.image.version"]` 为准（本基线：sing-box v1.14.4），恢复后建议把 :latest 换成具体 tag 钉死。

**hermes 网关（0.22.4）**：
1. node：nvm 未备份——`dnf module install nodejs:20` 或重装 nvm（原 v24.22.2）
2. hermes-agent：从 GitHub releases 拉 0.22.4 tarball 手动解包安装。**禁 `npm i -g hermes-agent`**（npm 壳会 sparse-checkout 就地覆盖、摧毁多版本共存退路）
3. `systemctl enable --now hermes-gateway`
4. 验证：`journalctl -u hermes-gateway -f | grep "connected to wss"`；**双 profile 各发一条实测消息**（default=aliyun助手 + scheduler=日程管家；单通道绿≠全绿，见 nas-disaster-recovery 陷阱#15）

**验证矩阵**：
- [ ] frps 7000 监听 + WebDAV 5005 回环 207 + dashboard 7500
- [ ] 容器 Up ×2；`curl -s http://127.0.0.1:3000/api/status`
- [ ] hermes-gateway active + 飞书双 profile 实测收发
- [ ] cron 面：02:00 备份 / 03:40 A2 pull / 05:00 主同步 / 08:35 简报 / 23:30 workspace 推送（crontab -l + /etc/cron.d/hermes-config-pull 核对）
- [ ] 手动触发 `bash /root/.openclaw/workspace/scripts/backup/nas_backup.sh` 跑通 v5.1 全链（注意：= 真实执行，会上传真 tar + 发真飞书卡片）

## Phase 4 frps 代理表（frps 恢复即 NAS 服务面回归）

dashboard API 核验：
```bash
PW=$(grep -oP '(?<=webServer.password = ")[^"]+' /root/frp_0.60.0_linux_amd64/frps.toml)
curl -s -u "admin:$PW" http://127.0.0.1:7500/api/proxy/tcp \
  | python3 -c "import sys,json; [print(p['name'], p['status']) for p in json.load(sys.stdin)['proxies']]"
```
基线 14 条（2026-11-10 实测）：aliyunpan、bill-web、console-api、console-web、hermes-mobile、hermes-studio、jellyfin、nas、newapi、ssh2、vaultwarden、vaultwarden-ws、webdav、webdav-http —— 全 online。恢复后逐条对照，缺哪条去 NAS 侧查 frpc。

## 缺口声明（拿得到/拿不到）

| 缺口 | 影响 | 缓解 |
|------|------|------|
| .ssh id_rsa 未备份 | GitHub 拉取需重配 | deploy key 重建（10min） |
| nvm/node、hermes 运行时 4.1G 未备份 | 需重装 | tarball 纪律（见 Phase 3） |
| :latest 镜像漂移 | 容器版本可能≠原版 | container-meta version 钉 tag |
| .backup-creds.env 不入 tar（设计） | 恢复期从 NAS/Boss 取 | Phase 0 已列 |
| default state.db ≤2026-11-09 无快照 | v5.0 时代会话史不可恢复 | v5.1 起每日快照 |
| server-backup 下 403 滞留散目录 | 删不掉是 DSM 权限锁非脚本 bug | NAS 侧本地删 |

## 恢复期纪律

1. 命令逐条复核再执行，勿整块照抄（本册已按 glm-5.3 幻字教训回读核验，但恢复时的现场状态才是真相）
2. 手动跑 nas_backup.sh = 真实执行（真上传+真飞书）
3. 变更走决策门：只读探测 → 报告+决策点 → Boss 批准 → 执行
4. 恢复完成 23 点前飞书卡片汇报（勿扰红线）
