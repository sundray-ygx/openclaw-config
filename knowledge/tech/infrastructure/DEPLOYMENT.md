# hermes-bridge + hermes-mobile 部署手册

> [REQ-hermes_bridge / REQ-hermes_mobile] - 2026-09-20
> 零侵入扩展：hermes-web-ui (Studio) 官方镜像不改动，通过其 Webhook 与 HTTP/Socket.IO API 补齐
> ① 会话事件 → 飞书通知 ② 手机网页访问（替代收费 APP，复用 cc.ygxpro.online）。

## 架构总览

```
                                   ┌─────────────── NAS (192.168.0.113) ───────────────┐
                                   │                                                    │
claude 会话事件 ──→ hermes-studio :8648 ── webhook POST ──→ hermes-bridge :3345 ──→ 飞书群
                   (Docker 容器)                                  (node, 零依赖)      机器人
                                   │                                                    │
                                   │  hermes-mobile :3346 (静态页 + socket.io.min.js)   │
                                   └──────────────┬─────────────────────────────────────┘
                                                  │ frpc 隧道
                                                  ▼
                                   ECS frps remote_port: 8648 / 3345 / 3346
                                                  │
手机浏览器 ── https://cc.ygxpro.online ──→ ECS nginx 443
    location /           → proxy 127.0.0.1:3346   (移动页)
    location /api/       → proxy 127.0.0.1:8648   (Studio API，同域无 CORS)
    location /socket.io/ → proxy 127.0.0.1:8648   (WebSocket upgrade)
    location /health     → proxy 127.0.0.1:3345   (bridge 探活，可选)
```

## 组件一：hermes-bridge（webhook → 飞书）

### 文件
| 文件 | 说明 |
|---|---|
| `bridge.js` | 服务主体（零 npm 依赖，node 内置模块） |
| `config.json` | 端口/事件开关/飞书地址/contentMaxChars |
| `deploy.sh` | 部署脚本（lsof→busybox netstat→启动→健康检查） |

### 环境变量（敏感项不落盘）
| 变量 | 说明 |
|---|---|
| `FEISHU_WEBHOOK_URL` | 飞书群机器人 webhook 地址（也可写 config.json 的 feishuWebhookUrl） |
| `WEBHOOK_SECRET` | 与 Studio webhook endpoint 的 secret 一致；不配则跳过验签 |

### Studio 侧配置（PC 打开 Studio → 设置 → Webhook）
1. 新建 endpoint：
   - URL: `http://192.168.0.113:3345/hook`（bridge 与 Studio 同机；如配了 secret，同步填入 bridge 的 `WEBHOOK_SECRET`）
   - ⚠️ **必须勾选"允许私网地址"(allow_private_network)**，否则 Studio 会拒绝向内网 IP 投递（url-safety 默认封锁私网）
   - 事件勾选：`chat.run.completed` / `chat.run.failed` / `chat.approval.requested`（默认三项，bridge 侧 config.json 还有 12 事件全量开关）
   - 勾选 include_content（通知带内容摘要）
2. 点 endpoint 的"测试"按钮 → 飞书群应收到卡片

### 事件处理逻辑（bridge 内置）
- `chat.run.completed` → 绿色卡片 ✅ 会话任务完成（Agent/会话ID/内容摘要/深链）
- `chat.run.failed` → 红色卡片 ❌（含 error_kind）
- `chat.approval.requested` → 橙色卡片 ⏸️ 等待审批
- 深链格式：`https://cc.ygxpro.online/?id=<session_id>` → 手机点开直达会话
- 其余事件默认关闭（config.json → events 节点可开）

## 组件二：hermes-mobile（移动网页端）

### 文件
| 文件 | 说明 |
|---|---|
| `public/mobile.html` | 单文件 SPA（登录/列表/详情/发送/中断/审批/深链） |
| `public/socket.io.min.js` | socket.io client 4.8.3（与 Studio 服务端同版本，从容器拷出，无 CDN 依赖） |
| `server.js` | 零依赖静态服务 :3346（no-cache，目录穿越防护，/health） |
| `deploy.sh` | 部署脚本 |

