#!/bin/bash
# openclaw → hermes 网关回切（2026-10-29 配套能力，手动触发）
# 与 cutover-start-openclaw.sh 互逆。日志: /var/log/hermes-cutover-back.log
LOG=/var/log/hermes-cutover-back.log
exec >> "$LOG" 2>&1
echo "=== 切回 hermes $(date '+%F %T') ==="
systemctl stop openclaw-gateway
sleep 3
systemctl enable hermes-gateway
systemctl start hermes-gateway
# 轮询 gateway 进程
for i in $(seq 1 24); do
  sleep 5
  systemctl is-active hermes-gateway | grep -q active && break
done
echo "hermes-gateway: $(systemctl is-active hermes-gateway) (${i}x5s)"
echo "提示: 用户需向 hermes TUI/飞书发消息实测闭环"
echo "=== done $(date '+%F %T') ==="
