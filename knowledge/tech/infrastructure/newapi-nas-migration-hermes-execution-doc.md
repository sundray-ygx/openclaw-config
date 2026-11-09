# new-api 迁移 · hermes 执行文档（NAS 侧 Step C）

- **日期**: 2026-09-17 | **执行者**: NAS hermes | **协调**: ECS OpenClaw（小助）| **批准**: Boss
- **读完本文档后按顺序执行 Step 1 / Step 2，共两条命令，不需要任何其他判断。**

## 一、背景与意图（30 秒）

AI 网关 new-api 从 ECS Docker 迁移到本机（NAS）Docker。前置 Phase A/B 已完成：桥接容器 `newapi-bridge`(172.17.0.1:8081)、frpc 3100 代理、new-api 容器（09-11 版本）均已就绪并验证。

**接下来发生的时序**：

1. ECS 侧将停掉旧网关并打包配置数据上传到本机备份目录，同时写一个 `DATA_READY` 信号文件（内含数据包文件名和 md5）
2. **本机的任务**：后台脚本轮询等待该信号 → 拉取数据包 → md5 校验 → 替换 new-api 数据 → 重启容器 → 双渠道真实调用验证 → 写 `NAS_READY` 信号
3. ECS 脚本收到 `NAS_READY` 后自动切 nginx 流量到本机，迁移完成

**为什么脚本必须后台运行、为什么不需要你在场**：
502 窗口内（约 2-3 分钟），本机的 LLM 出口（api.ygxpro.online）也会中断——**你（hermes）自己也会连不上大模型**。因此整个脚本设计为零 LLM 依赖：启动后它独立运行，你不需要观察、不需要推理、不需要任何后续动作。本步执行完成即你的任务结束。

## 二、执行步骤

### Step 1：创建脚本文件（原样执行，不要修改内容）

```bash
cat > /root/newapi-cutover.sh <<'SCRIPT_EOF'
#!/bin/bash
# new-api 迁移 hermes 侧 C 脚本 v2（轮询 DATA_READY → 拉包 → 替换 → 启动 → 验证 → NAS_READY）
set -u
LOG=/tmp/newapi-cutover.log
BACKUP_DIR="${BACKUP_DIR:-}"
SIG_SUBDIR="server-backup/newapi-migration"
WAIT_TIMEOUT=1800
WEBDAV_LOCAL=http://127.0.0.1:5005
WU="${WEBDAV_USER:-}"
WP="${WEBDAV_PASS:-}"
NAS_DATA=/volume1/docker/newapi/data
FAIL_EXIT(){ log "FATAL: $1"; exit 1; }
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

log "=== hermes C 脚本启动 (pid=$$) ==="

if [ -z "$BACKUP_DIR" ]; then
  BACKUP_DIR=$(ls -d /volume*/*aliyun_backup* 2>/dev/null | head -1)
fi
MODE=""
if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR/$SIG_SUBDIR" ]; then
  MODE="fs"; PKG_DIR="$BACKUP_DIR/$SIG_SUBDIR"
elif [ -n "$WU" ] && [ -n "$WP" ]; then
  MODE="webdav"; PKG_DIR="$WEBDAV_LOCAL/aliyun_backup/$SIG_SUBDIR"
else
  FAIL_EXIT "找不到 aliyun_backup 目录且无 WebDAV 凭据。请把 A6 探测到的目录填入 BACKUP_DIR 后重跑"
fi
log "0 数据通道: $MODE → $PKG_DIR"

log "1 等待 DATA_READY (超时 ${WAIT_TIMEOUT}s)..."
START=$(date +%s)
while true; do
  if [ "$MODE" = "fs" ] && [ -f "$PKG_DIR/DATA_READY" ]; then
    CONTENT=$(cat "$PKG_DIR/DATA_READY")
    break
  elif [ "$MODE" = "webdav" ]; then
    CODE=$(curl -s -u "$WU:$WP" -o /tmp/dr.check -w '%{http_code}' --max-time 10 "$PKG_DIR/DATA_READY")
    [ "$CODE" = "200" ] && CONTENT=$(cat /tmp/dr.check) && break
  fi
  NOW=$(date +%s)
  [ $((NOW-START)) -gt $WAIT_TIMEOUT ] && FAIL_EXIT "等待 DATA_READY 超时"
  sleep 5
done
PKG=$(echo "$CONTENT" | awk '{print $1}')
MD5=$(echo "$CONTENT" | awk '{print $2}')
[ -n "$PKG" ] && [ -n "$MD5" ] || FAIL_EXIT "DATA_READY 内容异常: $CONTENT"
log "1 收到 DATA_READY: $PKG md5=$MD5 → 502 窗口计时开始，动作要快"

if [ "$MODE" = "fs" ]; then
  cp "$PKG_DIR/$PKG" /tmp/$PKG || FAIL_EXIT "拉包失败"
else
  curl -s -u "$WU:$WP" "$PKG_DIR/$PKG" -o /tmp/$PKG || FAIL_EXIT "拉包失败"
fi
log "2 拉包完成 ($(du -h /tmp/$PKG | cut -f1))"

ACTUAL=$(md5sum /tmp/$PKG | awk '{print $1}')
[ "$ACTUAL" = "$MD5" ] || FAIL_EXIT "md5 不匹配 expect=$MD5 actual=$ACTUAL"
log "3 md5 校验通过"

docker stop new-api >/dev/null 2>&1
mkdir -p /tmp/newapi-mig-extract && rm -rf /tmp/newapi-mig-extract && mkdir -p /tmp/newapi-mig-extract
tar -xzf /tmp/$PKG -C /tmp/newapi-mig-extract || FAIL_EXIT "解压失败"
[ -f /tmp/newapi-mig-extract/data/one-api.db ] || FAIL_EXIT "包内无 data/one-api.db"
rm -f "$NAS_DATA"/one-api.db*
cp -a /tmp/newapi-mig-extract/data/one-api.db* "$NAS_DATA/" || FAIL_EXIT "数据替换失败"
docker start new-api || FAIL_EXIT "docker start 失败"
sleep 6
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://172.17.0.1:3000/api/status)
[ "$CODE" = "200" ] || FAIL_EXIT "3000 status=$CODE"
log "4 数据已替换, new-api 启动, 本地 3000 status=200"

KEY=*** '^NEWAPI_API_KEY=' ~/.hermes/.env | cut -d= -f2)
[ -n "$KEY" ] || FAIL_EXIT "无法从 ~/.hermes/.env 提取 NEWAPI_API_KEY"
T1=$(curl -s --max-time 60 -X POST http://172.17.0.1:3000/v1/chat/completions \
  -H "Authorization: Bearer ***" -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":500}')
echo "$T1" | grep -q '"choices"' || FAIL_EXIT "deepseek 渠道失败: $(echo "$T1" | head -c 200)"
log "5a deepseek 渠道 OK"
T2=$(curl -s --max-time 90 -X POST http://172.17.0.1:3000/v1/chat/completions \
  -H "Authorization: Bearer ***" -H 'Content-Type: application/json' \
  -d '{"model":"glm-4.7-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":1000}')
echo "$T2" | grep -q '"choices"' || FAIL_EXIT "glm 渠道失败: $(echo "$T2" | head -c 200)"
log "5b glm 渠道 OK（桥接链路通）"

if [ "$MODE" = "fs" ]; then
  date +%s > "$PKG_DIR/NAS_READY"
else
  echo "$(date +%s)" | curl -s -u "$WU:$WP" -T - "$PKG_DIR/NAS_READY" -o /dev/null
fi
log "6 NAS_READY 已写, hermes 侧完成"
log "=== HERMES_SIDE_DONE ==="
SCRIPT_EOF
bash -n /root/newapi-cutover.sh && echo "STEP1_OK 语法通过" || echo "STEP1_FAIL 语法错误，停止并回报"
```

