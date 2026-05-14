# Vaultwarden Nginx 反向代理 + SSL 配置

## 任务目标

为 Vaultwarden 密码管理服务配置 Nginx 反向代理和 Let's Encrypt SSL 证书，实现 `https://vw.ygxpro.online` 的 HTTPS 访问。

## 背景

- 本机运行 Nginx，frp 客户端已将 NAS 上的 Vaultwarden 通过 TCP 隧道映射到本机
- HTTP API：`localhost:3011`
- WebSocket 通知：`localhost:3012`
- 域名 `vw.ygxpro.online` 已解析到本机 IP `47.119.177.194`

## 执行步骤

### 1. 确认 DNS 已生效

```bash
dig +short vw.ygxpro.online
```

必须返回 `47.119.177.194`。未生效则等待重试，**不要继续**。

### 2. 确认 frp 隧道连通

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3011
```

应返回 `200`。返回 `000` 或超时则 frp 隧道有问题，**停止并报告**。

### 3. 安装 Certbot（如未安装）

```bash
which certbot && certbot --version
```

未安装则执行：

```bash
# CentOS / Alibaba Cloud Linux:
yum install -y certbot python3-certbot-nginx

# Ubuntu / Debian:
# apt install -y certbot python3-certbot-nginx
```

### 4. 创建 HTTP-only 的 Nginx 配置（先用于签证书）

创建 `/etc/nginx/conf.d/vaultwarden.conf`：

```nginx
server {
    listen 80;
    server_name vw.ygxpro.online;

    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
```

```bash
mkdir -p /usr/share/nginx/html
nginx -t && nginx -s reload
```

### 5. 签发 SSL 证书

```bash
certbot certonly --webroot \
  -w /usr/share/nginx/html \
  -d vw.ygxpro.online \
  --non-interactive \
  --agree-tos \
  -m i@ygxpro.online
```

验证证书：

```bash
ls -la /etc/letsencrypt/live/vw.ygxpro.online/
```

应包含 `fullchain.pem` 和 `privkey.pem`。

### 6. 补全完整 Nginx 配置（HTTP + HTTPS + WebSocket）

将 `/etc/nginx/conf.d/vaultwarden.conf` 替换为完整内容：

```nginx
server {
    listen 80;
    server_name vw.ygxpro.online;

    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name vw.ygxpro.online;

    ssl_certificate     /etc/letsencrypt/live/vw.ygxpro.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vw.ygxpro.online/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 525M;

    location / {
        proxy_pass http://127.0.0.1:3011;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /notifications/hub {
        proxy_pass http://127.0.0.1:3012;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /notifications/hub/negotiate {
        proxy_pass http://127.0.0.1:3011;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

重载：

```bash
nginx -t && nginx -s reload
```

### 7. 设置证书自动续期

```bash
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --deploy-hook 'nginx -s reload'") | crontab -
crontab -l
```

确认输出包含 certbot 续期任务。

### 8. 最终验证

```bash
# HTTPS 访问
curl -sI https://vw.ygxpro.online | head -5

# 证书信息（确认 Let's Encrypt 且未过期）
echo | openssl s_client -connect vw.ygxpro.online:443 -servername vw.ygxpro.online 2>/dev/null \
  | openssl x509 -noout -subject -dates
```

## 预期结果

- `https://vw.ygxpro.online` → Vaultwarden Web Vault 页面（HTTP 200）
- SSL 证书：Let's Encrypt，90 天有效期，已配置自动续期
- WebSocket `/notifications/hub` 可达

## 注意事项

- **不要修改** Nginx 已有的其他配置文件
- certbot 签证书失败时，检查：DNS 是否生效、80 端口是否被安全组放行
- 每步先验证再继续，遇到错误 **停止并报告**
