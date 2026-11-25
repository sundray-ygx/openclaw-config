# sure + movieclaw 子域名公网接入 — ECS 侧可行性评估

- 日期：2026-11-25
- 任务书：`nas-recovery/ecs-task-sure-movieclaw-subdomain-20261125.md`（NAS Hermes 发起，称 Boss 已批复）
- 结论：**nginx 部分可行、零风险；但任务书前提「通配 A 记录已存在」与实测不符，DNS 是硬阻断，需 Boss 在阿里云控制台补两条 A 记录后才能真正验收。**
- **执行结果（同日 11:50 CST）：已全部完成并终验通过。** Boss 控制台补两条显式 A 记录、NAS frpc 重启后，ECS 落地 4 文件（新增 00-ws-map.conf/sure.conf/movieclaw.conf，note.conf 抽 map 等价重构，备份 note.conf.bak-20261125），reload 零中断。sure 302→真实登录页、movieclaw 200 + JS 真身抽验通过、note/kuma 回归正常。附带发现 pdf 域 502=NAS 侧 18080 后端问题（直连回环即断连，与本次无关），已在任务书回执中告知 NAS 侧。

## 一、任务概述

| 子域名 | 反代后端（frps 回环） | 服务 |
|---|---|---|
| sure.ygxpro.online | http://127.0.0.1:31210 | 个人理财（Rails，敏感数据，注册已关闭） |
| movieclaw.ygxpro.online | http://127.0.0.1:31200 | AI 影音服务器 |

时序：NAS frpc.toml 已加映射但未重启；ECS 先备 nginx（reload 前端口未上线，预验收预期 502）；frpc 重启后再终验。

## 二、只读核实结果（2026-11-25 实测）

| # | 核实项 | 实测结果 | 判定 |
|---|---|---|---|
| 1 | sure/movieclaw DNS | 阿里 DoH `Status:3 = NXDOMAIN`（权威 dns9.hichina.com 明确无此名） | ❌ **不存在** |
| 2 | 是否存在通配 A 记录 | 随机探测名 `randomprobe-9x7q.ygxpro.online` 同样 NXDOMAIN；现有子域 pdf/note/kuma 均为**逐条显式 A 记录** | ❌ **无通配记录，任务书前提错误** |
| 3 | ECS 能否加 DNS | aliyun CLI 已装但**未配置凭据**（/root/.aliyun/config.json 不存在），scripts/creds 中无 DNS API Key | ❌ 只能 Boss 控制台操作 |
| 4 | 目标 conf 是否已存在 | sure.conf / movieclaw.conf 均不存在，无覆盖冲突 | ✅ |
| 5 | 证书覆盖 | `*.ygxpro.online` + 裸域 SAN，有效期至 2027-01-21 | ✅ 直接复用 |
| 6 | WebSocket map 定义 | 全 conf.d 仅 note.conf 定义了一次 `$connection_upgrade`，**无共享 map 文件** | ⚠️ 新 conf 各自带 map 会重复定义 → nginx -t 失败 |
| 7 | frps 状态/端口策略 | frps 0.60.0 运行中，frps.toml **无 allowPorts/denyPorts 限制**；既有 6800/3001 等隧道均监听 `*:port`（frpc 上线即自动监听），31200/31210 当前未监听 | ✅ frpc 一重启即可用 |
| 8 | nginx 模板 | note.conf 是 11-17 事故修复后的最新模板（map 兜底、proxy_http_version 1.1、Upgrade 头、read_timeout 600s） | ✅ 照抄 |
| 9 | 502 预验收可行性 | 未监听端口 nginx 回环直连必返 502，不依赖 DNS（用 `-H Host:` + https://127.0.0.1） | ✅ |

## 三、与任务书的差异（交接信息 vs 实际）

1. **DNS：任务书称"若已有通配 A 记录则零操作"——实测没有通配，两个子域连显式记录都没有。** 这是唯一硬阻断。
2. **map 段：任务书让"若已有共享文件则复用"——实际是定义在 note.conf 内的非共享块。** 新 conf 再定义即重复。正确做法是把 map 块抽成 `/etc/nginx/conf.d/00-ws-map.conf` 共享文件（nginx 按文件名字母序加载，00 前缀保证最先），note.conf 内的同名块删除；或更保守：两个新 conf 都不写 map、直接引用 note.conf 里已加载的变量（耦合文件名，不推荐）。**采用抽取共享文件方案**，note.conf 同步去块，nginx -t 验证为唯一 map。
3. 其余（证书、frps、模板、备份命名 `.bak-20261125`、超时、client_max_body_size）均与实际一致。

## 四、执行方案（批准后执行，预计 <5 分钟，零中断）

1. **备份**：`cp -a note.conf note.conf.bak-20261125`（note.conf 要动 map 块；新文件无旧版可备）。
2. **抽 map 共享文件**：新建 `/etc/nginx/conf.d/00-ws-map.conf`，内容仅 map 块；从 note.conf 删除该 5 行。
3. **新建 sure.conf / movieclaw.conf**（照 note.conf 模板）：
   - server_name 各自域名；80 跳 443 + acme challenge；
   - 证书 `/etc/letsencrypt/live/ygxpro.online/`；
   - proxy_pass `127.0.0.1:31210` / `127.0.0.1:31200`；
   - Host/X-Real-IP/X-Forwarded-For/X-Forwarded-Proto 四件头；
   - `proxy_http_version 1.1` + Upgrade + `Connection $connection_upgrade`（map 兜底，**不硬编码 upgrade**）；
   - sure：`client_max_body_size 20m; proxy_read_timeout 300s;`
   - movieclaw：`client_max_body_size 0; proxy_read_timeout 600s;`（影音大文件）
4. `nginx -t` 通过 → `systemctl reload nginx`（零中断）。
5. **预验收**：两域 `-H Host:` 回环打 https，预期均 **502**（隧道未上线）。
6. **不动**：frps、frpc、安全组、DNS、任何现有 conf 内容（除 note.conf 抽出 map，行为等价）。
7. 回执写回任务书 WebDAV 原文件末尾「回执区」。

## 五、需要 Boss 做的事（决策点）

- **D1【必须】阿里云 DNS 控制台加两条 A 记录**（ECS 无凭据代劳）：
  - `sure.ygxpro.online` → A → `47.119.177.194`
  - `movieclaw.ygxpro.online` → A → `47.119.177.194`
  - TTL 默认即可（参照 pdf/kuma/note 既有显式记录惯例；也可 Boss 决定改配一条 `*` 通配一劳永逸，但与现状惯例不一致，不主动建议）。
- D2【批准执行】是否按第四节在 ECS 落 nginx 配置（含 note.conf 抽 map 的等价重构）？
- D3【时序】nginx 可先落（502 是预期态，不影响任何现网）；终验等 NAS frpc 重启 + D1 生效后触发。

## 六、终验标准（frpc 重启 + DNS 生效后）

- `https://sure.ygxpro.online/` → 302 跳登录；
- `https://movieclaw.ygxpro.online/` → 200/302；
- 抽验 HTML 内 `/assets/*.js` 真身返回 JS（非 `<!DOCTYPE`），防 nginx fallback 伪 200；
- 顺带回归 note/pdf/kuma 三域 200，确认抽 map 无副作用。

## 七、风险

- 抽 map 为等价重构，reload 前 `nginx -t` 把关，失败即不 reload、秒级回滚（cp 备份）。
- sure 含理财敏感数据，任务书已记录注册关闭；上线后建议 Boss 实测登录页强度，ECS 侧不掌握应用认证细节。
