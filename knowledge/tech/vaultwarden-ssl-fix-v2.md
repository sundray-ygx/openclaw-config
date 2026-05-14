# 修复 Bitwarden iOS SSL 错误 (errSSLXCertChainInvalid -9816)

## 已确认的事实

- 浏览器（Safari/Chrome）能正常访问 https://vw.ygxpro.online ✅
- Bitwarden iOS App 报 SSL 错误 -9816 ❌
- ECS 上 fullchain.pem 包含 3 张证书，链完整 ✅
- Nginx ssl_certificate 指向 fullchain.pem ✅

## 根因分析

**Bitwarden iOS App 对自托管服务器有更严格的 TLS 校验。** 浏览器会自动通过 AIA (Authority Information Access) 补全缺失的中间证书，但 iOS App 不会。

虽然 ECS 本地检查链完整，但可能存在以下问题：

### 请逐一检查以下项目：

## 1. 检查 Nginx 是否发送了完整的证书链

```bash
# 从 ECS 本地检查（关键！）
echo | openssl s_client -connect 127.0.0.1:443 -servername vw.ygxpro.online -showcerts 2>&1 | grep -c "BEGIN CERTIFICATE"
echo "--- 证书详情 ---"
echo | openssl s_client -connect 127.0.0.1:443 -servername vw.ygxpro.online -showcerts 2>&1 | grep "s:\|i:"
```

应返回 **2 或 3** 张证书。如果只有 1，问题就在这里。

## 2. 检查 fullchain.pem 实际内容

```bash
grep -c "BEGIN CERTIFICATE" /etc/letsencrypt/live/vw.ygxpro.online/fullchain.pem
# 应为 2 或 3

# 查看每张证书的主题和签发者
awk '/BEGIN CERT/{n++} /END CERT/{print "Cert #"n; system("echo "$0" | openssl x509 -noout -subject -issuer 2>/dev/null")}' /etc/letsencrypt/live/vw.ygxpro.online/fullchain.pem
```

用这个更可靠的方式：
```bash
csplit -s -z -f /tmp/cert_ /etc/letsencrypt/live/vw.ygxpro.online/fullchain.pem '/-----BEGIN/' '{*}'
for f in /tmp/cert_*; do
  openssl x509 -noout -subject -issuer -in "$f" 2>/dev/null
  echo "---"
done
rm -f /tmp/cert_*
```

## 3. 修复方案：添加 ssl_stapling + ssl_trusted_certificate

即使证书链完整，添加 OCSP Stapling 可以帮助 iOS 客户端验证证书。

编辑 `/etc/nginx/conf.d/vaultwarden.conf`，在 443 server block 中添加：

```nginx
    # 在现有 ssl_* 配置后添加以下内容：
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/vw.ygxpro.online/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
```

然后：
```bash
nginx -t && nginx -s reload
```

## 4. 确认 Nginx 使用 http2 正确

检查当前的 listen 指令。在某些 Nginx 1.20 版本中，`listen 443 ssl http2` 可能需要调整为：

```nginx
    # Nginx 1.25.1+ 的新写法：
    # listen 443 ssl;
    # http2 on;
    
    # Nginx 1.20.x 的写法（当前应该用这个）：
    listen 443 ssl http2;
```

## 5. 如果以上都没问题，尝试重新签发证书

```bash
# 强制重新签发，确保生成新的完整证书链
certbot certonly --webroot -w /usr/share/nginx/html -d vw.ygxpro.online --force-renewal --non-interactive --agree-tos -m i@ygxpro.online

# 确认新证书链
grep -c "BEGIN CERTIFICATE" /etc/letsencrypt/live/vw.ygxpro.online/fullchain.pem

# 重载 nginx
nginx -t && nginx -s reload
```

## 6. 最终验证

```bash
# 从 ECS 本地验证
echo | openssl s_client -connect 127.0.0.1:443 -servername vw.ygxpro.online 2>&1 | grep "Verify return"
# 期望: Verify return code: 0 (ok)

# 检查 OCSP stapling
echo | openssl s_client -connect 127.0.0.1:443 -servername vw.ygxpro.online -status 2>&1 | grep "OCSP"
# 期望看到 OCSP Response Status: successful

# 外部验证
curl -sI https://vw.ygxpro.online
```

## 每步执行后报告结果
