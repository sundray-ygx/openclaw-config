# ECS 操作：通配符 SSL 证书 + Console 域名配置

> **目标**：申请 `*.ygxpro.online` 通配符证书，配置 `console.ygxpro.online` Nginx 反代，并将现有 `vw.ygxpro.online` 切换到通配符证书。
> **执行方**：OpenClaw
> **日期**：2026-05-20

---

## 前置条件确认

```bash
# 1. DNS 已生效
dig +short console.ygxpro.online
# 期望: 47.119.177.194

dig +short vw.ygxpro.online
# 期望: 47.119.177.194

# 2. FRP 隧道连通（NAS 侧会先完成 frpc 配置，此处确认）
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3200
# 期望: 200（前端页面）

# 3. 现有 vw 服务正常
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3011
# 期望: 200
```

如果 FRP 隧道不通（返回 000 或超时），说明 NAS 侧 frpc 还没配好，**暂停并报告**，等 NAS 侧完成后再继续。

---

## 阶段 1：安装 acme.sh + 申请通配符证书

### 1.1 安装 acme.sh（如已安装则跳过）

```bash
# 检查是否已安装
[ -d ~/.acme.sh ] && echo "ALREADY_INSTALLED" || echo "NEED_INSTALL"

# 安装（以 root 身份）
if [ ! -d ~/.acme.sh ]; then
  curl https://get.acme.sh | sh -s email=i@ygxpro.online
  source ~/.bashrc
fi

# 验证
~/.acme.sh/acme.sh --version
```

### 1.2 配置阿里云 DNS API

通配符证书 `*.ygxpro.online` 需要通过 DNS 验证。使用阿里云 DNS API 实现自动验证。

RAM 子账号 `acme-dns`（仅 AliyunDNSFullAccess 权限）已创建。

```bash
# 设置环境变量（acme.sh 会自动持久化到 ~/.acme.sh/account.conf）
export Ali_Key="LTAI_REDACTED"
export Ali_Secret="ClOgEwdu02ezLDzAccx7aaJIJLSoVX"
```

> ⚠️ 这两个值会被 acme.sh 写入 `~/.acme.sh/account.conf`，续期时自动读取，无需再次设置。

### 1.3 申请通配符证书

```bash
# 申请 *.ygxpro.online + ygxpro.online（裸域也覆盖）
~/.acme.sh/acme.sh --issue \
  --dns dns_ali \
  -d '*.ygxpro.online' \
  -d ygxpro.online \
  --keylength ec-256 \
  --force

# 成功后会显示证书路径，确认：
ls -la ~/.acme.sh/\*.ygxpro.online_ecc/
```

### 1.4 安装证书到 Nginx 可用路径

```bash
# 创建证书目录
mkdir -p /etc/letsencrypt/live/ygxpro.online/

# 安装（acme.sh 会自动管理续期）
~/.acme.sh/acme.sh --install-cert -d '*.ygxpro.online' \
  --ecc \
  --fullchain-file /etc/letsencrypt/live/ygxpro.online/fullchain.pem \
  --key-file /etc/letsencrypt/live/ygxpro.online/privkey.pem \
  --reloadcmd "nginx -s reload"

# 验证
ls -la /etc/letsencrypt/live/ygxpro.online/
openssl x509 -in /etc/letsencrypt/live/ygxpro.online/fullchain.pem -noout -text | grep -A1 "Subject Alternative Name"
# 应看到: DNS:*.ygxpro.online, DNS:ygxpro.online
```

---

## 阶段 2：切换 vw.ygxpro.online 到通配符证书

### 2.1 备份现有配置

```bash
cp /etc/nginx/conf.d/vaultwarden.conf /etc/nginx/conf.d/vaultwarden.conf.bak.$(date +%Y%m%d)
```

### 2.2 更新证书路径

