#!/bin/bash
# new-api 迁移 ECS 编排脚本 v2（零 LLM 依赖 + 自动回滚）
# 用法: DRY_RUN=1 bash newapi-cutover-ecs.sh   干跑验证
#       bash newapi-cutover-ecs.sh             正式切换（阻塞约 3-6 分钟）
set -u

LOG=/tmp/newapi-cutover-ecs.log
WEBDAV_URL=http://127.0.0.1:5005
BACKUP_SH=/root/.openclaw/workspace/scripts/backup/nas_backup.sh
WU=$(grep '^WEBDAV_USER=' "$BACKUP_SH" | cut -d'"' -f2)
WP=$(grep "^WEBDAV_PASS=" "$BACKUP_SH" | cut -d"'" -f2)
SIGURL="$WEBDAV_URL/aliyun_backup/server-backup/newapi-migration"
NGINX_CONF=/etc/nginx/conf.d/newapi.conf
NGINX_BAK=/etc/nginx/conf.d/newapi.conf.bak-nas-migration
READY_TIMEOUT=600
INFLIGHT=/tmp/.newapi-cutover-inflight
FAIL=0

log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

rollback(){
  log "=== ROLLBACK: $1 ==="
  rm -f "$INFLIGHT"
  if [ -f "$NGINX_BAK" ]; then
    cp "$NGINX_BAK" "$NGINX_CONF" && nginx -t 2>/dev/null && nginx -s reload 2>/dev/null \
      && log "nginx 已还原" || log "WARN: nginx 还原异常，需人工检查"
  fi
  docker start new-api 2>/dev/null && log "旧容器已启动" || log "WARN: docker start 失败，需人工检查"
  sleep 3
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:3000/api/status)
  log "=== ROLLBACK 完成, 旧实例 local-3000=$CODE (预期200) ==="
}
trap 'if [ -f "$INFLIGHT" ]; then rollback "脚本异常中断(trap)"; fi' EXIT

