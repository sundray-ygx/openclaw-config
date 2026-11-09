#!/bin/bash
# new-api GLM 渠道健康检查（root crontab 版，2026-10-08 从 openclaw cron 迁移）
# 调度: 30 9 * * * bash /root/scripts/utils/glm-check-cron.sh >> /var/log/glm-channel-check-cron.log 2>&1
# 行为: 执行 glm_channel_check.sh（纯 shell 零 LLM）；成功静默；失败 exit 1 → 推飞书告警
# 原 openclaw failureAlert 语义等价迁移（2026-09-13 方案B+静默模式）
set -u

TS=$(date '+%F %T')
echo "===== $TS glm-check-cron 开始 ====="

if OUT=$(bash /root/.openclaw/workspace/scripts/utils/glm_channel_check.sh 2>&1); then
    echo "$OUT"
    echo "===== $TS glm-check-cron 结束(正常) ====="
else
    RC=$?
    echo "$OUT"
    echo "[$TS] 🔴 GLM 渠道检查失败(exit=$RC)，推送飞书告警"
    python3 /root/scripts/utils/notify_feishu.py --card \
        "🔴 [ECS] GLM 渠道健康检查失败" \
        "时间: $TS
退出码: $RC
输出:
$OUT" red || echo "[告警也失败，检查 notify_feishu.py]"
    exit $RC
fi
