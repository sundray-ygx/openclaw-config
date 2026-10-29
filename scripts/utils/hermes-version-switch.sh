#!/bin/bash
# hermes 版本切换 v2（2026-10-29 定版机制）
# 切换点 = /usr/bin/hermes 软链 + hermes-gateway unit 的 venv 路径（NAS Strategy B 原版做法）
# ⚠️ 不动 /usr/lib/node_modules/hermes-agent 目录本身——pm 按 install 路径哈希登记依赖环境，
#    改名会触发 repair 循环（2026-10-29 实测教训），现役目录保持原名。
# 用法:
#   hermes-version-switch.sh            # 状态
#   hermes-version-switch.sh 0.19.0     # 切到 0.19.0（venv/pip 形态，独立目录）
#   hermes-version-switch.sh 0.22.4     # 切回 0.22.4（git/npm 壳形态，现役原名目录）
# 效果: 只影响新进程；gateway 需 systemctl restart hermes-gateway 生效，TUI 需重开。
set -euo pipefail
UNIT=/etc/systemd/system/hermes-gateway.service
V19=/usr/lib/node_modules/hermes-agent-0.19.0
V22=/usr/lib/node_modules/hermes-agent

status() {
  echo '=== 版本目录真身 ==='
  [ -d "$V19" ] && $V19/runtime/hermes-agent/venv/bin/python -c "from hermes_cli import __version__; print('0.19.0 目录:', __version__)" 2>/dev/null
  [ -d "$V22" ] && $V22/runtime/hermes-agent/venv/bin/python -c "import sys; sys.path.insert(0,'$V22/runtime/hermes-agent'); from hermes_cli import __version__; print('现役目录:', __version__)" 2>/dev/null
  echo
  echo '=== CLI 指向 ==='; readlink /usr/bin/hermes
  echo '=== unit venv 路径 ==='; grep ExecStart "$UNIT" | head -1
}

[ $# -eq 0 ] && { status; exit 0; }
VER="$1"

if [ "$VER" = "0.19.0" ]; then
  [ -d "$V19" ] || { echo "错误: $V19 不存在"; exit 1; }
  cp -a "$UNIT" "$UNIT.bak-version-switch"
  sed -i "s|$V22/|$V19/|g" "$UNIT"
  ln -sfn "$V19/bin/hermes.js" /usr/bin/hermes
elif [ "$VER" = "0.22.4" ]; then
  cp -a "$UNIT" "$UNIT.bak-version-switch"
  sed -i "s|$V19/|$V22/|g" "$UNIT"
  ln -sfn ../lib/node_modules/hermes-agent/bin/hermes.js /usr/bin/hermes
else
  echo "不支持的版本: $VER（当前支持 0.19.0 / 0.22.4）"; exit 1
fi

systemctl daemon-reload
echo '=== 切换完成，当前状态 ==='
status
echo
echo '生效: gateway → systemctl restart hermes-gateway（先退 TUI 会话）；TUI → 退出重开。'
echo "回滚: $0 <另一版本>；unit 备份: $UNIT.bak-version-switch"
