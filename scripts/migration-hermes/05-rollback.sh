#!/usr/bin/env bash
# 回滚: 恢复 openclaw，停止 hermes（数据均未删除）
set -euo pipefail
systemctl stop hermes-gateway 2>/dev/null && systemctl disable hermes-gateway || true
systemctl enable --now openclaw-gateway
sleep 5
systemctl status openclaw-gateway --no-pager | head -5
free -m | head -2
echo "✅ 已回滚至 openclaw。hermes 保留在系统上（npm uninstall -g hermes-agent 可彻底移除）。"
