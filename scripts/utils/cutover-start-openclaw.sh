#!/bin/bash
# 2026-10-29 网关回切: hermes-gateway → openclaw-gateway
# 必须由 systemd-run 派发（脱离两会话进程树）——停 hermes 会杀死 hermes TUI 会话，
# 脚本若挂在会话进程树下会被连坐。日志: /var/log/openclaw-cutover-20261029.log
LOG=/var/log/openclaw-cutover-20261029.log
exec >> "$LOG" 2>&1
echo "=== cutover start $(date '+%F %T') ==="

systemctl stop hermes-gateway
systemctl disable hermes-gateway 2>/dev/null
sleep 3
systemctl start openclaw-gateway

# 轮询 /health 最多 10 分钟（10.x 冷启动 30s~数分钟，端口在听≠能应答）
CODE=000
for i in $(seq 1 120); do
  sleep 5
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:18789/health 2>/dev/null)
  [ "$CODE" = "200" ] && break
done
echo "health_code=$CODE after $((i*5))s"

if [ "$CODE" = "200" ]; then
  export HOME=/root
  export PATH=/root/.nvm/versions/node/v24.22.2/bin:/root/.local/share/pnpm/bin:/root/.local/share/pnpm:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
  echo '--- doctor --fix (OPENCLAW_SERVICE_REPAIR_POLICY=external) ---'
  OPENCLAW_SERVICE_REPAIR_POLICY=external timeout 300 openclaw doctor --fix 2>&1 | tail -25
  echo '--- channels status ---'
  timeout 90 openclaw channels status 2>&1 | tail -25
  echo '--- 等待 Boss 飞书实测（给小群 bot 发消息）---'
else
  echo '!! health 10 分钟未就绪，自动回滚到 hermes-gateway'
  journalctl -u openclaw-gateway --no-pager -n 30
  systemctl stop openclaw-gateway
  systemctl start hermes-gateway
  echo "rolled_back $(date '+%F %T')"
fi
echo "=== cutover end $(date '+%F %T') ==="
