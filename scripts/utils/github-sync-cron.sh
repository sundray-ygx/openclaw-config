#!/bin/bash
# GitHub 每日同步（root crontab 版，2026-10-08 从 openclaw cron 迁移）
# 调度: 30 23 * * * bash /root/scripts/utils/github-sync-cron.sh >> /var/log/github-sync.log 2>&1
# 行为: 执行 sync-to-github.sh；失败推飞书告警（notify_feishu.py，零网关依赖）；成功静默
set -u

TS=$(date '+%F %T')
echo "===== $TS github-sync-cron 开始 ====="

if OUT=$(bash /root/.openclaw/workspace/scripts/sync-to-github.sh 2>&1); then
    echo "$OUT"
    # 无变更/成功均静默；仅当有实质推送时记录一行摘要
    echo "$OUT" | grep -q '同步完成' && echo "[$TS] ✅ 已提交并推送"
    echo "===== $TS github-sync-cron 结束(成功) ====="
else
    RC=$?
    echo "$OUT"
    echo "[$TS] 🔴 同步失败(exit=$RC)，推送飞书告警"
    python3 /root/scripts/utils/notify_feishu.py \
        "🔴 [ECS] GitHub每日同步失败" \
        "时间: $TS
退出码: $RC
输出:
$OUT" || echo "[告警也失败，检查 notify_feishu.py]"
    exit $RC
fi
