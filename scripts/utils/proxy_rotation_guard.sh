#!/bin/bash
# proxy_rotation_guard.sh — sing-box 轮转守卫（crontab: 2 8 * * *，北京 08:02）
# 背景（2026-11-04 诊断）：机场自 11-02 起每日 00:00 UTC 轮转入口 IP，旧 IP 立即拒新连接；
#   sing-box DNS 缓存 ≤30min 期间持续拨旧 IP → 新建会话全部 i/o timeout（北京 08:00-08:30 死窗）。
#   urltest 健康检查走 anytls 存量会话被蒙蔽，不触发切节点，需外部强制重启重新解析。
# 2026-11-05 方案 B（Boss 批准）：双目标探活，任一失败即重启。
#   盲区修正：单探 gstatic 时 anytls 会话复用让存量连接蒙混过关（11-05 08:02 误判 healthy），
#   github atom 必走新建会话路径，能探出死窗。任一失败 → 二次确认 → docker restart → 双目标复测。
#   代理健康时零动作；幂等可手动重跑。持续故障由 F2 看门狗（heartbeat_syscheck.sh）负责告警。
# 日志：stdout 由 crontab 重定向到 /var/log/proxy-rotation-guard.log
# 详见 knowledge/tech/infrastructure/2026-11-04-singbox-morning-window-outage.md

# 探活目标: name|url|期望http_code|最小body字节|超时秒
TARGETS=(
  "gstatic|https://www.gstatic.com/generate_204|204|0|10"
  "github|https://github.com/NousResearch/hermes-agent/releases.atom|200|1000|15"
)
ts() { date '+%F %T'; }

probe() {  # $1=name $2=url $3=expect_code $4=min_size $5=timeout; 0=通 1=死
  local name="$1" url="$2" expect="$3" min="$4" tmo="$5" out code size
  out=$(curl -s --socks5-hostname 127.0.0.1:1080 -m "$tmo" -o /dev/null \
        -w '%{http_code} %{size_download}' "$url" 2>/dev/null)
  code=${out%% *}; size=${out##* }
  if [ "$code" = "$expect" ] && [ "${size:-0}" -ge "$min" ] 2>/dev/null; then
    return 0
  fi
  echo "[$(ts)] probe FAIL: $name -> code=${code:-none} size=${size:-0}B (expect=$expect min=${min}B)"
  return 1
}

probe_all() {  # 0=全通 1=有失败（失败项打日志）
  local failed=0 t name url expect min tmo
  for t in "${TARGETS[@]}"; do
    IFS='|' read -r name url expect min tmo <<< "$t"
    probe "$name" "$url" "$expect" "$min" "$tmo" || failed=1
  done
  return $failed
}

echo "[$(ts)] guard start (dual-target: gstatic + github-atom)"
if probe_all; then
  echo "[$(ts)] proxy healthy (both targets), no action"
  exit 0
fi
sleep 5  # 二次确认，避免瞬时抖动误杀
if probe_all; then
  echo "[$(ts)] proxy recovered on retry (transient blip), no action"
  exit 0
fi

echo "[$(ts)] proxy DEAD (rotation window suspected) -> restarting sing-box"
if ! docker ps -a --format '{{.Names}}' | grep -qx 'sing-box'; then
  echo "[$(ts)] ERROR: sing-box container not found, abort"
  exit 1
fi
docker restart sing-box
sleep 8
ok=0
for i in 1 2 3; do
  if probe_all; then ok=1; break; fi
  echo "[$(ts)] re-probe #$i still dead, wait 10s"
  sleep 10
done
if [ "$ok" = 1 ]; then
  echo "[$(ts)] RECOVERED after restart (both targets pass)"
else
  echo "[$(ts)] STILL DEAD after restart (公共DNS边缘缓存可能仍持旧记录，死窗自然过期即恢复; 持续故障由F2看门狗告警)"
fi
