# NAS 外网业务域名更换预案（现状梳理 + 迁移方案规划）

> 状态：**已归档备案（2026-11-05）——域名新购/续费决策推迟至 2026-12 续期观察节点**
> 决策记录：Boss 指示先备案；已挂续期观察提醒（见 §七），届时二选一：A.采购新域名（启动本预案阶段 0）/ B.续费旧域名（本预案搁置，仅续费）。
> 日期：2026-11-05 | 作者：小群（ECS 实例）
> 背景：群晖 NAS 因 DSM 升级导致 hermes 业务中断的教训之后，提前为「域名有效期（1 年）+ 证书依赖 ECS」这一风险点做预案，确保换域名不伤业务。

---

## 一、现状核实（全部为只读探测的实测结果）

### 1.1 域名与证书链

| 项目 | 实测值 |
|---|---|
| 域名 | `ygxpro.online`，阿里云（HiChina）注册 |
| **域名到期日** | **2027-05-13**（RDAP 实测，status=active） |
| 证书 | `*.ygxpro.online` 泛域名，Let's Encrypt，acme.sh 管理 |
| 证书有效期 | 2026-10-23 → 2027-01-21（90 天周期，下次自动续期 2026-12-22） |
| 签发方式 | `dns_ali`（阿里云 DNS API，全自动续期，凭据在 acme.sh account.conf） |
| 雷点 | 域名 2027-05-13 到期，证书 90 天一续——若域名到期未续费，DNS API 验证失败 → 证书续期失败 → 全线断；域名过期被释放则无法找回 |
| 零散依赖 | frps.toml 有注释掉的 `subdomainHost = "ygxpro.xyz"` 残留；hermes-config 仓有 11 处 `ygxpro.xyz` 引用（历史文档/技能存档，非运行时依赖） |

### 1.2 ECS 入口层（frps + nginx）

**frps**（`/root/frp_0.60.0_linux_amd64/frps.toml`，v0.60.0，常驻运行）：
- bindPort=7000，vhostHTTPPort=8080（当前全部为 TCP 端口映射，无 HTTP vhost、无 subdomainHost）
- 管理台 7500
- **14 个在线 TCP 隧道**（frps API 实测，另有 1 个 offline 残留 tcp_59591）

**nginx**（80/443）：10 个活跃 conf 消费该泛域名证书，全部为 `proxy_pass 127.0.0.1:<frp端口>` 反代——**frps 本身不碰证书，证书只在 nginx 层**。这是换域名的核心改造面。

### 1.3 业务域名依赖全景（域名 → DNS → nginx → frp 隧道 → NAS 业务）

ECS 公网 IP：47.119.177.194（阿里云 metadata 实测）。DNS TTL=600s。

| 子域名 | DNS | nginx conf（→本地端口） | frp 隧道(remotePort) | NAS 业务 | 换域名影响 |
|---|---|---|---|---|---|
| `api` | ✓ | newapi.conf→3000 | newapi(3100) | new-api 网关 | **高**：.env×5 / openclaw.json×3 / 脚本×7 / hermes-config 仓 98 处引用 |
| `vw` | ✓ | vaultwarden.conf→3011/3012 | vaultwarden(3011)+ws(3012) | Vaultwarden | **高**：hermes-config 仓 112 处引用（含 NAS 侧客户端 URL 配置） |
| `hermes` | ✓ | hermes-studio.conf→8648 | hermes-studio(8648) | Hermes Studio | 中：hermes-config 仓 22 处 |
| `nas` | ✓ | nas.conf→5000 | nas(5000) | DSM 管理台 | 中：浏览器书签 |
| `cc` | ✓ | cc.conf→3346/8648（server_name 含 cc. 和 hermes. 双域名） | hermes-mobile(3346) | Claude Code 网关页 | 中：42 处引用 |
| `console` | ✓ | console.conf→3200 | console-web(3200)+console-api(3300) | 个人数字中心 | 中：26 处引用 |
| `bill` | ✓ | bill.conf→8001 | bill-web(8001) | 房租账单系统 | 中：10 处引用 |
| `jellyfin` | ✓ | jellyfin.conf→8096 | jellyfin(8096) | Jellyfin 媒体库 | 中：手机/TV 客户端填了地址，需 Boss 自报清单 |
| `webdav` | **无 A 记录** | webdav.conf→5005 | webdav(5006)+webdav-http(5005) | Synology WebDAV | **无**：ECS 备份走 127.0.0.1:5005 本地环回，不经域名 |
| `pan` | **无 A 记录** | pan.conf→9080 | aliyunpan(9080) | 阿里云盘 WebDAV 转接 | 无：DNS 已无记录，conf 属休眠态 |
| `newapi`（探测） | **无 A 记录** | — | — | — | 我误猜的子域名，实际不存在 |
| —（纯端口） | — | — | ssh2(7023) | NAS SSH（仅 NAS→ECS 方向暴露） | **无**：纯 IP:port |
| —（纯端口） | — | — | aliyunpan(9080) | 同 pan | 无 |

