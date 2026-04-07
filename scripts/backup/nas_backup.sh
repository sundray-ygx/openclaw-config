#!/bin/bash
# NAS自动备份脚本 - WebDAV方式
# 每天凌晨2:00执行

# 防并发锁：同一时间只允许一个实例运行
LOCK_FILE="/tmp/nas-backup.lock"
exec 200>"$LOCK_FILE"
flock -n 200 || { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份跳过：另一个实例正在运行"; exit 0; }

# 配置
WEBDAV_URL="http://47.119.177.194:5005"
WEBDAV_USER="aliyun-ygx"
WEBDAV_PASS='%dOr91[#'
WEBDAV_BASE="/aliyun_backup/server-backup"
BACKUP_DATE=$(date +%Y%m%d)
BACKUP_TIME=$(date '+%Y-%m-%d %H:%M:%S')
LOCAL_BACKUP_DIR="/tmp/backup-$BACKUP_DATE"
LOG_FILE="/var/log/nas-backup.log"

# 日志函数（不使用tee，避免重复输出）
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 创建本地临时备份目录
mkdir -p "$LOCAL_BACKUP_DIR"

log "开始备份数据..."

# 创建目录结构
mkdir -p "$LOCAL_BACKUP_DIR/01-sing-box"
mkdir -p "$LOCAL_BACKUP_DIR/02-frp"
mkdir -p "$LOCAL_BACKUP_DIR/03-scripts"
mkdir -p "$LOCAL_BACKUP_DIR/04-workspace"
mkdir -p "$LOCAL_BACKUP_DIR/05-openclaw-config"

# 1. sing-box配置
log "备份: sing-box配置"
cp /etc/sing-box/config.json "$LOCAL_BACKUP_DIR/01-sing-box/"

# 2. FRP配置
log "备份: FRP配置"
cp /root/frp_0.60.0_linux_amd64/frps.toml "$LOCAL_BACKUP_DIR/02-frp/"
cp /root/frp_0.60.0_linux_amd64/frpc.toml "$LOCAL_BACKUP_DIR/02-frp/"
cp /root/frp_0.60.0_linux_amd64/frps "$LOCAL_BACKUP_DIR/02-frp/"
cp /root/frp_0.60.0_linux_amd64/frpc "$LOCAL_BACKUP_DIR/02-frp/"

# 3. 脚本
log "备份: 脚本"
# 使用新的workspace目录结构
cp /home/openclaw/.openclaw/workspace/scripts/briefing/morning_briefing.py "$LOCAL_BACKUP_DIR/03-scripts/"
cp /home/openclaw/.openclaw/workspace/scripts/daily/daily_report.py "$LOCAL_BACKUP_DIR/03-scripts/"
cp /home/openclaw/.openclaw/workspace/scripts/backup/nas_backup.sh "$LOCAL_BACKUP_DIR/03-scripts/"
cp /home/openclaw/.openclaw/workspace/scripts/news/rss_news_fetch.py "$LOCAL_BACKUP_DIR/03-scripts/"

# 4. OpenClaw工作区核心文档
log "备份: OpenClaw工作区核心文档"
cp /home/openclaw/.openclaw/workspace/AGENTS.md "$LOCAL_BACKUP_DIR/04-workspace/"
cp /home/openclaw/.openclaw/workspace/SOUL.md "$LOCAL_BACKUP_DIR/04-workspace/"
cp /home/openclaw/.openclaw/workspace/USER.md "$LOCAL_BACKUP_DIR/04-workspace/"
cp /home/openclaw/.openclaw/workspace/TOOLS.md "$LOCAL_BACKUP_DIR/04-workspace/"
cp /home/openclaw/.openclaw/workspace/HEARTBEAT.md "$LOCAL_BACKUP_DIR/04-workspace/"
cp /home/openclaw/.openclaw/workspace/IDENTITY.md "$LOCAL_BACKUP_DIR/04-workspace/"

# 5. OpenClaw完整配置
log "备份: OpenClaw完整配置"
# 使用tar排除.git目录，避免备份冗余数据
tar -czf "$LOCAL_BACKUP_DIR/05-openclaw-config/openclaw-workspace.tar.gz" \
    -C /home/openclaw/.openclaw \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='node_modules' \
    --exclude='.venv' \
    workspace/

# 6. 安全脚本
log "备份: 安全脚本"
mkdir -p "$LOCAL_BACKUP_DIR/06-security-scripts"
cp /home/openclaw/.openclaw/scripts/*.sh "$LOCAL_BACKUP_DIR/06-security-scripts/"

# 生成备份信息
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "47.119.177.194")
cat > "$LOCAL_BACKUP_DIR/backup-info.json" << EOF
{
  "backup_date": "$BACKUP_DATE",
  "backup_time": "$BACKUP_TIME",
  "server_hostname": "$(hostname)",
  "server_ip": "$SERVER_IP",
  "backup_version": "3.0",
  "structure": "workspace-organized"
}
EOF

# 生成README
log "生成README说明文档"
cat > "$LOCAL_BACKUP_DIR/README.txt" << EOF
================================================================================
服务器备份说明文档
备份时间: $BACKUP_TIME
备份服务器: $(hostname)
服务器IP: $SERVER_IP
备份版本: 3.0 (Workspace结构)
================================================================================

目录结构说明:

01-sing-box/          - 网络代理配置
   └── config.json    - sing-box代理节点配置

02-frp/               - 内网穿透配置
   ├── frps.toml      - FRP服务端配置
   ├── frpc.toml      - FRP客户端配置
   ├── frps           - FRP服务端程序
   └── frpc           - FRP客户端程序

03-scripts/           - 自动化脚本
   ├── morning_briefing.py    - 早间简报生成
   ├── daily_report.py        - 工作日报生成
   ├── nas_backup.sh          - 本备份脚本
   └── rss_news_fetch.py      - RSS资讯抓取

04-workspace/         - OpenClaw工作区核心文档
   ├── AGENTS.md              - 代理配置和行为规范
   ├── SOUL.md                - AI助手身份和性格
   ├── USER.md                - 用户配置
   ├── TOOLS.md               - 工具和环境配置
   ├── HEARTBEAT.md           - 定时任务配置
   └── IDENTITY.md            - 身份标识

05-openclaw-config/   - OpenClaw完整配置
   └── openclaw-workspace.tar.gz  - 完整工作区打包

06-security-scripts/  - 安全基线脚本
   ├── check_config.sh        - 配置防护检查
   ├── monitor-suspicious-process.sh - 可疑进程监控
   ├── self-integrity-check.sh - 脚本完整性自检
   └── ...                    - 其他安全脚本

backup-info.json      - 备份元数据

================================================================================
恢复说明:

1. 恢复sing-box:
   cp 01-sing-box/config.json /etc/sing-box/
   docker restart sing-box

2. 恢复FRP:
   cp 02-frp/* /root/frp_0.60.0_linux_amd64/
   systemctl restart frps

3. 恢复脚本:
   cp 03-scripts/* /home/openclaw/.openclaw/workspace/scripts/
   # 注意: 脚本已按功能分类存储在 scripts/{daily,briefing,news,backup,utils}/

4. 恢复工作区核心文档:
   cp 04-workspace/* /home/openclaw/.openclaw/workspace/

5. 恢复完整OpenClaw工作区:
   tar -xzf 05-openclaw-config/openclaw-workspace.tar.gz -C /home/openclaw/.openclaw/

6. 恢复安全脚本:
   cp 06-security-scripts/* /home/openclaw/.openclaw/scripts/

================================================================================
服务管理命令:

# sing-box代理
docker ps | grep sing-box
docker restart sing-box

# FRP内网穿透
systemctl status frps
systemctl restart frps

# 早间简报测试
python3 /home/openclaw/.openclaw/workspace/scripts/briefing/morning_briefing.py

================================================================================
定时任务:

- 早间简报: 每天8:00
- OpenClaw资讯: 每天8:00
- 工作日报: 每天22:00
- NAS备份: 每天2:00

================================================================================
EOF

# 打包整个备份目录
log "打包备份..."
tar -czf "$LOCAL_BACKUP_DIR/../server-backup-$BACKUP_DATE.tar.gz" -C "$LOCAL_BACKUP_DIR" .

# 创建远程目录结构
REMOTE_DIR="$WEBDAV_BASE/$BACKUP_DATE"
log "创建远程目录: $REMOTE_DIR"

# 创建日期目录
curl -s -o /dev/null -w "%{http_code}" -X MKCOL -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$WEBDAV_BASE/" 2>/dev/null
curl -s -o /dev/null -w "%{http_code}" -X MKCOL -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$REMOTE_DIR/"

# 上传打包文件（带重试，最多3次）
log "上传备份包..."
MAX_RETRIES=3
RETRY_DELAY=15
UPLOAD_RESULT=""
UPLOAD_SUCCESS=false

for i in $(seq 1 $MAX_RETRIES); do
    UPLOAD_RESULT=$(curl -s -o /dev/null -w "%{http_code}" --max-time 120 -T "$LOCAL_BACKUP_DIR/../server-backup-$BACKUP_DATE.tar.gz" -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$REMOTE_DIR/server-backup-$BACKUP_DATE.tar.gz")
    
    if [ "$UPLOAD_RESULT" = "201" ] || [ "$UPLOAD_RESULT" = "200" ] || [ "$UPLOAD_RESULT" = "204" ]; then
        UPLOAD_SUCCESS=true
        break
    fi
    
    log "上传失败 (第${i}次): HTTP $UPLOAD_RESULT"
    if [ $i -lt $MAX_RETRIES ]; then
        log "等待${RETRY_DELAY}秒后重试..."
        sleep $RETRY_DELAY
    fi
done

if [ "$UPLOAD_SUCCESS" = true ]; then
    log "上传成功: server-backup-$BACKUP_DATE.tar.gz (HTTP $UPLOAD_RESULT)"
    UPLOAD_STATUS="成功"
else
    log "上传最终失败: server-backup-$BACKUP_DATE.tar.gz (HTTP $UPLOAD_RESULT，已重试${MAX_RETRIES}次)"
    UPLOAD_STATUS="失败"
fi

# 清理本地临时文件
rm -rf "$LOCAL_BACKUP_DIR"
rm -f "$LOCAL_BACKUP_DIR/../server-backup-$BACKUP_DATE.tar.gz"

log "备份完成: $UPLOAD_STATUS"

# 生成通知文件
NOTIFICATION_FILE="/tmp/backup-notification-$BACKUP_DATE.txt"
cat > "$NOTIFICATION_FILE" << EOF
📦 NAS自动备份完成

备份时间: $BACKUP_TIME
备份路径: /aliyun_backup/server-backup/$BACKUP_DATE/
备份文件: server-backup-$BACKUP_DATE.tar.gz
备份状态: $UPLOAD_STATUS
服务器IP: $SERVER_IP

目录结构:
├── 01-sing-box/        - 网络代理配置
├── 02-frp/             - 内网穿透配置
├── 03-scripts/         - 自动化脚本
├── 04-workspace/       - OpenClaw工作区核心文档
├── 05-openclaw-config/ - OpenClaw完整配置
├── 06-security-scripts/ - 安全基线脚本
├── backup-info.json    - 备份元数据
└── README.txt          - 恢复说明

详细恢复说明请查看README.txt
EOF

log "通知内容已保存"
