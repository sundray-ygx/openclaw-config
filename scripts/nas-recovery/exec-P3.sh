#!/bin/bash
# ============================================================
# NAS 只读探测 P3 — v0.19.0 回滚「Python 3.11.15 缺失」根因定位
# 日期: 2026-11-07 · 作者: ECS 小群
# 背景: hermes-rollback 报 "Python 3.11.15 缺失" + "uv: command not found"
#       但 10-31 S4 曾把 3.11.15 供体装到 /volume1/hermes-data/python-runtime/
#       并修好 v0.19.0 venv —— 现在又缺失 = 中间有回归，需定位哪一环断了
# 安全: 全程只读，不改任何文件、不重启任何服务、不执行 rollback；
#       唯一执行的二进制是 <donor>/bin/python3 --version（无副作用）
# ============================================================
OUT="/tmp/nas-p3-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS P3 — v0.19.0 回滚 Python 缺失根因探测  $(date '+%F %T')"
echo "=================================================="

HN=$(hostname)
if [ "$HN" != "enjoysynology" ]; then
    echo "❌ 主机守卫: hostname=$HN ≠ enjoysynology, 终止"
    exit 1
fi
echo "✅ 主机守卫通过: $HN"

sec() { echo; echo "########## $1 ##########"; }

# ------------------------------------------------------------
sec "A. 软链全景（版本切换的骨架）"
ls -la /usr/local/lib/ 2>/dev/null | grep -i hermes
echo "--- 逐个解析真实指向 ---"
for l in /usr/local/lib/hermes-agent /usr/local/lib/hermes-agent-v0.19.0 /usr/local/lib/hermes-agent-v0.22.4; do
    [ -e "$l" ] || { echo "$l  不存在"; continue; }
    echo "$l -> $(readlink -f "$l")"
done
echo "--- CLI 入口 ---"
ls -la /usr/local/bin/hermes 2>/dev/null || echo "/usr/local/bin/hermes 不存在"
head -2 /usr/local/bin/hermes 2>/dev/null

# ------------------------------------------------------------
sec "B. rollback 脚本本体（只 cat 不执行）"
ls -la /usr/local/sbin/hermes-rollback
md5sum /usr/local/sbin/hermes-rollback
echo "---- 全文 ----"
cat /usr/local/sbin/hermes-rollback

# ------------------------------------------------------------
sec "C. v0.19.0 venv 诊断（rollback 报缺失的目标）"
T=/usr/local/lib/hermes-agent-v0.19.0
echo "--- pyvenv.cfg 全文 ---"
cat "$T/venv/pyvenv.cfg" 2>&1
echo "--- venv/bin/python* 软链实况 ---"
ls -la "$T"/venv/bin/python* 2>&1
echo "--- 逐个解析指向是否存活 ---"
for p in "$T"/venv/bin/python "$T"/venv/bin/python3 "$T"/venv/bin/python3.11; do
    [ -L "$p" ] || { echo "$p 非软链或不存在"; continue; }
    real=$(readlink -f "$p")
    if [ -x "$real" ]; then echo "$p -> $real  [存活]"; else echo "$p -> $real  [断裂❌]"; fi
done
echo "--- 复刻 rollback 检测逻辑（逐中间变量） ---"
th=$(grep "^home = " "$T/venv/pyvenv.cfg" 2>/dev/null | cut -d= -f2 | xargs)
tv=$(grep "^version = " "$T/venv/pyvenv.cfg" 2>/dev/null | cut -d= -f2 | xargs)
[ -z "$tv" ] && tv=$(grep "^version_info = " "$T/venv/pyvenv.cfg" 2>/dev/null | cut -d= -f2 | xargs | cut -d. -f1-3)
echo "home = [$th]"
echo "version = [$tv]"
echo "ls \$home 输出: $(ls "$th" 2>&1 | tr '\n' ' ')"
first=$(ls "$th" 2>/dev/null | grep "^python3" | head -1)
echo "grep ^python3 首个 = [$first]"
if [ -n "$first" ] && [ -x "$th/$first" ]; then echo "判定: 解释器在位（rollback 不应触发安装）"; else echo "判定: 解释器缺失 → 这就是 rollback 报缺失的原因"; fi

# ------------------------------------------------------------
sec "D. Python 供体目录（S4 装到 /volume1 的那份）"
ls -la /volume1/hermes-data/python-runtime/ 2>&1
DONOR=/volume1/hermes-data/python-runtime/cpython-3.11.15-linux-x86_64-gnu
if [ -x "$DONOR/bin/python3" ]; then
    echo "--- 供体自检 ---"
    "$DONOR/bin/python3" --version 2>&1
