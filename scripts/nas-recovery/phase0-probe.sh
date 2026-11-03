#!/bin/bash
# ============================================================
# NAS Phase 0 只读探测 — DSM 升级后恢复评估 (2026-10-31)
# 纪律：100% 只读。不安装、不重启、不写任何系统路径。
# 唯一写入：本脚本所在目录下的输出文件（共享目录内）。
# 用法：SSH 到 NAS，root 身份执行：bash <本脚本路径>
# 预计耗时 1-3 分钟（含 state.db 打开测试与镜像列表）
# ============================================================

OUT="/tmp/nas-phase0-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS Phase 0 只读探测  $(date '+%F %T')"
echo " 主机: $(hostname)  用户: $(whoami)"
echo "=================================================="

sec() { echo; echo "########## $1 ##########"; }

# ---------- A. 系统概况 ----------
sec "A. 系统概况"
cat /etc/VERSION 2>/dev/null || echo "[FAIL] /etc/VERSION"
uname -a
uptime
echo "--- 磁盘 ---"
df -h / /volume1 /volume2 2>/dev/null
echo "--- 内存 ---"
free -m 2>/dev/null || cat /proc/meminfo | head -3

# ---------- B. 升级痕迹（确认升级是否完成、何时发生） ----------
sec "B. DSM 升级痕迹"
ls -la /usr/syno/synoupdate/ 2>/dev/null | head -15
echo "--- synoupdate.log ---"
tail -60 /var/log/synoupdate.log 2>/dev/null || echo "[无此日志]"
echo "--- 其他升级日志候选 ---"
ls -la /var/log/synoupdate* /usr/syno/synoupdate/var/* 2>/dev/null | head -10
echo "--- /etc.defaults/VERSION（出厂基准） ---"
cat /etc.defaults/VERSION 2>/dev/null || echo "[FAIL]"
echo "--- 最近系统日志（升级前后） ---"
tail -30 /var/log/messages 2>/dev/null | head -30 || echo "[无 messages]"

# ---------- C. /root 状态（H1/H2 判定核心） ----------
sec "C. /root 状态"
ls -la /root/ 2>/dev/null || echo "[FAIL] /root 不可列"
echo "--- /root/.hermes/ ---"
ls -la /root/.hermes/ 2>/dev/null | head -40 || echo "[MISSING] /root/.hermes 不存在"

# ---------- D. .hermes 关键资产逐项确认 ----------
sec "D1. .env / config.yaml（只看元数据，不打印密钥）"
ls -la /root/.hermes/.env 2>/dev/null || echo "[MISSING] .env"
ls -la /root/.hermes/config.yaml 2>/dev/null || echo "[MISSING] config.yaml"
head -12 /root/.hermes/config.yaml 2>/dev/null

sec "D2. cron 任务定义 jobs.json"
ls -la /root/.hermes/cron/jobs.json 2>/dev/null || echo "[MISSING] jobs.json"
python3 -c "
import json
try:
    d = json.load(open('/root/.hermes/cron/jobs.json'))
    jobs = d.get('jobs', d if isinstance(d, list) else [])
    print('任务数:', len(jobs))
    for j in jobs:
        print('-', j.get('name'), '|', j.get('schedule'), '| deliver:', j.get('deliver'), '| enabled:', j.get('enabled'))
except Exception as e:
    print('[解析失败]', e)
" 2>/dev/null || echo "[python3 解析跳过]"

sec "D3. platforms 飞书配对"
ls -laR /root/.hermes/platforms/ 2>/dev/null | head -25 || echo "[MISSING] platforms/"

sec "D4. state.db 会话库（软链 + 实体）"
ls -la /root/.hermes/state.db* 2>/dev/null || echo "[MISSING] state.db 软链"
echo "readlink: $(readlink -f /root/.hermes/state.db 2>/dev/null)"
REAL=$(readlink -f /root/.hermes/state.db 2>/dev/null)
if [ -n "$REAL" ] && [ -f "$REAL" ]; then
    stat -c '实体: %n | 大小: %s bytes | mtime: %y' "$REAL" 2>/dev/null
    echo "--- SQLite 打开测试（只读 URI） ---"
    timeout 60 sqlite3 "file:${REAL}?mode=ro" "SELECT count(*) FROM sqlite_master;" 2>&1
    timeout 60 sqlite3 "file:${REAL}?mode=ro" "SELECT name FROM sqlite_master WHERE type='table' LIMIT 25;" 2>&1
else
    echo "[实体缺失] 在 /volume1 上搜索候选..."
    find /volume1 -maxdepth 3 -name 'state.db' -size +50M -exec stat -c '%n | %s bytes | %y' {} \; 2>/dev/null | head -5
fi

sec "D5. projects/ 代码资产"
ls -la /root/.hermes/projects/ 2>/dev/null || echo "[MISSING] projects/"
for p in /root/.hermes/projects/*/; do
    [ -d "$p" ] && echo "--- $p ---" && ls "$p" 2>/dev/null | head -8
