# *.ygxpro.online 通配符证书生成机制报告

> 核实日期：2026-10-19（ECS 本机只读实测）
> 范围：仅 ECS 本机；NAS 侧未涉及
> 性质：现状梳理报告，未做任何变更
> 姊妹篇：[acmesh-tool-deep-dive.md](./acmesh-tool-deep-dive.md)（acme.sh 工具本体深度解析）

## 1. 总览：全链路一张图

```
┌─────────────────────────────────────────────────────────────────┐
│  每日 22:06  root crontab                                        │
│  "/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh"         │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
              到达续期窗口？(Le_NextRenewTime=2026-10-22)
                           │ 是
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  acme.sh 发起 DNS-01 挑战（Le_Webroot='dns_ali'）                │
│  用 account.conf 里的 SAVED_Ali_Key/Secret 调阿里云 DNS API       │
│  自动添加 _acme-challenge.ygxpro.online TXT 记录                  │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Let's Encrypt (acme-v02.api.letsencrypt.org) 验证 TXT           │
│  签发新证书：CN=*.ygxpro.online + SAN: ygxpro.online (ECC ec-256) │
│  存入 /root/.acme.sh/*.ygxpro.online_ecc/                        │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  install-cert 部署（acme.sh 域名配置里的 install 钩子）：           │
│  fullchain → /etc/letsencrypt/live/ygxpro.online/fullchain.pem   │
│  privkey   → /etc/letsencrypt/live/ygxpro.online/privkey.pem     │
│  ReloadCmd → nginx -s reload                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  nginx 13 个 conf 引用 live/ygxpro.online 证书对外服务 443         │
│  api / console / cc / bill / vw / nas / pan / jellyfin / ...     │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 关键组件明细

### 2.1 签发工具与 CA
- 工具：acme.sh，home=`/root/.acme.sh`
- CA：Let's Encrypt 生产目录 `https://acme-v02.api.letsencrypt.org/directory`（ YE1 中级签发）
- 证书规格：ECC **ec-256**，通配符 `*.ygxpro.online` + 裸域 `ygxpro.online` 双 SAN
- 有效期 90 天，acme.sh 默认 60 天触发续期

### 2.2 域名验证（关键设计）
- 模式：**DNS-01 via `dns_ali` 插件**——通配符证书唯一可用的验证方式
- 阿里云 DNS API 凭据存于 `/root/.acme.sh/account.conf`（`SAVED_Ali_Key` / `SAVED_Ali_Secret`，明文保存，权限 root-only）
- 流程：acme.sh 调 API 写 TXT → 等待 DNS 生效（Le_DNSSleep 已配置）→ LE 验证 → API 删 TXT

### 2.3 自动续期触发
- crontab（root）：`6 22 * * * acme.sh --cron`，每日 22:06 扫描
- 日志：`/root/.acme.sh/acme.sh.log`（近期日志显示 cron 正常运行，无报错）
- 当前窗口：**下次续期 2026-10-22**，证书到期 2026-11-22，余量 30 天

### 2.4 部署与生效
- acme.sh 的 install-cert 机制把证书"安装"到 nginx 真实路径后执行 `nginx -s reload`
- 部署目录 `/etc/letsencrypt/live/ygxpro.online/` 只有 2 个文件（fullchain/privkey），干净
- ⚠️ 该路径虽在 letsencrypt 目录下，但**不是 certbot 管理**，是 acme.sh 的部署目标

### 2.5 消费方（nginx 引用清单）
正式生效（10 个）：
`newapi` `console` `cc` `bill` `vaultwarden` `hermes-studio` `nas` `pan` `jellyfin` `webdav`

遗留备份（3 个，不影响运行）：
`newapi.conf.bak-nas-migration` `newapi.conf.bak-probe` `bill.conf.bak.20260603_222931`

## 3. 发现的问题

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 1 | ~~vw.ygxpro.online 独立证书已过期~~ **已于 2026-10-19 清理**：三处目录移入 `/root/.trash-vw-cert-20260919/`，nginx -t 通过，vw 域名线上继续由通配符证书服务 | 无 | 已完成 |
| 2 | ~~acme.sh 无 NOTIFY_HOOK~~ **已于 2026-10-19 加装**：`--set-notify --notify-hook /root/scripts/utils/acme_notify.sh --notify-level 1`，失败推飞书红色卡片（复用 notify_feishu.py 统一入口，零网关依赖），成功静默 | 续期失败会在当天 22:06 后告警 | 已完成 |
| 3 | 阿里云 API 凭据**明文**存 account.conf | 依赖文件权限（600）保护；凭据泄露可劫持域名验证 | 低风险可接受；建议用 RAM 子账号最小权限 key |
| 4 | crontab 22:06 每日全量扫描 | 无（成本可忽略） | 无需处理 |

vw 遗留资产清单（待清理时用，合计约 80K）：
- `/root/.acme.sh/vw.ygxpro.online_ecc/`（含 cert/key/csr/conf + backup/nginx.conf）
- `/etc/letsencrypt/live/vw.ygxpro.online/`
- `/etc/letsencrypt/archive/vw.ygxpro.online/`

## 4. 故障排查手册

**看日志**：`tail -100 /root/.acme.sh/acme.sh.log`

**常见失败模式**：
1. **阿里云 API 凭据失效/欠费** → 日志出现 `dns_ali` 相关 error；检查 account.conf 的 Key 是否仍有效、域名解析是否还在该账号
2. **DNS TXT 未及时生效** → 日志 verification failed；可加大 `Le_DNSSleep`
3. **Let's Encrypt 限频**（每周同域名 5 张）→ 反复强制重签会触发；调试用 staging：`--server letsencrypt_test`
4. **nginx reload 失败** → 证书已落盘但旧配置语法错误时 reload 不生效；`nginx -t` 先验

**手动操作命令**（变更类，执行前走决策门）：
```bash
# 强制立即续期（测试用，注意 LE 限频）
"/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh" --force
# 只重部署不重签
"/root/.acme.sh"/acme.sh --install-cert -d '*.ygxpro.online' --ecc \
  --fullchain-file /etc/letsencrypt/live/ygxpro.online/fullchain.pem \
  --key-file /etc/letsencrypt/live/ygxpro.online/privkey.pem \
  --reloadcmd "nginx -s reload"
# 查看当前证书状态
"/root/.acme.sh"/acme.sh --list --home "/root/.acme.sh"
openssl x509 -in /etc/letsencrypt/live/ygxpro.online/fullchain.pem -noout -dates
```

## 5. 结论

机制整体健康：DNS-01 全自动闭环（cron → dns_ali → LE 签发 → install-cert → nginx reload），证书余量 30 天，日志无异常。原两个改进点（vw 遗留清理、续期失败告警钩子）已于 2026-10-19 完成：vw 三处目录移入 `/root/.trash-vw-cert-20260919/`，告警钩子 `acme_notify.sh` 已注册并实测送达飞书。稳定观察一周后备份目录可删。
