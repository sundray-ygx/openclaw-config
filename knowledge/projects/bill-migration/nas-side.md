# Bill_to_notion 服务迁移 — NAS 侧操作文档

> 执行时间：2026-05-31
> 目标：在 NAS 服务器上部署 Bill_to_notion 服务，通过 frp 代理到 ECS

## 一、前置条件

- NAS 服务器：47.119.177.194:7022（SSH）
- frpc 已连接到 ECS frps（120.229.76.2 → ECS:7000）
- 数据文件已通过 NAS 备份通道同步到 `/tmp/bill-migration/`

## 二、部署步骤

### 2.1 克隆代码

```bash
# 创建目标目录
mkdir -p /opt/bill-to-notion
cd /opt/bill-to-notion

# SSH clone（需要 deploy key 或 GitHub SSH key）
git clone git@github.com:sundray-ygx/Import_Bill_To_Notion.git .

# 切换到 ygx 分支（最新代码）
git checkout ygx
```

> **注意**：仓库已迁移到 `Import_Bill_To_Notion`（新名称），如果 clone 失败试旧名 `Bill_to_notion`

### 2.2 安装依赖

```bash
cd /opt/bill-to-notion

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2.3 配置环境

```bash
# 从迁移目录复制配置文件
cp /tmp/bill-migration/.env /opt/bill-to-notion/.env

# 从迁移目录复制数据库
mkdir -p /opt/bill-to-notion/data
cp /tmp/bill-migration/database.sqlite /opt/bill-to-notion/data/

# 设置目录权限
chmod 755 /opt/bill-to-notion
chmod 600 /opt/bill-to-notion/.env
```

### 2.4 验证启动

```bash
cd /opt/bill-to-notion
source .venv/bin/activate

# 先手动启动测试
uvicorn web_service.main:app --host 127.0.0.1 --port 8000

# 另一个终端验证
curl -I http://127.0.0.1:8000
# 应返回 200 或 302

# 确认后 Ctrl+C 停止
```

### 2.5 配置 systemd 自启

创建 `/etc/systemd/system/bill-to-notion.service`：

```ini
[Unit]
Description=Bill to Notion Web Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bill-to-notion
ExecStart=/opt/bill-to-notion/.venv/bin/uvicorn web_service.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=PATH=/opt/bill-to-notion/.venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
```

启动并设置自启：

```bash
systemctl daemon-reload
systemctl enable bill-to-notion
systemctl start bill-to-notion
systemctl status bill-to-notion
```

## 三、frpc 代理配置

### 3.1 修改 NAS frpc 配置

在 NAS 的 frpc 配置文件中添加：

```toml
[[proxies]]
name = "bill-web"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8000
remotePort = 8001
```

### 3.2 重启 frpc

```bash
# 找到 frpc 进程
ps aux | grep frpc

# 重启（方式取决于 frpc 部署方式）
# 如果是 systemd：
systemctl restart frpc
# 如果是直接运行：
# kill <pid> && nohup frpc -c /path/to/frpc.toml &
```

### 3.3 验证 frp 连通性

在 NAS 上验证：
```bash
curl -I http://127.0.0.1:8000
```

在 ECS 上验证：
```bash
curl -I http://127.0.0.1:8001
# 应返回 200 或 302
```

## 四、通知 ECS 侧完成

NAS 侧部署完成后，通知 ECS 侧执行：
1. 修改 nginx bill.conf（proxy_pass 改为 8001）
2. 停止 ECS 上的 web_service

## 五、安全加固（迁移后执行）

### 5.1 立即执行

| 项目 | 操作 |
|------|------|
| 关闭注册 | `.env` 中 `REGISTRATION_ENABLED=false` |
| 修复权限 | `chmod 755 /opt/bill-to-notion`（非 777） |
| 绑定本地 | 确认 uvicorn `--host 127.0.0.1`（不暴露 0.0.0.0） |

### 5.2 后续优化

| 项目 | 操作 |
|------|------|
| CORS 收紧 | `allow_origins` 指定 `https://bill.ygxpro.online` |
| 隐藏 API 文档 | FastAPI 设置 `docs_url=None` |
| 限制上传 | nginx 层加 `client_max_body_size` |

## 六、故障排查

| 问题 | 排查 |
|------|------|
| NAS 服务启动失败 | `journalctl -u bill-to-notion -n 50` |
| frp 连接不通 | 检查 frpc 日志，确认 ECS frps 端口 7000 正常 |
| 数据库错误 | 确认 `data/database.sqlite` 权限和路径 |
| 页面白屏 | 检查 `.env` 中 `NOTION_API_KEY` 是否正确 |
