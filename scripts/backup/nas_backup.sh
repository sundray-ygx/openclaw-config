#!/bin/bash
# NAS自动备份脚本 - WebDAV方式
# 每天凌晨2:00执行

# 防并发锁：同一时间只允许一个实例运行
LOCK_FILE="/tmp/nas-backup.lock"
exec 200>"$LOCK_FILE"
flock -n 200 || { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份跳过：另一个实例正在运行"; exit 0; }

# ==================== 配置 ====================
# 凭证外置（2026-10-13 v5.0）：从 /root/.backup-creds.env 读取，脚本内不再硬编码密钥
# （该文件 chmod 600，位于 workspace 外不入 git；脚本本身随 workspace 每日推送 GitHub）
CREDS_FILE="/root/.backup-creds.env"
if [ -r "$CREDS_FILE" ]; then
    source "$CREDS_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ 凭证文件 $CREDS_FILE 不可读，备份终止" >> /var/log/nas-backup.log
    exit 1
fi
WEBDAV_URL="http://127.0.0.1:5005"
WEBDAV_BASE="/aliyun_backup/server-backup"

BACKUP_DATE=$(date +%Y%m%d)
BACKUP_TIME=$(date '+%Y-%m-%d %H:%M:%S')
LOCAL_BACKUP_DIR="/tmp/backup-$BACKUP_DATE"
ARCHIVE_FILE="/tmp/server-backup-$BACKUP_DATE.tar.gz"
LOG_FILE="/var/log/nas-backup.log"

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

    python3 - "$status" "$size" "$duration" "$verify" "$fail_reason" "$BACKUP_TIME" "$REMOTE_DIR" "$BACKUP_DATE" \
        "$FEISHU_APP_ID" "$FEISHU_APP_SECRET" "$FEISHU_USER_ID" << 'PYEOF' >/dev/null 2>&1
import sys, json, urllib.request, urllib.parse

status, size, duration, verify, fail_reason, backup_time, remote_dir, backup_date = sys.argv[1:9]
# 凭证经 argv 传入（外置于 /root/.backup-creds.env，2026-10-13 v5.0）
APP_ID, APP_SECRET, USER_ID = sys.argv[9:12]

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
            {"is_short": True, "text": {"tag": "lark_md", "content": f"📂 备份版本\n**v5.0**"}},
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
        "text": {"tag": "lark_md", "content": "**备份内容（v5.0）**\n🔹 sing-box 代理配置 ｜ FRP 内网穿透配置\n🔹 crontab+脚本快照 ｜ OpenClaw workspace 完整包\n🔹 安全基线脚本 ｜ Nginx 配置 ｜ new-api 网关数据\n🔹 Hermes 网关配置 ｜ Hermes scheduler profile（新增）\n🔹 systemd 服务单元（新增） ｜ 备份元数据"}
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

# 3. 脚本（v5.0 简化：/root/scripts 为 workspace/scripts 软链，完整内容已由第 5 项 tar 覆盖，
#    此处仅留本脚本自身快照 + crontab 快照以便重建定时任务）
log "备份: 脚本(本脚本+crontab快照)"
mkdir -p "$LOCAL_BACKUP_DIR/03-scripts"
cp /root/.openclaw/workspace/scripts/backup/nas_backup.sh "$LOCAL_BACKUP_DIR/03-scripts/"
crontab -l > "$LOCAL_BACKUP_DIR/03-scripts/crontab.bak" 2>/dev/null || log "⚠️ crontab 导出失败"

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

# 8. new-api 网关数据（宿主侧 sqlite3 .backup 保证一致性；2026-11-06 G1 修复）
#    背景: 09-27 容器重建后镜像内无 sqlite3，原「容器内 .backup」链路慢性失效并静默
#          降级为裸 cp 活库（WAL 模式下快照一致性无保证）。改用宿主 sqlite3 直连
#          bind mount 路径 /opt/new-api/data（与第 10 步 hermes state.db 同款模式）。
#          快照自包含，不再与活库 -wal/-shm 混装（异时刻 WAL 混装是恢复期损坏隐患）。
log "备份: new-api 网关数据"
mkdir -p "$LOCAL_BACKUP_DIR/08-new-api"
NEWAPI_OK=0
if sqlite3 /opt/new-api/data/one-api.db ".backup '$LOCAL_BACKUP_DIR/08-new-api/one-api.db'" 2>>"$LOG_FILE"; then
    NEWAPI_OK=1
    log "new-api: 宿主侧 .backup 一致性快照完成"
else
    log "⚠️ new-api: 宿主侧 .backup 失败，回退容器内快照 + docker cp"
    if docker exec new-api sqlite3 /data/one-api.db ".backup /data/one-api-backup.db" 2>>"$LOG_FILE" \
       && docker cp new-api:/data/one-api-backup.db "$LOCAL_BACKUP_DIR/08-new-api/one-api.db" 2>>"$LOG_FILE"; then
        NEWAPI_OK=1
        log "new-api: 容器内快照经 docker cp 完成"
    else
        # 最终兜底：同一时刻 db+wal+shm 三元组裸拷 —— 可抢救但非一致性快照，显式记录降级
        cp /opt/new-api/data/one-api.db "$LOCAL_BACKUP_DIR/08-new-api/one-api.db" 2>>"$LOG_FILE" || true
        cp /opt/new-api/data/one-api.db-wal "$LOCAL_BACKUP_DIR/08-new-api/one-api.db-wal" 2>/dev/null || true
        cp /opt/new-api/data/one-api.db-shm "$LOCAL_BACKUP_DIR/08-new-api/one-api.db-shm" 2>/dev/null || true
        log "🔴 new-api: 一致性快照链全部失败，已降级裸拷三元组（恢复需 WAL 回放，非一致性快照）"
    fi
    docker exec new-api rm -f /data/one-api-backup.db /data/one-api-backup.db-wal /data/one-api-backup.db-shm 2>/dev/null || true
fi
cp /opt/new-api/data/admin-credentials.txt "$LOCAL_BACKUP_DIR/08-new-api/" 2>/dev/null || true
docker inspect new-api --format '{{json .Config.Env}}{{json .HostConfig.Binds}}' > "$LOCAL_BACKUP_DIR/08-new-api/container-meta.json" 2>/dev/null || true

# 9. Hermes Gateway 配置（2026-10-08 补：ECS hermes 主力网关）
# 范围：小而关键的配置（config/cron/memory/技能清单），排除 cache 等大目录；.env 密钥仅入包（WebDAV 私有通道），权限 600
log "备份: Hermes Gateway 配置"
mkdir -p "$LOCAL_BACKUP_DIR/09-hermes-config"
tar -czf "$LOCAL_BACKUP_DIR/09-hermes-config/hermes-config.tar.gz" \
    -C /root/.hermes \
    --exclude='cache' \
    --exclude='audio_cache' \
    --exclude='desktop' \
    --exclude='*.lock' \
    --exclude='feishu_seen_message_ids.json' \
    config.yaml auth.json .env cron/ skills/ 2>/dev/null \
    || log "⚠️ Hermes配置备份失败(部分文件缺失不致命)"

# 10. Hermes 活跃 profile（v5.0 2026-10-13 新增：scheduler 为当前主力网关 profile，此前零备份）
#     含会话 state.db / cron 任务 / skills / plans / memories —— ECS 挂掉后 hermes 侧唯一可恢复来源
#     state.db 用 sqlite3 .backup 保证一致性（排除 -wal/-shm 由快照文件自带）
log "备份: Hermes scheduler profile"
mkdir -p "$LOCAL_BACKUP_DIR/10-hermes-profile"
HP_SRC="/root/.hermes/profiles/scheduler"
HP_TMP="$LOCAL_BACKUP_DIR/10-hermes-profile"
sqlite3 "$HP_SRC/state.db" ".backup '$HP_TMP/state.db'" 2>/dev/null || cp "$HP_SRC/state.db" "$HP_TMP/state.db" 2>/dev/null || log "⚠️ state.db 备份失败"
tar -czf "$HP_TMP/hermes-profile.tar.gz" \
    -C "$HP_SRC" \
    --exclude='state.db*' \
    --exclude='lsp' \
    --exclude='cache' \
    --exclude='audio_cache' \
    --exclude='image_cache' \
    --exclude='runtime' \
    --exclude='*.lock' \
    --exclude='backups' \
    cron/ skills/ plans/ memories/ sessions/ workspace/ home/ hooks/ platforms/ SOUL.md config.yaml 2>/dev/null \
    || log "⚠️ Hermes profile 备份失败(部分目录缺失不致命)"
[ -f "$HP_TMP/state.db" ] || log "⚠️ profile state.db 缺失"
tar -tzf "$HP_TMP/hermes-profile.tar.gz" >/dev/null 2>&1 || { rm -f "$HP_TMP/hermes-profile.tar.gz"; log "⚠️ profile tar 损坏已移除"; }

# 11. systemd 服务单元快照（v5.1 2026-11-10 D3：从 2 个扩到 6 个——审计发现 frps/bill-import 等 4 个 unit 不在备份）
log "备份: systemd 服务单元"
mkdir -p "$LOCAL_BACKUP_DIR/11-systemd"
for U in hermes-gateway openclaw-gateway openclaw-gateway-daily-restart frps bill-import notion-bill-import; do
    cp "/etc/systemd/system/$U.service" "$LOCAL_BACKUP_DIR/11-systemd/" 2>/dev/null || true
done

# 11b. ECS 杂项配置快照（v5.1 2026-11-10 D3 新增：审计发现的备份盲区）
#   含 /etc/cron.d/（crontab -l 不含它）、nginx 主配置、docker daemon.json、acme 证书资产、.ssh（任务书 O2 批复入包）
log "备份: ECS 杂项配置(cron.d/nginx/docker/acme/ssh)"
mkdir -p "$LOCAL_BACKUP_DIR/11b-ecs-misc"
tar -czf "$LOCAL_BACKUP_DIR/11b-ecs-misc/etc-cron-d.tar.gz" -C /etc cron.d 2>/dev/null || log "⚠️ /etc/cron.d 备份失败"
cp /etc/nginx/nginx.conf "$LOCAL_BACKUP_DIR/11b-ecs-misc/" 2>/dev/null || true
cp /etc/docker/daemon.json "$LOCAL_BACKUP_DIR/11b-ecs-misc/" 2>/dev/null || true
tar -czf "$LOCAL_BACKUP_DIR/11b-ecs-misc/acme.sh.tar.gz" -C /root .acme.sh 2>/dev/null \
    --exclude='.acme.sh/http.header' || log "⚠️ acme 备份失败"
tar -czf "$LOCAL_BACKUP_DIR/11b-ecs-misc/ssh.tar.gz" -C /root .ssh 2>/dev/null || log "⚠️ .ssh 备份失败"
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Digest}}\t{{.ID}}\t{{.Size}}' > "$LOCAL_BACKUP_DIR/11b-ecs-misc/docker-images.txt" 2>/dev/null || true
for C in sing-box new-api; do
    docker inspect "$C" > "$LOCAL_BACKUP_DIR/11b-ecs-misc/container-meta-$C.json" 2>/dev/null || true
