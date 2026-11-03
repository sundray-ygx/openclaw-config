#!/bin/bash
# ============================================================
# NAS 恢复 S5 — gateway 启动链修复 + 全面复活
# 变更动作（Boss 已批准的网关恢复范畴）：
#   1. mkdir /root/.hermes/courses（console-api bind 源）+ 重试容器
#   2. 若单元引用的 EnvironmentFile 缺失 → 从 /root/.hermes/.env 复制
#   3. systemctl daemon-reload + start hermes-gateway（最终启动）
# 其余只读。ExecStartPre 引用缺失脚本时只报告不强修。
# 用法：SSH 到 NAS root 执行：bash <本脚本路径>
# ============================================================

OUT="/tmp/nas-s5-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS 恢复 S5 — gateway 复活  $(date '+%F %T')"
echo "=================================================="
sec() { echo; echo "########## $1 ##########"; }

sec "A. gateway 单元文件全貌（只读）"
systemctl cat hermes-gateway 2>/dev/null || cat /etc/systemd/system/hermes-gateway.service
echo "--- 单元引用路径存在性逐项核对 ---"
UNIT=/etc/systemd/system/hermes-gateway.service
grep -oE '^(EnvironmentFile|ExecStartPre|ExecStart|ExecStop|WorkingDirectory)=.*' "$UNIT" 2>/dev/null | while IFS='=' read -r k v; do
    P=$(echo "$v" | sed 's/^-//g' | awk '{print $1}' | tr -d '"')
    [ -e "$P" ] && echo "  $k=$P → ✅存在" || echo "  $k=$P → ❌缺失"
done

sec "B. console-api 第二次尝试（已批准变更）"
mkdir -p /root/.hermes/courses
docker start projects-console-api-1 2>&1
sleep 4
docker ps --filter name=projects-console-api-1 --format 'table {{.Names}}\t{{.Status}}'
timeout 5 curl -s -o /dev/null -w 'console-api 3300: HTTP %{http_code}\n' http://127.0.0.1:3300/ 2>/dev/null || echo 'console-api: CONN-FAIL（若仍 bind 失败，报告下一条缺失路径）'
docker inspect projects-console-api-1 --format '{{json .Mounts}}' 2>/dev/null | grep -o '"Source":"[^"]*"' 

sec "C. EnvironmentFile 缺失修复（已批准变更，自适应）"
ENVREF=$(grep -oE '^EnvironmentFile=.*' "$UNIT" 2>/dev/null | head -1 | sed 's/EnvironmentFile=//' | sed 's/^-//g' | tr -d '"' | awk '{print $1}')
if [ -n "$ENVREF" ] && [ ! -e "$ENVREF" ]; then
    echo "单元要的 env 文件: $ENVREF（缺失）"
    if [ -f /root/.hermes/.env ]; then
        cp /root/.hermes/.env "$ENVREF"
        chmod 600 "$ENVREF"
        echo "✅ 已从 /root/.hermes/.env 复制到 $ENVREF（600）"
    else
        echo "❌ /root/.hermes/.env 也不存在，无法修复"
    fi
else
    echo "env 文件引用: ${ENVREF:-无} $([ -e "$ENVREF" ] && echo '✅在位' || echo '')"
fi

sec "D. ExecStartPre 缺失脚本报告（只读不强修）"
PREF=$(grep -oE '^ExecStartPre=.*' "$UNIT" 2>/dev/null | head -1 | sed 's/ExecStartPre=//' | sed 's/^-//g' | awk '{print $1}')
[ -n "$PREF" ] && { [ -e "$PREF" ] && echo "ExecStartPre: $PREF ✅" || echo "⚠️ ExecStartPre: $PREF 缺失——内容如下供决策"; }
grep -A2 '^ExecStartPre' "$UNIT" 2>/dev/null

sec "E. 启动 gateway（已批准变更）"
systemctl daemon-reload
systemctl restart hermes-gateway 2>&1 || systemctl start hermes-gateway 2>&1
sleep 8
systemctl status hermes-gateway --no-pager 2>&1 | head -15

sec "F. 启动后观察（75s 窗口，hermes 启动惯例）"
sleep 75
systemctl is-active hermes-gateway
echo "--- journal 最近 30 行 ---"
journalctl -u hermes-gateway --no-pager -n 30 2>/dev/null | tail -30
echo "--- 飞书连接迹象 ---"
journalctl -u hermes-gateway --no-pager --since '-3 min' 2>/dev/null | grep -iE 'lark|feishu|websocket|wss|error' | tail -10
echo "--- gateway 进程 ---"
ps aux | grep -E 'hermes' | grep -v grep | head -5

sec "G. 收尾全景（只读）"
docker ps --format 'table {{.Names}}\t{{.Status}}' | head -12
df -h / | tail -1; free -m | head -2

sec "S5 完成"
date '+结束: %F %T'
echo "输出文件: $OUT"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cp "$OUT" "$SCRIPT_DIR/" 2>/dev/null && echo "已回传: $SCRIPT_DIR/$(basename "$OUT")" || echo "[回传失败，请手动取 $OUT]"