### Step 2：后台启动脚本（进入等待状态，此刻不影响任何服务）

```bash
BACKUP_DIR=$(ls -d /volume*/*aliyun_backup* 2>/dev/null | head -1) nohup bash /root/newapi-cutover.sh > /tmp/newapi-cutover-console.log 2>&1 &
sleep 2 && tail -5 /tmp/newapi-cutover.log
```

**Step 2 成功标志**（日志应显示三行）：

```
=== hermes C 脚本启动 (pid=xxxx) ===
0 数据通道: fs → /volume1/aliyun_backup/server-backup/newapi-migration
1 等待 DATA_READY (超时 1800s)...
```

看到以上日志即执行完毕。向 Boss 回报「hermes 已进入等待状态」，之后**不再需要任何操作**。

## 三、行为说明与红线

| 项 | 说明 |
|---|---|
| 等待时长 | DATA_READY 最长等 30 分钟；超时脚本自动退出（FATAL），无任何副作用，Boss 决定是否重投喂 |
| 502 窗口内 | 脚本全自动（拉包→校验→替换→启动→验证→写信号），**你无需也无法介入** |
| 成功标志 | 日志出现 `=== HERMES_SIDE_DONE ===`；全日志在 `/tmp/newapi-cutover.log` |
| 失败行为 | 任一环节 FATAL 退出且**不写** NAS_READY；ECS 侧轮询超时（10 分钟）后自动回滚到 ECS 旧实例，服务自动恢复 |
| 🚫 红线 1 | 除本脚本外，不要手动操作 new-api 容器与 `/volume1/docker/newapi/data` |
| 🚫 红线 2 | 不要删除/修改备份目录中 ECS 传来的任何文件（数据包、DATA_READY、NAS_READY） |
| 🚫 红线 3 | 若 Step 1 语法检查失败或 Step 2 日志异常，**停下回报**，不要自行修改脚本逻辑 |