else
    echo "❌ 供体解释器不存在于 $DONOR/bin/python3"
    echo "--- /volume1/hermes-data/ 下还有什么 python 相关目录 ---"
    ls -la /volume1/hermes-data/ 2>/dev/null | grep -iE "python|runtime"
fi
echo "--- WebDAV 供体包（灾备物料，不动） ---"
ls -la /volume1/aliyun_backup/nas-recovery/python-runtime-donor.tar.gz 2>&1
sha256sum /volume1/aliyun_backup/nas-recovery/python-runtime-donor.tar.gz 2>/dev/null
echo "(S4 期望 sha256: c4ee7916a272a415288c49827e2a7beaf04cded35be209483a4504ad5fb98ef2)"

# ------------------------------------------------------------
sec "E. uv 猎捕（次生故障定位 + 供后续决策）"
echo "which -a uv: $(which -a uv 2>/dev/null || echo 无)"
ls -la /root/.local/bin/uv /usr/local/bin/uv /usr/bin/uv 2>&1 | grep -v "No such"
echo "--- /root/.local/bin/ 目录是否存在及内容 ---"
ls -la /root/.local/bin/ 2>&1 | head -8
echo "--- find /volume1/hermes-data 下的 uv 二进制（限深度4） ---"
find /volume1/hermes-data -maxdepth 4 -name uv -type f 2>/dev/null | head -5
echo "--- uv 托管 python 目录 ---"
ls /root/.local/share/uv/python/ 2>&1

# ------------------------------------------------------------
sec "F. uv python 目录逐项存活检查（对照 venv 期望）"
ls -la /root/.local/share/uv/python/ 2>/dev/null | tail -n +2 | awk '{print $NF}' | while read -r d; do
    p="/root/.local/share/uv/python/$d"
    [ -x "$p/bin/python3" ] && echo "$d [存活]" || echo "$d [缺解释器]"
done

# ------------------------------------------------------------
sec "G. gateway 现状（生产是否健在）"
systemctl is-active hermes-gateway 2>&1
ps aux 2>/dev/null | grep -E "hermes_cli.*gateway" | grep -v grep
GWPID=$(ps aux 2>/dev/null | grep -E "hermes_cli.*gateway run" | grep -v grep | awk '{print $2}' | head -1)
if [ -n "$GWPID" ] && [ -r "/proc/$GWPID/cmdline" ]; then
    echo "--- 网关进程 $GWPID 启动于: $(ps -o lstart= -p $GWPID) ---"
    echo "--- 其解释器真实路径: $(readlink -f /proc/$GWPID/exe) ---"
fi
echo "--- journal 自 11-05 起的启停/失败/飞书WS ---"
journalctl -u hermes-gateway --since "2026-11-05" --no-pager 2>/dev/null | grep -iE "started|stopped|FAILURE|connected to wss" | tail -15

# ------------------------------------------------------------
sec "H. v0.23.0 现状（对照 + 为 stamp 修复备料）"
echo "--- install-stamp.json ---"
cat /volume1/hermes-data/hermes-agent-v0.23.0/install-stamp.json 2>&1
echo "--- pm-runtime 目录 ---"
ls /volume1/hermes-data/hermes-agent-v0.23.0/pm-runtime 2>&1
echo "--- v0.23.0 venv 用的哪个 python（它活着=有可用解释器线索） ---"
grep -E "^(home|version)" /volume1/hermes-data/hermes-agent-v0.23.0/venv/pyvenv.cfg 2>&1
P23=$(grep "^home = " /volume1/hermes-data/hermes-agent-v0.23.0/venv/pyvenv.cfg 2>/dev/null | cut -d= -f2 | xargs)
[ -n "$P23" ] && "$P23/python3" --version 2>&1
ls -la /volume1/hermes-data/hermes-agent-v0.23.0/venv/bin/python* 2>&1

# ------------------------------------------------------------
sec "I. v0.22.4 venv 对照"
grep -E "^(home|version)" /usr/local/lib/hermes-agent-v0.22.4/venv/pyvenv.cfg 2>&1

# ------------------------------------------------------------
sec "J. 磁盘与收尾"
df -h /volume1 /root 2>&1 | grep -v tmpfs
echo
echo "########## P3 完成（只读，无任何变更）##########"
SRC="$(cd "$(dirname "$0")" && pwd)"
cp "$OUT" "$SRC/nas-p3-latest.txt" 2>/dev/null && echo "已回传: $SRC/nas-p3-latest.txt" || echo "⚠️ 回传失败, 请手动拷 $OUT"
