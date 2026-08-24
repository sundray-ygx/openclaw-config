# ECS 运维任务：续期 *.ygxpro.online 通配符证书（紧急）

> **生成时间**: 2026-08-24
> **执行环境**: 阿里云 ECS (47.119.177.194)，由 OpenClaw 执行
> **优先级**: 🔴 高 —— NAS 侧 Hermes 密钥拉取已被阻断，所有子域 HTTPS 过期
> **预计耗时**: 15-30 分钟

---

## 一、背景（为什么做）

- 通配符证书 `*.ygxpro.online`（ZeroSSL ECC，acme.sh 签发）已于 **2026-08-18 23:59:59 UTC 过期**
- 影响所有子域：vw（Vaultwarden）、console、nas、bill、pan、webdav
- NAS 侧后果：Hermes 的密钥加载脚本 `load_secrets.sh` 无法从 Vaultwarden 拉取密钥（已临时降级用 8/14 的缓存密钥，缓存仅到 VW 内部数据无变化为止）
- 证书签发方式：acme.sh + 阿里云 DNS API（RAM 子账号 `acme-dns`，凭证已持久化在 `~/.acme.sh/account.conf`）
- 部署方式：`--install-cert` 到 nginx，带自动 reload

## 二、诊断：自动续期为什么失效（先跑这步）

```bash
# 1. acme.sh 的 cron 任务是否存在
crontab -l | grep acme
# 期望: "0 0 * * * ~/.acme.sh/acme.sh --cron --home ~/.acme.sh" 类似行
# 如果没有 → 这就是根因，续期后要补 crontab

# 2. 手动触发一次续期看真实报错（dry-run 不动证书）
~/.acme.sh/acme.sh --cron --home ~/.acme.sh 2>&1 | tail -30

# 3. 查看续期日志（如果上一步有错误）
tail -50 ~/.acme.sh/*.log 2>/dev/null

# 4. 检查证书当前状态
~/.acme.sh/acme.sh --list
openssl x509 -in ~/.acme.sh/ygxpro.online_ecc/fullchain.cer -noout -dates 2>/dev/null
# （目录名可能是 *.ygxpro.online_ecc，先 ls ~/.acme.sh/ 确认）
```

**常见根因排序**：
1. crontab 里没有 acme.sh 任务（曾清理过 crontab）
2. 阿里云 RAM 子账号 acme-dns 的 AccessKey 被禁用/删除
3. ZeroSSL 账号注册过期（EAB 问题）
4. acme.sh 版本太老（API 变更）

## 三、续期执行

```bash
# 强制重新签发（DNS-01，全自动，无需人工）
~/.acme.sh/acme.sh --renew -d '*.ygxpro.online' --force --ecc

# 成功标志: "Cert success" + 新的 notAfter 日期（约 +90 天）

# install-cert 会自动执行 reloadcmd（如果当初配置了）
# 如果上面 renew 后 nginx 没自动 reload，手动：
nginx -t && nginx -s reload
```

如果 renew 报 Aliyun DNS API 错误（InvalidAccessKeyId 等）：

```bash
# 需要新的 RAM AccessKey（在阿里云控制台创建/启用，权限: AliyunDNSFullAccess）
export Ali_Key="<新的AccessKey ID>"
export Ali_Secret="<新的AccessKey Secret>"
~/.acme.sh/acme.sh --renew -d '*.ygxpro.online' --force --ecc
```

## 四、验证（必须全部通过）

```bash
# 1. ECS 本地验证新证书生效
echo | openssl s_client -connect 127.0.0.1:443 -servername vw.ygxpro.online 2>/dev/null | openssl x509 -noout -dates
# 期望: notAfter 在 ~11 月（+90天）

# 2. 确认 crontab 自动续期存在（防止 90 天后再过期）
crontab -l | grep acme
# 没有就补上:
# (crontab -l 2>/dev/null; echo "0 0 * * * ~/.acme.sh/acme.sh --cron --home ~/.acme.sh") | crontab -

# 3. 外部可达性
curl -sI https://vw.ygxpro.online/alive --max-time 10 | head -3
# 期望: HTTP 200
```

## 五、完成后反馈给 NAS 侧

ECS 执行完成后，NAS 侧需要做两个验证（Boss 通知小群，或直接在 NAS 终端跑）：

```bash
# NAS 上验证（会由小群执行）:
# 1. bw sync 恢复
bash /root/.hermes/scripts/load_secrets.sh
# 期望: "[secrets] Loaded secrets from Vaultwarden"（不再是 WARN 降级）

# 2. gateway 重启一次，确认走新密钥路径
systemctl restart hermes-gateway
```

## 六、回退方案

- 续期失败不影响现有服务（证书本来就过期了，不会更糟）
- nginx reload 失败：`nginx -t` 会拦截配置错误，不会中断服务
- 最坏情况：改用 HTTP-01 单域名证书临时顶 vw.ygxpro.online 一个子域

## 七、长期建议（本次顺手做）

```bash
# acme.sh 升级 + 开启自动升级（防止 API 变更导致静默失败）
~/.acme.sh/acme.sh --upgrade --auto-upgrade
```

另外建议在 NAS 侧加一个证书到期监控（小群会在 ECS 完成后配置：cron 每 7 天检查 vw.ygxpro.online 证书剩余天数 < 14 天就飞书告警）。
