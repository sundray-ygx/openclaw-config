# 修复 Vaultwarden SSL 证书链

## 问题

iPhone Bitwarden App 报错：`SSL 错误 -9816 (errSSLXCertChainInvalid)` — 证书链不完整。
浏览器能正常访问（浏览器会自动补全中间证书），但 iOS App 要求完整的证书链。

## 诊断步骤

### 1. 检查 fullchain.pem 是否包含完整证书链

```bash
openssl crl2pkcs7 -nocrl -certfile /etc/letsencrypt/live/vw.ygxpro.online/fullchain.pem | openssl pkcs7 -print_certs -noout
```

应显示 **2 张证书**（服务器证书 + Let's Encrypt R12 中间证书）。如果只显示 1 张，说明 fullchain.pem 不完整。

### 2. 检查 chain.pem（中间证书）

```bash
cat /etc/letsencrypt/live/vw.ygxpro.online/chain.pem | openssl x509 -noout -subject -issuer
```

### 3. 检查 Nginx 配置指向

```bash
grep ssl_certificate /etc/nginx/conf.d/vaultwarden.conf
```

**必须指向 `fullchain.pem`，不能是 `cert.pem`**。

## 修复

### 情况 A：Nginx 配置指向了 cert.pem（只有服务器证书，没有中间证书）

编辑 `/etc/nginx/conf.d/vaultwarden.conf`，修改为：

```nginx
ssl_certificate     /etc/letsencrypt/live/vw.ygxpro.online/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/vw.ygxpro.online/privkey.pem;
```

然后：

```bash
nginx -t && nginx -s reload
```

### 情况 B：fullchain.pem 本身不完整

```bash
cd /etc/letsencrypt/live/vw.ygxpro.online/
cp fullchain.pem fullchain.pem.bak
cat cert.pem chain.pem > fullchain.pem
nginx -t && nginx -s reload
```

## 验证

```bash
# 1. 检查证书链中证书数量（应为 2 或 3）
echo | openssl s_client -connect localhost:443 -servername vw.ygxpro.online -showcerts 2>&1 | grep -c "BEGIN CERTIFICATE"

# 2. 验证证书链完整性
echo | openssl s_client -connect localhost:443 -servername vw.ygxpro.online 2>&1 | grep "Verify return"
# 期望: Verify return code: 0 (ok)

# 3. 外部验证
curl -sI https://vw.ygxpro.online | head -3
```

完成后请报告结果。
