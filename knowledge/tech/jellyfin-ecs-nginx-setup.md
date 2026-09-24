# ECS nginx 配置 jellyfin.ygxpro.online 反代（交接文档）

> 由 NAS 侧小群生成 2026-09-24。NAS 侧已完成：Jellyfin 容器部署(127.0.0.1:8096) + frpc 隧道 `[jellyfin] remote_port=8096`。ECS 侧只需做以下 3 步。

## 前置：DNS 解析

在域名 DNS 服务商处添加：

```
类型: A
主机记录: jellyfin
记录值: 47.119.177.194
TTL: 600
```

（api.ygxpro.online 已有同 IP 记录，可参照其配置）

## 步骤 1：nginx 站点配置

新建 `/etc/nginx/conf.d/jellyfin.conf`：

```nginx
server {
    listen 80;
    server_name jellyfin.ygxpro.online;

    # certbot 续期用
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    http2 on;
    server_name jellyfin.ygxpro.online;

    # 证书先注释，步骤2 certbot 签好后取消注释
    # ssl_certificate     /etc/letsencrypt/live/jellyfin.ygxpro.online/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/jellyfin.ygxpro.online/privkey.pem;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8096;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Jellyfin 必需：WebSocket
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 视频流必需：关闭缓冲
        proxy_buffering off;
    }
}
```

> 注意：frps 在 ECS 上监听的 8096 是 `0.0.0.0:8096`（frpc 隧道 remote_port=8096），nginx 走 `127.0.0.1:8096` 不冲突。

## 步骤 2：签发证书

```bash
# 若 certbot 未装: apt install certbot (或 yum install certbot)
mkdir -p /var/www/certbot
certbot certonly --webroot -w /var/www/certbot -d jellyfin.ygxpro.online --email <你的邮箱> --agree-tos

# 签发后取消 nginx 配置中 ssl_certificate 两行注释
nginx -t && systemctl reload nginx
```

## 步骤 3：验证

```bash
curl -s https://jellyfin.ygxpro.online/system/info/public
# 期望: {"LocalAddress":...,"ServerName":"Jellyfin-NAS","Version":"12.1.0",...,"StartupWizardCompleted":true}
```

## 手机 Infuse 配置（ECS 完成后）

1. Infuse → 添加文件共享 → Jellyfin
2. 地址填 `jellyfin.ygxpro.online`（https 自动识别）
3. 账号 `boss` / 密码见 NAS `/volume1/docker/jellyfin/admin-credentials.txt`
4. 局域网内也可直连 `http://<NAS内网IP>:8096`（更快，Infuse 会自动切换）

## 回滚

```bash
rm /etc/nginx/conf.d/jellyfin.conf && nginx -t && systemctl reload nginx
certbot delete --cert-name jellyfin.ygxpro.online
# NAS 侧: 删 frpc.toml 中 [jellyfin] 段并重启 frpc
```
