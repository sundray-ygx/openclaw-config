# ECS (47.119.177.194) 服务清单报告
> 采集时间: 2026-05-16 22:00 CST

## 1. 系统信息

| 项目 | 值 |
|------|------|
| 操作系统 | Alibaba Cloud Linux 3.2104 U12.3 (OpenAnolis Edition) |
| 内核 | 5.10.134-19.2.al8.x86_64 |
| CPU | 2 核 |
| 内存 | 1.8G 总计，1.6G 已用，226M 可用 |
| Swap | 6.0G 总计，418M 已用 |
| 磁盘 | 40G 总计，30G 已用 (79%)，8.2G 可用 |
| 运行时间 | 36 天 |
| 负载 | 0.81, 0.22, 0.13 |

## 2. 监听端口

### TCP
| 端口 | 进程 | 用途 |
|------|------|------|
| 80 | nginx (pid 742/933698/933699) | HTTP |
| 443 | nginx | HTTPS |
| 111 | rpcbind/systemd | RPC |
| 1080 | docker-proxy (sing-box) | 代理 |
| 3011 | frps (vaultwarden) | Vaultwarden HTTP |
| 3012 | frps (vaultwarden) | Vaultwarden WebSocket |
| 5000 | frps | FRP 代理 |
| 5005 | frps | FRP 代理 |
| 7000 | frps | FRP 服务端绑定端口 |
| 7023 | frps | FRP 代理 |
| 7500 | frps | FRP 管理后台 |
| 8000 | python3.8 (bill-import) | 账单导入 Web 服务 |
| 8080 | frps | FRP vhostHTTP |
| 8096 | frps | FRP 代理 |
| 9080 | frps | FRP 代理 |
| 9090 | docker-proxy (sing-box) | sing-box 管理面板 |
| 18789 | openclaw-gateway (本地) | OpenClaw Gateway |
| 23456 | sshd | SSH |
| 33783 | openclaw-gateway (本地) | OpenClaw 内部 |
| 34129 | hbrclient (本地) | 阿里云备份客户端 |

### UDP
无

## 3. Docker 容器

### 运行中
| 容器名 | 镜像 | 端口 | 状态 | 挂载 |
|--------|------|------|------|------|
| sing-box | ghcr.io/sagernet/sing-box:v1.11.3 | 1080, 9090 | Up 5 weeks | /etc/sing-box/… |

### 已停止
| 容器名 | 镜像 | 状态 |
|--------|------|------|
| searxng | searxng/searxng:latest | Exited (0) 5 weeks ago |
| naughty_cannon | e89411894931 | Exited (100) 2 months ago |
| beautiful_archimedes | e89411894931 | Exited (100) 2 months ago |
| serene_shamir | hello-world | Exited (0) 3 months ago |

### Docker Compose 文件
- `/home/ygx/clawdbot/docker-compose.yml`（可能是旧项目）

## 4. Systemd 服务

### 关键自定义服务
| 服务 | 状态 | 用途 |
|------|------|------|
| nginx | enabled/running | 反向代理 |
| frps | enabled/running | FRP 内网穿透服务端 |
| docker | enabled/running | Docker 容器引擎 |
| openclaw-gateway | enabled/running | OpenClaw 网关 |
| bill-import | enabled/running | Notion 账单导入 Web 服务 (python3.8, 端口 8000) |
| ecs_mq | enabled | 阿里云 ECS 多队列优化（系统服务） |

### 阿里云自带服务
- hbrclient — 阿里云备份
- hbrclientupdater — 备份客户端更新

## 5. Nginx 配置

### 版本
nginx/1.20.1

### 站点配置

#### vw.ygxpro.online（Vaultwarden）
- **监听**: 443 SSL HTTP/2
- **SSL 证书**: `/etc/letsencrypt/live/vw.ygxpro.online/`
- **后端**: 
  - `/` → `127.0.0.1:3011`（Vaultwarden HTTP，经 FRP 代理）
  - `/notifications/hub` → `127.0.0.1:3012`（WebSocket）
