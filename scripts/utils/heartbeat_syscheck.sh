#!/bin/bash
# ============================================================
# 系统健康巡检 - 零LLM心跳（2026-09-28 由方案A'创建）
# 背景: OpenClaw 心跳(agentTurn)曾每小时用 LLM 做系统巡检并推飞书
#       (24次/天, ~180万 token/天)。本脚本接管确定性检查: 零 token,
#       正常态静默写日志, 异常才推飞书卡片, 同类异常 1h 内不重复推。
# cron: 0 * * * * (每小时)
# 手动: bash heartbeat_syscheck.sh [--test-push]
# ============================================================

LOG_TAG="[syscheck]"
STATE_DIR=/tmp/heartbeat-syscheck
mkdir -p "$STATE_DIR"

# --- 飞书推送(复用 ecs-failover-probe 同款已验证逻辑与凭证) ---
FEISHU_APP_ID="cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET="gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID="ou_d8ae71cd421f8954a9c97e973d4f03d1"

send_card() { # $1=标题 $2=正文 $3=green|red
  python3 - "$1" "$2" "$3" << 'PYEOF' >/dev/null 2>&1
import sys, json, urllib.request, urllib.parse
title, body, color = sys.argv[1:4]
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": "cli_a93c6b1e1ff89bd4", "app_secret": "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=10) as resp:
    token = json.loads(resp.read().decode()).get("tenant_access_token")
card = {"config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title}, "template": color},
        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": body}}]}
msg = {"receive_id": "ou_d8ae71cd421f8954a9c97e973d4f03d1", "msg_type": "interactive",
       "content": json.dumps(card, ensure_ascii=False)}
url = "https://open.feishu.cn/open-apis/im/v1/messages?" + urllib.parse.urlencode({"receive_id_type": "open_id"})
r = urllib.request.Request(url, data=json.dumps(msg, ensure_ascii=False).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, method="POST")
with urllib.request.urlopen(r, timeout=10) as resp:
    json.loads(resp.read().decode())
PYEOF
}

# 去抖: 同一 key 告警后 3600s 内不重推
should_alert() { # $1=key
  local f="$STATE_DIR/$1.last"
  local now=$(date +%s)
  if [ -f "$f" ]; then
    local last=$(cat "$f" 2>/dev/null || echo 0)
    [ $((now - last)) -lt 3600 ] && return 1
  fi
  echo "$now" > "$f"
  return 0
}

# --- 测试模式: 验证推送链路后退出 ---
if [ "${1:-}" = "--test-push" ]; then
  send_card "🧪 系统巡检推送测试" "心跳巡检脚本(heartbeat_syscheck.sh)推送链路验证,收到即链路正常。" "green"
  echo "$LOG_TAG test push sent"
  exit 0
fi

ALERTS=()

# 1. 磁盘 (根分区 >85% 告警)
DISK=$(df -h / | awk 'NR==2{print $5}' | tr -d '%')
[ -n "$DISK" ] && [ "$DISK" -ge 85 ] && ALERTS+=("磁盘使用率 ${DISK}% (阈值85%)")

# 2. 内存 (available < 300M 告警)
MEM_AVAIL=$(free -m | awk '/Mem:/{print $7}')
[ -n "$MEM_AVAIL" ] && [ "$MEM_AVAIL" -lt 300 ] && ALERTS+=("内存 available ${MEM_AVAIL}M (阈值300M)")

# 3. swap (使用 >50% 告警)
SWAP_PCT=$(free | awk '/Swap:/{if($2>0) printf "%.0f", $3/$2*100; else print 0}')
[ -n "$SWAP_PCT" ] && [ "$SWAP_PCT" -ge 50 ] && ALERTS+=("swap 使用 ${SWAP_PCT}% (阈值50%)")

# 4. openclaw-gateway 服务
GW_STATUS=$(systemctl is-active openclaw-gateway 2>/dev/null || echo "unknown")
if [ "$GW_STATUS" != "active" ]; then
  ALERTS+=("openclaw-gateway 服务状态: $GW_STATUS")
else
  RESTARTS=$(systemctl show openclaw-gateway --property=NRestarts --value 2>/dev/null)
  TODAY_MARK="$STATE_DIR/gw-restarts.baseline"
  if [ -n "$RESTARTS" ] && [ -f "$TODAY_MARK" ]; then
    BASE=$(cat "$TODAY_MARK")
    DELTA=$((RESTARTS - BASE))
    [ "$DELTA" -ge 3 ] && [ "$DELTA" -le 20 ] && ALERTS+=("openclaw-gateway 今日异常重启 ${DELTA} 次 (累计$RESTARTS)")
  fi
fi

# 5. 关键容器 (new-api)
for C in new-api; do
  CS=$(docker inspect "$C" --format '{{.State.Status}}' 2>/dev/null)
  [ "$CS" != "running" ] && ALERTS+=("容器 $C 状态: ${CS:-不存在}")
done

# 6. 僵尸进程 (>< 10 告警)
ZOMBIES=$(ps aux | awk '$8=="Z"' | wc -l)
[ "$ZOMBIES" -ge 10 ] && ALERTS+=("僵尸进程 ${ZOMBIES} 个 (阈值10)")

# --- 结果处理 ---
echo "$LOG_TAG $(date '+%F %T') disk=${DISK}% mem_avail=${MEM_AVAIL}M swap=${SWAP_PCT}% gw=$GW_STATUS zombies=$ZOMBIES alerts=${#ALERTS[@]}"

if [ ${#ALERTS[@]} -eq 0 ]; then
  # 全部正常: 清除告警去抖状态, 保持静默
  rm -f "$STATE_DIR"/*.last 2>/dev/null
  exit 0
fi

# 有异常: 逐项去抖推送
SENT=0
for A in "${ALERTS[@]}"; do
  KEY=$(echo "$A" | md5sum | cut -c1-8)
  if should_alert "$KEY"; then
    send_card "⚠️ 系统巡检异常" "$A
$(hostname) · $(date '+%F %T')
(同类异常 1 小时内不重复提醒)" "red"
    SENT=$((SENT+1))
  fi
done
echo "$LOG_TAG pushed=$SENT pending=${#ALERTS[@]}"
