# new-api 迁移 NAS 侧执行手册（hermes 用）

- **日期**: 2026-09-17 | **执行者**: NAS 上的 hermes | **协调人**: ECS 上的 OpenClaw（小助）
- **决策**: Boss 已批准方案 A（域名入口留 ECS + frp 反代）+ 在线随切
- **红线**: ① 只有 Step C（切换窗口）允许触碰数据文件 ② 任何步骤验证失败 → 立即停下，按「回报格式」发结果等指示，**不要自行决策** ③ 不要删除/修改 ECS 传来的包以外的东西

## 背景（30 秒版）

AI 网关 new-api 目前跑在 ECS 的 Docker 里（api.ygxpro.online），现迁到本 NAS 的 Docker。迁移后：公网请求 → ECS nginx(TLS) → frp 隧道(ECS:3100) → 本机 new-api:3000。GLM/火山渠道经本机桥接容器(172.17.0.1:8081)路径重写出公网。渠道/令牌数据原样迁移（库内 base_url 写的 172.17.0.1 在 NAS Docker 环境下自动指向本机桥接，**无需改库**）。

```
Agent → api.ygxpro.online → ECS nginx:443 → ECS:3100 ==frp 隧道== → 本机 new-api:3000
                                                    new-api ─ GLM/Volc → 172.17.0.1:8081(桥接容器) → api.z.ai / ark.volces.com
                                                            └ DeepSeek → api.deepseek.com 直连
```

---

## Phase A：预检（只读，不部署）

逐条执行，**每条都要贴出实际输出**：

```bash
# A1 Docker 环境
docker --version && docker ps --format '{{.Names}}' | head -20
# 预期: Docker 20+，且列出现有容器

# A2 docker0 网段（关键！渠道数据写死 172.17.0.1）
ip addr show docker0 | grep 'inet '
# 预期: inet 172.17.0.1/16 ...（若不是 172.17.0.1 → 全部停下回报，方案要调整）

# A3 资源余量
free -h && df -h /volume1 2>/dev/null || df -h /
nproc
# 预期: 可用内存 ≥ 1G，磁盘剩余 ≥ 2G

# A4 出公网（两个上游）
curl -s -o /dev/null -w 'zai:%{http_code}\n' --connect-timeout 5 https://api.z.ai/api/coding/paas/v4/models
curl -s -o /dev/null -w 'deepseek:%{http_code}\n' --connect-timeout 5 https://api.deepseek.com
# 预期: 都有响应码（401/404 也算通，说明 DNS+出口正常；超时=不通，停下回报）

# A5 frpc 位置与形态
ps -ef | grep -i frpc | grep -v grep
docker ps | grep -i frp
# 记录: frpc 配置文件路径（-c 参数）、运行方式（宿主进程 or docker 容器）

# A6 本机 WebDAV/备份目录探测（Step C 取数据用）
ls -d /volume*/*aliyun_backup* 2>/dev/null
curl -s -o /dev/null -w 'local-webdav:%{http_code}\n' -u "$(grep WEBDAV_USER ~/.hermes/.env 2>/dev/null | cut -d= -f2)" http://127.0.0.1:5005/ 2>/dev/null || echo 'no local webdav cred'
# 预期: 找到 aliyun_backup 目录路径（记录下来）；WebDAV 用户名在下面 Step B 由 ECS 通知
```

**Phase A 回报格式**（贴给 Boss/小助）:
```
A1: docker=xx, A2: docker0=xx, A3: mem_free=xx disk_free=xx, A4: zai=xx deepseek=xx
A5: frpc_conf=<路径> run_mode=<host进程|docker容器>, A6: backup_dir=<路径>
```

---

## Phase B：影子部署（不停机，不影响现有服务）

### B1 拉镜像 + 版本锁定

```bash
docker pull calciumion/new-api:latest
docker images calciumion/new-api --format '{{.ID}} {{.CreatedAt}}'
```
- **预期**: image ID 以 `6670c75136f3` 开头（ECS 当前运行版本，2026-09-07 构建）
- **若 ID 不一致**: 停下回报（不要自行决定用新版本；备选方案是 ECS docker save 导出传输）

