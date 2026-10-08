#!/bin/bash
# ECS 侧每日同步 hermes-config：git pull + 技能增量传播
# cron: 0 5 * * * /root/scripts/hermes-sync/pull.sh >> /var/log/hermes-config-pull.log 2>&1
# 规则：
#   - 新技能（本机无）→ 自动装入
#   - NAS 自有技能有更新 → 自动覆盖（本机对该技能的手动改动会被还原，hub 是 NAS）
#   - protected-skills.txt 中的技能（官方版本漂移）→ 永不覆盖本机版本
#   - NAS 删除技能不联动删除本机
set -u
REPO=/root/hermes-config
LOCAL_SKILLS=/root/.hermes/skills
PROTECTED=/root/scripts/hermes-sync/protected-skills.txt
LOCK=/var/lock/hermes-config-pull.lock

# 失败告警：飞书直连 API(2026-10-08 修复:原 feishu_mcp_create_doc 是 openclaw 时代 MCP 工具,
# 网关切换后二进制不存在,且内容还是硬编码的——告警链路从未真正可用。改用 heartbeat_syscheck
# 已验证的直连模式,同 app cli_a93c6b1e)
alert_fail() {
  local title="[ECS] hermes-config 同步失败"
  local body="$(date '+%F %T') 主机: $(hostname) 原因: $1 日志: /var/log/hermes-config-pull.log"
  python3 - "$title" "$body" << 'PYEOF' >/dev/null 2>&1 || true
import sys, json, urllib.request, urllib.parse
title, body = sys.argv[1:3]
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": "cli_a93c6b1e1ff89bd4", "app_secret": "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=10) as resp:
    token = json.loads(resp.read().decode()).get("tenant_access_token")
card = {"config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title}, "template": "red"},
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

exec 9>"$LOCK"
flock -n 9 || { echo "[$(date '+%F %T')] 上一次同步仍在运行，跳过"; exit 0; }

cd "$REPO" || { echo "[$(date '+%F %T')] 🔴 仓库目录不存在: $REPO"; exit 1; }
echo "===== $(date '+%F %T') 同步开始 ====="

if ! git fetch origin main 2>&1; then
  echo "🔴 git fetch 失败（网络/SSH）"; alert_fail "git fetch 失败（网络/SSH）"; exit 1
fi
# 2026-10-08 修复:ECS 是纯消费者,不应有本地提交。原 --ff-only 在 NAS force-push 重写历史后
# 永久分叉(9/29 起 10 天同步失败)。改为 fetch + reset --hard,彻底根治。
if ! git reset --hard origin/main 2>&1; then
  echo "🔴 git reset --hard origin/main 失败"; alert_fail "git reset 失败"; exit 1
fi

added=0; updated=0; skipped=0
while IFS= read -r skill; do
  [ -n "$skill" ] || continue
  if [ -d "$LOCAL_SKILLS/$skill" ]; then
    if grep -qxF "$skill" "$PROTECTED" 2>/dev/null; then
      skipped=$((skipped+1)); continue
    fi
    if ! diff -rq "$REPO/skills/$skill" "$LOCAL_SKILLS/$skill" >/dev/null 2>&1; then
      rsync -a --delete "$REPO/skills/$skill/" "$LOCAL_SKILLS/$skill/"
      echo "  更新: $skill"
      updated=$((updated+1))
    fi
  else
    mkdir -p "$LOCAL_SKILLS/$(dirname "$skill")"
    rsync -a "$REPO/skills/$skill" "$LOCAL_SKILLS/$(dirname "$skill")/"
    echo "  新增: $skill"
    added=$((added+1))
  fi
done < <(cd "$REPO/skills" && find . -name SKILL.md -printf '%h\n' | sed 's|^\./||' | sort)

echo "✅ 完成: $(git log -1 --format='%h %s') | 技能 新增 $added / 更新 $updated / 官方保护跳过 $skipped"
