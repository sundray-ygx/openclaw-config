#!/bin/bash
# acme.sh NOTIFY_HOOK 包装器：证书签发/续期失败 → 飞书红色卡片告警
# 注册方式（已完成 2026-10-19）：
#   acme.sh --set-notify --notify-hook /root/scripts/utils/acme_notify.sh --notify-level 1 --home /root/.acme.sh
# --notify-level 1 = 仅错误时触发本钩子（成功静默，符合 feishu-alert-ops 铁律）
# acme.sh 调用时注入环境变量：NOTIFY_LEVEL / NOTIFY_SOURCE / NOTIFY_HOOK
# 手动测试：NOTIFY_SOURCE=test /root/scripts/utils/acme_notify.sh   （绿卡，验证链路用）
set +e

SOURCE="${NOTIFY_SOURCE:-unknown}"
LOG="/root/.acme.sh/acme.sh.log"

if [ "$SOURCE" = "test" ]; then
    COLOR="green"
    TITLE="SSL 证书告警链路测试"
    BODY="这是 acme.sh NOTIFY_HOOK 的链路测试卡片（非真实故障）。收到即链路正常。"
else
    COLOR="red"
    TITLE="SSL 证书签发/续期失败告警"
    BODY="**域名**: *.ygxpro.online / ygxpro.online
**触发源**: ${SOURCE}
**时间**: $(date '+%F %T')

**日志尾部**（${LOG}）：
\`\`\`
$(tail -n 20 "$LOG" 2>/dev/null)
\`\`\`

排查手册：knowledge/tech/infrastructure/ygxpro-wildcard-cert-mechanism.md 第4节"
fi

python3 /root/scripts/utils/notify_feishu.py --card "$TITLE" "$BODY" "$COLOR" >> /var/log/acme_notify.log 2>&1 || true
exit 0
