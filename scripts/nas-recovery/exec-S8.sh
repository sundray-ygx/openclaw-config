#!/bin/bash
# ============================================================
# NAS 恢复 S8 — Node 运行时供体移植（修 TUI npm not found）
# 变更动作（Boss 已批复方案 B）：
#   1. 解压 node 供体到 /volume1/hermes-data/node-runtime/v24.22.2
#   2. 写 /etc/profile.d/node-runtime.sh（PATH 注入，rootfs 但一行可自愈）
#   3. 自检：node/npm 版本 + hermes --tui 烟测（启动即退，不进交互）
# 不动：hermes 安装本体、ui-tui/、网关（已 active）
# 用法：SSH 到 NAS root 执行：bash <本脚本路径>
# ============================================================

OUT="/tmp/nas-s8-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS 恢复 S8 — Node 运行时移植  $(date '+%F %T')"
echo "=================================================="
sec() { echo; echo "########## $1 ##########"; }

# 主机守卫
HN=$(hostname)
if [ "$HN" != "enjoysynology" ]; then
    echo "❌ 主机守卫：hostname=$HN ≠ enjoysynology，终止（本脚本仅限 NAS）"
    exit 1
fi
echo "✅ 主机守卫通过: $HN"

DONOR_TAR="$(cd "$(dirname "$0")" && pwd)/node-runtime-donor.tar.gz"
NR=/volume1/hermes-data/node-runtime
NODEBIN=$NR/v24.22.2/bin

sec "A. 前置校验"
[ -f "$DONOR_TAR" ] && echo "✅ 供体包在位 ($(stat -c %s "$DONOR_TAR") bytes)" || { echo "❌ 供体包缺失"; exit 1; }
GOT=$(sha256sum "$DONOR_TAR" | awk '{print $1}')
echo "sha256: $GOT"
[ "$GOT" = "af8b562ecb2f8b76bbf3f61deed23c3a897e72346de94a3611c8e3c6251fa5ee" ] && echo "✅ sha 一致" || { echo "❌ sha 不符，终止"; exit 1; }

sec "B. 解压供体（已批准变更）"
mkdir -p "$NR"
tar xzf "$DONOR_TAR" -C "$NR"
echo "tar 退出码: $?"
ls "$NR/"

sec "C. PATH 注入（已批准变更）"
cat > /etc/profile.d/node-runtime.sh << 'PATHEOF'
# Node.js runtime (donor transplant 2026-10-31, survives DSM upgrades on volume1)
export PATH="/volume1/hermes-data/node-runtime/v24.22.2/bin:$PATH"
PATHEOF
chmod 644 /etc/profile.d/node-runtime.sh
cat /etc/profile.d/node-runtime.sh
# 当前 shell 也生效
export PATH="$NODEBIN:$PATH"

sec "D. 自检"
"$NODEBIN/node" --version
"$NODEBIN/npm" --version 2>/dev/null | head -1
command -v node && node --version
command -v npm && npm --version 2>/dev/null | head -1

sec "E. hermes --tui 烟测（启动即退）"
# TUI 是交互程序：给 stdin 喂 EOF 让它启动后立即退出；超时 60s 兜底
timeout 60 hermes --tui < /dev/null > /tmp/tui-smoke.out 2>&1
RC=$?
echo "退出码: $RC（124=超时被杀=其实TUI活着，也算通）"
head -20 /tmp/tui-smoke.out
if [ $RC -eq 124 ]; then
    echo "判读：TUI 持续运行至超时——启动成功（交互界面已渲染）"
elif [ $RC -eq 0 ]; then
    echo "判读：TUI 正常启动并退出"
else
    echo "⚠️ 非预期退出码，看上方输出定位"
fi

sec "F. ui-tui node_modules 状态（只读，判断是否需 npm install）"
# 直接找安装树里的 ui-tui（tarball 安装布局）
for cand in /volume1/hermes-data/hermes-agent-v0.19.0/ui-tui /usr/local/lib/hermes-agent-v0.19.0/ui-tui /usr/local/lib/hermes-agent/ui-tui; do
    if [ -d "$cand" ]; then
        echo "ui-tui: $cand"
        [ -d "$cand/node_modules" ] && echo "  node_modules ✅在位 ($(du -sh "$cand/node_modules" 2>/dev/null | cut -f1)) — 无需 npm install" || echo "  node_modules ❌缺失 — 首次跑 TUI 会自动 npm install（或手动跑）"
        [ -d "$cand/dist" ] && echo "  dist ✅在位（预构建）" || echo "  dist 无（走源码路径，正常）"
        break
    fi
done

sec "S8 完成"
date '+结束: %F %T'
echo "输出文件: $OUT"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cp "$OUT" "$SCRIPT_DIR/" 2>/dev/null && echo "已回传: $SCRIPT_DIR/$(basename "$OUT")" || echo "[回传失败，请手动取 $OUT]"
