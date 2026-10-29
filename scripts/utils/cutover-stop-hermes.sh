#!/bin/bash
# 2026-10-29 网关切换：停用 hermes-gateway（在脱离网关进程树的 systemd 单元中执行）
systemctl stop hermes-gateway
systemctl disable hermes-gateway
echo "done $(date +%T)" > /tmp/cutover-stop-hermes.flag