done

sec "D6. scripts/ 与 skills 规模"
ls -la /root/.hermes/scripts/ 2>/dev/null | head -15 || echo "[MISSING] scripts/"
find /root/.hermes/scripts -type f 2>/dev/null | wc -l | xargs echo "scripts 文件总数:"
find /root/.hermes/skills -name SKILL.md 2>/dev/null | wc -l | xargs echo "skills 总数:"
ls -t /root/.hermes/memory/ 2>/dev/null | head -5

sec "D7. hermes 日志（最后活动）"
ls -la /root/.hermes/logs/ 2>/dev/null | head -10 || echo "[MISSING] logs/"
tail -20 /root/.hermes/logs/gateway.log 2>/dev/null || echo "[无 gateway.log]"

# ---------- E. hermes 安装本体 ----------
sec "E. hermes 安装本体"
ls -d /usr/local/lib/hermes-agent* 2>/dev/null || echo "[MISSING] 安装目录"
ls -la /usr/local/bin/hermes 2>/dev/null || echo "[MISSING] /usr/local/bin/hermes"
hermes --version 2>/dev/null || echo "[hermes 命令不可用]"
for d in /usr/local/lib/hermes-agent*/; do
    [ -f "$d/package.json" ] && echo "$d -> $(grep -m1 '"version"' "$d/package.json")"
done

# ---------- F. systemd 服务 ----------
sec "F. systemd 服务"
systemctl list-units --type=service --state=running --no-pager 2>/dev/null | head -40
echo "--- 用户级单元文件 ---"
ls -la /root/.config/systemd/user/ 2>/dev/null || echo "[MISSING] ~/.config/systemd/user/"
for f in /root/.config/systemd/user/*.service /root/.config/systemd/user/*.timer; do
    [ -f "$f" ] && echo "=== $f ===" && cat "$f"
done
echo "--- hermes / user-systemd 进程 ---"
ps aux 2>/dev/null | grep -E 'hermes|systemd --user' | grep -v grep || echo "[无 hermes 进程]"

# ---------- G. crontab ----------
sec "G. crontab 全源"
echo "--- /etc/crontab ---"
cat /etc/crontab 2>/dev/null || echo "[FAIL]"
echo "--- /etc/cron.d/ ---"
ls -la /etc/cron.d/ 2>/dev/null
for f in /etc/cron.d/*; do [ -f "$f" ] && echo "=== $f ===" && cat "$f"; done

# ---------- H. Docker ----------
sec "H. Docker 状态"
timeout 20 docker ps -a 2>&1 | head -25 || echo "[docker ps 失败/超时]"
echo "--- images ---"
timeout 20 docker images 2>&1 | head -20 || echo "[FAIL]"
echo "--- volumes ---"
timeout 20 docker volume ls 2>&1 | head -15 || echo "[FAIL]"
echo "--- networks ---"
timeout 20 docker network ls 2>&1 || echo "[FAIL]"
echo "--- Docker 套件状态 ---"
synopkg status Docker 2>/dev/null || synopkg status ContainerManager 2>/dev/null || echo "[synopkg 查询失败]"
echo "--- /volume1/@docker/ ---"
ls -la /volume1/@docker/ 2>/dev/null | head -20 || echo "[MISSING]"

# ---------- I. 容器数据卷（/docker 共享） ----------
sec "I. 容器数据卷"
for cand in /volume1/docker /volume2/docker; do
    [ -d "$cand" ] && echo "=== $cand ===" && ls -la "$cand" | head -20
done
echo "--- vaultwarden 数据完整性（D4 决策依据） ---"
ls -la /volume1/docker/vaultwarden/ 2>/dev/null || ls -la /volume2/docker/vaultwarden/ 2>/dev/null || echo "[MISSING]"

# ---------- J. frpc（为何幸存） ----------
sec "J. frpc 状态"
ps aux 2>/dev/null | grep frpc | grep -v grep || echo "[frpc 未运行]"
systemctl status frpc --no-pager 2>/dev/null | head -12 || echo "[无 frpc systemd 单元]"
ls -la /volume1/Frp/ 2>/dev/null | head -8 || echo "[MISSING] /volume1/Frp"

# ---------- K. 监听端口 ----------
sec "K. 监听端口"
ss -tlnp 2>/dev/null | head -30 || netstat -tlnp 2>/dev/null | head -30

# ---------- L. 套件清单 ----------
sec "L. 套件清单"
synopkg list 2>/dev/null | tr ' ' '\n' | grep -vE '^$' | head -30 || echo "[synopkg list 失败]"

# ---------- 收尾 ----------
sec "探测完成"
echo "输出文件: $OUT"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cp "$OUT" "$SCRIPT_DIR/" 2>/dev/null && echo "已复制到共享目录: $SCRIPT_DIR/$(basename "$OUT")" || echo "[复制到脚本目录失败，请手动取 /tmp 下文件]"
echo "ECS 侧将通过 WebDAV 自动取回此文件。"
