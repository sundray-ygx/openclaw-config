#!/bin/bash
# new-api 网关切回: ECS 热备 → NAS（幂等，可重复执行）
# 场景: NAS 故障恢复后（容器/frp/家宽恢复），把流量切回 NAS 主实例
# 前提: NAS new-api 可达（脚本会强制检查 3100，不可达拒绝切换）
# 用法: DRY_RUN=1 bash failover-back-to-nas.sh   只做前置检查与预演
#       bash failover-back-to-nas.sh             正式切换（平滑 reload，零停机）
set -u
CONF=/etc/nginx/conf.d/newapi.conf
LOG=/tmp/newapi-failover-back.log
log(){ echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ---------- 前置检查 ----------
C=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:3100/api/status 2>/dev/null)
[ "$C" = "200" ] || { log "FATAL: NAS 链路 3100 不可达(http=$C)，NAS 未恢复，禁止切换"; exit 1; }

# ---------- DRY_RUN ----------
if [ "${DRY_RUN:-0}" = "1" ]; then
  log "=== DRY_RUN（只读预演） ==="
  log "NAS 链路 3100: 200 ✓"
  log "conf 当前: $(grep -o 'proxy_pass http://127.0.0.1:[0-9]*;' "$CONF")"
  log "将执行: nginx sed 3000→3100 → reload → 公网 status 三连 + LLM 双渠道验证"
  exit 0
fi

# ---------- step1 nginx 切回 3100 ----------
if grep -q 'proxy_pass http://127.0.0.1:3000;' "$CONF"; then
  BAK="$CONF.bak-to-nas-$(date +%Y%m%d-%H%M)"
  cp "$CONF" "$BAK"
  sed -i 's|proxy_pass http://127.0.0.1:3000;|proxy_pass http://127.0.0.1:3100;|' "$CONF"
  grep -q 'proxy_pass http://127.0.0.1:3100;' "$CONF" || { log "FATAL: sed 未生效"; exit 1; }
  nginx -t 2>&1 | tee -a "$LOG"
  if ! nginx -s reload 2>/dev/null; then
    cp "$BAK" "$CONF" && nginx -t >/dev/null 2>&1 && nginx -s reload
    log "FATAL: reload 失败, conf 已还原"; exit 1
  fi
  log "step1 nginx 已切回 3100（平滑 reload）"
elif grep -q 'proxy_pass http://127.0.0.1:3100;' "$CONF"; then
  log "step1 nginx 已指向 3100(幂等跳过)"
else
  log "FATAL: conf 中未找到预期的 proxy_pass 行, 人工检查 $CONF"; exit 1
fi

# ---------- step2 验证 ----------
CODE=000
for i in 1 2 3; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.ygxpro.online/api/status)
  [ "$CODE" = "200" ] && break
  sleep 2
done
[ "$CODE" = "200" ] || { log "FATAL: 公网 status=$CODE，如持续失败执行 failover-to-ecs.sh 应急"; exit 1; }
log "step2 公网 status=$CODE ✓"

KEY=sk-$(python3 -c "import sqlite3;db=sqlite3.connect('/opt/new-api/data/one-api.db');print(db.execute(\"SELECT key FROM tokens WHERE name='ecs-openclaw' AND status=1\").fetchone()[0])" 2>/dev/null)
if [ -n "${KEY#sk-}" ] && [ ${#KEY} -gt 3 ]; then
  for M in deepseek-v4-flash glm-5.3-flash; do
    R=$(curl -s --max-time 90 -X POST https://api.ygxpro.online/v1/chat/completions \
      -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
      -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"reply ok\"}],\"max_tokens\":1000}")
    echo "$R" | grep -q '"choices"' && log "step2 LLM $M: OK" || log "WARN step2 LLM $M: FAIL $(echo "$R" | head -c 150)"
  done
else
  log "WARN step2: key 提取失败, 跳过 LLM 验证（status 页已确认链路）"
fi

# ---------- step3 提示 ----------
log "提示: ECS 热备容器仍在运行（可保留常驻，或 docker stop new-api 省内存）"
log "提示: failover 期间产生的用量数据在 ECS 旧库中，如需合并由 hermes 侧另行处理（非必需）"
log "=== BACK_TO_NAS_DONE: 服务已切回 NAS 主实例 ==="
exit 0
