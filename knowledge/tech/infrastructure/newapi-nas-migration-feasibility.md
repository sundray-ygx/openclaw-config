# new-api 迁移 NAS Docker 可行性评估报告

- **日期**: 2026-09-17
- **状态**: ⏸️ 评估完成，待 Boss 决策（未执行）
- **评估人**: 小助（ECS 侧实测 + 记忆/文档交叉验证）
- **标签**: #gateway #new-api #nas #migration #feasibility

## 1. 结论

**可行，技术障碍低，核心代价是架构依赖变化**：迁移后家庭宽带（NAS）承载全部 AI 网关流量，TLS 入口仍在 ECS。收益 = ECS 内存释放 + 故障域分散；代价 = 多一跳 frp 隧道依赖。推荐「方案 A：域名入口不动 + frp 反代」，客户端零改动、回滚秒级。

## 2. 现状盘点（2026-09-17 ECS 实测）

| 项 | 实测值 | 说明 |
|---|---|---|
| 容器 | `calciumion/new-api:latest`（镜像 digest 前缀 6670c75136f3，构建于 2026-09-07，Up 7 天） | 127.0.0.1:3000，`--memory=300m` |
| 实际占用 | 内存 61MB / CPU 0.19% | 极轻 |
| 数据 | SQLite `one-api.db` 6.7MB + WAL，全目录 22MB | 无外部数据库依赖 |
| 非标依赖 | ① ECS nginx **8081 路径重写桥接**（GLM/Volc 渠道，`newapi-upstream.conf`，仅容器可达）② DeepSeek 直连 | 桥接是迁移唯一技术难点 |
| ECS 资源 | 2C/1.8G，内存 available 仅 336MB（长期紧张），磁盘 40G 用 61% | 迁移动机之一 |
| 客户端 | ECS 三平台（openclaw/hermes/claude-code 令牌）+ NAS 三平台（nas- 令牌已建） | 共 6 枚令牌，域名 `api.ygxpro.online` 不变 |
| frp 链路 | NAS frpc → ECS frps(bindPort 7000)，已注册 14 个代理（5000 DSM / 5005 WebDAV / 8648 hermes 等），链路健康 | 新增 3100 代理即可 |
| 执行通道 | NAS hermes 公网可达（hermes.ygxpro.online 200） | NAS 侧操作可由 hermes 执行 |

## 3. 迁移后架构（方案 A）

```
所有 Agent → api.ygxpro.online（DNS 不变 → ECS 47.119.177.194）
  → ECS nginx 443 TLS 终端（仅改 proxy_pass: 127.0.0.1:3000 → 127.0.0.1:3100）
  → frp 隧道（ECS:3100 ← NAS frpc → NAS:3000）
  → NAS new-api 容器
      ├─ GLM-Coding  → NAS 桥接容器(nginx:8081，配置从 ECS 拷贝) → api.z.ai
      ├─ Volc-Coding → NAS 桥接容器 → ark.cn-beijing.volces.com
      └─ DeepSeek    → api.deepseek.com 直连
```

**三个关键设计**：
1. **客户端零改动**——6 枚令牌、域名、OpenAI/Anthropic 双协议全不变
2. **3100 端口不进阿里云安全组**——公网扫不到（ECS 本机 127.0.0.1 连接不走安全组），暴露面不扩大
3. **桥接容器化复制到 NAS**——new-api 渠道 base_url 改指 NAS 内部桥接，与 ECS 解耦；ECS 旧桥接保留至观察期结束

## 4. 资源评估

| 端 | 需求 | 结论 |
|---|---|---|
| NAS 新增 | 内存 ~70-300MB（new-api + 桥接 nginx）+ 磁盘 ~550MB（镜像+数据） | 任何能跑 Docker 的 NAS 均有余；**具体余量待 hermes 执行 `free -h`/`df -h` 确认（Phase 0 前置项）** |
| ECS 释放 | 内存 61-300MB、磁盘 ~550MB | 对 available 仅 336MB 的 ECS 是实质缓解（此前升级曾 OOM） |
| 延迟 | +1 跳 frp（NAS↔ECS RTT，估 20-50ms） | LLM 响应数十秒级，无感；流式文本带宽极小 |

## 5. 风险清单