### B2 部署桥接容器（路径重写，从 ECS 配置原样复制）

```bash
mkdir -p /volume1/docker/newapi-bridge && cat > /volume1/docker/newapi-bridge/default.conf <<'EOF'
# new-api 渠道上游桥接：new-api(type=1)固定拼 /v1/*，此处映射到各家真实路径
# 仅映射到 docker0(172.17.0.1)，不对局域网/公网暴露
server {
    listen 80;
    server_name newapi-upstream;
    location /zai/v1/ {
        proxy_pass https://api.z.ai/api/coding/paas/v4/;
        proxy_set_header Host api.z.ai;
        proxy_ssl_server_name on;
        proxy_buffering off;
        proxy_read_timeout 600s;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /volc/v1/ {
        proxy_pass https://ark.cn-beijing.volces.com/api/coding/v3/;
        proxy_set_header Host ark.cn-beijing.volces.com;
        proxy_ssl_server_name on;
        proxy_buffering off;
        proxy_read_timeout 600s;
    }
}
EOF

docker run -d --name newapi-bridge --restart=always \
  -p 172.17.0.1:8081:80 \
  -v /volume1/docker/newapi-bridge/default.conf:/etc/nginx/conf.d/default.conf:ro \
  nginx:alpine

# 验证桥接（直接打重写路径，应返回 401/4xx JSON=链路通，超时/502=配置错）
curl -s -o /dev/null -w 'bridge-zai:%{http_code}\n' --connect-timeout 5 http://172.17.0.1:8081/zai/v1/chat/completions
curl -s -o /dev/null -w 'bridge-volc:%{http_code}\n' --connect-timeout 5 http://172.17.0.1:8081/volc/v1/chat/completions
```
- **预期**: 两个 401（上游要求鉴权 = 重写转发成功）
- ⚠️ 若 `/volume1/docker` 不是你的容器数据惯例路径，换成对应路径（如 `/volume1/docker/newapi-bridge` → 实际存在的 docker 目录）

### B3 frpc 加 3100 代理（⚠️ 影响面提示：重启 frpc 会瞬断全部 frp 代理几秒，自动重连恢复）

```bash
# 先备份
cp <A5发现的frpc配置路径> <同路径>.bak-newapi-migration
```
在配置文件**末尾**追加（toml 格式）:
```toml
[[proxies]]
name = "newapi"
type = "tcp"
localIP = "172.17.0.1"
localPort = 3000
remotePort = 3100
```
若配置是 ini 格式（有 [common] 段），则追加:
```ini
[newapi]
type = tcp
local_ip = 172.17.0.1
local_port = 3000
remote_port = 3100
```

重启 frpc（按 A5 发现的方式）:
```bash
# 宿主进程: 找到启动命令 kill 后用原命令重启（nohup ... &）
# docker 容器: docker restart <frpc容器名>
```

### B4 启动 new-api（空库预跑，验证容器与端口链路）

```bash
mkdir -p /volume1/docker/newapi/data
docker run -d --name new-api --restart=always --memory=300m \
  -p 172.17.0.1:3000:3000 \
  -v /volume1/docker/newapi/data:/data \
  -e TZ=Asia/Shanghai \
  calciumion/new-api:latest

sleep 5
curl -s -o /dev/null -w 'nas-local:%{http_code}\n' http://172.17.0.1:3000/api/status
docker logs new-api --tail 5
```
- **预期**: 200；日志无 FATAL
- （空库会生成全新 one-api.db，Step C 会被真数据覆盖，正常）

**Phase B 回报格式**:
```
B1: imageID=xx (匹配=是/否)
B2: bridge 401/401 ✓
B3: frpc已加 newapi→3100, 重启完成, 代理在线数=xx
B4: 3000 status=200 ✓
```
**回报后等待切换指令，不要进入 Step C。**

