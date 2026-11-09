#!/bin/bash
# 检查 workspace 根目录散落文件
# 用法: ./check_workspace_root.sh

WORKSPACE_DIR="/root/.openclaw/workspace"
IGNORE_FILES="AGENTS.md|BOOTSTRAP.md|DREAMS.md|HEARTBEAT.md|IDENTITY.md|MEMORY.md|README.md|SOUL.md|TOOLS.md|USER.md|.env.example|.gitignore|package.json|package-lock.json"
IGNORE_DIRS="agents|archive|backup|config|docs|extensions|.git|.github|.openclaw|knowledge|memory|node_modules|output|plans|reflection|reports|scripts|skills"

echo "🔍 检查 workspace 根目录散落文件..."
echo "=================================="

# 获取根目录下的文件（排除隐藏文件和已忽略的文件）
orphan_files=$(find "$WORKSPACE_DIR" -maxdepth 1 -type f ! -name ".*" | grep -vE ".*/($IGNORE_FILES)$" 2>/dev/null)

# 获取根目录下的目录（排除隐藏目录和已忽略的目录）
orphan_dirs=$(find "$WORKSPACE_DIR" -maxdepth 1 -type d ! -name ".*" ! -name "workspace" | grep -vE ".*/($IGNORE_DIRS)$" 2>/dev/null)

has_issues=0

if [ -n "$orphan_files" ]; then
    echo ""
    echo "⚠️  发现未归档文件："
    echo "$orphan_files" | while read -r file; do
        filename=$(basename "$file")
        echo "  - $filename"
    done
    has_issues=1
fi

if [ -n "$orphan_dirs" ]; then
    echo ""
    echo "⚠️  发现未归档目录："
    echo "$orphan_dirs" | while read -r dir; do
        dirname=$(basename "$dir")
        echo "  - $dirname/"
    done
    has_issues=1
fi

if [ $has_issues -eq 0 ]; then
    echo ""
    echo "✅ workspace 根目录整洁，无散落文件"
fi

echo ""
echo "💡 文件存放规范："
echo "  - 脚本/工具 → scripts/ 或 knowledge/tech/"
echo "  - 报告 → archive/ 或 knowledge/"
echo "  - 日志 → memory/"
echo "  - 参考: knowledge/README.md"

exit $has_issues
