#!/bin/bash
# quick-switch.sh — ECS 网关/版本 快速切换统一入口（2026-10-29）
# 用法: quick-switch.sh <动作>
#   quick-switch.sh status    # 查看当前状态（无副作用）
#   quick-switch.sh 0.19      # hermes 切到 v0.19.0（CLI+unit；gateway/TUI 重启后生效）
#   quick-switch.sh 0.22      # hermes 切回 v0.22.4（同上）
#   quick-switch.sh openclaw  # 网关切到 openclaw（停 hermes-gateway→起 openclaw→验证链，失败自动回滚）
#   quick-switch.sh hermes    # 网关切回 hermes（与上互逆）
# 说明: 所有切换动作自动经 systemd-run 脱离会话进程树派发（防 hermes TUI 会话连坐），
#       任何 shell（SSH/hermes TUI/openclaw TUI）里都可安全执行。日志 /var/log/quick-switch-*.log
set -u
ACTION="${1:-}"

S=/root/scripts/utils
LOGDIR=/var/log

dispatch() {  # dispatch <unit名> <命令字符串>；日志名由 unit 名派生
  local unit="$1" cmd="$2" log="$LOGDIR/quick-switch-$1.log"
  systemctl reset-failed "$unit" 2>/dev/null || true
  echo ">>> 派发(脱离进程树): $cmd （日志: $log）"
  systemd-run --wait --collect --quiet --unit="$unit" \
    sh -c "exec >>'$log' 2>&1; echo '=== quick-switch $ACTION $(date '+%F %T') ==='; $cmd"
  local rc=$?
  echo "--- 输出尾部($log) ---"; tail -15 "$log"
  [ $rc -eq 0 ] || echo "!! 动作失败(exit=$rc)，详见上方日志尾部"
  return $rc
}

case "$ACTION" in
  status)
    echo '=== 网关状态 ==='
    printf 'openclaw-gateway: %s (enabled:%s)\n' "$(systemctl is-active openclaw-gateway 2>/dev/null)" "$(systemctl is-enabled openclaw-gateway 2>/dev/null)"
    printf 'hermes-gateway : %s (enabled:%s)\n' "$(systemctl is-active hermes-gateway 2>/dev/null)" "$(systemctl is-enabled hermes-gateway 2>/dev/null)"
    echo; echo '=== hermes 版本指向 ==='
    CLI_TARGET=$(readlink /usr/bin/hermes 2>/dev/null)
    case "$CLI_TARGET" in
      *hermes-agent-0.19.0*) ACTIVE_VER='0.19.0' ;;
      *)                     ACTIVE_VER='0.22.4' ;;
    esac
    echo "CLI(/usr/bin/hermes) -> $CLI_TARGET"
    echo "★ 当前生效版本(新进程/TUI): $ACTIVE_VER"
    echo "unit ExecStart: $(grep -m1 ExecStart /etc/systemd/system/hermes-gateway.service | cut -c1-110)"
    echo "运行中 gateway: PID $(systemctl show hermes-gateway -p MainPID --value 2>/dev/null) 已运行 $(ps -o etime= -p "$(systemctl show hermes-gateway -p MainPID --value 2>/dev/null)" 2>/dev/null | tr -d ' ' || echo '-')"
    systemctl is-active --quiet hermes-gateway && echo "  (网关进程为重启前启动,版本可能仍是旧的;重启后才跟随 unit 生效)"
    echo; echo "=== 版本目录清单(两个并存) ==="
    /usr/lib/node_modules/hermes-agent/runtime/hermes-agent/venv/bin/python -c "import sys; sys.path.insert(0,'/usr/lib/node_modules/hermes-agent/runtime/hermes-agent'); from hermes_cli import __version__; print('hermes-agent/(原git目录):', __version__)" 2>/dev/null
    /usr/lib/node_modules/hermes-agent-0.19.0/runtime/hermes-agent/venv/bin/python -c "from hermes_cli import __version__; print('hermes-agent-0.19.0/(独立venv):', __version__)" 2>/dev/null
    echo; echo '=== openclaw 端口 ==='; /usr/sbin/ss -tln | grep 18789 || echo '18789 空闲(openclaw 网关未运行)'
    ;;
  0.19|0.19.0)
    dispatch qs-version "$S/hermes-version-switch.sh 0.19.0" \
      && echo '✅ 下一步: 退出并重开 hermes TUI 验证乱码；gateway 如需同降: systemctl restart hermes-gateway(先退TUI)'
    ;;
  0.22|0.22.4)
    dispatch qs-version "$S/hermes-version-switch.sh 0.22.4" \
      && echo '✅ 下一步: 重开 TUI / 重启 gateway 回到 0.22.4'
    ;;
  openclaw)
    dispatch qs-openclaw "$S/cutover-start-openclaw.sh" \
      && { echo '✅ 验收: 日志看 channels status 是否 feishu running，再飞书给小群 bot 发条消息实测'
           echo '   注意: hermes TUI 会话已下线；切回用 quick-switch.sh hermes'; }
    ;;
  hermes)
    dispatch qs-back "$S/cutover-back-to-hermes.sh" \
      && echo '✅ 验收: 飞书/hermes TUI 发消息实测'
    ;;
  *)
    grep '^#' "$0" | sed 's/^# \?//;s/^!.*//' | head -12
    [ -n "$ACTION" ] && echo "未知动作: $ACTION"
    exit 1
    ;;
esac
