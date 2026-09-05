#!/usr/bin/env bash
# 阶段4: 创建 hermes gateway systemd 单元并启动
# 前提: hermes 已安装、配置已初始化（模型 + 飞书凭据已填）
set -euo pipefail
HERMES_BIN=$(command -v hermes)
echo "hermes 路径: $HERMES_BIN"
cat > /etc/systemd/system/hermes-gateway.service <<EOF
[Unit]
Description=Hermes Agent Gateway
After=network.target

[Service]
Type=simple
User=root
Group=root
Environment=HOME=/root
# 内存上限参照 openclaw 经验值，观察期后可调
Environment=NODE_OPTIONS=
ExecStart=$HERMES_BIN gateway
Restart=always
RestartSec=10
TimeoutStopSec=30
MemoryMax=700M

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now hermes-gateway
sleep 8
systemctl status hermes-gateway --no-pager | head -8
echo "--- 内存 ---"
free -m | head -2
echo "✅ hermes gateway 已启动。验证清单:"
echo "  1. journalctl -u hermes-gateway -f  看飞书 websocket 连接日志"
echo "  2. 飞书发一条消息给 bot 验证响应"
echo "  3. 迁移 GitHub 每日同步 cron: hermes 内建 cron (23:30 Asia/Shanghai, isolated)"
