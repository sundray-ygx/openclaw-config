#!/bin/bash
# new-api 迁移 hermes 侧 C 脚本 v2（轮询 DATA_READY → 拉包 → 替换 → 启动 → 验证 → NAS_READY）
# 投喂后以 nohup 后台运行，全程零 LLM 依赖；日志: /tmp/newapi-cutover.log
# 用法: BACKUP_DIR 可先填 A6 探测到的目录，留空则自动探测
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

# 0. 探测备份目录（文件系统优先，免凭据）
if [ -z "$BACKUP_DIR" ]; then
  BACKUP_DIR=$(ls -d /volume*/*aliyun_backup* 2>/dev/null | head -1)
fi
MODE=""
if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR/$SIG_SUBDIR" ]; then
  MODE="fs"; PKG_DIR="$BACKUP_DIR/$SIG_SUBDIR"
elif [ -n "$WU" ] && [ -n "$WP" ]; then
  MODE="webdav"; PKG_DIR="$WEBDAV_LOCAL/aliyun_backup/$SIG_SUBDIR"
else
  FAIL_EXIT "找不到 aliyun_backup 目录且无 WebDAV 凭据。请把 A6 探测到的目录填入脚本 BACKUP_DIR 后重跑"
fi
log "0 数据通道: $MODE → $PKG_DIR"

# 1. 轮询等待 DATA_READY
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

# 2. 拉包
if [ "$MODE" = "fs" ]; then
  cp "$PKG_DIR/$PKG" /tmp/$PKG || FAIL_EXIT "拉包失败"
else
  curl -s -u "$WU:$WP" "$PKG_DIR/$PKG" -o /tmp/$PKG || FAIL_EXIT "拉包失败"
fi
log "2 拉包完成 ($(du -h /tmp/$PKG | cut -f1))"

# 3. md5 校验
ACTUAL=$(md5sum /tmp/$PKG | awk '{print $1}')
[ "$ACTUAL" = "$MD5" ] || FAIL_EXIT "md5 不匹配 expect=$MD5 actual=$ACTUAL"
log "3 md5 校验通过"

# 4. 替换数据 + 启动
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

# 5. 双渠道真实调用（deepseek=直连链路 / glm=桥接链路, 本迁移关键验证点）
KEY=$(grep '^NEWAPI_API_KEY=' ~/.hermes/.env | cut -d= -f2)
[ -n "$KEY" ] || FAIL_EXIT "无法从 ~/.hermes/.env 提取 NEWAPI_API_KEY"
T1=$(curl -s --max-time 60 -X POST http://172.17.0.1:3000/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":500}')
echo "$T1" | grep -q '"choices"' || FAIL_EXIT "deepseek 渠道失败: $(echo "$T1" | head -c 200)"
log "5a deepseek 渠道 OK"
T2=$(curl -s --max-time 90 -X POST http://172.17.0.1:3000/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"glm-4.7-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":1000}')
echo "$T2" | grep -q '"choices"' || FAIL_EXIT "glm 渠道失败: $(echo "$T2" | head -c 200)"
log "5b glm 渠道 OK（桥接链路通）"

# 6. 写 NAS_READY 信号
if [ "$MODE" = "fs" ]; then
  date +%s > "$PKG_DIR/NAS_READY"
else
  echo "$(date +%s)" | curl -s -u "$WU:$WP" -T - "$PKG_DIR/NAS_READY" -o /dev/null
fi
log "6 NAS_READY 已写, hermes 侧完成"
log "=== HERMES_SIDE_DONE ==="
