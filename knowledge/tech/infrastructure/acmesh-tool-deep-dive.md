# acme.sh 工具深度解析：问题、场景、原理与运维

> 撰写：2026-10-19 ｜ 本机实测：acme.sh v3.1.7（ECS /root/.acme.sh）
> 姊妹篇：[ygxpro-wildcard-cert-mechanism.md](./ygxpro-wildcard-cert-mechanism.md)（本机 *.ygxpro.online 证书机制梳理）——本文讲"这把枪"，姊妹篇讲"子弹怎么上膛"

## 1. 它解决什么问题

### 1.1 时代背景
HTTPS 全站化后，证书成了每个站点的刚性需求，但 2015 年前的问题链条是：

```
传统 CA 签发（收费、人工审核、1-2年有效期）
  → 证书贵（通配符数百~数千元/年）
  → 签发慢（人工验证域名所有权，小时~天级）
  → 续期靠人记（过期 = 线上告警/用户流失，是经典事故来源）
  → 运维无法自动化（没有机器可读的标准协议）
```

**核心矛盾：证书本质是"自动化基础设施里的人工环节"。**

### 1.2 ACME 协议的解法（RFC 8555，2019）
Let's Encrypt（ISRG 非营利组织）推出两样东西：
- **免费 CA**：域名验证型（DV）证书零成本签发，90 天短有效期
- **ACME 协议**：机器对机器的证书签发标准——注册账户、证明域名所有权、签发、续期全流程 API 化

短有效期是**有意设计**：逼迫自动化（90 天内不自动化，手工续期能把人逼疯），同时缩小失窃证书的暴露窗口。

### 1.3 acme.sh 在生态中的位置
ACME 只是协议，还需要一个**客户端**替你和 CA 对话。acme.sh 是其中部署量最大的实现之一（GitHub 42k+ star），定位：**纯 Shell、零依赖、单文件、覆盖插件最全**。

**一句话：acme.sh 把"证书生命周期管理"从人工事务变成了无人值守的 cron 任务。**

## 2. 核心概念速览

| 概念 | 含义 | 本机对应 |
|---|---|---|
| CA | 签发机构 | Let's Encrypt |
| ACME 账户 | 客户端在 CA 的身份（密钥对+邮箱） | `account.conf` + `ca/` 目录 |
| 订单 Order | 一次签发请求（域名列表→授权→证书） | 每次续期产生新订单 |
| 挑战 Challenge | 证明"你控制这个域名" | DNS-01（dns_ali 插件） |
| 证书有效期 | LE 统一 90 天 | acme.sh 默认 60 天时触发续期 |
| install-cert | 把证书复制到服务真实路径+reload | → `/etc/letsencrypt/live/ygxpro.online/` + `nginx -s reload` |

## 3. 技术实现原理（重点）

### 3.1 ACME 协议状态机

一次签发的完整旅程（本机每日 22:06 cron 检查，到窗口则走全流程）：

```
[账户层] 生成账户密钥对 → 向 CA 注册 accountKID
              │
[订单层] POST newOrder（*.ygxpro.online + ygxpro.online）
              │ CA 返回授权列表（每域名一个 authz）
              ▼
[挑战层] 选 DNS-01：
   1. CA 给出 token，客户端算出 key-authz（token+账户密钥的 SHA256）
   2. dns_ali 插件调阿里云 API 写 TXT 记录
      _acme-challenge.ygxpro.online = <base64(key-authz)>
   3. 等 DNS 生效（Le_DNSSleep）→ 告知 CA "就绪"
   4. CA 递归查询该 TXT → 匹配 → 授权通过
   5. 插件再调 API 删 TXT（现场清理）
              │
[签发层] 生成证书密钥对(ec-256) + CSR → POST finalize
              │ CA 用自己的私钥签发证书链
              ▼
[部署层] acme.sh 把证书存入域名目录（*.ygxpro.online_ecc/）
   → install-cert 拷贝到 /etc/letsencrypt/live/ygxpro.online/
   → 执行 ReloadCmd: nginx -s reload
              │
[续期层] 写入 Le_NextRenewTime（60天后），回到 cron 循环
```

