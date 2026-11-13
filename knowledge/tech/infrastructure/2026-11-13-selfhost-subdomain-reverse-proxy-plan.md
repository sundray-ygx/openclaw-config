# 自托管服务子域名反代上线评估（kuma/pdf/note.ygxpro.online）

> 日期：2026-11-13 ｜ 评估方：ECS Hermes ｜ 任务书来源：WebDAV nas-recovery/ecs-task-selfhost-subdomain-20261113.md
> 状态：**待 Boss 批准（D1）**——批准后执行；本文件执行后追加「执行回执」。

## 一、只读核实结果（全部实测，2026-11-13）

| # | 任务书声称 | ECS 实测 | 判定 |
|---|-----------|---------|------|
| 1 | frp 隧道三端口映射就绪 | 127.0.0.1:3001→302、:18080→200、:6800→401，均 frps(pid 2343043) 监听，后端经隧道真实响应 | ✅ 一致 |
| 2 | 预期状态码 kuma 302/pdf 200/note 401 | 实测 302/200/401 完全吻合 | ✅ 一致（文档质量高） |
| 3 | DNS 三记录待加 | getent+python3 socket 双工具：kuma/pdf/note 均 NXDOMAIN；对照组 console/api.ygxpro.online→47.119.177.194 正常解析 | ⚠️ 属实，需加记录 |
| 4 | EIP=47.119.177.194 | 外部视角实测一致（网卡是内网 172.27，EIP 经映射） | ✅ 一致 |
| 5 | 通配符证书可用 | /etc/letsencrypt/live/ygxpro.online/ 存在，SAN=*.ygxpro.online+裸域，有效期至 2027-01-21 | ✅ 一致 |
| 6 | console.conf 同款写法可参照 | console.conf 即「80 跳转+443 WS 反代」同构模板，现有 9 个子域名 conf 均此模式，无 kuma/pdf/note 冲突 | ✅ 一致 |
| 7 | 8080 在 ECS 被占 | 部分偏差：frps 自身正在监听 *:8080（某条已有隧道的 remote_port，非任务书三隧道）。「被占」说法成立但占者是 frps 自己的已存隧道——用 18080 避让正确，无遗留问题 | ✅ 无碍（信息差异，非错误） |
| 8 | DNS 可自动添加 | NS=dns9/dns10.hichina.com（阿里云解析），但本机 aliyun CLI 无凭据配置（~/.aliyun/config.json 不存在），Vaultwarden 未查到 AccessKey（域名的 DNS 托管在阿里云控制台，与 ECS RAM 不是一套凭据） | ⚠️ 无法自动加，需 Boss 手工 |
| 9 | 安全组无需放行 | 实测 EIP 直连 3001/18080/6800 全部超时（000）= 安全组未放行公网访问这些端口，期望态达成。流量路径：公网:443→nginx→127.0.0.1:frp 端口，纯本机回环 | ✅ 一致 |
| 10 | 隧道端口监听 0.0.0.0 | frps 监听 *:3001 等非仅 127.0.0.1，但安全组拦截使公网不可达，风险敞口=0 | ✅ 无碍（备注见三.2） |

**结论：任务书事实核查 8/10 完全一致，2 项无碍偏差。方案与 ECS 现有 9 个子域名反代的成熟模式同构，可行性=高。**

## 二、执行方案（批准后）

1. **DNS（Boss 手工，阿里云解析控制台 dns.console.aliyun.com）**：加 3 条 A 记录 → 47.119.177.194
   - kuma / pdf / note .ygxpro.online，TTL 默认（600）
   - 加完我可代为验证解析生效
2. **写 3 份 conf**：/etc/nginx/conf.d/{kuma,pdf,note}.conf，按任务书模板（console.conf 同构）：
   - kuma：proxy_pass 127.0.0.1:3001 + WS 头 + read_timeout 3600s
   - pdf：127.0.0.1:18080 + client_max_body_size 2048m + read_timeout 600s（大上传）
   - note：127.0.0.1:6800 + WS 头 + client_max_body_size 128m + read_timeout 600s
3. **生效**：nginx -t && systemctl reload nginx（reload 不断现有连接）
4. **验证（外网真路径 + 本机对照）**：https://kuma/pdf/note.ygxpro.online 各留 curl 状态码（预期 302/200/401）+ 证书链
5. **回写回执**：追加到 WebDAV 任务书文件「执行回执」节（含 DNS 状态/nginx 结果/三域名实测/偏差记录）

## 三、风险与决策点

### 决策点 D1：是否批准执行（nginx 三 conf + reload）
- 影响面：新增 3 个 server 块；nginx reload 对现有 9 个子域名服务**零中断**（仅重读配置）。
- conf 按模板生成后先 nginx -t，失败不 reload。
- 回滚：`rm /etc/nginx/conf.d/{kuma,pdf,note}.conf && nginx -t && systemctl reload nginx`，30 秒内。

### 决策点 D2：DNS 记录由谁加
- 方案 A（推荐）：Boss 在阿里云解析控制台手工加 3 条 A 记录（2 分钟），我验证。
- 方案 B：Boss 提供 AccessKey（写入 .env，600 权限），我用 CLI 代加。凭据面扩大，不主动推荐。

### 风险备注（不阻塞，仅记录）
1. frps 三端口监听 0.0.0.0，当前安全组兜底。若 Boss 期望纵深防御，可在 frps.toml 将 proxyBindAddr 改 127.0.0.1——属 NAS↔ECS frp 架构变更，超出本任务书，不动。
2. 通配符证书 2027-01-21 到期，与域名续期观察点（2026-12-24）同栈管理，acme cron 续期机制已有。

## 四、执行回执

**2026-11-13 D1 已批并执行，ECS 侧完成：**
1. 三 conf 落盘 /etc/nginx/conf.d/{kuma,pdf,note}.conf（暂存 md5 对照一致，644）
2. nginx -t 通过，systemctl reload 零中断
3. 本机强制解析验证（--resolve，不依赖 DNS）：
   - https://kuma → 302、https://pdf → 200、https://note → 401（严格 TLS 无 -k，逐项命中预期）
   - 80→443 跳转 301 三条全通；SNI 出示 *.ygxpro.online 通配符证书
4. 现有服务无回归：console/api 均 200
5. **DNS 已生效（Boss 2026-11-13 添加）**：权威侧（阿里 DoH）三条 A 记录均 → 47.119.177.194；三域名 HTTPS 全链路实测 kuma 302 / pdf 200 / note 401（严格 TLS）；80→443 301 全通；稳定性绕 DNS 直打 EIP 15/15。**执行回执已回写 WebDAV 任务书（PUT 204，双端 6272 字节 diff 一致），NAS 侧第四节可启动。**
   - 备注：ECS 本机内部 DNS 有负缓存残留（本机 curl 偶发 0.002s 瞬断），权威侧正常，公网不受影响，自然衰减无需处理。
