#!/bin/bash
# ============================================================
# NAS 恢复 S1 — ContainerManager 启动 + 容器回归验证 (2026-10-31)
# 变更动作（Boss 已批准「全部按推荐建议执行」）：
#   1. synopkg start ContainerManager   （唯一系统级变更）
#   2. docker start <未自动回归的关键容器>（仅限原本 RestartPolicy 应自启的）
# 其余全部只读。输出自动回传共享目录，ECS 侧分析。
# 用法：SSH 到 NAS root 执行：bash <本脚本路径>
# ============================================================

OUT="/tmp/nas-s1-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS 恢复 S1 — 容器恢复  $(date '+%F %T')"
echo " 主机: $(hostname)"
echo "=================================================="
sec() { echo; echo "########## $1 ##########"; }

sec "A. 起步前快照（只读）"
synopkg status ContainerManager 2>/dev/null
ls /volume1/@docker/containers/ 2>/dev/null | wc -l | xargs echo "注册表容器目录数:"
date '+开始: %F %T'

sec "B. 启动 ContainerManager（已批准的变更）"
synopkg start ContainerManager 2>&1
echo "synopkg start 退出码: $?"
synopkg status ContainerManager 2>/dev/null

sec "C. 轮询 docker daemon 就绪（最长 150s）"
DOCKERCMD=""
for can in docker /usr/local/bin/docker /var/packages/ContainerManager/target/usr/bin/docker; do
    command -v "$can" >/dev/null 2>&1 && DOCKERCMD="$can" && break
    [ -x "$can" ] && DOCKERCMD="$can" && break
done
[ -z "$DOCKERCMD" ] && DOCKERCMD="/var/packages/ContainerManager/target/usr/bin/docker"
echo "docker 命令: $DOCKERCMD"
READY=no
for i in $(seq 1 30); do
    if timeout 10 "$DOCKERCMD" info >/dev/null 2>&1; then
        echo "daemon 就绪（第 ${i} 次探测, $(date '+%T')）"
        READY=yes
        break
    fi
    sleep 5
done
[ "$READY" = no ] && echo "❌ daemon 150s 未就绪，输出诊断后继续" && timeout 10 "$DOCKERCMD" info 2>&1 | head -10

sec "D. 容器全量清单（含自启回归情况）"
timeout 30 "$DOCKERCMD" ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>&1
echo "--- 运行中数量 ---"
timeout 30 "$DOCKERCMD" ps -q 2>/dev/null | wc -l
echo "--- RestartPolicy 对照（找出本应自启却没回来的） ---"
for c in $(timeout 30 "$DOCKERCMD" ps -a --format '{{.Names}}' 2>/dev/null); do
    POL=$(timeout 10 "$DOCKERCMD" inspect "$c" --format '{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null)
    RUN=$(timeout 10 "$DOCKERCMD" inspect "$c" --format '{{.State.Running}}' 2>/dev/null)
    echo "$c | policy=$POL | running=$RUN"
done

sec "E. 关键服务本地连通验证（NAS 本机视角）"
for t in "vaultwarden 3011" "vaultwarden-ws 3012" "newapi-docker0 3000"; do
    set -- $t
    printf '%-18s : ' "$1($2)"
    timeout 5 curl -s -o /dev/null -w 'HTTP %{http_code}' "http://127.0.0.1:$2/" 2>/dev/null || printf 'CONN-FAIL'
    echo
done
printf '%-18s : ' "vaultwarden /alive"
timeout 5 curl -s -o /dev/null -w 'HTTP %{http_code}' "http://127.0.0.1:3011/alive" 2>/dev/null || printf 'CONN-FAIL'
echo

sec "F. 磁盘/内存收尾快照（只读）"
df -h / /volume1 | head -4
free -m | head -2

sec "S1 完成"
date '+结束: %F %T'
echo "输出文件: $OUT"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cp "$OUT" "$SCRIPT_DIR/" 2>/dev/null && echo "已回传: $SCRIPT_DIR/$(basename "$OUT")" || echo "[回传失败，请手动取 $OUT]"