### 认证说明（重要发现）
- Studio API/Socket 用**用户 JWT**（不是 .token！`.token` 仅 loopback 白名单路径可用，实测 API 401）
- 移动页走 `POST /api/auth/login` 用户名密码换 JWT（admin / ygx 账号），localStorage 存 30 天
- JWT payload: `{sub, username, role, type:'access', aud:'hermes-studio', exp}` HS256
- JWT secret = `AUTH_JWT_SECRET` 环境变量或 `.token` 文件内容；持有 secret 可自签 JWT（已实测）
- Socket: `io({ auth: { token: JWT }, query: { profile: 'default' } })` → `/chat-run` 命名空间

### 功能（v1）
1. 登录页（密码错/过期自动回登录）
2. 会话列表（运行中置顶+旋转动画、agent 标签、预览、token 用量、30s 兜底轮询）
3. 会话详情（resume 历史消息、流式增量渲染、发送、中断、审批卡片允许/拒绝）
4. 深链 `?id=<sessionId>`（IM 推送直达）
5. 连接状态点（socket.io 自动重连）

### 已实测通过的链路（NAS 本机）
- ✅ JWT 打 `/api/studio/sessions` → 200（含 claude/coding_agent 会话字段）
- ✅ socket.io-client 4.8.3 连 `/chat-run` → `resume` → 收 `resumed`（14 条历史消息）
- ✅ `session.activity.snapshot` 正常推送
- ✅ 3346 静态页 200；socket.io.min.js 版本匹配 4.8.3
- ✅ bridge：验签矩阵（正确签名 200/错误 401/缺失 401）、事件过滤、卡片构造

## ECS 侧操作（你执行）

### 1. frpc（NAS，我已改好则跳过）
`/volume1/Frp/frpc.toml` 追加（cc-manager 的 3344 段删除）：
```toml
[hermes-mobile]
name = "hermes-mobile"
type = "tcp"
local_ip = "127.0.0.1"
local_port = 3346
remote_port = 3346
```
（8648 段已存在，无需动；3345 是 Studio→bridge 的内网直连，不经 FRP）

### 2. ECS nginx：改 cc.ygxpro.online 的 server 块
```nginx
server {
    listen 443 ssl http2;
    server_name cc.ygxpro.online;
    ssl_certificate     /path/to/ygxpro.online.cert;   # 与现有一致
    ssl_certificate_key /path/to/ygxpro.online.key;

    # 移动页（NAS 静态服务）
    location / {
        proxy_pass http://127.0.0.1:3346;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Studio API（同域反代 → 无 CORS 问题）
    location /api/ {
        proxy_pass http://127.0.0.1:8648;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }

    # Socket.IO（必须支持 upgrade）
    location /socket.io/ {
        proxy_pass http://127.0.0.1:8648;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }

    # bridge 探活（console 健康面板可选接）
    location /health {
        proxy_pass http://127.0.0.1:3345;
    }
}
server {
    listen 80;
    server_name cc.ygxpro.online;
    return 301 https://$host$request_uri;
}
```
然后 `nginx -t && systemctl reload nginx`。

**注意**：原 server 块里如果 3344（cc-manager）相关内容可整体替换。

## cc-manager 停用（源码归档，服务停止）

```bash
# 1. 停服务
netstat -tlnp | grep 3344   # 找 PID
kill <PID>

# 2. frpc 删除 [cc-manager] 段（/volume1/Frp/frpc.toml）→ 重启 frpc
# 3. 归档（服务端代码已全部在本目录，直接打 tar）
cd /volume1/hermes-data/projects/tools
tar czf archive/cc-manager-archived-20260920.tar.gz cc-manager/ --exclude cc-manager/node_modules
# 4. console 菜单 CC Manager 链接不变（域名复用，自动指向移动页）
```

## 回滚

- 移动页异常：ECS nginx `location /` 的 3346 改回 3344（cc-manager 未删的话）
- bridge 异常：Studio Webhook 设置里禁用 endpoint 即可（Studio 零影响）
- 全链路回滚：删除两个目录 + frpc 删两段 + nginx 还原