**关键密码学事实**：
- 挑战本质 = "能向该域名的权威 DNS 写入指定内容" ⇒ 控制域名所有权。TXT 记录内容由账户密钥派生，CA 验证的是密钥持有者与域名控制者是同一人
- 通配符 `*.` 只能用 DNS-01——HTTP-01 无法证明你控制"任意子域"，RFC 8555 明确禁止
- 证书私钥始终在客户端本地生成，CSR 只含公钥——CA 永远摸不到你的私钥

### 3.2 acme.sh 的工程架构

纯 POSIX Shell 实现（~9000 行主脚本），价值在于：

```
acme.sh（主程序：状态机+HTTP+JWS签名+openssl调用）
   ├── dnsapi/    205 个 DNS 插件    ← 实测 /root/.acme.sh/dnsapi/
   ├── deploy/    60+ 个部署钩子     ← nginx/haproxy/docker/ssh/synology_dsm/k8s...
   ├── notify/    29 个通知插件      ← feishu/dingtalk/telegram/slack/mail...
   └── <domain>/  每域名一个状态目录  ← *.cer/*.key/*.conf(续期参数)
```

- **零依赖**：只要系统有 curl/wget + openssl 就能跑，这让它能装进路由器、NAS、嵌入式设备
- **插件约定**：每个 DNS 插件只需实现 `dns_xx_add()` / `dns_xx_rm()` 两个函数，acme.sh 负责其余全部流程——扩展性来自这个极简接口
- **状态自持**：续期所需的一切（CA、验证方式、部署路径、reload 命令）都记录在域名目录的 `.conf` 里，cron 扫描即可无人值守续期，无需外部数据库
- **通知解耦**：NOTIFY_HOOK 在签发/续期出错时被调用（本机已接飞书卡片，见运维节）

### 3.3 与 certbot 对比（为何本机是 acme.sh）

| 维度 | acme.sh | certbot |
|---|---|---|
| 语言/依赖 | Shell，零依赖 | Python + pip 生态 |
| 通配符 DNS 验证 | 插件一键自动化（dns_ali） | 需手工或第三方插件（certbot-dns-aliyun 等非官方） |
| 部署目标 | install-cert + reloadcmd，任意路径 | --nginx/--apache 插件绑定主流服务器，自定义路径较绕 |
| 多 CA 切换 | --server 一键（LE/ZeroSSL/Buypass/Google） | 主绑 LE |
| ECC 证书 | 原生 --keylength ec-256 | 支持（--ellptic-curve）但默认 RSA |
| NAS/嵌入式 | 完美（无 Python 依赖） | 依赖重 |

本机场景三个决定性因素：**阿里云 DNS 自动化验证**（certbot 无官方插件）、**ECS 低配 1.8G 内存**（零依赖占资源小）、**自定义部署路径 + reload**（install-cert 语义清晰）。结论：选型正确，无需动摇。

## 4. 应用场景矩阵

| 场景 | acme.sh 方案 | 本机使用状态 |
|---|---|---|
| 通配符证书 | DNS-01 + DNS API 插件 | ✅ 在用（dns_ali） |
| 常规单域名 | HTTP-01 webroot/standalone | ❌（已被通配符覆盖） |
| 内网/无公网 80 端口 | DNS-01（无需入站流量） | ✅ 天然受益 |
| 多域名一张证书 | -d 多次传参（SAN 合并） | ✅（*.ygxpro.online + 裸域） |
| 集群/远程部署 | deploy/ssh、deploy/docker 推到多机 | ❌ 单机不需要 |
| NAS/路由器 | synology_dsm、routeros 等 deploy 钩子 | ❌（NAS 侧另议） |
| CDN 同步 | deploy/ali_cdn、qiniu 等 | ❌ |
| 到期告警 | notify/feishu 等 29 个插件 | ✅ 已装（customscript 包装 notify_feishu.py） |

