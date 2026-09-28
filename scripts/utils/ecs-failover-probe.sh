#!/bin/bash
# ECS new-api failover probe（2026-09-27, NAS小群生成；ECS 侧改造：飞书告警复用现有应用机器人）
# 逻辑: 探活本地 new-api(3000), 连续2次失败 → nginx upstream 3000→3100(回落NAS热备) + 飞书红卡
#       恢复成功 → 飞书绿卡提示人工切回(不自动切回, 防抖动)
# 人工切回: bash $0 switchback
STATE=/tmp/ecs-newapi-probe.state
NGINX_CONF="/etc/nginx/conf.d/newapi.conf"
MAIN="127.0.0.1:3000"; BACKUP="127.0.0.1:3100"

# 飞书应用机器人（复用 NAS 备份脚本同一套凭证）
FEISHU_APP_ID="cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET="gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID="ou_d8ae71cd421f8954a9c97e973d4f03d1"

[ -f "$STATE" ] || echo "mode:main fails:0" > "$STATE"
MODE=$(grep -o 'mode:[a-z]*' "$STATE" | cut -d: -f2)
CODE=$(timeout 8 curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "http://$MAIN/api/status" 2>/dev/null)

send_card(){ # $1 = 标题, $2 = 正文, $3 = 颜色 green/red
  python3 - "$1" "$2" "$3" << 'PYEOF' >/dev/null 2>&1
import sys, json, urllib.request, urllib.parse
title, body, color = sys.argv[1:4]
APP_ID = "cli_a93c6b1e1ff89bd4"
APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"
try:
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        token = json.loads(resp.read().decode()).get("tenant_access_token")
except Exception:
    sys.exit(1)
card = {
    "config": {"wide_screen_mode": True},
    "header": {"title": {"tag": "plain_text", "content": title}, "template": color},
    "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": body}}],
}
msg = {"receive_id": USER_ID, "msg_type": "interactive",
       "content": json.dumps(card, ensure_ascii=False)}
url = "https://open.feishu.cn/open-apis/im/v1/messages?" + urllib.parse.urlencode({"receive_id_type": "open_id"})
try:
    r = urllib.request.Request(url, data=json.dumps(msg, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, method="POST")
    with urllib.request.urlopen(r, timeout=10) as resp:
        json.loads(resp.read().decode())
except Exception:
    sys.exit(1)
PYEOF
}

switch_nginx(){ # $1 = from_port, $2 = to_port
  [ -z "$NGINX_CONF" ] && { echo "NGINX_CONF not set"; return 1; }
  cp "$NGINX_CONF" "$NGINX_CONF.bak-probe"
  sed -i "s|127.0.0.1:$1|127.0.0.1:$2|g" "$NGINX_CONF" && nginx -t >/dev/null 2>&1 && systemctl reload nginx
}

if [ "$CODE" != "200" ]; then
  FAILS=$(( $(grep -o 'fails:[0-9]*' "$STATE" | cut -d: -f2) + 1 ))
  if [ "$FAILS" -ge 2 ] && [ "$MODE" = "main" ]; then
    if switch_nginx 3000 3100; then
      send_card "🚨 ECS new-api 宕机" "域名已切回 NAS 热备 (frp:3100)。ECS 侧探测连续 ${FAILS} 次失败，请检查 new-api 容器。"
      echo "mode:backup fails:$FAILS" > "$STATE"
    else
      echo "mode:main fails:$FAILS" > "$STATE"
    fi
  else
    echo "mode:$MODE fails:$FAILS" > "$STATE"
  fi
else
  if [ "$MODE" = "backup" ]; then
    send_card "✅ ECS new-api 已恢复" "请人工切回主网关：\n\`bash $0 switchback\`\n（自动切回已禁用，防抖动）"
  fi
  echo "mode:$MODE fails:0" > "$STATE"
fi

# 人工切回命令: bash $0 switchback
if [ "${1:-}" = "switchback" ]; then
  switch_nginx 3100 3000 && echo "mode:main fails:0" > "$STATE" && echo "switched back to main"
fi
