#!/usr/bin/env bash
# 阶段3: 停止 openclaw gateway（不删数据；disable 防重启双跑）
# ⚠️ 执行后 openclaw-tui 会话将中断 —— 预期行为
set -euo pipefail
read -p "确认已: 1)完成备份 2)hermes安装验证通过? 输入 YES 继续: " ANS
[ "$ANS" = "YES" ] || { echo "取消"; exit 1; }
echo "[1/2] 停止并禁用 openclaw-gateway ..."
systemctl stop openclaw-gateway
systemctl disable openclaw-gateway
systemctl status openclaw-gateway --no-pager | head -5 || true
echo "[2/2] 释放确认 ..."
sleep 3
free -m | head -2
ss -tlnp | grep 18789 || echo "端口 18789 已释放"
echo "✅ openclaw 已停止（数据完整保留于 /root/.openclaw）。"
echo "⚠️ 请退出当前 openclaw-tui 会话（exit），然后 SSH 到服务器执行 04 启动 hermes。"
