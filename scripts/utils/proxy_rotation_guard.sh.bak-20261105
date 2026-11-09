#!/bin/bash
# proxy_rotation_guard.sh — sing-box 轮转守卫（crontab: 2 8 * * *，北京 08:02）
# 背景（2026-11-04 诊断）：机场自 11-02 起每日 00:00 UTC 轮转入口 IP，旧 IP 立即拒新连接；
#   sing-box DNS 缓存 ≤30min 期间持续拨旧 IP → 新建会话全部 i/o timeout（北京 08:00-08:30 死窗）。
#   urltest 健康检查走 anytls 存量会话被蒙蔽，不触发切节点，需外部强制重启重新解析。
# 动作：探活 socks5 1080 → 失败（二次确认）则 docker restart sing-box → 复测 → 落日志。
#   代理健康时零动作；幂等可手动重跑。持续故障由 F2 看门狗（heartbeat_syscheck.sh）负责告警。
# 日志：stdout 由 crontab 重定向到 /var/log/proxy-rotation-guard.log
# 详见 knowledge/tech/infrastructure/2026-11-04-singbox-morning-window-outage.md

PROBE_URL="https://www.gstatic.com/generate_204"
ts() { date '+%F %T'; }

probe() {  # 0=通 1=死
  local code
  code=$(curl -s --socks5-hostname 127.0.0.1:1080 -m 10 -o /dev/null -w '%{http_code}' "$PROBE_URL" 2>/dev/null)
  [ "$code" = "204" ]
}

echo "[$(ts)] guard start"
if probe; then
  echo "[$(ts)] proxy healthy, no action"
  exit 0
fi
sleep 5  # 二次确认，避免瞬时抖动误杀
if probe; then
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
  if probe; then ok=1; break; fi
  echo "[$(ts)] re-probe #$i still dead, wait 10s"
  sleep 10
done
if [ "$ok" = 1 ]; then
  echo "[$(ts)] RECOVERED after restart"
else
  echo "[$(ts)] STILL DEAD after restart (公共DNS边缘缓存可能仍持旧记录，死窗自然过期即恢复; 持续故障由F2看门狗告警)"
fi