---

## Step C：切换窗口（⚠️ 只有收到 ECS 侧「DATA_UPLOADED」指令后才执行）

> 窗口目标 <2 分钟。ECS 已 `docker stop new-api` 并打包上传，此刻全平台网关 502（预期内）。

```bash
# C1 取包（两种方式择一可用）
PKG=newapi-migration-<时间戳>.tar.gz   # 以 ECS 通知的实际文件名为准
# 方式1: 本地文件系统（Phase A6 发现的目录）
cp <A6备份目录>/server-backup/newapi-migration/$PKG /tmp/$PKG
# 方式2: NAS 本地 WebDAV
curl -u '<user>:<pass>' http://127.0.0.1:5005/aliyun_backup/server-backup/newapi-migration/$PKG -o /tmp/$PKG

# C2 校验（必须与 ECS 通知的 md5 一致，不一致 → 停下回报）
md5sum /tmp/$PKG

# C3 停空库实例 → 替换数据 → 启动
docker stop new-api
tar -xzf /tmp/$PKG -C /tmp/newapi-mig-extract --one-top-level 2>/dev/null || (mkdir -p /tmp/newapi-mig-extract && tar -xzf /tmp/$PKG -C /tmp/newapi-mig-extract)
ls /tmp/newapi-mig-extract            # 确认结构: data/one-api.db + 附属文件
rm -f /volume1/docker/newapi/data/one-api.db*
cp -a /tmp/newapi-mig-extract/data/one-api.db* /volume1/docker/newapi/data/
docker start new-api && sleep 5
curl -s -o /dev/null -w 'nas-3000:%{http_code}\n' http://172.17.0.1:3000/api/status

# C4 端到端验证（注意：必须打本机 172.17.0.1:3000，此时打域名会到 ECS 旧实例）
KEY=$(grep '^NEWAPI_API_KEY=' ~/.hermes/.env | cut -d= -f2)
# C4a DeepSeek 渠道（直连链路）
curl -s --max-time 60 -X POST http://172.17.0.1:3000/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":500}' | head -c 300
# C4b GLM 渠道（覆盖 new-api→桥接→z.ai 全链路，本迁移关键验证点）
curl -s --max-time 60 -X POST http://172.17.0.1:3000/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"glm-4.7-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":500}' | head -c 300
```
- **预期**: 两个请求均返回 `"choices":[{"message":{"content":"ok"...`
- ⚠️ glm 系列强制 thinking：若 content 为空但 choices 正常返回，加大 max_tokens 到 2000 重测一次再判定

**Step C 回报格式**:
```
C2: md5=xx (匹配=是)
C3: 3000 status=200
C4a: deepseek=ok / C4b: glm=ok
NAS_READY   ← 全部通过才发这行
```
收到回报后 ECS 侧立即切 nginx，之后打 `https://api.ygxpro.online` 即为本机。

---

## Step D：切换后确认（ECS 切流完成后）

```bash
# 从本机走完整公网链路打一发（ECS nginx→frp→本机）
KEY=$(grep '^NEWAPI_API_KEY=' ~/.hermes/.env | cut -d= -f2)
curl -s --max-time 60 -X POST https://api.ygxpro.online/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"glm-4.7-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":1000}' | head -c 300
docker logs new-api --tail 20    # 应看到刚才的请求记录
```

## 回滚动作（ECS 通知 ROLLBACK 时执行，或本机 C3/C4 失败时主动执行）

```bash
docker stop new-api
# 不要删数据；通知 ECS「NAS_STOPPED」即可，ECS 侧恢复旧实例
```

## 观察期（切换后 1-2 周）

- 每天 1 次看: `docker ps | grep new-api`（Up 状态）、`docker logs new-api --since 24h | grep -iE 'error|fail' | tail -5`
- 磁盘: `du -sh /volume1/docker/newapi/data`（SQLite 日志增长监控）
- 发现异常贴日志回报，不要重启容器（先回报）
