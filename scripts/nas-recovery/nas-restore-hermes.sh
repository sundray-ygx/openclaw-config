#!/bin/bash
# NAS hermes 配置恢复入口（2026-11-05 定版）
# 前提: 新 NAS/重建后的 NAS 上已装 git；GitHub 私仓凭据在 Vaultwarden
# 用法: bash nas-restore-hermes.sh <恢复目标路径，默认 /volume1/hermes-config>
set -euo pipefail
DEST="${1:-/volume1/hermes-config}"
echo "=== NAS hermes 配置恢复 $(date '+%F %T') ==="
echo "目标: $DEST"
# 恢复优先级: ①阿里云盘上的冷备包(若有) ②GitHub 私仓
if command -v git >/dev/null && ssh -T git@github.com 2>&1 | grep -q 'sundray-ygx'; then
    echo "→ 通道①: GitHub 私仓 clone"
    git clone git@github.com:sundray-ygx/hermes-config.git "$DEST"
elif [ -d "/volume1/backups/hermes-config-latest/.git" ]; then
    echo "→ 通道②: NAS 本地冷备 clone"
    git clone /volume1/backups/hermes-config-latest "$DEST"
else
    echo "❌ 两通道均不可用: GitHub 凭据缺失且本地冷备不存在" >&2
    exit 1
fi
echo "✅ 仓库恢复完成: $DEST"
echo "后续: 参考 git-config-sync skill 的 client setup 步骤接入"
