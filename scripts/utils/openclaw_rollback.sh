#!/bin/bash
# OpenClaw 一键回滚脚本
# 用法：
#   bash openclaw_rollback.sh <备份目录>    # 回滚到指定备份
#   bash openclaw_rollback.sh --latest       # 回滚到最近的备份
#
# 注意：必须和升级时同一用户执行（root 或普通用户）

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查是否为 root
USER_HOME=$(eval echo ~$USER)
OPENCLAW_DIR="$USER_HOME/.openclaw"

# 查找最近的备份
find_latest_backup() {
    local latest=$(ls -dt "$OPENCLAW_DIR"/backup-pre-upgrade-*/ 2>/dev/null | head -1)
    if [ -z "$latest" ]; then
        log_error "未找到任何备份目录（backup-pre-upgrade-*）"
        exit 1
    fi
    echo "$latest"
}

# 验证备份完整性
validate_backup() {
    local backup_dir="$1"
    log_info "验证备份完整性：$backup_dir"

    if [ ! -d "$backup_dir" ]; then
        log_error "备份目录不存在：$backup_dir"
        exit 1
    fi

    local missing=0

    if [ ! -f "$backup_dir/openclaw.json" ]; then
        log_error "缺少配置文件：openclaw.json"
        missing=1
    fi

    if [ ! -f "$backup_dir/version.txt" ]; then
        log_error "缺少版本文件：version.txt"
        missing=1
    fi

    if [ ! -d "$backup_dir/agents" ]; then
        log_error "缺少 Profile 数据：agents/"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        log_error "备份不完整，中止回滚"
        exit 1
    fi

    log_info "备份验证通过"
}

# 停止 Gateway
stop_gateway() {
    log_info "停止 Gateway 服务..."
    if systemctl --user stop openclaw-gateway 2>/dev/null; then
        sleep 3
        log_info "Gateway 已停止"
    else
        log_warn "systemctl 停止失败，尝试直接杀进程"
        pkill -f "openclaw gateway" 2>/dev/null || true
        sleep 2
    fi
}

# 启动 Gateway
start_gateway() {
    log_info "启动 Gateway 服务..."
    systemctl --user start openclaw-gateway
    sleep 5

    if systemctl --user is-active --quiet openclaw-gateway; then
        log_info "Gateway 启动成功"
    else
        log_error "Gateway 启动失败！"
        return 1
    fi
}

# 验证服务
verify_service() {
    log_info "验证服务状态..."

    # 检查进程
    if ! systemctl --user is-active --quiet openclaw-gateway; then
        log_error "Gateway 服务未运行"
        return 1
    fi

    # 检查端口
    if ! ss -tlnp | grep -q ":18789 "; then
        log_error "端口 18789 未监听"
        return 1
    fi

    # 检查 CLI
    if ! openclaw --version >/dev/null 2>&1; then
        log_error "CLI 命令不可用"
        return 1
    fi

    local ver=$(openclaw --version 2>&1)
    log_info "版本：$ver"
    log_info "服务验证通过"
    return 0
}

# 主回滚流程
rollback() {
    local backup_dir="$1"

    echo ""
    echo "========================================="
    echo "  OpenClaw 一键回滚"
    echo "========================================="
    echo "  备份目录：$backup_dir"
    echo "  配置目录：$OPENCLAW_DIR"
    echo "========================================="
    echo ""

    # 确认
    read -p "确认执行回滚？此操作不可逆 (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_warn "已取消"
        exit 0
    fi

    # 1. 验证备份
    validate_backup "$backup_dir"

    # 2. 读取旧版本号
    OLD_VERSION=$(cat "$backup_dir/version.txt" | grep -oP '\d+\.\d+\.\d+[^ ]*' | head -1)
    if [ -z "$OLD_VERSION" ]; then
        log_error "无法从 version.txt 解析版本号"
        exit 1
    fi
    log_info "回滚目标版本：$OLD_VERSION"

    # 3. 停止服务
    stop_gateway

    # 4. 回滚二进制
    log_info "回滚二进制版本（npm install -g openclaw@$OLD_VERSION）..."
    if npm install -g "openclaw@$OLD_VERSION" 2>&1; then
        log_info "二进制回滚完成"
    else
        log_error "二进制回滚失败！尝试启动当前版本..."
        start_gateway
        exit 1
    fi

    # 5. 回滚配置
    log_info "回滚配置文件..."
    cp "$backup_dir/openclaw.json" "$OPENCLAW_DIR/openclaw.json"
    log_info "配置文件已回滚"

    # 6. 回滚 Profile（关键！不能只回配置）
    log_info "回滚 Profile 数据..."
    rm -rf "$OPENCLAW_DIR/agents"
    cp -r "$backup_dir/agents" "$OPENCLAW_DIR/agents"
    log_info "Profile 已回滚"

    # 7. 回滚插件（如果有备份）
    if [ -d "$backup_dir/plugins" ]; then
        log_info "回滚插件数据..."
        rm -rf "$OPENCLAW_DIR/plugins" 2>/dev/null || true
        cp -r "$backup_dir/plugins" "$OPENCLAW_DIR/plugins"
        log_info "插件数据已回滚"
    fi

    # 8. 启动服务
    if start_gateway; then
        log_info "服务启动成功"
    else
        log_error "服务启动失败，请检查日志：tail -100 /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log"
        exit 1
    fi

    # 9. 验证
    sleep 3
    if verify_service; then
        echo ""
        echo "========================================="
        echo -e "  ${GREEN}✅ 回滚成功！${NC}"
        echo "========================================="
        echo "  版本：$(openclaw --version 2>&1)"
        echo "  状态：运行中"
        echo ""
        echo "  后续步骤："
        echo "  1. 测试核心功能（模型调用、飞书消息等）"
        echo "  2. 检查日志：tail -50 /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log"
        echo "  3. 确认所有业务恢复正常"
        echo "========================================="
    else
        log_error "回滚后服务验证失败，请检查日志"
        exit 1
    fi
}

# 主流程
main() {
    if [ $# -eq 0 ]; then
        echo "用法："
        echo "  $0 <备份目录>    # 回滚到指定备份"
        echo "  $0 --latest       # 回滚到最近的备份"
        echo ""
        echo "可用备份："
        ls -dt "$OPENCLAW_DIR"/backup-pre-upgrade-*/ 2>/dev/null || echo "  （无）"
        exit 1
    fi

    local backup_dir

    if [ "$1" = "--latest" ]; then
        backup_dir=$(find_latest_backup)
    else
        backup_dir="$1"
        # 去掉末尾的 /
        backup_dir="${backup_dir%/}"
    fi

    rollback "$backup_dir"
}

main "$@"
