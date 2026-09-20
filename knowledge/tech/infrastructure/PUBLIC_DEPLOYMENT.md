# 公网部署手册 — cc.ygxpro.online

> [REQ-public_exposure] - 2026-09-20
> 目标：将 NAS 上的 cc-manager 通过自有 FRP 隧道暴露为 `https://cc.ygxpro.online`，
> 并在 console 个人数据中心加入口菜单。
> 架构与 console/nas 子域完全一致：`浏览器 → ECS nginx (443/TLS) → ECS frps remote_port → frpc 隧道 → NAS:3344`

## 链路总览

```
PC/手机浏览器
    │ https://cc.ygxpro.online (443)
    ▼
ECS 47.119.177.194  nginx  ← 你需要在这里加一个 server 块（见下）
    │ proxy_pass http://127.0.0.1:3344
    ▼
ECS frps（监听 remote_port 3344，frpc 已注册）
    │ FRP 隧道
    ▼
NAS 127.0.0.1:3344  cc-manager (node server.js, token 鉴权已启用)
```

**安全说明**：ECS 安全组**无需**开放 3344/TCP。流量走 nginx 443 → ECS 本机回环 → frps。
与 console.ygxpro.online(→3200)、nas.ygxpro.online 的模式一致。实测：3011/5000 是"安全组直通端口"，
3200/3300 是"nginx 反代端口"（安全组关闭但 443 可访问），cc-manager 走后者。

## 已完成（NAS 侧，我已做完）

| 项 | 状态 |
|----|------|
| cc-manager Token 鉴权（HTTP 401 + WS close 4401，已实测） | ✅ |
| `frpc.toml` 追加 `[cc-manager]` 隧道（remote_port 3344），frpc 已重启加载 | ✅ |
| console 菜单加 `🤖 CC Manager`（System 组，新窗口打开） | ✅ |
| console 服务卡片 + `/api/health` 探活（实测 online 94ms） | ✅ |
| console 前端已重建部署，公网 200 | ✅ |
| Token 值（config.json → auth.token） | `32e0179ceadeee0a2284801b89aacbabba07ff44840f23f7` |

## 待你操作（ECS + DNS，共 2 步）

### 步骤 1：DNS 解析

在你的域名 DNS 管理处（与现有子域同一位置）添加：

```
类型: A
主机记录: cc
记录值: 47.119.177.194
TTL: 默认
```

### 步骤 2：ECS nginx 加 server 块

SSH 到 ECS（47.119.177.194），参照现有 console/nas 的 server 块位置，新增：

```nginx
# /etc/nginx/conf.d/cc.conf  或你的 vhost 目录（与 console.ygxpro.online 同级）

server {
    listen 443 ssl http2;
    server_name cc.ygxpro.online;

    # 证书路径与 console/nas 子域保持一致（通配符证书则完全相同）
    ssl_certificate     /path/to/your/ygxpro.online.cert;   # ← 改成实际路径
    ssl_certificate_key /path/to/your/ygxpro.online.key;    # ← 改成实际路径

    # ⚠️ cc-manager 监听的是 TLS（自签证书），上游必须用 https 语义转发，
    # 用 http 会得到 Empty reply → nginx 502（2026-09-20 实踩坑）
    location / {
        proxy_pass https://127.0.0.1:3344;
        proxy_ssl_verify off;   # 自签证书，不校验；客户端 TLS 仍在 nginx 终结
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（终端实时输出必须）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 终端空闲不断流：拉长读超时（AI 长时间思考不输出时防断线）
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering off;          # 终端流式输出必须关闭缓冲
    }
}

server {
    listen 80;
    server_name cc.ygxpro.online;
    return 301 https://$host$request_uri;
}
```

然后：

```bash
nginx -t && systemctl reload nginx
```

**验证 frps 是否已注册 3344**（在 ECS 上执行一次，关键检查点）：

```bash
ss -tlnp | grep 3344
```

- 有输出（`*:3344` 或 `0.0.0.0:3344` LISTEN）→ frps 已注册，浏览器直接可用
- 无输出 → frps 端未注册，把 `ss` 输出发我，可能 frps 有 `allowPorts` 限制，我改 remote_port 换一个允许的端口

### 步骤 3（如果你用 acme/certbot 签发单域名证书）

通配符证书（`*.ygxpro.online`）则跳过。否则为新子域补签：

```bash
# acme.sh 示例（DNS API 方式，与你现有子域一致）
acme.sh --issue --dns dns_dp -d cc.ygxpro.online \
  --keypath /path/to/cc.key --fullchainpath /path/to/cc.cert
```

## 验收清单（DNS + nginx 生效后）

| 检查 | 预期 |
|------|------|
| 手机 4G（关 Wi-Fi）打开 `https://cc.ygxpro.online` | 弹出令牌输入框 |
| 输入 token 后 | 进入会话列表页 |
| 创建会话 → claude 自动启动 → 终端可交互 | 正常 |
| 不输 token / 输错 token | API 401，WS 断开 4401 |
| console.ygxpro.online 侧栏 System 组 | 出现 `🤖 CC Manager`，点击新窗口打开 |
| console 首页服务卡片 | CC Manager 显示在线（绿点/延迟） |

## 回滚

1. ECS：删除 cc.conf + `nginx -s reload`；DNS 删除 A 记录
2. NAS：`frpc.toml` 删除 `[cc-manager]` 段并重启 frpc（备份在 `/volume1/Frp/frpc.toml.bak.20260920`）
3. cc-manager 鉴权保留（内网使用也要求 token，属预期）；如需关闭：config.json 删除 `auth` 节并重启

## 已知边界

- token 存浏览器 localStorage，公用电脑上使用后建议点"退出"前清 localStorage（或换 token）
- token 即全部权限（可执行 NAS 任意命令），请勿在聊天记录/截图中外泄；泄露后改 `config.json` 的 `auth.token` 重启即可
- frpc 重启瞬断所有隧道几秒属正常（本次已实际验证 console/vw 自动恢复）
