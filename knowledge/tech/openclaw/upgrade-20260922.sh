#!/bin/bash
# OpenClaw 2026.9.3 -> 2026.9.5 升级脚本（systemd-run 自愈闭环模式）
# 用法:
#   预演:  DRY_RUN=1 bash upgrade-20260922.sh          (只打印动作，不执行)
#   真跑:  systemd-run --unit=claw-upgrade-0922 --collect bash upgrade-20260922.sh
# 日志:  /tmp/openclaw-upgrade-20260922.log（真跑模式）
set -u
export HOME=/root
export PNPM_HOME=/root/.local/share/pnpm
export PATH=/root/.nvm/versions/node/v24.21.0/bin:/root/.local/share/pnpm:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin

OLD_VER="2026.9.3"
NEW_VER="2026.9.5"
UNIT="/etc/systemd/system/openclaw-gateway.service"
WRAPPER="/usr/bin/openclaw"
DRY="${DRY_RUN:-0}"

if [ "$DRY" != "1" ]; then
  exec > /tmp/openclaw-upgrade-20260922.log 2>&1
fi
set -x

log()  { echo "### [$(date +%F' '%T)] $*"; }

rollback() {
  log "!!! ROLLBACK START"
  [ "$DRY" = "1" ] && { echo "(DRY_RUN 模拟回滚)"; exit 99; }
  pnpm add -g "openclaw@$OLD_VER" --dangerously-allow-all-builds
  sed -i "s|openclaw@$NEW_VER|openclaw@$OLD_VER|g" "$UNIT" "$WRAPPER"
  systemctl daemon-reload
  systemctl start openclaw-gateway || true
  for i in $(seq 1 15); do ss -tln | grep -q ':18789 ' && break; sleep 2; done
  if ss -tln | grep -q ':18789 '; then
    log "ROLLBACK OK - service restored on $OLD_VER"
  else
    log "ROLLBACK FAILED - MANUAL INTERVENTION NEEDED"
  fi
  exit 99
}

# 1) 停网关（腾 473M 防 pnpm OOM）
log "STEP1 stop gateway"
if [ "$DRY" = "1" ]; then echo "  (dry) systemctl stop openclaw-gateway"; else
  systemctl stop openclaw-gateway
  for i in $(seq 1 20); do ss -tln | grep -q ':18789 ' || break; sleep 2; done
  ss -tln | grep -q ':18789 ' && { log "PORT STILL BUSY"; fuser -k 18789/tcp 2>/dev/null; sleep 3; }
fi

# 2) kill TUI（Boss 决策：脚本杀，升级完手动重开）
log "STEP2 kill TUI"
if [ "$DRY" = "1" ]; then echo "  (dry) pkill -f openclaw-tui"; else pkill -f 'openclaw-tui' 2>/dev/null || true; fi

# 3) pnpm 安装 2026.9.5
log "STEP3 pnpm add -g openclaw@$NEW_VER"
if [ "$DRY" = "1" ]; then echo "  (dry) pnpm add -g openclaw@$NEW_VER --dangerously-allow-all-builds"; else
  pnpm add -g "openclaw@$NEW_VER" --dangerously-allow-all-builds || { log "INSTALL FAILED"; rollback; }
fi

# 4) unit + wrapper 路径切换 9.3 -> 9.5
log "STEP4 sed paths in unit+wrapper"
if [ "$DRY" = "1" ]; then
  echo "  (dry) sed s|openclaw@$OLD_VER|openclaw@$NEW_VER|g $UNIT $WRAPPER"
else
  sed -i "s|openclaw@$OLD_VER|openclaw@$NEW_VER|g" "$UNIT" "$WRAPPER"
  grep -q "openclaw@$NEW_VER" "$UNIT" || { log "UNIT PATH CHECK FAILED"; rollback; }
  grep -q "openclaw@$NEW_VER" "$WRAPPER" || { log "WRAPPER PATH CHECK FAILED"; rollback; }
  systemctl daemon-reload
fi

# 5) 启动 + 等端口
log "STEP5 start gateway"
if [ "$DRY" = "1" ]; then echo "  (dry) systemctl start + wait port"; else
  systemctl start openclaw-gateway
  for i in $(seq 1 20); do ss -tln | grep -q ':18789 ' && break; sleep 2; done
  ss -tln | grep -q ':18789 ' || { log "START FAILED - port down"; rollback; }
fi

# 6) 版本验证
log "STEP6 verify version"
if [ "$DRY" = "1" ]; then echo "  (dry) $WRAPPER --version expect $NEW_VER"; else
  VER=$("$WRAPPER" --version 2>&1 | grep -oP '\d{4}\.\d+\.\d+' | head -1)
  log "reported version: $VER"
  [ "$VER" = "$NEW_VER" ] || { log "VERSION MISMATCH"; rollback; }
fi

log "=== UPGRADE DONE: openclaw $OLD_VER -> $NEW_VER ==="