done

# 10b. Hermes default profile state.db（v5.1 2026-11-10 D3 新增：审计发现 55M 主力会话库零备份——最大单点缺口）
#   与第 10 项 scheduler 同款 sqlite3 .backup 一致性快照模式
log "备份: Hermes default profile state.db"
mkdir -p "$LOCAL_BACKUP_DIR/10b-hermes-default"
sqlite3 /root/.hermes/state.db ".backup '$LOCAL_BACKUP_DIR/10b-hermes-default/state.db'" 2>>"$LOG_FILE" \
    || cp /root/.hermes/state.db "$LOCAL_BACKUP_DIR/10b-hermes-default/state.db" 2>/dev/null \
    || log "⚠️ default state.db 备份失败"
[ -f "$LOCAL_BACKUP_DIR/10b-hermes-default/state.db" ] || log "⚠️ default state.db 缺失"

# 生成备份信息
SERVER_IP=$(curl -s --connect-timeout 5 ifconfig.me 2>/dev/null || echo "47.119.177.194")
cat > "$LOCAL_BACKUP_DIR/backup-info.json" << EOF
{
  "backup_date": "$BACKUP_DATE",
  "backup_time": "$BACKUP_TIME",
  "server_hostname": "$(hostname)",
  "server_ip": "$SERVER_IP",
  "backup_version": "5.1",
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
# v5.1 (2026-11-10 D2): 修复假删除 bug——原 (?<=<href>) 匹配不到 DSM 的 <D:href> 前缀，
#   文件列表恒空 → DELETE 非空目录被 DSM 拒(405) → 3 个历史散目录滞留多日而日志假绿。
#   修法: ①href 提取改 (?<=href>) 无前缀锚定 ②每个 DELETE 校验 HTTP 码并如实计数 ③失败推飞书
RETAIN_DAYS=15
log "开始清理过期备份（保留最近 ${RETAIN_DAYS} 天）..."

CUTOFF_DATE=$(date -d "-${RETAIN_DAYS} days" +%Y%m%d)
log "清理截止日期: $CUTOFF_DATE"

LIST_RESPONSE=$(curl -s -u "$WEBDAV_USER:$WEBDAV_PASS" -X PROPFIND -H "Depth: 1" "$WEBDAV_URL$WEBDAV_BASE/" 2>/dev/null)
BACKUP_DIRS=$(echo "$LIST_RESPONSE" | grep -oP '(?<=server-backup/)\d{8}(?=/)' | sort -u)

deleted_count=0
delete_fail=0
for dir in $BACKUP_DIRS; do
    if [ "$dir" -lt "$CUTOFF_DATE" ] 2>/dev/null; then
        log "删除过期备份: $dir"
        dir_response=$(curl -s -u "$WEBDAV_USER:$WEBDAV_PASS" -X PROPFIND -H "Depth: 1" "$WEBDAV_URL$WEBDAV_BASE/$dir/" 2>/dev/null)
        # v5.1.1 (O1 加固): href 提取不按行 grep——任务书要求兼容跨行 DSM XML；
        #   tr 压成单段后按 href> 锚定提取（兼容 <D:href>/<href> 前缀变体，NAS 侧同思路）
        files=$(echo "$dir_response" | tr '\n' ' ' | grep -oP '(?<=href>)[^<>]+(?=</)' | grep -v "/$dir/\?$")
        for file in $files; do
            http_code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$file" 2>/dev/null)
            if echo "$http_code" | grep -qE "^(200|201|204|404)$"; then
                deleted_count=$((deleted_count + 1))
            else
                delete_fail=$((delete_fail + 1))
                log "⚠️ 删除文件失败 HTTP $http_code: $file"
            fi
        done
        http_code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -u "$WEBDAV_USER:$WEBDAV_PASS" "$WEBDAV_URL$WEBDAV_BASE/$dir/" 2>/dev/null)
        if echo "$http_code" | grep -qE "^(200|201|204|404)$"; then
            deleted_count=$((deleted_count + 1))
        else
            delete_fail=$((delete_fail + 1))
            log "⚠️ 删除目录失败 HTTP $http_code: $dir"
        fi
    fi
done

log "清理完成: 删除 ${deleted_count} 项, 失败 ${delete_fail} 项"

# 任一 DELETE 失败即推飞书告警（防再次假绿静默）+ exit 非零（任务书 O1 要求）
if [ "$delete_fail" -gt 0 ]; then
    send_feishu_card "失败" "N/A" "0s" "未验证" "⚠️ 过期备份清理部分失败（${delete_fail} 项 DELETE 非 2xx）\n详见 /var/log/nas-backup.log"
    exit 1
fi