**边界提醒**：acme.sh 只管 DV 证书。OV/EV（组织验证）和代码签名证书不在 ACME/LE 范围内，那些仍要走传统 CA 人工流程。

## 5. 后续运维手册

### 5.1 日常（自动化，无需人工）
- 每日 22:06 cron 自动扫描续期；失败时飞书红色卡片（acme_notify.sh，2026-10-19 装机实测通过）
- 续期成功静默——**收到卡片 = 有事，没消息 = 正常**

### 5.2 值班关注点
- **每次续期日**（下次 2026-10-22）次日扫一眼 `tail /root/.acme.sh/acme.sh.log`，确认 renew 成功且无 NOTIFY 触发
- 阿里云 DNS 控制台：确认 ygxpro.online 域名解析服务未迁走、Ali_Key 未失效（凭据失效是最可能的故障源）
- Let's Encrypt 官方公告：中级 CA 轮换（如 YE1）通常平滑，无需动作

### 5.3 升级策略 —— AUTO_UPGRADE=1 现状与建议
本机 account.conf 实测 `AUTO_UPGRADE='1'`：acme.sh 每天 cron 时自检 GitHub 新版并自动升级。

**利**：自动获得 CA 兼容性修复（LE 侧协议/中级调整时，老客户端会突然失败——如 2025 年 LE 链变更导致大量过期版本集体报错，auto-upgrade 恰好免疫）。
**弊**：供应链风险（新版引入 bug/破坏性变更时无人把关）；对多证书+复杂 deploy 钩子的环境需灰度。

**明确建议：保持 AUTO_UPGRADE=1 不动。** 理由：本机仅 1 张证书、部署链路简单（install-cert+nginx reload）、且有失败飞书告警兜底——auto-upgrade 的"免维护"收益远大于理论风险。若未来扩展到 NAS 多证书+deploy 钩子，再改手动升级（`--upgrade` 前看 release note）。

### 5.4 灾备（重要且易被忽略）
证书机制的单点不是 acme.sh 程序（重装 30 秒），而是**两份状态**：
1. `account.conf` —— ACME 账户 + Ali_Key/Secret（丢了 = 账户重注册+DNS 凭据重配）
2. `<domain>/*.conf` —— 续期参数（CA、验证方式、部署路径、reloadcmd）

**行动**：已随 `/root/.hermes` 及知识库 git 体系覆盖配置类文件；建议将 `/root/.acme.sh/account.conf` 与域名 conf 纳入 hermes-config 备份范围（含密钥，勿入知识库 git）。

### 5.5 故障速查（详见姊妹篇第 4 节）
- 看日志：`tail -100 /root/.acme.sh/acme.sh.log`
- 调试重签：务必 `--server letsencrypt_test`（staging），防触发 LE 正式环境限频（同域名每周 5 张）
- 兜底：cert 文件还在 nginx 手里就能撑到修复；真过期 = 全站 HTTPS 拒连，故 60 天窗口 + 告警是双保险

## 6. 与姊妹篇的关系

| 本文 | 姊妹篇 |
|---|---|
| acme.sh 工具本体：协议原理、架构、选型、通用运维 | 本机实例：*.ygxpro.online 的具体链路、参数、消费方、排障 |
| 换机器/加域名时读这份 | 这台机器证书出问题时读那份 |

**总结**：acme.sh = "ACME 协议的 Shell 实现 + 插件生态"，把证书从人工年检事务变成 cron 里的静默循环。本机用法（dns_ali + ECC 通配符 + install-cert + 飞书告警 + auto-upgrade）已覆盖其核心价值面，运维焦点收敛为三件事：**看告警、护凭据、备状态**。