```bash
# 将 SSL 证书路径从单域名切换到通配符
sed -i 's|/etc/letsencrypt/live/vw.ygxpro.online/fullchain.pem|/etc/letsencrypt/live/ygxpro.online/fullchain.pem|' /etc/nginx/conf.d/vaultwarden.conf
sed -i 's|/etc/letsencrypt/live/vw.ygxpro.online/privkey.pem|/etc/letsencrypt/live/ygxpro.online/privkey.pem|' /etc/nginx/conf.d/vaultwarden.conf

# 验证修改
grep ssl_certificate /etc/nginx/conf.d/vaultwarden.conf
```

期望输出：
```
ssl_certificate     /etc/letsencrypt/live/ygxpro.online/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/ygxpro.online/privkey.pem;
```

### 2.3 测试并重载

```bash
nginx -t && nginx -s reload

# 验证 vw 仍然可用
curl -sI https://vw.ygxpro.online | head -5
# 期望: HTTP/2 200

# 验证证书是通配符证书
echo | openssl s_client -connect vw.ygxpro.online:443 -servername vw.ygxpro.online 2>/dev/null \
  | openssl x509 -noout -subject -dates
# 期望: CN = *.ygxpro.online
```

### 2.4 清理旧证书续期任务

```bash
# 查看现有 crontab
crontab -l

# 如果有旧的 certbot vw 续期任务，移除（acme.sh 会接管续期）
# 将 certbot 的 crontab 行删除，只保留 acme.sh 的自动续期
# acme.sh 安装时会自动添加 crontab，确认：
crontab -l | grep acme
# 期望看到类似: "0 0 * * * ~/.acme.sh/acme.sh --cron --home ~/.acme.sh"
```

> **注意**：acme.sh 安装时已自动创建 cron 续期任务。旧的 certbot 续期 crontab 可以移除。

---

## 阶段 3：配置 console.ygxpro.online Nginx 反代

### 3.1 创建 Nginx 配置

创建 `/etc/nginx/conf.d/console.conf`：

```nginx
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name console.ygxpro.online;

    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name console.ygxpro.online;

    # 通配符证书
    ssl_certificate     /etc/letsencrypt/live/ygxpro.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ygxpro.online/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 反代到 FRP 隧道（NAS 前端容器 :3200）
    location / {
        proxy_pass http://127.0.0.1:3200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（Vite HMR 等）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3.2 测试并重载

```bash
nginx -t && nginx -s reload
```

### 3.3 验证

```bash
# HTTPS 访问
curl -sI https://console.ygxpro.online | head -5
# 期望: HTTP/2 200

# 证书验证
echo | openssl s_client -connect console.ygxpro.online:443 -servername console.ygxpro.online 2>/dev/null \
  | openssl x509 -noout -subject -dates
# 期望: CN = *.ygxpro.online

# 页面内容（确认返回的是 Vue SPA）
curl -s https://console.ygxpro.online | head -20
# 期望: HTML 包含 Vue app 内容
```

---

## 阶段 4：最终验证清单

```bash
echo "=== 1. 通配符证书 ==="
echo | openssl s_client -connect console.ygxpro.online:443 -servername console.ygxpro.online 2>/dev/null \
  | openssl x509 -noout -subject -dates

echo ""
echo "=== 2. console.ygxpro.online ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" https://console.ygxpro.online

echo ""
echo "=== 3. vw.ygxpro.online (已切换到通配符) ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" https://vw.ygxpro.online

echo ""
echo "=== 4. acme.sh 续期 cron ==="
crontab -l | grep acme

echo ""
echo "=== 5. Nginx 配置检查 ==="
nginx -t 2>&1
```

所有检查通过即完成。

---

## 回滚方案

如果出问题，可以回退 vw 到原证书：

```bash
cp /etc/nginx/conf.d/vaultwarden.conf.bak.YYYYMMDD /etc/nginx/conf.d/vaultwarden.conf
nginx -t && nginx -s reload
```

## 注意事项

- **不要修改** Nginx 已有的其他配置文件
- **不要删除**旧的 `/etc/letsencrypt/live/vw.ygxpro.online/` 目录，留作回滚
- acme.sh 通配符证书自动续期依赖阿里云 DNS API，确保 AccessKey 长期有效
- 如果 AccessKey 过期，续期会失败，届时需要更新 `~/.acme.sh/account.conf` 中的 `Ali_Key` 和 `Ali_Secret`
