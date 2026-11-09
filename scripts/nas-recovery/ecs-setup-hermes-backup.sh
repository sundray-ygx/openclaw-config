#!/bin/bash
# ============================================================
# ECS 端 hermes-config 每日拉取备份（A2 定版 2026-11-05）
# 模式: ECS 主动 git pull GitHub 私仓（拉模式，NAS 零新增暴露面）
# 部署: 在 ECS 上执行本脚本一次，自动完成 cron 注册
# 链路: GitHub 私仓 ←——每日03:00 NAS push——— NAS
#              └——每日03:40 ECS pull（只读 deploy key）→ /opt/backups/hermes-config
# 前提: ECS 已配置 GitHub deploy key（只读），见 README 段落
# ============================================================
set -euo pipefail

DEST="/opt/backups/hermes-config"          # ECS 本地仓库副本
LOG="/var/log/hermes-config-pull.log"
REPO_SSH="git@github.com:sundray-ygx/hermes-config.git"
REPO_HTTPS="https://github.com/sundray-ygx/hermes-config.git"

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ---- 1. 初始化或更新仓库 ----
if [ ! -d "$DEST/.git" ]; then
    mkdir -p "$(dirname "$DEST")"
    log "首次克隆 $REPO_SSH → $DEST"
    # 优先 SSH deploy key，失败回退 HTTPS（需 token）
    git clone "$REPO_SSH" "$DEST" 2>/dev/null || git clone "$REPO_HTTPS" "$DEST"
else
    cd "$DEST"
    git remote set-url origin "$REPO_SSH" 2>/dev/null || true
    BEFORE=$(git rev-parse HEAD 2>/dev/null || echo "none")
    git pull --ff-only origin main >>"$LOG" 2>&1 || {
        log "❌ git pull 失败 (exit $?)"
        exit 1
    }
    AFTER=$(git rev-parse HEAD)
    if [ "$BEFORE" = "$AFTER" ]; then
        log "ℹ️  无新提交 (HEAD=$AFTER)"
    else
        N=$(git rev-list --count "$BEFORE..$AFTER" 2>/dev/null || echo "?")
        log "✅ 拉取 $N 个新提交 → $AFTER"
    fi
fi

# ---- 2. 健康自检：确认最近提交时间不超过 3 天 ----
cd "$DEST"
LAST_TS=$(git log -1 --format=%ct)
NOW=$(date +%s)
AGE=$(( (NOW - LAST_TS) / 86400 ))
if [ "$AGE" -gt 3 ]; then
    log "🟡 上游 NAS 已 $AGE 天未推送（NAS 侧可能故障，检查 /volume1/backups/ 与 GitHub）"
    exit 2
fi
log "✅ 副本新鲜度 OK（最新提交 $AGE 天前）"

# ---- 3. 注册每日 cron（幂等）----
CRON_LINE="40 3 * * * root /bin/bash $0 --pull-only >> $LOG 2>&1"
if [ "$(id -u)" = "0" ] && [ "${1:-}" != "--pull-only" ]; then
    cat > /etc/cron.d/hermes-config-pull <<EOF
# ECS 每日拉取 NAS 的 hermes-config GitHub 私仓（2026-11-05 A2）
$CRON_LINE
EOF
    chmod 644 /etc/cron.d/hermes-config-pull
    log "✅ cron 已注册: /etc/cron.d/hermes-config-pull (每日 03:40)"
fi
log "===== 本次拉取完成 ====="
