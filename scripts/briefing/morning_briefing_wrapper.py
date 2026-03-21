#!/usr/bin/env python3
"""
早间简报 - scheduler wrapper版本
生成简报内容，由scheduler通过announce发送
"""

import subprocess
import os
import sys

# 设置环境变量，跳过原脚本的发送
env = os.environ.copy()
env['SKIP_FEISHU_SEND'] = 'true'

# 运行原脚本生成简报
result = subprocess.run(
    ["python3", "/root/scripts/morning_briefing.py"],
    capture_output=True,
    text=True,
    timeout=300,
    env=env
)

# 输出日志
print("=== 早间简报生成日志 ===")
print(result.stdout)
if result.stderr:
    print("=== 错误输出 ===")
    print(result.stderr)

# 检查是否成功
if result.returncode == 0 and "生成早间简报..." in result.stdout:
    print("\n✅ 简报内容已生成")
    print("📤 请scheduler将简报内容发送到飞书")
else:
    print("\n❌ 简报生成失败")
    sys.exit(1)
