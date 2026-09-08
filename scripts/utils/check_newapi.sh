#!/bin/bash
# new-api 网关健康检查 - 每日执行
# 检查: 容器存活 / 内存 / 磁盘增长 / API 可用性 / nginx 桥接
# cron: 20 8 * * * (crontab)
LOG=/var/log/newapi-check.log
echo "===== $(date '+%F %T') new-api 健康检查 ====="

FAIL=0

# 1. 容器状态
STATUS=$(docker inspect new-api --format '{{.State.Status}} (restarts: {{.RestartCount}})' 2>/dev/null)
if [ "$STATUS" = "" ]; then
    echo "🔴 容器 new-api 不存在"; FAIL=1
else
    echo "容器: $STATUS"
    echo "$STATUS" | grep -q '^running' || { echo "🔴 容器非运行状态"; FAIL=1; }
fi

# 2. 内存占用
MEM=$(docker stats new-api --no-stream --format '{{.MemUsage}}' 2>/dev/null)
[ -n "$MEM" ] && echo "内存: $MEM"

# 3. 数据目录磁盘
SIZE=$(du -sh /opt/new-api/data 2>/dev/null | awk '{print $1}')
[ -n "$SIZE" ] && echo "数据目录: $SIZE"
echo "$SIZE" | grep -qE '^[0-9]+G' && { echo "⚠️ 数据目录超 1G，检查日志量"; }

# 4. API 可用性（走公网域名全链路）
CODE=$(curl -s -o /dev/null -w '%{http_code}' -m 10 https://api.ygxpro.online/api/status)
if [ "$CODE" = "200" ]; then
    echo "API 入口: ✅ 200"
else
    echo "🔴 API 入口异常 HTTP $CODE"; FAIL=1
fi

# 5. 实际模型调用（deepseek 便宜渠道）
KEY=$(python3 -c "
import sqlite3
db=sqlite3.connect('/opt/new-api/data/one-api.db')
k=dict((n,x) for n,x in db.execute('SELECT name,key FROM tokens')).get('ecs-openclaw','')
print('sk-'+k)" 2>/dev/null)
RCODE=$(curl -s -o /dev/null -w '%{http_code}' -m 30 -X POST https://api.ygxpro.online/v1/chat/completions \
    -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
    -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"ping"}],"max_tokens":300}')
if [ "$RCODE" = "200" ]; then
    echo "模型调用: ✅ 200"
else
    echo "🔴 模型调用异常 HTTP $RCODE"; FAIL=1
fi

# 6. nginx 桥接端口
ss -tln | grep -q '172.17.0.1:8081' && echo "nginx 桥接: ✅" || { echo "🔴 nginx 桥接 8081 未监听"; FAIL=1; }

if [ $FAIL -eq 1 ]; then
    echo "🔴🔴 new-api 巡检有失败项，需人工介入 🔴🔴"
    exit 1
fi
echo "✅ 全部通过"
