#!/bin/bash
# 域名证书续期观察 + 域名处置决策提醒（2026-11-05 Boss 指令）
# 背景：ygxpro.online 2027-05-13 到期；预案见 knowledge/tech/infrastructure/2026-11-05-nas-domain-migration-plan.md
# 链路：root crontab 硬编码凭据直连飞书 API（ECS 定版模式，不经 gateway）——同 pull.sh / heartbeat_syscheck.sh
# cron（两条，2026-11-05 挂载）：
#   42 8 24 12 * bash /root/scripts/reminder/domain_renewal_reminder.sh run   # 续期结果观察
#   42 8 28 12 * bash /root/scripts/reminder/domain_renewal_reminder.sh run   # 决策催办(可ACK跳过)
# 依据：Le_NextRenewTime=2026-12-22T23:51Z(=北京时间12-23 07:51)，acme cron 每日22:06跑
#       → 实际续期动作发生在 12-23 22:06，故 12-24 晨推送能带上实测结果
# ACK：Boss 已决策后执行 `domain_renewal_reminder.sh ack` 写标记，12-28 不再催办
# 幂等：无状态推送；日志 /var/log/domain-renewal-reminder.log
set -u

ACK_FILE="/root/scripts/reminder/.domain-decision-acked"
LOG="/var/log/domain-renewal-reminder.log"
MODE="${1:-}"

send_card() {  # $1=title $2=body(lark_md) $3=template(green/red/orange)
    python3 - "$1" "$2" "$3" << 'PYEOF'
import sys, json, urllib.request, urllib.parse
title, body, template = sys.argv[1:4]
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": "cli_a93c6b1e1ff89bd4", "app_secret": "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=10) as resp:
    token = json.loads(resp.read().decode()).get("tenant_access_token")
card = {"config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": title}, "template": template},
        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": body}}]}
msg = {"receive_id": "ou_d8ae71cd421f8954a9c97e973d4f03d1", "msg_type": "interactive",
       "content": json.dumps(card, ensure_ascii=False)}
url = "https://open.feishu.cn/open-apis/im/v1/messages?" + urllib.parse.urlencode({"receive_id_type": "open_id"})
r = urllib.request.Request(url, data=json.dumps(msg, ensure_ascii=False).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + token}, method="POST")
with urllib.request.urlopen(r, timeout=10) as resp:
    out = json.loads(resp.read().decode())
sys.exit(0 if out.get("code") == 0 else 1)
PYEOF
}

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# 线上证书实况：notAfter 字符串 + 是否已续期（80天阈值：12-23刚续=89天余量→OK；未续=28天→FAIL）
CERT_PEM=$(echo | timeout 8 openssl s_client -connect 127.0.0.1:443 -servername vw.ygxpro.online 2>/dev/null | openssl x509)
NA=$(echo "$CERT_PEM" | openssl x509 -noout -enddate | cut -d= -f2)
if echo "$CERT_PEM" | openssl x509 -checkend $((80*86400)) >/dev/null 2>&1; then RENEWED=ok; else RENEWED=fail; fi

case "$MODE" in
    ack)
        echo "$(date '+%F %T') Boss 已完成域名处置决策" > "$ACK_FILE"
        log "ACK: 决策标记写入 $ACK_FILE"
        echo "已标记决策完成，12-28 催办将自动跳过"
        exit 0 ;;
    test)
        send_card "域名证书续期提醒（链路测试）" "**这是链路测试卡片，非真实提醒。**
收到即链路正常。当前线上证书 notAfter: ${NA}

**背景**：\`*.ygxpro.online\` 实际续期动作预计 **2026-12-23 22:06**（acme cron）
12-24 08:42 推送续期结果观察卡；12-28 08:42 决策催办（可 ack 跳过）。
预案：knowledge/tech/infrastructure/2026-11-05-nas-domain-migration-plan.md" green \
        && { log "TEST: 推送成功"; echo "✅ 测试卡片已推送"; } \
        || { log "TEST: 推送失败"; echo "❌ 推送失败"; exit 1; }
        exit 0 ;;
    run)
        TODAY=$(date +%m-%d)
        if [ "$TODAY" = "12-24" ]; then
            if [ "$RENEWED" = "ok" ]; then
                BODY="**续期结果**：✅ 成功。线上证书新有效期至 **${NA}**，acme.sh dns_ali 链路健康。

**待决策**：域名 \`ygxpro.online\` **2027-05-13 到期**，二选一：
• **A. 采购新域名** → 启动预案阶段 0（新证书+nginx双轨+客户端切换）
• **B. 续费旧域名 1 年** → 零迁移，仅续费

预案已归档：knowledge/tech/infrastructure/2026-11-05-nas-domain-migration-plan.md
在 ECS 会话回复小群即可推进。"; TPL=green; TTL="✅ 证书续期成功 | 域名处置决策提醒"
            else
                BODY="**续期结果**：🔴 异常。线上证书 notAfter=**${NA}**（checkend 80 天不通过）。
预期 12-23 22:06 acme cron 续期后应顺延至 2027-03 下旬。
排查：/root/.acme.sh/acme.sh.log 尾部；acme_notify.sh 红卡应已先达。
**域名处置决策顺延**至续期问题解决。" ; TPL=red; TTL="🔴 证书续期异常 | 请处理"
            fi
            send_card "$TTL" "$BODY" "$TPL" && { log "12-24 观察卡推送成功 (renewed=$RENEWED, na=$NA)"; exit 0; } || { log "12-24 推送失败"; exit 1; }
        fi
        if [ "$TODAY" = "12-28" ]; then
            if [ -f "$ACK_FILE" ]; then log "12-28: 已 ACK，跳过催办"; exit 0; fi
            send_card "⏰ 域名处置决策催办（2/2）" "**待决策**：\`ygxpro.online\` 2027-05-13 到期，预案已归档备案。
• **A. 采购新域名** → 启动迁移预案阶段 0
• **B. 续费旧域名** → 零迁移，仅续费

未决策前不执行任何变更。若已决策，ECS 会话告知小群即可停止催办。" orange \
            && { log "12-28 催办卡推送成功"; exit 0; } || { log "12-28 催办卡推送失败"; exit 1; }
        fi
        log "run: 非目标日期($TODAY)，静默退出"; exit 0 ;;
    *)
        echo "用法: $0 {run|test|ack}"; exit 2 ;;
esac
