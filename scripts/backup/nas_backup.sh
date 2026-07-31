#!/bin/bash
# NAS自动备份脚本 - WebDAV方式
# 每天凌晨2:00执行

# 防并发锁：同一时间只允许一个实例运行
LOCK_FILE="/tmp/nas-backup.lock"
exec 200>"$LOCK_FILE"
flock -n 200 || { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份跳过：另一个实例正在运行"; exit 0; }

# ==================== 配置 ====================
WEBDAV_URL="http://47.119.177.194:5005"
WEBDAV_USER="aliyun-ygx"
WEBDAV_PASS='%dOr91[#'
WEBDAV_BASE="/aliyun_backup/server-backup"

BACKUP_DATE=$(date +%Y%m%d)
BACKUP_TIME=$(date '+%Y-%m-%d %H:%M:%S')
LOCAL_BACKUP_DIR="/tmp/backup-$BACKUP_DATE"
ARCHIVE_FILE="/tmp/server-backup-$BACKUP_DATE.tar.gz"
LOG_FILE="/var/log/nas-backup.log"

# 飞书通知配置
FEISHU_APP_ID="cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET="gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID="ou_d8ae71cd421f8954a9c97e973d4f03d1"

# 网络配置
NETWORK_TIMEOUT=10
MAX_RETRIES=5
RETRY_DELAY=15
UPLOAD_TIMEOUT=600

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# ==================== 飞书通知函数 ====================
send_feishu_card() {
    local status=$1      # 成功/失败
    local size=$2        # 备份大小
    local duration=$3    # 耗时
    local verify=$4      # 验证状态
    local fail_reason=$5 # 失败原因（可选）

    python3 - "$status" "$size" "$duration" "$verify" "$fail_reason" "$BACKUP_TIME" "$REMOTE_DIR" "$BACKUP_DATE" << 'PYEOF'
import sys, json, urllib.request, urllib.parse

status, size, duration, verify, fail_reason, backup_time, remote_dir, backup_date = sys.argv[1:9]

APP_ID = "cli_a93c6b1e1ff89bd4"
APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"

# 获取 token
try:
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        token = json.loads(resp.read().decode()).get("tenant_access_token")
except:
    sys.exit(1)

is_success = (status == "成功")
template = "green" if is_success else "red"
emoji = "✅" if is_success else "❌"

elements = []

# 第1块：核心指标（2x2 网格）
if is_success:
    elements.append({
        "tag": "div",
        "fields": [
            {"is_short": True, "text": {"tag": "lark_md", "content": f"📦 备份大小\n**{size}**"}},
            {"is_short": True, "text": {"tag": "lark_md", "content": f"⏱ 耗时\n**{duration}**"}},
            {"is_short": True, "text": {"tag": "lark_md", "content": f"🔒 远程验证\n**{verify}**"}},
            {"is_short": True, "text": {"tag": "lark_md", "content": f"📂 备份版本\n**v4.1**"}},
        ]
    })
else:
    elements.append({
        "tag": "div",
        "fields": [
            {"is_short": True, "text": {"tag": "lark_md", "content": f"📦 备份大小\n**{size}**"}},
            {"is_short": True, "text": {"tag": "lark_md", "content": f"⏱ 耗时\n**{duration}**"}},
        ]
    })
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"🔴 **失败原因**\n{fail_reason}"}
    })

elements.append({"tag": "hr"})

# 第2块：备份内容清单（两列用 ｜ 分隔）
if is_success:
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": "**备份内容**\n🔹 sing-box 代理配置 ｜ FRP 内网穿透配置\n🔹 自动化脚本 ｜ OpenClaw 核心文档\n🔹 OpenClaw 完整配置 ｜ 安全基线脚本\n🔹 Nginx 配置 ｜ 备份元数据"}
    })

elements.append({"tag": "hr"})

# 第3块：时间+路径（note 样式）
elements.append({
    "tag": "note",
    "elements": [
        {"tag": "lark_md", "content": f"🕐 {backup_time} ｜ 📁 {remote_dir}/server-backup-{backup_date}.tar.gz"}
    ]
})

