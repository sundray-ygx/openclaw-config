#!/bin/bash
# ============================================================
# NAS 恢复 S6 — hermes cron 任务重建（13 项核心周期链）
# 依据：S6-periodic-cycle-overview.md（26 任务全景权威清单，git 备份同源）
# 变更动作（Boss 已批准「全部按推荐建议执行」的 cron 重建范畴）：
#   仅写 /root/.hermes/cron/jobs.json + 建输出目录
#   全部 enabled=false —— 点火权留给 Boss 逐个确认（脚本域任务待 scripts/ 重建后再转 no_agent）
# 不动：系统 crontab / cron.d（S7 处理）
# 用法：SSH 到 NAS root 执行：bash <本脚本路径>
# ============================================================

OUT="/tmp/nas-s6-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS 恢复 S6 — cron 任务重建  $(date '+%F %T')"
echo "=================================================="
sec() { echo; echo "########## $1 ##########"; }

JOBS=/root/.hermes/cron/jobs.json

sec "A. 现状核查"
ls -la /root/.hermes/cron/ 2>/dev/null || echo "[cron 目录不存在，将新建]"
if [ -f "$JOBS" ]; then
    echo "⚠️ jobs.json 已存在，不覆盖，退出"; exit 1
fi
echo "✅ jobs.json 不存在，安全重建"

sec "B. 重建 jobs.json（全部 enabled=false）"
mkdir -p /root/.hermes/cron
cat > /tmp/jobs-s6.json << 'JSONEOF'
{
  "version": 1,
  "jobs": [
    {"id": "5a8d236f9706", "name": "早报 morning-briefing", "schedule": "0 8 * * *", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "推送早报。第一步实跑：python3 scripts/daily/notion_daily_fetch.py --mode briefing（脚本待重建，缺失时如实报告勿编造）。早报板块：今日计划/本周计划/今日待办/近期会话回顾(session_search 近1-2天)/系统状态(df/free/docker，基线见 memory/system-baseline.md)/需关注。无任务看板。"},
    {"id": "6df1cbff8e20", "name": "日反思 daily-reflection", "schedule": "0 22 * * *", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "生成当日反思，写入 Notion 日复盘页。数据源：当日会话(session_search)、日安排、待办库。方法参考 skill productivity/periodic-review（GRAI）。写完读回核验。"},
    {"id": "b6b0e8771fa2", "name": "日安排滚动修正", "schedule": "30 22 * * *", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "据 22:00 日反思修正明日日安排（直写+回复可改；纪要只建议不直写）。三分支：普通日=修正明日；周日=周计划复核分支（差异推复核卡不直改）；月末末天=次月1号简版。阶段B铁律(2026-10-30 Boss批复)：未完成项不自动顺延，保留原日+修订卡列「未完成项去向」请裁决。"},
    {"id": "c94ba5f4353c", "name": "周复盘首发（周五19:30）", "schedule": "30 19 * * 5", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "本周复盘初版。数据源：本周日复盘、周计划、待办库。方法参考 productivity/periodic-review。写入周复盘页+推卡。"},
    {"id": "75202c8dbe48", "name": "周计划起草（周五22:10）", "schedule": "10 22 * * 5", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "下周计划草稿+合理性诊断推卡。数据源：周复盘「下周建议」+当日日反思+当月月计划(消费显式化)+下周待办+企微日程。AI起草≠写入；周末批复后落库+产7天日安排。若 22:00 日反思尚未产出，等3分钟重试×2。"},
    {"id": "f590e89b228b", "name": "周复盘完整版更新（周日22:15）", "schedule": "15 22 * * 0", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "刚完结周全量重算（offset 0=周日视角）。数据源：周计划+全周7天日复盘（含周末）。覆盖写入+「更新版」卡片；写后校验+读回核验。"},
    {"id": "aeeb5d21a122", "name": "周末复盘提醒（周六日21:30）", "schedule": "30 21 * * 0,6", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "watchdog：查 Notion 日复盘页当日「今日复盘&反思」字段是否已填。已填=静默零打扰（不发消息）；未填=推飞书提醒卡。"},
    {"id": "c71bcef473a6", "name": "月复盘 periodic-review-monthly", "schedule": "0 22 28-31 * *", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "复盘当月（offset 0）。GRAI五节+健康统计+里程碑/教训上浮。数据源：月计划+当月全部周复盘+日复盘+健康打卡库。手术式写入+读回核验。guard：非月末最后一天静默退出；12/31 让路给年计划链。"},
    {"id": "772a5c340243", "name": "月计划起草（月末23:30）", "schedule": "30 23 28-31 * *", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "下月计划草稿+六项诊断推卡。数据源：季度计划(上层)+当月月复盘行动建议+目标/KR库。批复落库批=落库+回查+同产次月7天日安排+周计划向后复核。guard：非月末最后一天静默；12/31 让路。"},
    {"id": "94f20499bcb1", "name": "季复盘 periodic-review-quarterly", "schedule": "30 22 28-31 3,6,9,12 *", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "复盘当季，策略层 GRAI。数据源：季度计划+3篇月复盘(含月度AI复盘)+周复盘摘要+健康聚合。手术式写入+读回核验；非季末最后一天静默。"},
    {"id": "1d64dccf22af", "name": "季计划起草（季末23:00）", "schedule": "0 23 28-31 3,6,9,12 *", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "下季计划草稿（主题句+季级举措+KR布局建议）。数据源：年计划(上层)+季复盘行动建议。批复后季首前落库。guard：非季末最后一天静默；12/31 让路。"},
    {"id": "ad2f249c865b", "name": "年复盘（12/31 23:00）", "schedule": "0 23 31 12 *", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "复盘当年（战略层 GRAI）。读4篇季复盘+12篇月计划摘要+全年健康聚合。写入年复盘页+推卡。"},
    {"id": "4bc53d856191", "name": "年计划三连（12/31 23:10）", "schedule": "10 23 31 12 *", "enabled": false, "deliver": "feishu", "origin": null, "workdir": "/root/.hermes", "no_agent": false, "script": null, "prompt": "单会话连出年(23:10)→季(23:25)→月(23:40)三份草稿，一张卡一批批复；跨年批复→1/1落库；止于月不出周/日草稿。"}
  ]
}
JSONEOF
python3 -m json.tool /tmp/jobs-s6.json > /dev/null && echo "✅ JSON 语法合法" || { echo "❌ JSON 语法错误，终止"; exit 1; }
cp /tmp/jobs-s6.json "$JOBS"

