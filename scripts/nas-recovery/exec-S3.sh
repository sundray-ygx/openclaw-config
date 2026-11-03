#!/bin/bash
# ============================================================
# NAS 恢复 S3 — console 容器修复 + venv/版本深度探测（只读为主）
# 变更动作（Boss 已批准「全部按推荐建议执行」内的容器恢复范畴）：
#   1. docker start projects-console-api-1  （尝试拉起被升级杀掉的服务）
#   2. docker stop projects-console-1       （停止无意义 crash loop，可逆）
# 其余全部只读探测（python/venv/版本/state.db 元数据/.env 填写状态）。
# 用法：SSH 到 NAS root 执行：bash <本脚本路径>
# ============================================================

OUT="/tmp/nas-s3-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS 恢复 S3 — console 修复 + 启动链深探  $(date '+%F %T')"
echo "=================================================="
sec() { echo; echo "########## $1 ##########"; }

sec "A. console-api 拉起（已批准变更）"
docker start projects-console-api-1 2>&1
sleep 5
docker ps -a --filter name=projects-console-api-1 --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo "--- 挂载方式（判断代码是烤进镜像还是 bind） ---"
docker inspect projects-console-api-1 --format '{{json .Mounts}}' 2>/dev/null | head -c 800
echo
echo "--- 本地连通 ---"
timeout 5 curl -s -o /dev/null -w 'console-api 3300: HTTP %{http_code}\n' http://127.0.0.1:3300/ 2>/dev/null || echo 'console-api 3300: CONN-FAIL'

sec "B. console-1 crash loop 止血（已批准变更）"
docker logs --tail 15 projects-console-1 2>&1 | head -18
echo "--- 挂载（确认是否 bind 到已丢失的 /root 路径） ---"
docker inspect projects-console-1 --format '{{json .Mounts}}' 2>/dev/null | head -c 800
echo
docker stop projects-console-1 2>&1
docker ps -a --filter name=projects-console-1 --format 'table {{.Names}}\t{{.Status}}'

sec "C. python 解释器全景（只读）"
echo "--- 系统 python ---"
command -v python3 && python3 --version
ls /usr/local/bin/python* /usr/bin/python3* 2>/dev/null
echo "--- 各 hermes 目录的 bin/ 深查（找自带 python） ---"
for d in /usr/local/lib/hermes-agent /usr/local/lib/hermes-agent-v0.19.0 /usr/local/lib/hermes-agent-v0.21.0 /usr/local/lib/hermes-agent-v0.21.6 /usr/local/lib/hermes-agent-v0.22.4; do
    [ -d "$d" ] || continue
    echo "=== $d ==="
    ls "$d" | head -20
    echo "  bin/: $(ls "$d/bin" 2>/dev/null | head -8 | tr '\n' ' ')"
    [ -x "$d/bin/python3" ] && echo "  ✅ 自带 python3: $($d/bin/python3 --version 2>&1)"
    [ -f "$d/pyvenv.cfg" ] && echo "  pyvenv.cfg: $(head -5 "$d/pyvenv.cfg" | tr '\n' ' ')"
    [ -d "$d/venv" ] && echo "  venv/: $(ls "$d/venv/bin" 2>/dev/null | head -5 | tr '\n' ' ')" || echo "  (无 venv/ 子目录)"
done
echo "--- 全盘找 python3.1x（限 /usr/local，depth 4） ---"
find /usr/local -maxdepth 4 -name 'python3.1*' -type f 2>/dev/null | head -10

sec "D. hermes 各目录版本指纹（只读）"
for d in /usr/local/lib/hermes-agent /usr/local/lib/hermes-agent-v*; do
    [ -d "$d" ] || continue
    V1=$(grep -m1 -rE 'version' "$d/VERSION" 2>/dev/null | head -1)
    V2=$(ls "$d" | grep -iE 'change|version' | head -2 | tr '\n' ' ')
    V3=$(stat -c '%y' "$d" | cut -d' ' -f1)
    echo "$d | VERSION文件:${V1:-无} | 特征文件:$V2 | mtime:$V3"
done

sec "E. state.db 写入者指纹（只读，决定版本选择）"
REAL=/volume1/hermes-data/state.db
timeout 300 sqlite3 "file:${REAL}?mode=ro" "PRAGMA integrity_check;" 2>&1 | head -3
timeout 60 sqlite3 "file:${REAL}?mode=ro" "PRAGMA user_version;" 2>&1
echo "--- 表清单（找 meta/kv/version 类） ---"
timeout 60 sqlite3 "file:${REAL}?mode=ro" "SELECT name FROM sqlite_master WHERE type='table';" 2>&1 | head -30
echo "--- 疑似版本表内容 ---"
for t in meta kv app_meta settings; do
    timeout 30 sqlite3 "file:${REAL}?mode=ro" "SELECT * FROM $t LIMIT 5;" 2>/dev/null && echo "  ^-- table: $t"
done
echo "--- 最近会话时间（写入活跃度） ---"
timeout 60 sqlite3 "file:${REAL}?mode=ro" "SELECT count(*), max(updated_at) FROM sessions;" 2>&1 | head -2 || timeout 60 sqlite3 "file:${REAL}?mode=ro" "SELECT * FROM sessions ORDER BY rowid DESC LIMIT 1;" 2>&1 | head -c 400

sec "F. .env 填写状态（只数空值，不打印内容）"
TOTAL=$(grep -cE '^[A-Z_]+=' /root/.hermes/.env 2>/dev/null)
EMPTY=$(grep -cE '^[A-Z_]+=$' /root/.hermes/.env 2>/dev/null)
echo "键总数: $TOTAL / 空值: $EMPTY $([ "$EMPTY" = 0 ] && echo '✅ 已填齐' || echo '⏳ 待 Boss 填')"

sec "G. newapi 隧道复测（NAS 本机视角）"
timeout 5 curl -s -o /dev/null -w 'newapi 172.17.0.1:3000/api/status: HTTP %{http_code}\n' http://172.17.0.1:3000/api/status 2>/dev/null || echo 'newapi 3000: CONN-FAIL'

sec "S3 完成"
date '+结束: %F %T'
echo "输出文件: $OUT"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cp "$OUT" "$SCRIPT_DIR/" 2>/dev/null && echo "已回传: $SCRIPT_DIR/$(basename "$OUT")" || echo "[回传失败，请手动取 $OUT]"