card = {
    "config": {"wide_screen_mode": True},
    "header": {
        "title": {"tag": "plain_text", "content": f"{emoji} NAS 自动备份"},
        "template": template
    },
    "elements": elements
}

message = {
    "receive_id": USER_ID,
    "msg_type": "interactive",
    "content": json.dumps(card, ensure_ascii=False)
}

msg_url = "https://open.feishu.cn/open-apis/im/v1/messages?" + urllib.parse.urlencode({"receive_id_type": "open_id"})
msg_req = urllib.request.Request(
    msg_url,
    data=json.dumps(message, ensure_ascii=False).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    method="POST")
try:
    with urllib.request.urlopen(msg_req, timeout=10) as resp:
        json.loads(resp.read().decode())
except:
    pass
PYEOF
}

# ==================== 网络预检查 ====================
log "开始网络预检查..."
NETWORK_READY=false
for try in $(seq 1 3); do
    CHECK_RESULT=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $NETWORK_TIMEOUT --max-time $NETWORK_TIMEOUT -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL/" 2>&1)

    if echo "$CHECK_RESULT" | grep -qE "^(200|301|302|401|403|404)$"; then
        log "网络预检查通过 (尝试 $try/3): HTTP $CHECK_RESULT"
        NETWORK_READY=true
        break
    fi

    log "网络预检查失败 (尝试 $try/3): HTTP $CHECK_RESULT"
    if [ $try -lt 3 ]; then
        sleep $NETWORK_TIMEOUT
    fi
done

if [ "$NETWORK_READY" = false ]; then
    log "❌ 网络预检查失败，备份终止"
    send_feishu_card "失败" "N/A" "0s" "未验证" "⚠️ WebDAV 服务不可达 (HTTP $CHECK_RESULT)\n远程地址: $WEBDAV_URL"
    exit 1
fi

# ==================== 本地备份打包 ====================
BACKUP_START=$(date +%s)
mkdir -p "$LOCAL_BACKUP_DIR"

log "开始备份数据..."

# 创建目录结构
mkdir -p "$LOCAL_BACKUP_DIR/01-sing-box"
mkdir -p "$LOCAL_BACKUP_DIR/02-frp"
mkdir -p "$LOCAL_BACKUP_DIR/03-scripts"
mkdir -p "$LOCAL_BACKUP_DIR/04-workspace"
mkdir -p "$LOCAL_BACKUP_DIR/05-openclaw-config"
mkdir -p "$LOCAL_BACKUP_DIR/06-security-scripts"
mkdir -p "$LOCAL_BACKUP_DIR/07-nginx"

# 1. sing-box配置
log "备份: sing-box配置"
cp /etc/sing-box/config.json "$LOCAL_BACKUP_DIR/01-sing-box/" 2>/dev/null || log "⚠️ sing-box配置不存在"

# 2. FRP配置
log "备份: FRP配置"
cp /root/frp_0.60.0_linux_amd64/frps.toml "$LOCAL_BACKUP_DIR/02-frp/"
cp /root/frp_0.60.0_linux_amd64/frpc.toml "$LOCAL_BACKUP_DIR/02-frp/"
cp /root/frp_0.60.0_linux_amd64/frps "$LOCAL_BACKUP_DIR/02-frp/"
cp /root/frp_0.60.0_linux_amd64/frpc "$LOCAL_BACKUP_DIR/02-frp/"

# 3. 脚本
log "备份: 脚本"
cp /root/.openclaw/workspace/scripts/briefing/morning_briefing.py "$LOCAL_BACKUP_DIR/03-scripts/"
cp /root/.openclaw/workspace/scripts/daily/daily_report.py "$LOCAL_BACKUP_DIR/03-scripts/" 2>/dev/null || log "⚠️ daily_report.py不存在"
cp /root/.openclaw/workspace/scripts/backup/nas_backup.sh "$LOCAL_BACKUP_DIR/03-scripts/"
cp /root/.openclaw/workspace/scripts/news/rss_news_fetch.py "$LOCAL_BACKUP_DIR/03-scripts/" 2>/dev/null || log "⚠️ rss_news_fetch.py不存在"

