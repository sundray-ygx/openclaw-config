#!/usr/bin/env python3
"""
早间简报 - scheduler专用版本
生成简报并通过OpenClaw announce机制发送
"""

import subprocess
import os
import sys
import json
import re

# 设置环境变量
env = os.environ.copy()
env['SKIP_FEISHU_SEND'] = 'true'  # 跳过原脚本的发送
env['OUTPUT_JSON'] = 'true'       # 输出JSON格式

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

# 提取JSON输出
json_match = re.search(r'===JSON_OUTPUT_START===(.+?)===JSON_OUTPUT_END===', result.stdout, re.DOTALL)
if json_match:
    try:
        briefing_data = json.loads(json_match.group(1).strip())
        title = briefing_data.get('title', '早间简报')
        elements = briefing_data.get('elements', [])
        
        # 构建飞书卡片
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": elements
        }
        
        # 输出卡片JSON到文件，供OpenClaw读取
        output_file = "/tmp/morning_briefing_card.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(card, f, ensure_ascii=False)
        
        print(f"\n✅ 简报卡片已生成: {output_file}")
        print("\n请使用以下命令发送:")
        print(f"cat {output_file}")
        
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON解析失败: {e}")
        sys.exit(1)
else:
    print("\n❌ 未能提取简报内容")
    sys.exit(1)

sys.exit(0)