### 1.4 控制面通道（不依赖域名，换域名零影响）

- **frpc→frps**：早期架构文档显示 NAS 直连 `47.119.177.194:7000`（IP 直连）。待 NAS 会话核实当前 frpc.toml 实况（ECS 无法 SSH 到 NAS，7023 是反向的）。
- **ECS→NAS 备份**（nas_backup.sh）：`WEBDAV_URL="http://127.0.0.1:5005"`——走 frp 隧道本地环回，不经域名、不经公网 DNS。
- **hermes-config 同步**：NAS 03:00 push → ECS 05:00 pull（rsync over SSH？——实际为 NAS push 到 ECS 方向，同样不经域名）。

### 1.5 关键时间线

```
2026-12-22  acme.sh 下次自动续期（正常应自动成功，观察点）
2027-01-21  当前证书自然到期（续期成功则顺延 90 天）
2027-03 中   若走换域：新域证书签发+双轨部署的最晚启动点（留 45 天双轨期）
2027-04-13  ygxpro.online 到期前 30 天（注册商提醒，最后决策窗口）
2027-05-13  ygxpro.online 到期——不续费且未迁移完成 = 外网业务全断
```

## 二、需求理解（我的复述，请确认）

1. **不是现在换**：域名 2027-05 到期，现在做预案，择期执行。
2. **核心诉求**：外网可达的 NAS 业务（frp 隧道 + ECS nginx + 泛域名证书）在域名更换时零中断。
3. **隐含约束**：NAS 侧 hermes/openclaw/各客户端硬编码的 api/vw 引用需同步切换；NAS 侧动作需 Boss 在 NAS 会话指挥或手动配合（ECS 无 SSH 到 NAS）。
4. 本报告仅现状+方案，**未动任何配置**。

## 三、方案规划（三阶段，可分段批准）

### 阶段 0：预备（纯增量，零风险）
1. 确定新域名并注册（建议仍在阿里云：dns_ali 插件零改造，凭据复用）。
2. acme.sh 签发新域泛域名证书：先 `--server letsencrypt_test` staging 调试，再正式签。
3. 新子域名 A 记录 → 47.119.177.194（TTL 600，提前建好）。
4. nginx 每个站点**新增** server 块（新域名+新证书），`nginx -t && nginx -s reload`——老域名不动，零中断。
5. 在 gateway-switch 技能补充新旧域名全局映射表。

### 阶段 1：双轨并行期（≥2 周）
1. 全子域名 HTTPS 探测 + 功能 smoke：vw 登录、api 通路、jellyfin 播放、nas 登录、bill/console/cc 页面。
2. 客户端硬编码切换：NAS 侧（hermes .env、openclaw.json、frpc 核实）由 NAS 会话执行——另附 NAS 侧清单；ECS 侧（.env×5、openclaw.json、newapi 相关脚本 7 处）本会话可做。
3. 观察新链路连续 14 天无故障 + 新证书第一次自动续期成功 → 进入阶段 2。

