#!/usr/bin/env bash
# 阶段1: 备份 openclaw（不删除任何数据，仅快照）
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
DEST=/root/openclaw-backups
mkdir -p "$DEST"
echo "[1/2] 打包 /root/.openclaw (排除 logs/cache/history) ..."
tar -czf "$DEST/openclaw-pre-hermes-$TS.tar.gz" \
  --exclude='root/.openclaw/logs' \
  --exclude='root/.openclaw/history' \
  --exclude='root/.openclaw/tui' \
  -C /root .openclaw
echo "[2/2] 校验 ..."
tar -tzf "$DEST/openclaw-pre-hermes-$TS.tar.gz" | head -3
ls -lh "$DEST/openclaw-pre-hermes-$TS.tar.gz"
echo "✅ 备份完成: $DEST/openclaw-pre-hermes-$TS.tar.gz"
