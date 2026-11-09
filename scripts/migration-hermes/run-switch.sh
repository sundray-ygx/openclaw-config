#!/usr/bin/env bash
# 03+04 合并执行: 停 openclaw → 启 hermes gateway → 自检
# 由切换流程后台调用，日志: /var/log/hermes-migration.log
set -x
exec >> /var/log/hermes-migration.log 2>&1
echo "===== 切换开始 $(date '+%F %T') ====="

# 1. 停止并禁用 openclaw
systemctl stop openclaw-gateway
systemctl disable openclaw-gateway
sleep 5
ss -tlnp | grep 18789 && fuser -k 18789/tcp 2>/dev/null
free -m | head -2

# 2. 创建 hermes systemd 单元
cat > /etc/systemd/system/hermes-gateway.service <<'EOF'
[Unit]
Description=Hermes Agent Gateway
After=network.target

[Service]
Type=simple
User=root
Group=root
Environment=HOME=/root
WorkingDirectory=/root
ExecStart=/usr/bin/hermes gateway run
Restart=always
RestartSec=10
TimeoutStopSec=30
MemoryMax=700M

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now hermes-gateway
sleep 15

# 3. 自检
echo "--- hermes 服务状态 ---"
systemctl is-active hermes-gateway
journalctl -u hermes-gateway --no-pager -n 30 | grep -i -E "feishu|websocket|listen|error|started" | tail -10
echo "--- 内存 ---"
free -m | head -2
echo "===== 切换完成 $(date '+%F %T') ====="
