#!/bin/bash
# ============================================================
# ECS 端 hermes-config 每日拉取备份（A2 定版 2026-11-05 · ECS 补丁版）
# 原案: README-ecs-hermes-backup.md / ecs-setup-hermes-backup.sh（Boss 提供）
# 本版变更（Boss 2026-11-05 批复 D1=B + D2 全批）:
#   D1=B  凭据复用现有 id_rsa（git@github.com 直连，零 GitHub 操作）
#   D2-1  日志分离: /var/log/hermes-config-pull-a2.log（原案与 05:00 主同步任务
#         同写 hermes-config-pull.log，交叉污染排障取证）
#   D2-2  陈旧度 🟡 告警接飞书直推（heartbeat_syscheck 已验证模式：
#         app cli_a93c6b1e → ou_d8ae71cd，原案 exit 2 只写日志无人看）
#   D2-3  cron.d 条目钉死本脚本绝对路径（防 WebDAV 物料目录被清理后断链）
# 链路: GitHub 私仓 sundray-ygx/hermes-config
#         ← 每日03:00 NAS push
#         ← 每日03:40 ECS pull → /opt/backups/hermes-config（全量含 knowledge/）
# 前提: 现有 id_rsa 对私仓有读权限（05:00 主同步任务每日实证中）
# 幂等: .git 存在则走更新分支；cron.d 覆盖写（内容自校验）
# ============================================================
set -euo pipefail

DEST="/opt/backups/hermes-config"
LOG="/var/log/hermes-config-pull-a2.log"
REPO_SSH="git@github.com:sundray-ygx/hermes-config.git"

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ---- D2-2: 飞书直推（陈旧度/失败告警；静默失败不阻塞主流程）----
alert_feishu() {
    local title="$1" body="$2" color="${3:-red}"
    python3 - "$title" "$body" "$color" << 'PYEOF' >/dev/null 2>&1 || true
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

# ---- 0. 拉取模式（cron 调用不带 --pull-only 时先自注册）----
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

if [ "${1:-}" = "--pull-only" ]; then
    :
else
    log "===== A2 部署/运行 $(date '+%F %T') ====="
fi

# ---- 1. 初始化或更新仓库 ----
if [ ! -d "$DEST/.git" ]; then
    mkdir -p "$(dirname "$DEST")"
    log "首次克隆 $REPO_SSH → $DEST"
    if ! git clone "$REPO_SSH" "$DEST" >>"$LOG" 2>&1; then
        log "❌ 克隆失败（检查 id_rsa 对私仓读权限 / 网络）"
        alert_feishu "[ECS] A2 hermes-config 备份克隆失败" "$(date '+%F %T') 主机: $(hostname)\n目标: $DEST\n动作: 手动排查 ssh -T git@github.com 与仓库凭据" "red"
        exit 1
    fi
    log "✅ 克隆完成 → $(git -C "$DEST" rev-parse --short HEAD)"
else
    cd "$DEST"
    git remote set-url origin "$REPO_SSH" 2>/dev/null || true
    BEFORE=$(git rev-parse HEAD 2>/dev/null || echo "none")
    if ! git pull --ff-only origin main >>"$LOG" 2>&1; then
        log "❌ git pull 失败 (exit $?)"
        alert_feishu "[ECS] A2 hermes-config 备份 pull 失败" "$(date '+%F %T') 主机: $(hostname)\n日志: $LOG" "red"
        exit 1
    fi
    AFTER=$(git rev-parse HEAD)
    if [ "$BEFORE" = "$AFTER" ]; then
        log "ℹ️  无新提交 (HEAD=$AFTER)"
    else
        N=$(git rev-list --count "$BEFORE..$AFTER" 2>/dev/null || echo "?")
        log "✅ 拉取 $N 个新提交 → $AFTER"
    fi
fi

# ---- 2. 健康自检：最近提交 >3 天 = NAS 推送断链预警 ----
cd "$DEST"
LAST_TS=$(git log -1 --format=%ct)
NOW=$(date +%s)
AGE=$(( (NOW - LAST_TS) / 86400 ))
if [ "$AGE" -gt 3 ]; then
    log "🟡 上游 NAS 已 $AGE 天未推送（NAS 侧可能故障，检查 /volume1/backups/ 与 GitHub）"
    alert_feishu "[ECS] A2 备份陈旧预警" "上游 NAS 已 **$AGE 天**未推送 hermes-config（最新提交 $(git log -1 --format='%h %s' | head -c 60)）\n排查: NAS 03:00 push 任务 / /volume1/backups/ / GitHub" "yellow"
    exit 2
fi
log "✅ 副本新鲜度 OK（最新提交 $AGE 天前）"

# ---- 3. cron 注册（幂等，D2-3: 绝对路径）----
if [ "$(id -u)" = "0" ] && [ "${1:-}" != "--pull-only" ]; then
    cat > /etc/cron.d/hermes-config-pull <<EOF
# ECS A2: 每日拉取 NAS 的 hermes-config GitHub 私仓（2026-11-05 定版，Boss 批 D1=B+D2）
40 3 * * * root /bin/bash $SELF --pull-only >> $LOG 2>&1
EOF
    chmod 644 /etc/cron.d/hermes-config-pull
    log "✅ cron 已注册: /etc/cron.d/hermes-config-pull (每日 03:40, 脚本 $SELF)"
fi
log "===== 本次拉取完成 ====="