# 4. OpenClaw工作区核心文档
log "备份: OpenClaw工作区核心文档"
for f in AGENTS.md SOUL.md USER.md TOOLS.md HEARTBEAT.md IDENTITY.md MEMORY.md; do
    cp "/root/.openclaw/workspace/$f" "$LOCAL_BACKUP_DIR/04-workspace/" 2>/dev/null || true
done

# 5. OpenClaw完整配置
log "备份: OpenClaw完整配置"
tar -czf "$LOCAL_BACKUP_DIR/05-openclaw-config/openclaw-workspace.tar.gz" \
    -C /root/.openclaw \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='node_modules' \
    --exclude='.venv' \
    workspace/

# 6. 安全脚本
log "备份: 安全脚本"
cp /root/.openclaw/scripts/*.sh "$LOCAL_BACKUP_DIR/06-security-scripts/" 2>/dev/null || log "⚠️ 安全脚本目录为空"

# 7. Nginx 配置
log "备份: Nginx配置"
cp /etc/nginx/conf.d/*.conf "$LOCAL_BACKUP_DIR/07-nginx/" 2>/dev/null || log "⚠️ Nginx配置目录为空"

# 生成备份信息
SERVER_IP=$(curl -s --connect-timeout 5 ifconfig.me 2>/dev/null || echo "47.119.177.194")
cat > "$LOCAL_BACKUP_DIR/backup-info.json" << EOF
{
  "backup_date": "$BACKUP_DATE",
  "backup_time": "$BACKUP_TIME",
  "server_hostname": "$(hostname)",
  "server_ip": "$SERVER_IP",
  "backup_version": "4.1",
  "upload_method": "webdav",
  "structure": "workspace-organized"
}
EOF

# 打包
log "打包备份..."
tar -czf "$ARCHIVE_FILE" -C "$LOCAL_BACKUP_DIR" .
ARCHIVE_SIZE=$(du -h "$ARCHIVE_FILE" | awk '{print $1}')
log "备份包大小: $ARCHIVE_SIZE"

# ==================== 上传到 NAS (WebDAV) ====================
REMOTE_DIR="$WEBDAV_BASE/$BACKUP_DATE"
UPLOAD_STATUS="失败"
UPLOAD_DETAIL=""

# 创建远程目录
log "创建远程目录: $REMOTE_DIR"
curl -s -o /dev/null -w "%{http_code}" -X MKCOL -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$WEBDAV_BASE/" 2>/dev/null
curl -s -o /dev/null -w "%{http_code}" -X MKCOL -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$REMOTE_DIR/" 2>/dev/null

for i in $(seq 1 $MAX_RETRIES); do
    log "上传备份 (第 ${i} 次，超时 ${UPLOAD_TIMEOUT} 秒)..."
    UPLOAD_RESULT=$(curl -s -o /dev/null -w "%{http_code}" --max-time $UPLOAD_TIMEOUT --connect-timeout 30 -H "Expect:" -T "$ARCHIVE_FILE" -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$REMOTE_DIR/server-backup-$BACKUP_DATE.tar.gz")

    if echo "$UPLOAD_RESULT" | grep -qE "^(200|201|204|301|302)$"; then
        log "✅ 上传成功 (HTTP $UPLOAD_RESULT)"
        UPLOAD_STATUS="成功"
        break
    fi

    log "❌ 上传失败 (第 ${i} 次): HTTP $UPLOAD_RESULT"
    UPLOAD_DETAIL="上传失败: HTTP $UPLOAD_RESULT (尝试 $i/$MAX_RETRIES)"
    if [ $i -lt $MAX_RETRIES ]; then
        log "等待 ${RETRY_DELAY} 秒后重试..."
        sleep $RETRY_DELAY
    fi
done

# ==================== 验证备份 ====================
VERIFY_STATUS="未验证"
if [ "$UPLOAD_STATUS" = "成功" ]; then
    log "验证远程备份文件..."
    VERIFY_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 -u "$WEBDAV_USER:$WEBDAV_PASS" -I "$WEBDAV_URL$REMOTE_DIR/server-backup-$BACKUP_DATE.tar.gz")

    if echo "$VERIFY_CODE" | grep -qE "^(200)$"; then
        REMOTE_SIZE=$(curl -s -I --connect-timeout 10 -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$REMOTE_DIR/server-backup-$BACKUP_DATE.tar.gz" 2>/dev/null | grep -i "Content-Length" | awk '{print $2}' | tr -d '\r')
        log "✅ 远程验证成功 (HTTP $VERIFY_CODE, 大小: ${REMOTE_SIZE} bytes)"
        VERIFY_STATUS="✅ 已验证"
    else
        log "⚠️ 远程验证失败: HTTP $VERIFY_CODE"
        VERIFY_STATUS="⚠️ 验证失败"
    fi
fi

# ==================== 清理本地临时文件 ====================
rm -rf "$LOCAL_BACKUP_DIR"
rm -f "$ARCHIVE_FILE"
log "本地临时文件已清理"

# 计算耗时
BACKUP_END=$(date +%s)
DURATION=$((BACKUP_END - BACKUP_START))
DURATION_FMT="${DURATION}s"
if [ $DURATION -gt 60 ]; then
    DURATION_FMT="$((DURATION / 60))m$((DURATION % 60))s"
fi

log "备份完成: $UPLOAD_STATUS (耗时 ${DURATION_FMT})"

# ==================== 发送飞书通知 ====================
if [ "$UPLOAD_STATUS" = "成功" ]; then
    send_feishu_card "成功" "$ARCHIVE_SIZE" "$DURATION_FMT" "$VERIFY_STATUS" ""
else
    send_feishu_card "失败" "$ARCHIVE_SIZE" "$DURATION_FMT" "未验证" "$UPLOAD_DETAIL\n重试次数: $MAX_RETRIES\n请检查 WebDAV 服务和 FRP 隧道状态"
fi
log "飞书通知已发送 ($UPLOAD_STATUS)"

# ==================== 自动清理过期备份 ====================
RETAIN_DAYS=15
log "开始清理过期备份（保留最近 ${RETAIN_DAYS} 天）..."

CUTOFF_DATE=$(date -d "-${RETAIN_DAYS} days" +%Y%m%d)
log "清理截止日期: $CUTOFF_DATE"

LIST_RESPONSE=$(curl -s -u "$WEBDAV_USER:$WEBDAV_PASS" -X PROPFIND -H "Depth: 1" "$WEBDAV_URL$WEBDAV_BASE/" 2>/dev/null)
BACKUP_DIRS=$(echo "$LIST_RESPONSE" | grep -oP '(?<=server-backup/)\d{8}' | sort -u)

deleted_count=0
for dir in $BACKUP_DIRS; do
    if [ "$dir" -lt "$CUTOFF_DATE" ] 2>/dev/null; then
        log "删除过期备份: $dir"
        dir_response=$(curl -s -u "$WEBDAV_USER:$WEBDAV_PASS" -X PROPFIND -H "Depth: 1" "$WEBDAV_URL$WEBDAV_BASE/$dir/" 2>/dev/null)
        files=$(echo "$dir_response" | grep -oP "(?<=<href>)[^<]+" | grep -v "^$WEBDAV_BASE/$dir/?$")
        for file in $files; do
            curl -s -o /dev/null -X DELETE -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$file" 2>/dev/null
        done
        curl -s -o /dev/null -X DELETE -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$WEBDAV_BASE/$dir/" 2>/dev/null
        deleted_count=$((deleted_count + 1))
    fi
done

log "清理完成: 删除 ${deleted_count} 个过期备份"
