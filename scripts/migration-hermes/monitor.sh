#!/usr/bin/env bash
# 观察期监控: 输出当前资源与进程快照，供 24h 观察期多次调用
echo "=== $(date '+%F %T') ==="
free -m | head -3
echo "--- swap 趋势 ---"; swapon --show
echo "--- hermes/关键进程 ---"
ps aux | grep -E "hermes|openclaw" | grep -v grep || echo "(无 hermes/openclaw 进程)"
echo "--- 负载 ---"; uptime | awk -F'load average:' '{print "load:"$2}'
echo "--- hermes 服务 ---"
systemctl is-active hermes-gateway 2>/dev/null || echo "hermes-gateway 未配置"
echo "--- 磁盘 ---"; df -h / | tail -1
