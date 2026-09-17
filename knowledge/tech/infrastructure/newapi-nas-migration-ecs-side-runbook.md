# new-api 迁移 ECS 侧执行手册（OpenClaw/小助用，Boss 审阅）

- **日期**: 2026-09-17 | **执行者**: ECS 上的 OpenClaw（小助） | **协作**: NAS hermes（见 nas-side-runbook）
- **已批准决策**: 方案 A（域名入口留 ECS + frp 反代）/ hermes 执行 NAS 侧 / 在线随切
- **配套文档**: `newapi-nas-migration-nas-side-runbook.md`（整份投喂给 hermes）

## 分工与回合总览

```
回合1  hermes: Phase A 预检 ──────────────── 回报
回合2  hermes: Phase B 影子部署(镜像/桥接/frpc/空库) ─ 回报
回合3  ECS:   验证 3100 通 ───────────────  确认 GO
       Boss:  下达切换指令
回合4  ECS:   Step5 停机+打包+上传 ────────  通知 DATA_UPLOADED(文件名+md5)
回合5  hermes: StepC 拉包+替换+启动+本地验证 ─ 回报 NAS_READY
回合6  ECS:   Step7 nginx 切流+端到端验证 ──  通知 CUTOVER_DONE / ROLLBACK
回合7  hermes: StepD 公网链路确认
```

**影响面（Boss 已知悉）**:
- 回合4-6 之间全平台 AI 调用 502，目标 <2 分钟
- 回合2 B3 重启 frpc：全部 frp 代理瞬断数秒（DSM/WebDAV/hermes 公网入口），自动重连恢复
- 切换完成后 NAS 家宽 = 全部 AI 服务的承重墙（方案 A 已知代价）

---

## Step 3（ECS）：验证 frp 通道（hermes 回报 Phase B 后）

```bash
# 3100 应已由 frps 监听（hermes frpc 注册后出现）
ss -tlnp | grep 3100
curl -s -o /dev/null -w 'via-frp:%{http_code}\n' --connect-timeout 5 http://127.0.0.1:3100/api/status
```
- **预期**: 监听存在 + 200（空库新实例）
- **通过 → 向 Boss 报 GO，等切换指令**

## Step 5（ECS）：停机 + 打包 + 上传（收到 Boss 切换指令后）

```bash
STAMP=$(date +%Y%m%d-%H%M)
# 5.1 停旧实例（SIGTERM 优雅退出，SQLite WAL 自动合并）→ 此刻起全平台 502
docker stop new-api
ls -la /opt/new-api/data/    # 确认 one-api.db-wal 已合并（缩小/消失）

# 5.2 打包（数据 + 3 个附属凭据/备份文件）
tar -czf /tmp/newapi-migration-$STAMP.tar.gz -C /opt/new-api \
  data admin-credentials.txt original-upstream-keys.json price-options-backup.json
md5sum /tmp/newapi-migration-$STAMP.tar.gz && du -h /tmp/newapi-migration-$STAMP.tar.gz

# 5.3 上传 WebDAV（凭据从 nas_backup.sh 引用，不落明文）
WEBDAV_URL=http://127.0.0.1:5005
WU=$(grep '^WEBDAV_USER=' /root/.openclaw/workspace/scripts/backup/nas_backup.sh | cut -d'"' -f2)
WP=$(grep "^WEBDAV_PASS=" /root/.openclaw/workspace/scripts/backup/nas_backup.sh | cut -d"'" -f2)
curl -s -u "$WU:$WP" -X MKCOL "$WEBDAV_URL/aliyun_backup/server-backup/newapi-migration/" # 已存在则405,忽略
curl -s -u "$WU:$WP" -T /tmp/newapi-migration-$STAMP.tar.gz \
  "$WEBDAV_URL/aliyun_backup/server-backup/newapi-migration/newapi-migration-$STAMP.tar.gz" -w 'upload:%{http_code}\n'
# 5.4 校验上传（Content-Length 与本地一致）
curl -s -u "$WU:$WP" -I "$WEBDAV_URL/aliyun_backup/server-backup/newapi-migration/newapi-migration-$STAMP.tar.gz" | grep -i content-length
```
- **预期**: upload:201/204 + Content-Length 匹配
- **完成 → 通知 hermes: `DATA_UPLOADED newapi-migration-$STAMP.tar.gz md5=<值>`**
- 超过 3 分钟未完成 → 直接走回滚 Step R（停机时间超预期）

## Step 7（ECS）：nginx 切流（收到 NAS_READY 后）

