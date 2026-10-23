#!/bin/bash
# new-api 网关统一切换入口（ECS 主 ⇄ NAS 热备）
# 2026-10-14 建立，封装旧 failover 脚本为统一 CLI
#
# 用法:
#   bash newapi-switch.sh status     # 只读：查看当前主备状态
#   bash newapi-switch.sh verify     # 只读：全链路验证（两端探活+公网+LLM）
#   bash newapi-switch.sh to-nas     # 切到 NAS 热备（ECS 挂了应急）
#   bash newapi-switch.sh to-ecs     # 切回 ECS 主（故障恢复后）
#
# 安全模式（预演，不动服务）:
#   DRY_RUN=1 bash newapi-switch.sh to-nas
#   DRY_RUN=1 bash newapi-switch.sh to-ecs

set -u

CONF=/etc/nginx/conf.d/newapi.conf
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TO_ECS="$SCRIPT_DIR/failover-to-ecs.sh"
TO_NAS="$SCRIPT_DIR/failover-back-to-nas.sh"

probe(){
  # $1 = 地址, 输出 http_code 或 unreachable
  curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://$1/api/status" 2>/dev/null || echo "unreachable"
}

cmd_status(){
  echo "=== new-api 网关状态 ==="
  echo
  echo "[nginx conf]"
  grep -o 'proxy_pass http://127.0.0.1:[0-9]*;' "$CONF"
  echo
  if grep -q 'proxy_pass http://127.0.0.1:3000;' "$CONF"; then
    echo "当前主: ECS 本地 (3000) ✅"
  elif grep -q 'proxy_pass http://127.0.0.1:3100;' "$CONF"; then
    echo "当前主: NAS 热备 (3100) ⚠️（ECS 故障或维护中）"
  else
    echo "⚠️ conf 指向未知，人工检查 $CONF"
  fi
  echo
  echo "[两端探活]"
  echo "  ECS 本地 3000: $(probe 127.0.0.1:3000)"
  echo "  NAS 热备 3100: $(probe 127.0.0.1:3100)"
  echo
  echo "[公网]"
  echo "  api.ygxpro.online: $(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.ygxpro.online/api/status 2>/dev/null || echo unreachable)"
  echo
  echo "[自动探测]"
  if [ -f /tmp/ecs-newapi-probe.state ]; then
    cat /tmp/ecs-newapi-probe.state
  else
    echo "  无状态文件（ecs-failover-probe.sh 可能未运行过）"
  fi
}

cmd_verify(){
  echo "=== new-api 全链路验证 ==="
  echo
  ECS_CODE=$(probe 127.0.0.1:3000)
  NAS_CODE=$(probe 127.0.0.1:3100)
  PUB_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.ygxpro.online/api/status 2>/dev/null || echo unreachable)
  echo "ECS 本地 3000: $ECS_CODE   $([ "$ECS_CODE" = "200" ] && echo ✅ || echo ❌)"
  echo "NAS 热备 3100: $NAS_CODE   $([ "$NAS_CODE" = "200" ] && echo ✅ || echo ❌)"
  echo "公网域名    : $PUB_CODE   $([ "$PUB_CODE" = "200" ] && echo ✅ || echo ❌)"
  echo
  # LLM 双渠道验证（用 ecs-hermes 令牌，2026-10-23 自 ecs-openclaw 切换）
  KEY=$(sed -n 's/^NEWAPI_API_KEY=//p' /root/.hermes/.env | tr -d '"\r')
  if [ -n "${KEY#sk-}" ] && [ ${#KEY} -gt 3 ]; then
    echo "[LLM 双渠道验证]"
    for M in deepseek-v4-flash glm-5.3-flash; do
      R=$(curl -s --max-time 60 -X POST https://api.ygxpro.online/v1/chat/completions \
        -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
        -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"reply ok\"}],\"max_tokens\":100}" 2>/dev/null)
      if echo "$R" | grep -q '"choices"'; then
        echo "  $M: OK ✅"
      else
        echo "  $M: FAIL ❌ ($(echo "$R" | head -c 100))"
      fi
    done
  else
    echo "[LLM 验证] 令牌提取失败，跳过（仅 status 验证已完成）"
  fi
}

cmd_to_nas(){
  if [ ! -f "$TO_NAS" ]; then
    echo "FATAL: 底层脚本不存在: $TO_NAS" >&2
    exit 1
  fi
  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "=== DRY_RUN: 切到 NAS 热备（预演，不动服务） ==="
  else
    echo "=== 切到 NAS 热备 ==="
  fi
  exec env DRY_RUN="${DRY_RUN:-0}" bash "$TO_NAS"
}

cmd_to_ecs(){
  if [ ! -f "$TO_ECS" ]; then
    echo "FATAL: 底层脚本不存在: $TO_ECS" >&2
    exit 1
  fi
  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "=== DRY_RUN: 切回 ECS 主（预演，不动服务） ==="
  else
    echo "=== 切回 ECS 主 ==="
  fi
  exec env DRY_RUN="${DRY_RUN:-0}" bash "$TO_ECS"
}

# ---- 主入口 ----
case "${1:-}" in
  status)   cmd_status ;;
  verify)   cmd_verify ;;
  to-nas)   cmd_to_nas ;;
  to-ecs)   cmd_to_ecs ;;
  -h|--help|help|"")
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
    ;;
  *)
    echo "未知命令: $1" >&2
    echo "用法: newapi-switch.sh {status|verify|to-nas|to-ecs}" >&2
    exit 1
    ;;
esac
