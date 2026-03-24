#!/bin/bash
# OpenClaw 用户迁移脚本
# 执行方式: 分阶段执行，每阶段需确认
# 时间: 2026-03-23 22:30

set -euo pipefail

# 配置
NEW_USER="openclaw"
NEW_HOME="/home/openclaw"
OLD_HOME="/root/.openclaw"
SCRIPTS_DIR="/root/scripts"
LOG_FILE="/tmp/openclaw-migration-$(date +%Y%m%d-%H%M%S).log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

# ==================== 阶段一: 准备阶段 ====================
phase1_prepare() {
    log "========== 阶段一: 准备阶段 =========="
    
    # 1.1 创建 openclaw 用户
    log "步骤 1.1: 创建 $NEW_USER 用户..."
    if id "$NEW_USER" &>/dev/null; then
        warn "用户 $NEW_USER 已存在，跳过创建"
    else
        useradd -r -m -s /bin/bash -d "$NEW_HOME" "$NEW_USER"
        log "✅ 用户 $NEW_USER 创建成功"
    fi
    
    # 1.2 创建新目录结构
    log "步骤 1.2: 创建新目录结构..."
    mkdir -p "$NEW_HOME/.openclaw"
    mkdir -p "$NEW_HOME/scripts"
    log "✅ 目录结构创建成功"
    
    # 1.3 复制数据（rsync，保留权限）
    log "步骤 1.3: 复制数据（预计3-5分钟）..."
    rsync -av --progress "$OLD_HOME/" "$NEW_HOME/.openclaw/" | tee -a "$LOG_FILE"
    log "✅ 数据复制完成"
    
    # 1.4 验证数据完整性
    log "步骤 1.4: 验证数据完整性..."
    OLD_SIZE=$(du -sb "$OLD_HOME" | cut -f1)
    NEW_SIZE=$(du -sb "$NEW_HOME/.openclaw" | cut -f1)
    
    if [ "$OLD_SIZE" -eq "$NEW_SIZE" ]; then
        log "✅ 数据完整性验证通过 (大小: $OLD_SIZE bytes)"
    else
        error "数据完整性验证失败!"
        error "原目录: $OLD_SIZE bytes"
        error "新目录: $NEW_SIZE bytes"
        return 1
    fi
    
    # 1.5 调整 /root/scripts 权限
    log "步骤 1.5: 调整 /root/scripts 权限..."
    chown -R "$NEW_USER:$NEW_USER" "$SCRIPTS_DIR"
    chmod -R 755 "$SCRIPTS_DIR"
    log "✅ /root/scripts 权限调整完成"
    
    # 创建符号链接（兼容层）
    log "创建符号链接兼容层..."
    ln -sf "$NEW_HOME/.openclaw" "$NEW_HOME/openclaw-workspace"
    log "✅ 兼容层创建完成"
    
    log "========== 阶段一完成 =========="
    log "数据已准备就绪，等待阶段二执行"
}

# ==================== 阶段二: 服务切换 ====================
phase2_switch() {
    log "========== 阶段二: 服务切换 =========="
    
    # 2.1 停止 OpenClaw gateway
    log "步骤 2.1: 停止 OpenClaw gateway..."
    openclaw gateway stop || true
    sleep 2
    
    # 检查是否停止
    if pgrep -f "openclaw-gateway" > /dev/null; then
        warn "Gateway 进程仍在运行，强制终止..."
        pkill -f "openclaw-gateway" || true
        sleep 1
    fi
    log "✅ Gateway 已停止"
    
    # 2.2 最终数据同步
    log "步骤 2.2: 最终数据同步..."
    rsync -av --delete "$OLD_HOME/" "$NEW_HOME/.openclaw/" | tee -a "$LOG_FILE"
    log "✅ 最终同步完成"
    
    # 2.3 更新配置中的路径（如有必要）
    log "步骤 2.3: 检查并更新配置..."
    # 更新 workspace 路径
    sed -i "s|/root/.openclaw/workspace|$NEW_HOME/.openclaw/workspace|g" "$NEW_HOME/.openclaw/openclaw.json" || true
    log "✅ 配置检查完成"
    
    # 2.4 以 openclaw 用户启动 gateway
    log "步骤 2.4: 以 $NEW_USER 用户启动 gateway..."
    
    # 设置环境变量
    export HOME="$NEW_HOME"
    export OPENCLAW_HOME="$NEW_HOME/.openclaw"
    
    # 启动 gateway
    su - "$NEW_USER" -c "openclaw gateway start" || {
        error "Gateway 启动失败!"
        return 1
    }
    
    sleep 3
    
    # 2.5 验证服务正常
    log "步骤 2.5: 验证服务..."
    if pgrep -u "$NEW_USER" -f "openclaw-gateway" > /dev/null; then
        log "✅ Gateway 进程运行正常 (用户: $NEW_USER)"
    else
        error "Gateway 进程未找到!"
        return 1
    fi
    
    # 检查端口监听
    if netstat -tlnp 2>/dev/null | grep -q "127.0.0.1:18789"; then
        log "✅ Gateway 端口监听正常 (127.0.0.1:18789)"
    else
        warn "无法确认端口监听状态"
    fi
    
    log "========== 阶段二完成 =========="
    log "服务切换成功！"
}

