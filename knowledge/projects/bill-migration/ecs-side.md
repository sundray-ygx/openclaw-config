# Bill_to_notion 服务迁移 — ECS 侧操作文档

> 执行时间：2026-05-31
> 目标：将 Bill_to_notion 服务从 ECS 迁移到 NAS，ECS 保留 nginx 反代

## 一、前置条件确认

- [x] 代码已推送到 GitHub（分支 `ygx`，commit `3613e61`）
- [ ] NAS 侧部署完成并确认服务可访问
- [ ] NAS 侧 frpc 代理配置完成

## 二、通过 NAS 备份通道同步数据

将以下文件同步到 NAS：

```bash
# 通过 NAS 备份通道（WebDAV: http://47.119.177.194:5005）上传
# 方式1: curl 上传
curl -T /home/ygx/python/Import_Bill_To_Notion/.env http://aliyun-ygx:password@47.119.177.194:5005/bill-migration/.env
curl -T /home/ygx/python/Import_Bill_To_Notion/data/database.sqlite http://aliyun-ygx:password@47.119.177.194:5005/bill-migration/database.sqlite

# 方式2: 如果 NAS 备份通道是 rsync/scp
scp -P 7022 /home/ygx/python/Import_Bill_To_Notion/.env root@47.119.177.194:/tmp/bill-migration/
scp -P 7022 /home/ygx/python/Import_Bill_To_Notion/data/database.sqlite root@47.119.177.194:/tmp/bill-migration/
```

**需要同步的文件（仅 2 个）**：

| 文件 | 大小 | 说明 |
|------|------|------|
| `.env` | ~2KB | 配置文件（含 Notion API Key、SECRET_KEY 等） |
| `data/database.sqlite` | 196KB | 用户数据库 |

## 三、NAS 侧部署完成后 — ECS nginx 配置变更

### 3.1 修改 bill.conf

编辑 `/etc/nginx/conf.d/bill.conf`，将 proxy_pass 从本地改为 frp 映射端口：

```nginx
# 修改前：
proxy_pass http://127.0.0.1:8000;

# 修改后（假设 NAS frpc 映射到 ECS 的 8001 端口）：
proxy_pass http://127.0.0.1:8001;
```

### 3.2 重载 nginx

```bash
nginx -t && systemctl reload nginx
```

### 3.3 验证

```bash
curl -I https://bill.ygxpro.online
# 应返回 200 或 302
```

## 四、确认迁移成功后 — 清理 ECS

### 4.1 停止 ECS 上的 web_service

```bash
kill 800141 800145 2>/dev/null
# 或者如果是 systemd 管理的：
# systemctl stop bill-to-notion
```

### 4.2 确认端口已释放

```bash
ss -tlnp | grep 8000
# 应无输出
```

### 4.3 确认内存释放

```bash
free -h
# 预期释放 ~32MB
```

## 五、回滚方案

如果 NAS 服务异常，快速回滚：

```bash
# 1. 恢复 nginx 配置
sed -i 's/127.0.0.1:8001/127.0.0.1:8000/' /etc/nginx/conf.d/bill.conf
nginx -t && systemctl reload nginx

# 2. 重启 ECS 上的 web_service
cd /home/ygx/python/Import_Bill_To_Notion
source .venv/bin/activate
nohup python3.8 -m web_service.main &
```

## 六、备注

- DNS 无需修改（bill.ygxpro.online 始终指向 ECS）
- SSL 证书无需修改（通配符证书 *.ygxpro.online）
- NAS frpc 需配置 `remotePort = 8001`（避免与 ECS 本地 8000 冲突）
