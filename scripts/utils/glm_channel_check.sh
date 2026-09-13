#!/bin/bash
# new-api GLM 渠道健康检查（纯脚本，零 LLM agent 消耗）
# 行为：异常才推送（job 层 delivery=none + failureAlert），正常静默
# 设计约束：零 $( ) 命令替换、key 不经 shell 文本插值（curl -K 头配置文件），规避传输层内容清洗
set -u
ENV_FILE=/root/.hermes/.env
RESP=/tmp/glm-health.json
META=/tmp/glm-health-meta.txt
HDRCONF=/tmp/glm-hdr.conf
LOG=/var/log/glm-channel-check.log
URL="${GLM_CHECK_URL:-http://127.0.0.1:3000/v1/chat/completions}"
trap 'rm -f "$RESP" "$META" "$HDRCONF"' EXIT

# 从 .env 生成 curl 头配置：key 只存在于临时文件，不进 shell 变量/命令文本
tr -d '\r' < "$ENV_FILE" 2>/dev/null | sed -n 's/^NEWAPI_API_KEY=/header = "Authorization: Bearer /p' | head -1 > "$HDRCONF"
echo '"' >> "$HDRCONF"
if ! grep -q '^header = "Authorization: Bearer .' "$HDRCONF"; then
  echo "🔴 GLM 渠道检查异常：未在 $ENV_FILE 找到有效 NEWAPI_API_KEY" >&2
  date "+%F %T FAIL nokey" >> "$LOG"
  exit 1
fi

# curl：body 落文件，http_code+耗时落 META，read 读回（无命令替换）
if curl -s -m 25 -K "$HDRCONF" -o "$RESP" -w '%{http_code} %{time_total}\n' \
     -X POST "$URL" \
     -H 'Content-Type: application/json' \
     -d '{"model":"glm-5.3","messages":[{"role":"user","content":"ping"}],"max_tokens":8}' \
     > "$META" 2>/dev/null; then
  RC=0
else
  RC=$?
fi
read -r CODE TSEC < "$META" 2>/dev/null || { CODE="000"; TSEC="0"; }

if [ "$RC" -eq 0 ] && [ "$CODE" = "200" ] && grep -q '"choices"' "$RESP" 2>/dev/null; then
  date "+%F %T OK http=${CODE} latency=${TSEC}s" >> "$LOG"
  exit 0
fi

{
  echo "🔴 GLM 渠道异常（HTTP ${CODE}，耗时 ${TSEC}s）"
  echo "主模型 glm-5.3 不可用：Claude Code / Hermes 无自动 fallback，需人工在 new-api 切换渠道；OpenClaw 会自动走 fallback 链。"
  echo -n "详情："
  head -c 300 "$RESP" 2>/dev/null | tr '\n' ' ' | sed 's/sk-[A-Za-z0-9_-]*/sk-***/g'
  echo
} >&2
date "+%F %T FAIL http=${CODE} rc=${RC} latency=${TSEC}s" >> "$LOG"
exit 1
