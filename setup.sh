#!/bin/bash
# OpenClaw 环境恢复脚本
# 用法: ./setup.sh

set -e

echo "🚀 OpenClaw 环境恢复脚本"
echo "========================"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件"
    echo "请复制 .env.example 为 .env 并填入真实配置:"
    echo "  cp .env.example .env"
    echo "  nano .env  # 编辑配置"
    exit 1
fi

# 加载环境变量
export $(grep -v '^#' .env | xargs)

# 设置工作区路径
OPENCLAW_DIR="${HOME}/.openclaw"
WORKSPACE_DIR="${OPENCLAW_DIR}/workspace"

echo "📁 创建目录结构..."
mkdir -p "${OPENCLAW_DIR}"
mkdir -p "${WORKSPACE_DIR}"
mkdir -p "${OPENCLAW_DIR}/extensions"

# 备份现有配置（如果存在）
if [ -f "${OPENCLAW_DIR}/openclaw.json" ]; then
    BACKUP_FILE="${OPENCLAW_DIR}/openclaw.json.backup.$(date +%Y%m%d_%H%M%S)"
    echo "💾 备份现有配置到 ${BACKUP_FILE}"
    cp "${OPENCLAW_DIR}/openclaw.json" "${BACKUP_FILE}"
fi

echo "📝 生成 openclaw.json..."
# 使用 envsubst 替换环境变量
envsubst < config/openclaw.json > "${OPENCLAW_DIR}/openclaw.json"

echo "📂 同步工作区文件..."
# 使用 rsync 或 cp 同步工作区
if command -v rsync &> /dev/null; then
    rsync -av --exclude='.git' --exclude='.env' --exclude='setup.sh' \
        ./ "${WORKSPACE_DIR}/"
else
    cp -r AGENTS.md SOUL.md USER.md TOOLS.md HEARTBEAT.md IDENTITY.md \
        memory/ skills/ agents/ archive/ knowledge/ \
        "${WORKSPACE_DIR}/" 2>/dev/null || true
fi

echo "🔌 同步扩展..."
if [ -d "extensions/" ]; then
    cp -r extensions/* "${OPENCLAW_DIR}/extensions/" 2>/dev/null || true
fi

echo "✅ 恢复完成！"
echo ""
echo "下一步:"
echo "1. 安装 OpenClaw（如果尚未安装）"
echo "2. 运行: openclaw gateway start"
echo "3. 检查状态: openclaw status"