### 阶段 2：正式切换（独立决策点）
1. 全局替换 ygxpro.online → 新域（nginx conf、.env、openclaw.json、脚本、hermes-config 仓，含 .bak 文件防复活旧配置）。
2. 老域名 DNS 保留 30 天作回退通道（TTL 600，回退 RTO≈10 分钟）。

### 回退方案
- 阶段 2 前：删新 server 块即回退，老域名全程在线，RTO≈0。
- 阶段 2 后：重建老域名 DNS + 恢复 .bak 配置（均会先备份）。

## 四、决策点（需你拍板）

| # | 决策点 | 选项 | 建议 |
|---|---|---|---|
| 1 | 新域名 | a. 新购（.com 等） b. 续费现域名观望 c. 免费域 | **a**：新购同厂（阿里云），dns_ali 零改造 |
| 2 | 证书策略 | a. 泛域名单证（同现状） b. 多 SAN | **a**：机制与现状一致 |
| 3 | NAS 侧切换 | a. Boss 在 NAS 会话指挥执行 b. Boss 手动 c. 仅做 ECS 侧 | **a**：有先例（网关四端同步） |
| 4 | 老域名处置 | a. 续费 1 年保号 b. 到期放掉 | **a**：年费几十块换回退保险 |
| 5 | 启动时序 | a. 2026-12-22 续期观察后启动阶段 0 b. 立即启动 | **a**：先验证续期链路健康再动 |

## 五、本次只读操作清单（透明化）

RDAP 域名查询、`acme.sh --list`、读 frps.toml / nginx confs、frps 管理 API 查代理状态、DNS 解析实测（223.5.5.5）、openssl s_client 证书探测、grep 统计各配置域名引用、读 crontab / nas_backup.sh / 架构文档。**未修改任何文件、未重启任何服务。**

## 六、开放问题（如实报告）

1. NAS 侧 frpc 的 serverAddr 当前实况（IP 或域名）需在 NAS 会话核实——这是阶段 0 第一个待办。
2. jellyfin/nas/vw 手机与 TV 客户端里填的服务器地址清单，只能 Boss 自报（无法枚举你设备上的配置）。
3. hermes-config 仓 98 处 api 引用中含历史文档（非运行时），阶段 2 替换时需区分运行时配置 vs 文档存档，避免大范围误替换制造 diff 噪音——git 仓每日自动 commit，改动会被推送。
4. 本机 python3=3.6.8 无 pip，DNS/RDAP 探测用原生代码完成，无新增安装。

---

## 七、归档备案附记（2026-11-05）

**Boss 决策**：方案备案，暂不执行。域名处置（新购 vs 续费）推迟至 2026-12 续期观察节点决策。

**已落地的观察提醒机制**（本次唯一实际变更，其余全部只读）：
- 脚本：`/root/scripts/reminder/domain_renewal_reminder.sh`（+软链镜像至 workspace/scripts）
- crontab：`42 8 24 12 *`（续期结果观察卡）+ `42 8 28 12 *`（决策催办，可 ACK 跳过）
- 推送链路：crontab 直连飞书 API（app cli_a93c6b1e，open_id ou_d8ae71...，同每日简报/心跳链路，已实测推送成功）
- ACK 机制：Boss 决策后 ECS 会话告知小群即写 `.domain-decision-acked`，12-28 不再催办

**12-24 观察卡的判定逻辑**：`openssl -checkend 80天`——12-23 22:06 acme cron 续期成功则 notAfter 顺延至 2027-03 下旬（checkend 通过→绿卡）；未续期则剩余 ~28 天（checkend 不通过→红卡+排查路径）。此卡同时承担「续期结果汇报」与「域名处置决策提醒」双职能。

**待办沉淀**（阶段 0 启动前置，本次不执行）：
1. NAS 侧 frpc serverAddr 实况核实（IP 或域名，NAS 会话查 frpc.toml）
2. Boss 自报 jellyfin/nas/vw 的手机/TV 客户端服务器地址清单
3. acme.sh 新域名签发（staging 先行）+ nginx 双轨 server 块 + 新 DNS A 记录
