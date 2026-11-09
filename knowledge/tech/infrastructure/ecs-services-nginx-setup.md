# ECS 操作：新增 4 个服务的 Nginx 反代配置

> **前置条件**：通配符证书 `*.ygxpro.online` 已申请并安装到 `/etc/letsencrypt/live/ygxpro.online/`（上一份文档已完成）
> **执行方**：OpenClaw
> **日期**：2026-05-21

---

## 前置检查

```bash
# 确认通配符证书存在
ls -la /etc/letsencrypt/live/ygxpro.online/fullchain.pem /etc/letsencrypt/live/ygxpro.online/privkey.pem

# 确认各 FRP 隧道连通（nas/aliyunpan/webdav 已有隧道，bill 跑在 ECS 本地）
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000   # DSM (FRP隧道)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000   # Bill Import (ECS本地)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9080   # Aliyun Pan (FRP隧道)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5005   # WebDAV (FRP隧道)
```

所有应返回 HTTP 状态码（200/301/302/401 等均可，不返回 000 即代表隧道通）。如有返回 000 的，**停止并报告**。

---

## 服务 1：nas.ygxpro.online → DSM 管理后台

### 说明
- FRP 隧道：NAS:5000 → ECS:5000（已存在）
- DSM 默认 HTTPS 在 5001，但通过 FRP 映射的是 5000（HTTP）
- DSM 有自己的登录认证，不需要额外保护

### 创建 `/etc/nginx/conf.d/nas.conf`

```nginx
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name nas.ygxpro.online;
    return 301 https://$host$request_uri;
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name nas.ygxpro.online;

    ssl_certificate     /etc/letsencrypt/live/ygxpro.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ygxpro.online/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 0;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }
}
```

---

## 服务 2：bill.ygxpro.online → 账单导入

### 说明
- 服务运行在 ECS 本地 :8000（systemd 服务 bill-import）
- 无需 FRP 隧道，直接反代本地端口

### 创建 `/etc/nginx/conf.d/bill.conf`

```nginx
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name bill.ygxpro.online;
    return 301 https://$host$request_uri;
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name bill.ygxpro.online;

    ssl_certificate     /etc/letsencrypt/live/ygxpro.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ygxpro.online/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 服务 3：pan.ygxpro.online → 阿里云盘 WebDAV

### 说明
- FRP 隧道：NAS:9080 → ECS:9080（已存在）

### 创建 `/etc/nginx/conf.d/pan.conf`

```nginx
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name pan.ygxpro.online;
    return 301 https://$host$request_uri;
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name pan.ygxpro.online;

    ssl_certificate     /etc/letsencrypt/live/ygxpro.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ygxpro.online/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 0;

    location / {
        proxy_pass http://127.0.0.1:9080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }
}
```

---

## 服务 4：webdav.ygxpro.online → NAS WebDAV

### 说明
- FRP 隧道：NAS:5005 → ECS:5005（已存在）
- WebDAV 需要支持 PUT/DELETE/PROPFIND 等 WebDAV 方法

### 创建 `/etc/nginx/conf.d/webdav.conf`

```nginx
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name webdav.ygxpro.online;
    return 301 https://$host$request_uri;
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name webdav.ygxpro.online;

    ssl_certificate     /etc/letsencrypt/live/ygxpro.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ygxpro.online/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 0;

    # WebDAV 方法支持
    if ($request_method !~ ^(GET|HEAD|POST|PUT|DELETE|OPTIONS|PROPFIND|PROPPATCH|MKCOL|COPY|MOVE|LOCK|UNLOCK)$ ) {
        return 405;
    }

    location / {
        proxy_pass http://127.0.0.1:5005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;

        # WebDAV 需要 pass-through body
        proxy_request_buffering off;
    }
}
```

---

## 执行步骤

### 1. 一次性创建所有配置文件

将上面 4 个 server block 分别写入对应文件：

```bash
# 确认目标目录
ls -la /etc/nginx/conf.d/

# 创建 4 个配置文件（复制上面各段内容）
# 文件列表：
# /etc/nginx/conf.d/nas.conf
# /etc/nginx/conf.d/bill.conf
# /etc/nginx/conf.d/pan.conf
# /etc/nginx/conf.d/webdav.conf
```

### 2. 测试 Nginx 配置

```bash
nginx -t
```

必须输出 `syntax is ok` 和 `test is successful`。

### 3. 重载 Nginx

```bash
nginx -s reload
```

### 4. 验证所有服务

```bash
echo "=== nas.ygxpro.online ==="
curl -sI --max-time 10 https://nas.ygxpro.online | head -5

echo ""
echo "=== bill.ygxpro.online ==="
curl -sI --max-time 10 https://bill.ygxpro.online | head -5

echo ""
echo "=== pan.ygxpro.online ==="
curl -sI --max-time 10 https://pan.ygxpro.online | head -5

echo ""
echo "=== webdav.ygxpro.online ==="
curl -sI --max-time 10 https://webdav.ygxpro.online | head -5
```

期望：每个都返回 HTTP/2 响应（200/301/302/401 均可），证书统一为 `*.ygxpro.online`。

---

## DNS 确认

以下 4 个域名需要 A 记录指向 `47.119.177.194`（Boss 已确认 console 的 DNS 已配，请确认这 4 个是否也已配置）：

| 域名 | A 记录 → 47.119.177.194 |
|------|------------------------|
| nas.ygxpro.online | 需确认 |
| bill.ygxpro.online | 需确认 |
| pan.ygxpro.online | 需确认 |
| webdav.ygxpro.online | 需确认 |

如果未配置，需要先在阿里云 DNS 控制台添加，否则域名无法解析。

---

## 注意事项

- 4 个配置文件全部使用同一个通配符证书路径，无需为每个子域名单独申请
- **不要修改** `vaultwarden.conf` 和 `console.conf`（已有配置）
- 所有 80 端口请求自动 301 到 HTTPS
- bill.ygxpro.online 反代的是 ECS 本地 :8000（不是 FRP 隧道）
