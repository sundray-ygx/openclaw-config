# ECS 服务清单收集 — OpenClaw 执行文档

## 背景

需要梳理阿里云 ECS（47.119.177.194）上运行的所有服务，为后续统一域名访问方案提供决策依据。请依次执行以下命令，将完整输出生成一份报告文件。

## 已知信息

- ECS IP: 47.119.177.194
- 域名: ygxpro.online（ICP 备案已通过，vw.ygxpro.online 已可用）
- 已知服务: Nginx、frps、certbot、OpenClaw
- 已知 Nginx 站点: vw.ygxpro.online（Vaultwarden 反代）

## 执行步骤

请依次执行以下命令，**保留完整输出，不要省略**。最终将所有输出整合为一份报告。

### 1. 系统基础信息

```bash
# 操作系统版本
cat /etc/os-release

# 内核版本
uname -a

# CPU / 内存 / 磁盘概览
echo "=== CPU ==="
nproc
echo "=== Memory ==="
free -h
echo "=== Disk ==="
df -h
echo "=== Uptime ==="
uptime
```

### 2. 所有运行中的进程及监听端口

```bash
# 所有监听端口
ss -tlnp | grep LISTEN | sort -t: -k2 -n

# 所有 UDP 监听
ss -ulnp | grep LISTEN | sort -t: -k2 -n
```

### 3. Docker 容器（如有）

```bash
# 检查 Docker 是否安装
which docker 2>/dev/null && docker --version

# 运行中的容器
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}\t{{.Mounts}}"

# 所有容器（含停止的）
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

# Docker Compose 项目（如有）
find / -maxdepth 4 -name "docker-compose.yml" -o -name "docker-compose.yaml" -o -name "compose.yml" -o -name "compose.yaml" 2>/dev/null
```

### 4. Systemd 服务

```bash
# 所有正在运行的自定义服务（排除系统默认的）
systemctl list-units --type=service --state=running --no-pager | grep -v -E '^(systemd-|dbus-|getty@|user@|polkit|NetworkManager|firewalld|irqbalance|sshd|crond|rsyslog|chronyd|tuned|cloud-|aliyun|aegis|AliyunDun|AliyunService)'

# 特别关注的服务状态
for svc in nginx frps frpc openclaw docker; do
    echo "=== $svc ==="
    systemctl status $svc 2>/dev/null | head -15
    echo ""
done

# 列出所有自定义 systemd unit 文件
systemctl list-unit-files --type=service --state=enabled --no-pager | grep -v -E '^(@|systemd-|dbus-|getty|polkit|network|firewall|irq|ssh|crond|rsyslog|chrony|tuned|cloud-|aliyun|aegis)'
```

### 5. Nginx 完整配置

```bash
# Nginx 版本
nginx -v 2>&1

# Nginx 主配置
cat /etc/nginx/nginx.conf

# 所有站点配置
echo "=== 站点配置文件列表 ==="
ls -la /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ /etc/nginx/sites-available/ 2>/dev/null

# 逐个输出站点配置
for f in /etc/nginx/conf.d/*.conf /etc/nginx/sites-enabled/*; do
    if [ -f "$f" ]; then
        echo "========== $f =========="
        cat "$f"
        echo ""
    fi
done
```

### 6. FRP 配置

```bash
# frps 配置
echo "=== frps 配置文件位置 ==="
find / -maxdepth 4 -name "frps.toml" -o -name "frps.ini" -o -name "frps.conf" 2>/dev/null

# 读取 frps 配置
for f in $(find / -maxdepth 4 -name "frps.toml" -o -name "frps.ini" 2>/dev/null); do
    echo "========== $f =========="
    cat "$f"
done

# frps systemd 配置
systemctl cat frps 2>/dev/null || cat /etc/systemd/system/frps.service 2>/dev/null
```

### 7. SSL 证书

```bash
# Let's Encrypt 证书列表
echo "=== certbot 证书 ==="
certbot certificates 2>/dev/null || echo "certbot 未安装"

# 证书目录
ls -la /etc/letsencrypt/live/ 2>/dev/null

# certbot 续期配置
crontab -l 2>/dev/null | grep -i cert
cat /etc/cron.d/certbot 2>/dev/null
```

### 8. OpenClaw 信息

```bash
# OpenClaw 安装位置
which openclaw 2>/dev/null
find / -maxdepth 3 -name "openclaw" -type f 2>/dev/null | head -5

# OpenClaw 配置
find /root -maxdepth 3 -name "openclaw.json" -o -name "config.json" -path "*openclaw*" 2>/dev/null

# OpenClaw 运行状态
ps aux | grep -i openclaw | grep -v grep

# OpenClaw 工作目录
ls -la /root/.openclaw/ 2>/dev/null || ls -la /opt/openclaw/ 2>/dev/null

# OpenClaw Gateway（如有）
ps aux | grep -i gateway | grep -v grep
```

### 9. 定时任务

```bash
# 系统 crontab
cat /etc/crontab

# 用户 crontab
crontab -l 2>/dev/null

# cron.d 目录
ls /etc/cron.d/ 2>/dev/null
for f in /etc/cron.d/*; do
    if [ -f "$f" ]; then
        echo "=== $f ==="
        cat "$f"
        echo ""
    fi
done
```

### 10. 其他 Web 服务 / 应用

```bash
# 检查常见应用服务器
for cmd in node python3 python go java php; do
    echo "=== $cmd ==="
    which $cmd 2>/dev/null && $cmd --version 2>/dev/null
done

# 检查 PM2（Node 进程管理）
pm2 list 2>/dev/null

# 检查是否有其他反代/应用在跑
ps aux | grep -E 'node|python|java|php|ruby|uvicorn|gunicorn|flask|django|express|next|nuxt' | grep -v grep

# 检查数据库
for svc in mysql mariadb postgres mongod redis; do
    systemctl status $svc 2>/dev/null | head -5
done
```

### 11. 防火墙与安全组

```bash
# iptables 规则
iptables -L -n --line-numbers 2>/dev/null | head -50

# firewalld
firewall-cmd --list-all 2>/dev/null

# 阿里云安全组（如有命令行工具）
aliyun ecs DescribeSecurityGroupAttribute --RegionId cn-shenzhen 2>/dev/null | head -50
```

### 12. 磁盘使用详情

```bash
# 各目录占用空间
du -h --max-depth=2 / 2>/dev/null | sort -rh | head -30

# /root 目录详情
du -h --max-depth=2 /root/ 2>/dev/null | sort -rh | head -20

# /opt 目录详情（如有）
du -h --max-depth=2 /opt/ 2>/dev/null | sort -rh | head -20
```

## 输出要求

将以上所有命令的输出整合为一份报告，格式如下：

```markdown
# ECS (47.119.177.194) 服务清单报告
> 采集时间: YYYY-MM-DD HH:MM

## 1. 系统信息
（完整输出）

## 2. 监听端口
（完整输出）

## 3. Docker 容器
（完整输出）

...（按章节依次列出）

## 总结

请基于采集到的信息，给出以下总结：

### 正在运行的服务列表
| 服务名 | 类型 | 端口 | 用途 | 备注 |
|--------|------|------|------|------|

### Nginx 站点列表
| 域名 | 后端 | SSL | 备注 |
|------|------|-----|------|

### 可迁移到 NAS 的服务
| 服务 | 迁移难度 | 建议是否迁移 | 理由 |
|------|---------|-------------|------|

### 必须保留在 ECS 的服务
| 服务 | 理由 |
|------|------|

### 发现的问题或风险
- （如无用服务、安全风险、配置问题等）
```

请将报告保存为 `/root/ecs-service-report.md`。
