#!/bin/bash
# OpenClaw 配置同步脚本
# 用法: ./scripts/sync-to-github.sh

set -e

#!/bin/bash
# OpenClaw 配置同步脚本
# 用法: ./scripts/sync-to-github.sh
# 修复(2026-07-31): 统一在 master 分支提交并推送，避免分支漂移导致同步失效

set -e

cd "$(dirname "$0")/.."

# 统一在 master 分支操作（防止在 feature 分支上提交后推不到 master）
if [ "$(git rev-parse --abbrev-ref HEAD)" != "master" ]; then
    echo "🔄 当前分支 $(git rev-parse --abbrev-ref HEAD)，切换到 master..."
    git checkout master
fi

# 检查是否有变更
if git diff --quiet && git diff --cached --quiet; then
    echo "✅ 没有变更需要同步"
    exit 0
fi

# 添加所有变更
git add -A

# 提交
git commit -m "Auto sync: $(date +'%Y-%m-%d %H:%M:%S')" || true

# 推送（需要手动配置 remote 和 token）
if git remote | grep -q origin; then
    echo "🔄 推送到 GitHub..."
    git push origin master
    echo "✅ 同步完成"
else
    echo "⚠️  未配置 remote，请手动设置:"
    echo "  git remote add origin https://github.com/sundray-ygx/openclaw-config.git"
    echo "  或使用 token:"
    echo "  git remote add origin https://TOKEN@github.com/sundray-ygx/openclaw-config.git"
fi
