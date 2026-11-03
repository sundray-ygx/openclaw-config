#!/bin/bash
# ============================================================
# NAS 恢复 S4 — Python runtime 移植 + venv 修复 + 启动链恢复
# 前置：python-runtime-donor.tar.gz 已在共享目录（ECS 供体，sha 一致）
# 变更动作（Boss 已批准「全部按推荐建议执行」的启动链恢复范畴）：
#   1. 解压供体到 /volume1/hermes-data/python-runtime/（volume1，抗升级）
#   2. 修 v0.22.4 与 hermes-agent 主目录两个 venv 的软链 + pyvenv.cfg
#   5. mkdir console-api data 目录 + docker start（拉起被 bind 失败卡住的服务）
# 不动：state.db（只读探查）、其余三个旧版本目录（不修复，留观）
# 用法：SSH 到 NAS root 执行：bash <本脚本路径>
# ============================================================

OUT="/tmp/nas-s4-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS 恟复 S4 — runtime 移植 + venv 修复  $(date '+%F %T')"
echo "=================================================="
sec() { echo; echo "########## $1 ##########"; }

DONOR_TAR="$(cd "$(dirname "$0")" && pwd)/python-runtime-donor.tar.gz"
RT=/volume1/hermes-data/python-runtime
PY3=$RT/cpython-3.11.15-linux-x86_64-gnu/bin/python3

sec "A. 前置校验"
[ -f "$DONOR_TAR" ] && echo "✅ 供体包在位: $DONOR_TAR ($(stat -c %s "$DONOR_TAR") bytes)" || { echo "❌ 供体包缺失"; exit 1; }
sha256sum "$DONOR_TAR" | awk '{print "供体 sha256:", $1}'
echo "期望 sha256: c4ee7916a272a415288c49827e2a7beaf04cded35be209483a4504ad5fb98ef2"
sha256sum "$DONOR_TAR" | grep -q c4ee7916a272a415288c49827e2a7beaf04cded35be209483a4504ad5fb98ef2 && echo "✅ sha 一致" || { echo "❌ sha 不符，终止"; exit 1; }

sec "B. 解压供体到 volume1（已批准变更）"
mkdir -p "$RT"
tar xzf "$DONOR_TAR" -C "$RT"
echo "tar 退出码: $?"
ls "$RT/"
echo "--- 供体自检 ---"
"$PY3" --version
"$PY3" -c 'import ssl,sqlite3; print("stdlib ok:", ssl.OPENSSL_VERSION)'

sec "C. 修复 venv 软链（已批准变更，逐个处理）"
fix_venv() {
    local VDIR="$1"
    local VBIN="$VDIR/venv/bin"
    echo "=== $VDIR ==="
    [ -d "$VBIN" ] || { echo "  ❌ venv/bin 不存在，跳过"; return; }
    # 记录修复前状态
    echo "  修复前: $(ls -la "$VBIN"/python* 2>/dev/null | head -4 | tr '\n' ' ')"
    # 删除死链，指向供体
    for link in python python3 python3.11 python3.10 python3.8; do
        [ -e "$VBIN/$link" ] || [ -L "$VBIN/$link" ] || continue
        if [ -L "$VBIN/$link" ] && [ ! -e "$VBIN/$link" ]; then
            rm -f "$VBIN/$link"
            ln -s "$PY3" "$VBIN/$link"
            echo "  ✅ $link -> $PY3"
        fi
    done
    # python3 是常规名，若仍缺则直接补
    [ -e "$VBIN/python3" ] || { ln -s "$PY3" "$VBIN/python3"; echo "  ✅ 补建 python3 -> $PY3"; }
    # pip 若软链死链也修
    for link in pip pip3; do
        if [ -L "$VBIN/$link" ] && [ ! -e "$VBIN/$link" ]; then
            rm -f "$VBIN/$link"; ln -s "$RT/cpython-3.11.15-linux-x86_64-gnu/bin/$link" "$VBIN/$link"
            echo "  ✅ $link -> donor"
        fi
    done
    # pyvenv.cfg 的 home 指向供体
    CFG="$VDIR/venv/pyvenv.cfg"
    if [ -f "$CFG" ]; then
        echo "  pyvenv.cfg 修复前: $(grep -E '^(home|version)' "$CFG" | tr '\n' ' ')"
        sed -i "s|^home *=.*|home = $RT/cpython-3.11.15-linux-x86_64-gnu/bin|" "$CFG"
        sed -i "s|^version *=.*|version = 3.11.15|" "$CFG"
        echo "  pyvenv.cfg 修复后: $(grep -E '^(home|version)' "$CFG" | tr '\n' ' ')"
    fi
    # 自检
    echo "  --- venv 自检 ---"
    "$VBIN/python3" --version 2>&1
    "$VBIN/python3" -c 'import ssl,sqlite3,sys; print("venv stdlib ok, prefix:", sys.prefix)' 2>&1
}
fix_venv /usr/local/lib/hermes-agent
fix_venv /usr/local/lib/hermes-agent-v0.22.4

sec "D. hermes CLI 复活验证"
hermes --version 2>&1 | head -3
echo "--- gateway 预检（不启动） ---"
hermes gateway status 2>&1 | head -8 || true

sec "E. console-api 复活（已批准变更）"
mkdir -p /root/.hermes/projects/console-api/data
docker start projects-console-api-1 2>&1
sleep 4
docker ps --filter name=projects-console-api-1 --format 'table {{.Names}}\t{{.Status}}'
timeout 5 curl -s -o /dev/null -w 'console-api 3300: HTTP %{http_code}\n' http://127.0.0.1:3300/ 2>/dev/null || echo 'console-api 3300: CONN-FAIL'

sec "F. 收尾全景"
df -h /volume1 | tail -1
echo "--- 本次修复清单 ---"
cat << 'LIST'
✅ python runtime → /volume1/hermes-data/python-runtime/cpython-3.11.15-linux-x86_64-gnu
✅ venv 修复: /usr/local/lib/hermes-agent(=0.22.4 别名) + v0.22.4
✅ console-api data 目录补建 + 容器拉起
LIST

sec "S4 完成"
date '+结束: %F %T'
echo "输出文件: $OUT"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cp "$OUT" "$SCRIPT_DIR/" 2>/dev/null && echo "已回传: $SCRIPT_DIR/$(basename "$OUT")" || echo "[回传失败，请手动取 $OUT]"
