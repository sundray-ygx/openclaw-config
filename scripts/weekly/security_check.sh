#!/bin/bash
# 安全配置巡检包装脚本 - 替代 openclaw cron 中的 AI agent 执行
# 每周一 9:00 执行

SCRIPT="/root/.openclaw/workspace/skills/security-audit/scripts/config_checker.py"
LOG_DIR="/root/.openclaw/workspace/memory"
DATE=$(date +%Y-%m-%d)
LOG_FILE="/var/log/security-check.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始安全配置巡检..." >> "$LOG_FILE"

# 运行检查脚本
RESULT=$(python3 "$SCRIPT" 2>&1)
SCORE=$(echo "$RESULT" | grep -oP '评分[：:]\s*\K\d+' || echo "0")

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 评分: $SCORE" >> "$LOG_FILE"

# 记录到 memory
cat > "$LOG_DIR/security-config-check-$DATE.md" << EOF
# 安全配置巡检 - $DATE

- **评分**: $SCORE
- **执行时间**: $(date '+%Y-%m-%d %H:%M:%S')

## 检查结果

$RESULT
EOF

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 巡检完成，结果已保存" >> "$LOG_FILE"