```bash
# 7.1 备份 + 原子修改
cp /etc/nginx/conf.d/newapi.conf /etc/nginx/conf.d/newapi.conf.bak-nas-migration
sed -i 's|proxy_pass http://127.0.0.1:3000;|proxy_pass http://127.0.0.1:3100;|' /etc/nginx/conf.d/newapi.conf
grep proxy_pass /etc/nginx/conf.d/newapi.conf    # 目视确认仅此一处变更
nginx -t && nginx -s reload

# 7.2 链路验证（三连）
curl -s -o /dev/null -w 'status-page:%{http_code}\n' --max-time 10 https://api.ygxpro.online/api/status
# 真实 LLM 调用（GLM 渠道 = 覆盖 nginx→frp→NAS→桥接→z.ai 全链）
KEY=$(python3 -c "import json;print(json.load(open('/root/.openclaw/openclaw.json'))['env']['DEEPSEEK_API_KEY'])" 2>/dev/null || grep -o 'NEWAPI_KEY_OPENCLAW=sk-[^ ]*' /root/.openclaw/workspace/knowledge/tech/infrastructure/nas-agent-gateway-cutover.md 2>/dev/null | head -1 | cut -d= -f2)
curl -s --max-time 60 -X POST https://api.ygxpro.online/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"glm-4.7-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":1000}' | head -c 300
curl -s --max-time 60 -X POST https://api.ygxpro.online/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":500}' | head -c 300
```
- **预期**: 200 + 两个请求均返回 choices content 非空
- **最终证据**: 本会话下一轮对话正常（OpenClaw 自身就走网关）+ hermes StepD 回报通过
- **通过 → 通知 hermes: `CUTOVER_DONE`；任一失败且 10 分钟内无法定位 → 回滚**

## Step R（ECS）：回滚（~1 分钟）

```bash
cp /etc/nginx/conf.d/newapi.conf.bak-nas-migration /etc/nginx/conf.d/newapi.conf
nginx -t && nginx -s reload
docker start new-api
curl -s -o /dev/null -w '%{http_code}\n' https://api.ygxpro.online/api/status   # 200 即恢复
```
- 同时通知 hermes: `ROLLBACK`（hermes 执行 docker stop new-api，NAS 新实例下线）
- 数据说明：切换窗口后新产生的用量日志在 NAS 侧，回滚后丢失（令牌/渠道配置无损，已接受）

---

## Phase 3：观察期（1-2 周，切换完成即开始）

- [ ] 巡检脚本 `check_newapi.sh`（每日 08:20）继续打域名，观察连续 7 天全绿
- [ ] 渠道健康检查 cron（每日 09:30）正常投递
- [ ] 新增 3100 连通性检查加入巡检（`ss -tlnp | grep 3100` + curl）
- [ ] hermes 每日回报容器状态/错误日志/数据目录增长
- [ ] ECS 旧环境保留热备：容器（stopped）/镜像/`/opt/new-api/data` 均不删

## Phase 4：收尾（观察期满，Boss 确认后单独执行）

- [ ] ECS: `docker rm new-api && docker rmi calciumion/new-api:latest`
- [ ] ECS: `/opt/new-api` 归档至备份后清理（保留 admin-credentials.txt 副本在归档）
- [ ] 备份脚本 `08-new-api` 段改造：标记已迁 NAS，NAS 本地备份方案另立
- [ ] 更新 `new-api-gateway-deployment.md`（架构图/运维归属）、MEMORY.md、projects.md
- [ ] nas-side-runbook 从 hermes 侧清理（C 步骤中的临时文件 /tmp/newapi-mig-extract）

## 执行日志（2026-09-17）

- 21:15 回合0 ECS 预检: WebDAV 通道 201/201/GET一致/204 ✓，new-api 基线 200/200 ✓
- 21:31 回合1-2 hermes Phase A/B 完成。**偏差记录**: B1 版本锁定失败（上游 latest 已更新至 2026-09-11 构建），Boss 批准接受新版本。影响: 新版首开旧库自动 schema migration（标准升级路径，单向）→ 回滚仍用 ECS 自留旧库+旧容器，不受影响
- 21:40 回合3 ECS 验证: frps 监听 3100 ✓，经 frp 打 NAS /api/status 200（新版本特征响应）✓ → **GO**

## 执行检查单（切流当天）

| # | 动作 | 前置 | 完成标志 |
|---|---|---|---|
| 1 | hermes 投喂 runbook → Phase A | - | 回报 6 项全过 |
| 2 | hermes Phase B | A 通过 | 回报 B1-B4 全过 |
| 3 | ECS 验证 3100 + 报 GO | 2 完成 | 200 |
| 4 | Boss 下切换指令 | Boss 在线 | - |
| 5 | ECS Step5 停机打包上传 | 4 | DATA_UPLOADED 已发 |
| 6 | hermes StepC | 5 | NAS_READY 已发 |
| 7 | ECS Step7 切流 | 6 | CUTOVER_DONE 已发 |
| 8 | 双方 StepD 复验 | 7 | 公网链路 200 + 真实调用 ok |
