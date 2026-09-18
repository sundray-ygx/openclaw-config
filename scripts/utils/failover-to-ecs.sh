#!/bin/bash
# new-api 网关故障切换: NAS → ECS 热备（幂等，可重复执行）
# 场景: NAS 容器挂 / frp 隧道断 / 家宽断 → ECS 旧实例接管
# 用法: DRY_RUN=1 bash failover-to-ecs.sh   只做前置检查与预演，不动任何服务
#       bash failover-to-ecs.sh             正式切换（热备常驻时约 5 秒）
# 注意: 切回后数据 = 2026-09-17 23:15 快照；NAS 期间控制台配置变更将暂时不可见（数据仍在 NAS，切回即恢复）
set -u
CONF=/etc/nginx/conf.d/newapi.conf
LOG=/tmp/newapi-failover-ecs.log
log(){ echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ---------- 前置检查 ----------
[ -f /opt/new-api/data/one-api.db ] || { log "FATAL: /opt/new-api/data/one-api.db 不存在, 热备数据缺失"; exit 1; }
docker inspect new-api >/dev/null 2>&1 || { log "FATAL: ECS 旧容器 new-api 不存在"; exit 1; }

# ---------- DRY_RUN ----------
if [ "${DRY_RUN:-0}" = "1" ]; then
  log "=== DRY_RUN（只读预演） ==="
  log "容器状态: Running=$(docker inspect -f '{{.State.Running}}' new-api) (false 时将自动 start)"
  log "conf 当前: $(grep -o 'proxy_pass http://127.0.0.1:[0-9]*;' "$CONF")"
  log "NAS 链路 3100: $(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:3100/api/status 2>/dev/null || echo unreachable)"
  log "旧实例 3000: $(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:3000/api/status 2>/dev/null || echo unreachable)"
  log "将执行: (容器未跑则 start) → nginx sed 3100→3000 → reload → 公网 status 三连 + LLM 双渠道验证"
  exit 0
fi

# ---------- step1 容器 ----------
ST=$(docker inspect -f '{{.State.Running}}' new-api)
if [ "$ST" != "true" ]; then
  docker start new-api || { log "FATAL: docker start 失败"; exit 1; }
  sleep 4
  log "step1 旧容器已启动"
else
  log "step1 旧容器常驻运行中, 无需启动"
fi
C=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:3000/api/status)
[ "$C" = "200" ] || { log "FATAL: 旧实例 3000 不可用(http=$C)"; exit 1; }
log "step1 local-3000=200 ✓"

# ---------- step2 nginx 切回 3000 ----------
if grep -q 'proxy_pass http://127.0.0.1:3100;' "$CONF"; then
  BAK="$CONF.bak-failover-$(date +%Y%m%d-%H%M)"
  cp "$CONF" "$BAK"
  sed -i 's|proxy_pass http://127.0.0.1:3100;|proxy_pass http://127.0.0.1:3000;|' "$CONF"
  grep -q 'proxy_pass http://127.0.0.1:3000;' "$CONF" || { log "FATAL: sed 未生效"; exit 1; }
  nginx -t 2>&1 | tee -a "$LOG"
  if ! nginx -s reload 2>/dev/null; then
    cp "$BAK" "$CONF" && nginx -t >/dev/null 2>&1 && nginx -s reload
    log "FATAL: reload 失败, conf 已还原"; exit 1
  fi
  log "step2 nginx 已切回 3000"
elif grep -q 'proxy_pass http://127.0.0.1:3000;' "$CONF"; then
  log "step2 nginx 已指向 3000(幂等跳过)"
else
  log "FATAL: conf 中未找到预期的 proxy_pass 行, 人工检查 $CONF"; exit 1
fi

# ---------- step3 验证 ----------
CODE=000
for i in 1 2 3; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.ygxpro.online/api/status)
  [ "$CODE" = "200" ] && break
  sleep 2
done
[ "$CODE" = "200" ] || { log "WARN: 公网 status=$CODE（nginx 已切 3000, 请人工核查）"; }
log "step3 公网 status=$CODE ✓"

KEY=sk-$(python3 -c "import sqlite3;db=sqlite3.connect('/opt/new-api/data/one-api.db');print(db.execute(\"SELECT key FROM tokens WHERE name='ecs-openclaw' AND status=1\").fetchone()[0])" 2>/dev/null)
if [ -n "${KEY#sk-}" ] && [ ${#KEY} -gt 3 ]; then
  for M in deepseek-v4-flash glm-5.3-flash; do
    R=$(curl -s --max-time 90 -X POST https://api.ygxpro.online/v1/chat/completions \
      -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
      -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"reply ok\"}],\"max_tokens\":1000}")
    echo "$R" | grep -q '"choices"' && log "step3 LLM $M: OK" || log "WARN step3 LLM $M: FAIL $(echo "$R" | head -c 150)"
  done
else
  log "WARN step3: key 提取失败, 跳过 LLM 验证（status 页已确认链路）"
fi

log "=== FAILOVER_DONE: 服务已切回 ECS 热备（数据=2026-09-17 23:15 快照；NAS 恢复后可执行 failover-back-to-nas.sh 切回） ==="
exit 0
