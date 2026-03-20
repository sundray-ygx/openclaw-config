# FRP 内网穿透配置文档

> 创建时间：2026-03-14  
> 版本：FRP 0.60.0

---

## 📋 配置概览

| 项目 | 详情 |
|------|------|
| **FRP版本** | 0.60.0 |
| **安装路径** | `/root/frp_0.60.0_linux_amd64/` |
| **服务端** | frps (运行中) |
| **客户端** | frpc (配置存在) |
| **服务端IP** | 47.119.177.194 |

---

## 🔧 服务端配置 (frps.toml)

**配置文件路径：** `/root/frp_0.60.0_linux_amd64/frps.toml`

```toml
# 服务端与客户端通信端口
bindPort = 7000

# HTTP虚拟主机端口
vhostHTTPPort = 8080

# 管理后台配置
webServer.addr = "0.0.0.0"
webServer.port = 7500
webServer.user = "admin"
webServer.password = "qwer1234"
```

| 配置项 | 值 | 说明 |
|--------|-----|------|
| bindPort | 7000 | 服务端与客户端通信端口 |
| vhostHTTPPort | 8080 | HTTP虚拟主机端口 |
| webServer.addr | 0.0.0.0 | 管理后台地址 |
| webServer.port | 7500 | 管理后台端口 |
| webServer.user | admin | 管理后台用户名 |
| webServer.password | qwer1234 | 管理后台密码 |

**管理后台：** http://47.119.177.194:7500

---

## 🔌 客户端配置 (frpc.toml)

**配置文件路径：** `/root/frp_0.60.0_linux_amd64/frpc.toml`

```toml
[common]
server_addr = "47.119.177.194"
server_port = 7000

[ssh]
name = "ssh"
type = "tcp"
local_ip = "127.0.0.1"
local_port = 22
remote_port = 7022

[nas]
name = "nas"
type = "tcp"
local_ip = "127.0.0.1"
local_port = 5000
remote_port = 5000

[jellyfin]
name = "jellyfin"
type = "tcp"
local_ip = "127.0.0.1"
local_port = 8096
remote_port = 8096

[vaultwarden]
name = "password"
type = "tcp"
local_ip = "127.0.0.1"
local_port = 3011
remote_port = 3011

[aliyunpan]
name = "aliyunpan"
type = "tcp"
local_ip = "127.0.0.1"
local_port = 9080
remote_port = 9080
```

| 服务名 | 类型 | 本地端口 | 远程端口 | 说明 |
|--------|------|---------|---------|------|
| ssh | tcp | 22 | 7022 | SSH远程连接 |
| nas | tcp | 5000 | 5000 | NAS服务 |
| jellyfin | tcp | 8096 | 8096 | 媒体服务器 |
| vaultwarden | tcp | 3011 | 3011 | 密码管理器 |
| aliyunpan | tcp | 9080 | 9080 | 阿里云盘 |

---

## 📝 Systemd服务

**服务文件：** `/etc/systemd/system/frps.service`

```ini
[Unit]
Description=FRP Server Service
After=network.target

[Service]
Type=simple
ExecStart=/root/frp_0.60.0_linux_amd64/frps -c /root/frp_0.60.0_linux_amd64/frps.toml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### 管理命令

```bash
# 查看状态
systemctl status frps

# 启动/停止/重启
systemctl start frps
systemctl stop frps
systemctl restart frps

# 开机自启
systemctl enable frps

# 查看日志
journalctl -u frps -f
```

---

## 🌐 访问地址

| 服务 | 外网访问地址 | 内网地址 |
|------|-------------|---------|
| FRP管理后台 | http://47.119.177.194:7500 | - |
| SSH | ssh://47.119.177.194:7022 | 127.0.0.1:22 |
| NAS | http://47.119.177.194:5000 | 127.0.0.1:5000 |
| Jellyfin | http://47.119.177.194:8096 | 127.0.0.1:8096 |
| Vaultwarden | http://47.119.177.194:3011 | 127.0.0.1:3011 |
| 阿里云盘 | http://47.119.177.194:9080 | 127.0.0.1:9080 |

---

## ⚠️ 安全建议

1. **管理后台密码**为明文存储，建议定期更换
2. **Token认证**当前被注释，建议启用以增强安全性
3. 所有服务均为**HTTP明文传输**，建议配合HTTPS使用
4. 建议限制管理后台访问IP，避免暴露在公网

---

## 📁 相关文件

| 文件 | 路径 |
|------|------|
| 服务端二进制 | `/root/frp_0.60.0_linux_amd64/frps` |
| 客户端二进制 | `/root/frp_0.60.0_linux_amd64/frpc` |
| 服务端配置 | `/root/frp_0.60.0_linux_amd64/frps.toml` |
| 客户端配置 | `/root/frp_0.60.0_linux_amd64/frpc.toml` |
| Systemd服务 | `/etc/systemd/system/frps.service` |

---

## 🔗 参考链接

- FRP官方文档：https://gofrp.org/
- GitHub仓库：https://github.com/fatedier/frp