- **上传限制**: 525M
- **HSTS**: 已启用
- **HTTP → HTTPS**: 301 重定向（在 nginx.conf 主配置中）

#### nginx.conf 中的 80 端口
- vw.ygxpro.online 的 HTTP 跳转 + ACME 验证

## 6. FRP 配置

### frps.toml
- **绑定端口**: 7000
- **vhostHTTP**: 8080
- **管理后台**: 0.0.0.0:7500（用户: admin，密码: qwer1234）
- **无 token 验证**（已注释）

### FRP 代理端口
从监听端口推断，FRP 注册了以下代理：
| 端口 | 推测用途 |
|------|---------|
| 3011 | Vaultwarden HTTP |
| 3012 | Vaultwarden WebSocket |
| 5000 | 未知 |
| 5005 | 未知 |
| 7023 | 未知 |
| 8096 | 未知 |
| 9080 | 未知 |

### FRP Service
- 二进制: `/root/frp_0.60.0_linux_amd64/frps`
- 自动重启: on-failure

## 7. SSL 证书

### Let's Encrypt
- **域名**: vw.ygxpro.online
- **证书路径**: `/etc/letsencrypt/live/vw.ygxpro.online/`
- **备份**: `vw.ygxpro.online.bak.genY`（旧证书）
- ⚠️ **renewal 配置无效**: `vw.ygxpro.online.conf` 报错

### 证书续期
- crontab: `0 3 * * * certbot renew --quiet --deploy-hook 'nginx -s reload'`
- acme.sh: `27 11 * * *`（每日自动）

### 其他证书
- nginx 启动日志引用了 `/usr/local/nginx/cert/ygxpro.xyz.pem`（旧域名）

## 8. OpenClaw

| 项目 | 值 |
|------|------|
| 安装路径 | `/usr/bin/openclaw` |
| 配置 | `/root/.openclaw/openclaw.json` |
| 工作区 | `/root/.openclaw/workspace` |
| Gateway PID | 971034，占用 ~500MB 内存 |
| TUI PID | 974453，占用 ~525MB 内存 |
| 扩展 | 787MB（/root/.openclaw/extensions） |
| 记忆 | 11MB（/root/.openclaw/memory） |

## 9. 定时任务（crontab）

| 任务 | 时间 | 说明 |
|------|------|------|
| 早间简报 | 08:00 | morning_briefing.py |
| 每日工作日报 | 08:30 | daily_report.py |
| 每日反思 | 08:45 | daily_reflection.py |
| NAS 备份 | 02:00 | nas_backup.sh |
| 周复盘 | 周五 18:30 | weekly_review.py |
| 周报提醒 | 周五 17:00 | 日志记录 |
| 周反思 | 周日 20:00 | weekly_reflection.py |
| 月反思 | 每月最后一天 21:00 | monthly_reflection.py |
| 安全巡检 | 周一 09:00 | security_check.sh |
| 租金提醒 | 每月 25/27 日 | rent_expense_remind.py |
| 磁盘清理 | 周一 10:00 | 清理 pip 缓存和 __pycache__ |
| certbot 续期 | 每日 03:00 | certbot renew |
| acme.sh | 每日 11:27 | acme.sh --cron |

## 10. 其他应用

### 运行时环境
| 语言 | 版本 |
|------|------|
| Node.js | v22.22.1 |
| Python 3 | 3.6.8（系统） |
| Python 3.8 | /usr/bin/python3.8（bill-import 使用） |
| Go | 已安装 |

### 其他进程
- python3.8 (bill-import) — 端口 8000，Notion 账单导入

### 未安装
- Java, PHP, PM2, 数据库服务（MySQL/PostgreSQL/MongoDB/Redis）

## 11. 防火墙

