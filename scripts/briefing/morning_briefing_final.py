#!/usr/bin/env python3
"""
早间简报 - 最终版本
支持两种模式：
1. 直接发送（默认）：发送到配置的FEISHU_USER_ID
2. 输出模式（OUTPUT_MODE=stdout）：输出简报内容，供scheduler读取并发送
"""

import subprocess
import os
import sys

# 获取模式
output_mode = os.environ.get('OUTPUT_MODE', 'send')

if output_mode == 'stdout':
    # 输出模式：只生成简报，不发送
    env = os.environ.copy()
    env['SKIP_FEISHU_SEND'] = 'true'
    env['OUTPUT_JSON'] = 'true'
    
    result = subprocess.run(
        ["python3", "/root/scripts/morning_briefing.py"],
        capture_output=True,
        text=True,
        timeout=300,
        env=env
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    sys.exit(result.returncode)
else:
    # 直接发送模式
    result = subprocess.run(
        ["python3", "/root/scripts/morning_briefing.py"],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    sys.exit(result.returncode)
