# ECS new-api 主网关部署（NAS 小群生成 2026-09-27）

> 目标：ECS 上部署 new-api 作为主网关，api.ygxpro.online 指向 ECS 本地；NAS new-api 降为热备。
> 执行方式：按顺序把本文档喂给 ECS OpenClaw（或你手工执行），每步完成后勾选。

## 前置确认
- [ ] ECS docker 可用：`docker version`
- [ ] 3000/8081 端口空闲：`ss -tlnp | grep -E ':3000|:8081'`（无输出即空闲）

## 第 1 步：部署 new-api 容器

```bash
docker run -d --name new-api --restart always \
  -p 127.0.0.1:3000:3000 \
  -v /volume1/docker/newapi/data:/data 2>/dev/null || \
docker run -d --name new-api --restart always \
  -p 127.0.0.1:3000:3000 \
  -v /root/newapi-data:/data \
  -e TZ=Asia/Shanghai \
  --memory 1g \
  --log-driver json-file --log-opt max-size=20m --log-opt max-file=3 \
  calciumion/new-api:latest
```
> 说明：数据卷优先放 NAS 挂载路径（若 ECS 有挂载），否则 /root/newapi-data。
> 只绑 127.0.0.1，不暴露公网——公网流量只经 nginx 反代。
> 内存 1G + json-file 日志是 2026-09-27 NAS 僵死事故的教训配置，勿省略。

- [ ] 启动成功：`docker ps --filter name=new-api`
- [ ] 健康检查：`curl -s http://127.0.0.1:3000/api/status`（返回 JSON 即 OK）

## 第 2 步：初始化渠道/令牌

1. 把附带的 `ecs_seed.sql` 文件放到 ECS `/root/ecs_seed.sql`
2. 执行：

```bash
docker exec new-api sh -c 'which sqlite3 || apk add --no-cache sqlite >/dev/null 2>&1'
docker cp /root/ecs_seed.sql new-api:/tmp/ecs_seed.sql
docker exec new-api sqlite3 /data/one-api.db < /tmp/ecs_seed.sql
docker restart new-api
sleep 8
curl -s http://127.0.0.1:3000/api/status
```

- [ ] 管理后台（先经 nginx 或 SSH 隧道访问）确认：渠道 3 条全启用、令牌 8 条存在
- [ ] 渠道 1/2 的 base_url 指向 **ECS 本地 bridge**（`http://172.17.0.1:8081/zai`、`http://172.17.0.1:8081/volc`）

> ⚠️ **2026-09-27 执行修正（重要）**：本文档原写"渠道 1/2 改为上游公网直连"是**错误的**。
> new-api(type=1) 固定拼接 `/v1/chat/completions`，直连 z.ai/ark 的 base_url 会拼出
> `/paas/v4/v1/chat/completions` → 上游 404。ECS 上本就存在 bridge
> `/etc/nginx/conf.d/newapi-upstream.conf`（监听 docker0 172.17.0.1:8081），
> 它把 `/zai/v1/`→`api.z.ai/api/coding/paas/v4/`、`/volc/v1/`→`ark.../api/coding/v3/`。
> 因此正确配置是走 bridge，bridge 必须保留。

## 第 3 步：nginx upstream 切换（域名指向 ECS 本地）

```bash
# 找到 api.ygxpro.online 的 server 块
grep -rn '3100\|api.ygxpro' /etc/nginx/ 2>/dev/null | head
# 备份后把 proxy_pass / upstream 中的 3100 改为 127.0.0.1:3000，例如:
#   proxy_pass http://127.0.0.1:3000;   (原 http://127.0.0.1:3100)
cp -r /etc/nginx /root/nginx-backup-$(date +%Y%m%d)
nginx -t && systemctl reload nginx
```

- [ ] 公网验证：`curl -s https://api.ygxpro.online/api/status`（从 ECS 本机测）
- [ ] NAS 侧验证（我会做）：探活 200

## 第 4 步：failover-probe（ECS 故障自动切回 NAS 热备）

1. 把附带的 `ecs-failover-probe.sh` 放到 ECS `/root/scripts/utils/ecs-failover-probe.sh`
2. `chmod +x` 后加入 root crontab：`*/5 * * * * /root/scripts/utils/ecs-failover-probe.sh >/dev/null 2>&1`
3. 脚本逻辑（与 NAS 侧同构，已实战验证）：
   - 探活 `127.0.0.1:3000/api/status`，连续 2 次失败 → sed nginx 3000→3100 + reload（域名回落 NAS 热备）+ 飞书红卡
   - 恢复探测成功 → 绿卡提示人工切回（`sed` 3100→3000 + reload），不自动切回防抖动
4. 飞书推送：ECS 侧改造为复用**现有飞书应用机器人**（tenant_access_token + im/v1/messages，
   与 `scripts/backup/nas_backup.sh` 同一套凭证），不再需要自定义 webhook 占位。
5. 前置依赖：ECS 上 `newapi-upstream.conf`（8081 bridge）必须在位，否则渠道 1/2 会 404。

- [ ] 手动演练：`docker stop new-api` → 5-10 分钟内应收到红卡且 `curl https://api.ygxpro.online/api/status` 仍 200（走 NAS）
- [ ] `docker start new-api` → 收到绿卡 → 执行脚本内给出的切回命令 → 确认 200

## 回滚方案
任一步异常：nginx upstream 改回 3100 + reload，即回到现状；`docker rm -f new-api` 清理。
