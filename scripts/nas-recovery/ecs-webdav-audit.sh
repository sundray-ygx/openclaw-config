#!/bin/bash
# ECS侧 WebDAV 依赖审计脚本（只读，不改任何东西）2026-11-05
# 用法：ECS上执行  bash ecs-webdav-audit.sh  把输出发回即可
echo '=== 1. ECS上有没有进程连frps的5005/5006端口 ==='
ss -tnp 2>/dev/null | grep -E ':500[56]\b' || echo '(无任何到5005/5006的连接)'
echo '=== 2. ECS上本地监听5005/5006的进程(frp visitor/转发类) ==='
ss -tlnp 2>/dev/null | grep -E ':500[56]\b' || echo '(ECS本地无5005/5006监听)'
echo '=== 3. frps配置与运行状态(隐去token行) ==='
ps aux | grep -E '[f]rps' | head -3
for f in ~/frp/frps.toml /etc/frp/frps.toml ~/frps.toml ~/frp/frps.ini /etc/frp/frps.ini; do
  [ -f "$f" ] && echo "--- $f ---" && grep -vE 'token|auth' "$f"
done
echo '=== 4. ECS上的阿里云盘客户端/同步进程 ==='
ps aux | grep -iE 'aliyun|aDrive' | grep -v grep | head -5 || true
echo '=== 5. 近30天日志里有无访问5005/5006的痕迹 ==='
find ~ /var/log -name '*.log' -mtime -30 2>/dev/null | xargs grep -lE ':500[56]' 2>/dev/null | head -3 || echo '(近30天日志无5005/5006访问痕迹)'
echo '=== 审计结束，请把以上输出发回 ==='