- **iptables**: INPUT 策略 ACCEPT，无自定义规则。Docker 自动管理 FORWARD 链。
- **firewalld**: 未运行
- **安全组**: 依赖阿里云安全组（需在控制台确认）

## 12. 磁盘使用

| 目录 | 大小 |
|------|------|
| /usr | 8.5G |
| /var | 6.3G |
| /root | 2.3G |
| /opt | 336M |
| **总计使用** | **30G / 40G (79%)** |

### /root 明细
| 目录 | 大小 |
|------|------|
| .openclaw | 1.1G（extensions 787M, workspace 176M, agents 113M） |
| .trae-cn-server | 577M |
| .local | 447M |
| .cache | 88M |
| openclaw-backups | 41M |
| frp_0.60.0_linux_amd64 | 32M |
| go | 25M |

---

## 总结

### 正在运行的服务列表
| 服务名 | 类型 | 端口 | 用途 | 备注 |
|--------|------|------|------|------|
| nginx | 反向代理 | 80, 443 | HTTPS 反代 Vaultwarden | 版本 1.20.1 |
| frps | 内网穿透 | 7000, 7500, 8080, 3011/3012, 5000, 5005, 7023, 8096, 9080 | FRP 服务端 | 管理 7500 无 token 验证 |
| sing-box (Docker) | 代理工具 | 1080, 9090 | 网络代理 | v1.11.3 |
| openclaw-gateway | AI 助手网关 | 18789 (本地) | OpenClaw | 占用 ~500MB 内存 |
| bill-import | Python Web | 8000 | Notion 账单导入 | python3.8 |
| sshd | SSH | 23456 | 远程管理 | 非标准端口 |
| certbot/acme.sh | SSL 续期 | - | 证书自动续期 | 每日自动 |

### Nginx 站点列表
| 域名 | 后端 | SSL | 备注 |
|------|------|-----|------|
| vw.ygxpro.online | 127.0.0.1:3011 (FRP→Vaultwarden) | ✅ Let's Encrypt | 唯一对外站点 |

### 发现的问题或风险

#### 🔴 高风险
1. **FRP 管理后台 (7500) 暴露在 0.0.0.0**，且使用弱密码 `qwer1234`，无 token 验证。任何人可访问 FRP 控制面板
2. **FRP 无 token 验证**（已注释），任何人可注册代理连接
3. **certbot renewal 配置无效** — `vw.ygxpro.online.conf` 报错，可能导致 SSL 证书续期失败
4. **磁盘使用 79%**，仅剩 8.2G，接近告警线。/var (6.3G) 和 /usr (8.5G) 是大头

#### 🟡 中风险
5. **内存使用率高** (1.6G/1.8G)，OpenClaw 两个进程占 ~1GB。依赖 Swap
6. **多个已停止的 Docker 容器**（searxng, hello-world 等），占用空间
7. **Python 3.6.8 已 EOL** — 系统自带版本，不再接收安全更新
8. **旧域名 ygxpro.xyz 证书残留** — nginx 启动时有 warn
9. **bill-import 运行在 python3.8**，也是较旧版本
10. **trae-cn-server (577M)** — 用途不明，占用较大空间

#### 🟢 低风险
11. Docker Compose 文件 `/home/ygx/clawdbot/docker-compose.yml` — 旧项目残留
12. 备份证书 `vw.ygxpro.online.bak.genY` 可清理
13. `/root/openclaw-backups/20260324` (26M) — 旧备份可归档

### 建议

1. **优先修复 FRP 安全**: 设置 token，管理后台绑定 127.0.0.1 或通过 nginx 反代加鉴权
2. **修复 certbot renewal**: 检查 `/etc/letsencrypt/renewal/vw.ygxpro.online.conf`
3. **清理磁盘**: 删除停止的 Docker 容器、旧备份、trae-cn-server（如不用）
4. **考虑升级 ECS 规格**: 2C2G 跑 OpenClaw + FRP + Docker 比较紧张