# ==================== 阶段三: 清理阶段 ====================
phase3_cleanup() {
    log "========== 阶段三: 清理阶段 =========="
    
    # 3.1 迁移 crontab 到 openclaw 用户
    log "步骤 3.1: 迁移 crontab 到 $NEW_USER 用户..."
    
    # 导出当前 root crontab
    crontab -l > /tmp/root-crontab-backup.txt 2>/dev/null || true
    
    # 创建新的 crontab 内容（调整路径）
    cat > /tmp/new-crontab.txt << 'EOF'
# OpenClaw 定时任务
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME=/home/openclaw

# 早间简报 (8:00)
0 8 * * * python3 /root/.openclaw/workspace/scripts/briefing/morning_briefing.py >> /tmp/morning_briefing.log 2>&1

# OpenClaw资讯推送 (8:05)
5 8 * * * python3 /root/scripts/openclaw_news.py >> /tmp/openclaw_news.log 2>&1

# 每日工作日报 (8:30)
30 8 * * * python3 /root/.openclaw/workspace/scripts/daily/daily_report.py >> /tmp/daily_report.log 2>&1

# NAS备份通知 (8:35)
35 8 * * * cat /tmp/backup-notification-$(date +\%Y\%m\%d).txt 2>/dev/null || echo '备份通知文件不存在'

# 每日归档 (23:00)
0 23 * * * python3 /root/.openclaw/workspace/backup/growth/multi-agents/xiaomi/cron/daily_archive.py >> /tmp/daily_archive.log 2>&1

# GitHub每日同步 (23:30)
30 23 * * * cd /root/.openclaw/workspace && ./scripts/sync-to-github.sh >> /tmp/github-sync.log 2>&1

# NAS自动备份 (2:00)
0 2 * * * /root/.openclaw/workspace/scripts/backup/nas_backup.sh >> /tmp/nas_backup.log 2>&1

# 每日自我反思 (4:00)
0 4 * * * echo "执行每日自我反思" >> /tmp/reflection.log 2>&1

# 每日反思生成 (4:30)
30 4 * * * python3 /root/.openclaw/workspace/scripts/daily/daily_reflection.py >> /tmp/daily_reflection.log 2>&1

# 自动归档记忆到inbox (5:00)
0 5 * * * python3 /root/.openclaw/workspace/scripts/utils/auto_archive_to_inbox.py >> /tmp/auto_archive.log 2>&1

# 周报提醒 (周五 17:00)
0 17 * * 5 python3 /root/.openclaw/workspace/knowledge/tech/automation/cron/weekly_reminder.py >> /tmp/weekly_reminder.log 2>&1

# 周复盘 (周五 18:30)
30 18 * * 5 python3 /root/.openclaw/workspace/skills/weekly-review/weekly_review.py >> /tmp/weekly_review.log 2>&1

# 周计划制定 (周日 20:00)
0 20 * * 0 echo "生成下周周计划草稿" >> /tmp/weekly_plan.log 2>&1

# 周反思报告 (周日 20:00)
0 20 * * 0 python3 /root/reflection/weekly_reflection.py >> /tmp/weekly_reflection.log 2>&1

# 周计划提醒 (周日 20:00)
0 20 * * 0 echo "提醒用户做下周计划" >> /tmp/weekly_plan_reminder.log 2>&1

# 日计划生成 (周一 8:30)
30 8 * * 1 echo "生成下周日计划" >> /tmp/daily_plan.log 2>&1

# 月度inbox整理提醒 (每月1日 10:00)
0 10 1 * * python3 /root/.openclaw/workspace/scripts/utils/monthly_inbox_cleanup.py >> /tmp/monthly_cleanup.log 2>&1

# 月反思报告 (每月28-31日 21:00)
0 21 28-31 * * python3 /root/reflection/monthly_reflection.py >> /tmp/monthly_reflection.log 2>&1
EOF
    
    # 安装到 openclaw 用户
    su - "$NEW_USER" -c "crontab /tmp/new-crontab.txt"
    log "✅ Crontab 迁移完成"
    
    # 3.2 验证定时任务
    log "步骤 3.2: 验证定时任务..."
    su - "$NEW_USER" -c "crontab -l" | head -5
    log "✅ 定时任务验证完成"
    
    # 3.3 更新文档
    log "步骤 3.3: 更新文档..."
    cat > "$NEW_HOME/.openclaw/workspace/memory/migration-completed-$(date +%Y%m%d).md" << EOF
# OpenClaw 用户迁移完成记录

**迁移时间**: $(date '+%Y-%m-%d %H:%M:%S')
**新用户**: $NEW_USER
**新主目录**: $NEW_HOME

## 变更内容
1. OpenClaw 服务从 root 迁移到 $NEW_USER 用户运行
2. 数据目录: $OLD_HOME → $NEW_HOME/.openclaw
3. Crontab 迁移到 $NEW_USER 用户
4. /root/scripts 权限调整为 $NEW_USER 可访问

## 保留项
- 原数据目录保留7天观察期: $OLD_HOME
- /root/scripts 目录保留，权限已调整

## 回滚方法
如需回滚，执行:
\`\`\`bash
openclaw gateway stop
# 以 root 启动
openclaw gateway start
# 恢复 root crontab
crontab /tmp/root-crontab-backup.txt
\`\`\`

## 验证命令
\`\`\`bash
# 检查进程用户
ps aux | grep openclaw-gateway

# 检查定时任务
su - openclaw -c "crontab -l"

# 检查服务状态
openclaw gateway status
\`\`\`
EOF
    log "✅ 文档更新完成"
    
    # 3.4 设置7天后清理提醒
    log "步骤 3.4: 设置7天后清理提醒..."
    echo "$(date -d '+7 days' '+%Y-%m-%d') 检查后可删除 /root/.openclaw 旧数据" >> "$NEW_HOME/.openclaw/workspace/memory/migration-cleanup-reminder.txt"
    log "✅ 清理提醒已设置"
    
    log "========== 阶段三完成 =========="
}

# ====================