verify_llm(){
  local KEY R M FAILV=0
  KEY=sk-$(python3 -c "import sqlite3;db=sqlite3.connect('/opt/new-api/data/one-api.db');print(db.execute(\"SELECT key FROM tokens WHERE name='ecs-openclaw' AND status=1\").fetchone()[0])" 2>/dev/null)
  if [ -z "${KEY#sk-}" ] || [ ${#KEY} -le 3 ]; then
    log "WARN: openclaw key 提取失败，跳过 ECS 侧 LLM 双重验证（hermes NAS_READY 已含真实验证）"
    return 0
  fi
  for M in deepseek-v4-flash glm-4.7-flash; do
    R=$(curl -s --max-time 90 -X POST https://api.ygxpro.online/v1/chat/completions \
      -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
      -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"reply ok\"}],\"max_tokens\":1000}")
    if echo "$R" | grep -q '"choices"'; then log "LLM 验证 $M: OK"
    else log "LLM 验证 $M: FAIL $(echo "$R" | head -c 200)"; FAILV=1; fi
  done
  return $FAILV
}

# ---------- DRY_RUN ----------
if [ "${DRY_RUN:-0}" = "1" ]; then
  log "=== DRY_RUN 模式：不触碰容器/nginx/真信号 ==="
  T=$(mktemp)
  cp "$NGINX_CONF" "$T"
  sed -i 's|proxy_pass http://127.0.0.1:3000;|proxy_pass http://127.0.0.1:3100;|' "$T"
  grep -q 'proxy_pass http://127.0.0.1:3100;' "$T" && ! grep -q 'proxy_pass http://127.0.0.1:3000;' "$T" \
    && log "dry1 sed 表达式: OK" || { log "dry1 sed 表达式: FAIL"; exit 1; }
  K=sk-$(python3 -c "import sqlite3;db=sqlite3.connect('/opt/new-api/data/one-api.db');print(db.execute(\"SELECT key FROM tokens WHERE name='ecs-openclaw' AND status=1\").fetchone()[0])" 2>/dev/null)
  [ ${#K} -gt 3 ] && log "dry2 key 提取: OK(len=${#K})" || log "dry2 key 提取: EMPTY(运行时将跳过LLM双重验证,依赖hermes验证)"
  echo "dryrun-$(date +%s)" > /tmp/dry-mig.txt
  C=$(curl -s -u "$WU:$WP" -T /tmp/dry-mig.txt "$SIGURL/dry-run-test.txt" -w '%{http_code}' -o /dev/null)
  [ "$C" = "201" ] || [ "$C" = "204" ] && log "dry3 WebDAV PUT: OK($C)" || { log "dry3 WebDAV PUT: FAIL($C)"; exit 1; }
  G=$(curl -s -u "$WU:$WP" -o /dev/null -w '%{http_code}' --max-time 10 "$SIGURL/dry-run-test.txt")
  [ "$G" = "200" ] && log "dry4 WebDAV GET: OK" || { log "dry4 WebDAV GET: FAIL($G)"; exit 1; }
  curl -s -u "$WU:$WP" -X DELETE "$SIGURL/dry-run-test.txt" -o /dev/null
  rm -f /tmp/dry-mig.txt "$T"
  log "=== DRY_RUN 全部通过 ==="
  exit 0
fi

# ---------- 正式切换 ----------
log "=== new-api 切换开始 ==="
touch "$INFLIGHT"

log "step1 停旧实例"
docker stop -t 30 new-api >/dev/null || { rollback "docker stop 失败"; exit 1; }
sleep 2
[ "$(docker inspect -f '{{.State.Running}}' new-api 2>/dev/null)" = "false" ] || { rollback "容器未停止"; exit 1; }
log "step1 容器已停止, 502 窗口开始"

log "step2 打包"
[ -f /opt/new-api/data/one-api.db ] || { rollback "one-api.db 不存在"; exit 1; }
STAMP=$(date +%Y%m%d-%H%M)
PKG=newapi-migration-$STAMP.tar.gz
tar -czf /tmp/$PKG -C /opt/new-api data admin-credentials.txt original-upstream-keys.json price-options-backup.json \
  || { rollback "tar 失败"; exit 1; }
MD5=$(md5sum /tmp/$PKG | awk '{print $1}')
log "step2 打包完成 $PKG ($(du -h /tmp/$PKG | cut -f1)) md5=$MD5"

log "step3 清理旧信号 + 上传"
curl -s -u "$WU:$WP" -X DELETE "$SIGURL/NAS_READY" -o /dev/null
curl -s -u "$WU:$WP" -X DELETE "$SIGURL/DATA_READY" -o /dev/null
C=$(curl -s -u "$WU:$WP" -T /tmp/$PKG "$SIGURL/$PKG" -w '%{http_code}' -o /dev/null)
{ [ "$C" = "201" ] || [ "$C" = "204" ]; } || { rollback "上传失败 http=$C"; exit 1; }
log "step3 数据包已上传 ($C)"

C=$(echo "$PKG $MD5" | curl -s -u "$WU:$WP" -T - "$SIGURL/DATA_READY" -w '%{http_code}' -o /dev/null)
{ [ "$C" = "201" ] || [ "$C" = "204" ]; } || { rollback "DATA_READY 信号写入失败 http=$C"; exit 1; }
log "step3 DATA_READY 已发, 等待 hermes..."

log "step4 轮询 NAS_READY (超时 ${READY_TIMEOUT}s)"
ELAPSED=0
while [ "$ELAPSED" -lt "$READY_TIMEOUT" ]; do
  CODE=$(curl -s -u "$WU:$WP" -o /tmp/nasready.check -w '%{http_code}' --max-time 10 "$SIGURL/NAS_READY")
  if [ "$CODE" = "200" ]; then
    log "step4 收到 NAS_READY (内容: $(cat /tmp/nasready.check))"
    break
  fi
  sleep 3; ELAPSED=$((ELAPSED+3))
done
[ "$ELAPSED" -lt "$READY_TIMEOUT" ] || { rollback "等待 NAS_READY 超时 ${READY_TIMEOUT}s"; exit 1; }

log "step5 nginx 切流"
cp "$NGINX_CONF" "$NGINX_BAK" || { rollback "nginx 备份失败"; exit 1; }
sed -i 's|proxy_pass http://127.0.0.1:3000;|proxy_pass http://127.0.0.1:3100;|' "$NGINX_CONF"
grep -q 'proxy_pass http://127.0.0.1:3100;' "$NGINX_CONF" || { rollback "sed 未生效"; exit 1; }
nginx -t 2>&1 | tee -a "$LOG"
if ! nginx -s reload 2>/dev/null; then rollback "nginx reload 失败"; exit 1; fi
log "step5 nginx 已切至 3100"

log "step6 端到端验证"
OK=0
for i in 1 2 3; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.ygxpro.online/api/status)
  [ "$CODE" = "200" ] && OK=1 && break
  sleep 2
done
[ "$OK" = "1" ] || { rollback "公网 status 页非 200 (last=$CODE)"; exit 1; }
log "step6 公网 status=200 ✓"

verify_llm || { rollback "LLM 双重验证失败"; exit 1; }

rm -f "$INFLIGHT" /tmp/nasready.check /tmp/$PKG
log "=== CUTOVER_DONE === 502 窗口关闭, new-api 已运行于 NAS"
exit 0