| 级别 | 风险 | 缓解 |
|---|---|---|
| 🔴 | **家庭宽带成为全部 AI 服务单点**：NAS 断网/重拨 → 6 个 agent 全断粮（现状只影响 NAS 侧） | frp 断线秒级重连；切流后加 3100 连通性监控；ECS 旧容器热备保留，回滚一条命令 |
| 🟡 | 桥接配置复制出错 → GLM/Volc 渠道全 503 | 照搬 ECS `newapi-upstream.conf`；切换前用渠道「测试」按钮逐个验证 |
| 🟡 | SQLite 数据一致性 | 停机窗口 <1 分钟：停容器 → WAL checkpoint → 传数据 → NAS 启动 |
| 🟡 | `latest` 标签版本漂移 | NAS 按 ECS 当前 image digest 拉取，锁定同版本 |
| 🟢 | 运维半径变长：`docker exec` 排障需经 hermes/DSM | 巡检脚本打域名不受影响；排障走 hermes |
| 🟢 | 回滚时切换窗口内用量日志丢失（数据在 NAS，ECS 是旧副本） | 令牌/渠道配置不变，仅丢统计记录，可接受 |

## 6. 操作步骤（5 阶段）

### Phase 0 预检（NAS hermes 执行，~10 分钟）
- `docker --version` / `free -h` / `df -h` / `nproc` 确认 Docker 环境与资源余量
- NAS 出公网验证：`curl api.z.ai`、`curl api.deepseek.com`
- 定位 NAS frpc 配置文件

### Phase 1 影子部署（不停机，~30 分钟）
- NAS 拉镜像（锁定 digest 6670c75136f3 对应版本）
- 部署桥接 nginx 容器（拷 ECS `/etc/nginx/conf.d/newapi-upstream.conf`，HTTP 内部口无需证书）
- frpc 加代理 `newapi: remotePort=3100 → NAS:3000`
- ECS 侧验证 `curl 127.0.0.1:3100/api/status` 通

### Phase 2 切流（停机窗口 <1 分钟）
1. ECS `docker stop new-api`（停写）
2. 数据经已有 WebDAV 通道（ECS:5005）传至 NAS，NAS 启动 new-api（挂载数据卷，`--memory=300m --restart=always` 同参）
3. 验证：控制台登录、渠道列表、3 渠道逐个「测试」
4. ECS nginx `newapi.conf` 改 `proxy_pass 127.0.0.1:3100` → `nginx -t && reload`
5. 端到端：openclaw / claude-code 令牌各打一发真实调用 + 控制台日志确认令牌记录

### Phase 3 观察 1-2 周
- 每日 08:20 巡检（check_newapi.sh）/ 09:30 渠道健康检查继续（打域名，无感）
- 新增 frp 隧道（3100）连通性监控项
- ECS 旧容器保留（不启动）作热备

### Phase 4 收尾
- 删 ECS 旧容器/镜像，数据归档备份
- 备份脚本 `08-new-api` 段改为 NAS 本地备份；更新本部署文档与 MEMORY.md

### 回滚
ECS nginx upstream 改回 `127.0.0.1:3000` + `docker start new-api`，全程约 1 分钟，客户端无感。

## 7. 决策点（待 Boss 拍板，2026-09-17 提问未答复）

| # | 决策 | 选项 |
|---|---|---|
| D1 | 迁移方案 | A. 迁，入口不动（推荐）/ B. 不迁 / C. 连入口一起迁（若 ECS 退役，需二期单独设计：家宽 DDNS+CDN 或最小 ECS 做入口） |
| D2 | NAS 侧执行通道 | hermes 执行（我出分阶段脚本，Boss 投喂）/ Boss 手动 / 混合（需 SSH 反向通道） |
| D3 | 停机窗口 | 凌晨 02:30（推荐，避开 02:00 备份与高峰）/ 在线随切 / 我挑低峰 |

## 8. 评估备注（判断依据）

- 若动机是 ECS 内存压力：迁，但收益是「缓解」非「解决」（ECS 1.8G 根本约束仍在）
- 若动机是 ECS 退役/降配省钱：方案 A 不够，入口仍绑 ECS，需选 C 二期
- 若动机是架构整理（AI 基建下沉 NAS）：方案 A 是正确第一步