sec "C. 语义校验"
python3 << 'PYEOF'
import json
d = json.load(open('/root/.hermes/cron/jobs.json'))
jobs = d['jobs']
print('任务数:', len(jobs))
assert len(jobs) == 13, 'expect 13'
REQ = ('id','name','schedule','enabled','deliver','origin','workdir','no_agent','script','prompt')
bad = [j['name'] for j in jobs if not all(k in j for k in REQ) or any(j.get(k) in ('katalog','启用') for k in j)]
assert not bad, f'bad jobs: {bad}'
ids = [j['id'] for j in jobs]
assert len(set(ids)) == 13, 'duplicate ids'
for j in jobs:
    parts = j['schedule'].split()
    assert 5 <= len(parts) <= 6, f"bad schedule {j['name']}: {j['schedule']}"
    assert j['enabled'] is False, f"enabled!=False: {j['name']}"
    assert j['workdir'] == '/root/.hermes', 'workdir must be explicit (pitfall #30)'
    assert j['deliver'] == 'feishu', 'deliver must be feishu not local (pitfall #20)'
    print(f"  {j['id']} | {j['name'][:20]:<22} | {j['schedule']:<20} | enabled={j['enabled']}")
print('✅ 13 任务全部 enabled=false / workdir 显式 / deliver=feishu —— 点火权在 Boss')
PYEOF
RC=$?
[ $RC -ne 0 ] && { echo "❌ 语义校验失败，回滚"; rm -f "$JOBS"; exit 1; }

sec "D. 输出目录与权限"
mkdir -p /root/.hermes/cron/output
chmod 700 /root/.hermes/cron
chmod 600 "$JOBS"
ls -la /root/.hermes/cron/

sec "S6 完成"
date '+结束: %F %T'
echo "输出文件: $OUT"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cp "$OUT" "$SCRIPT_DIR/" 2>/dev/null && echo "已回传: $SCRIPT_DIR/$(basename "$OUT")" || echo "[回传失败，请手动取 $OUT]"
