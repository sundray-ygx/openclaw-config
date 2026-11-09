#!/usr/bin/env bash
# 阶段2: 安装 hermes-agent (npm bridge) 并验证
# 此时 openclaw 仍在运行，内存足够
set -euo pipefail
echo "[1/4] 检查依赖: node/git ..."
node -v; git --version
echo "[2/4] 安装 hermes-agent ..."
npm install --global hermes-agent
echo "[3/4] 版本验证 ..."
hermes --version || hermes-npm status --json
echo "[4/4] 检查飞书 channel 支持（关键验证）..."
hermes --help 2>&1 | grep -i -E "channel|feishu|lark" || echo "⚠️ help 中未见 channel 字样，需进一步查文档"
hermes doctor 2>&1 | tail -20 || true
echo "✅ 安装完成。下一步: 手动初始化 hermes 配置（模型/飞书凭据），验证通过后再执行 03 停 openclaw。"
