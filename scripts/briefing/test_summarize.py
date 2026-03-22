#!/usr/bin/env python3
"""测试 summarize 功能"""

import subprocess
import os
import re

def summarize_article(url, fallback_summary=""):
    """使用 summarize 生成 AI 摘要，带超时保护和降级"""
    try:
        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = "33838b1cec6b454c824d87bfd2161b87.j7D7D7gtNgACDHVa"
        env["ANTHROPIC_BASE_URL"] = "https://open.bigmodel.cn/api/anthropic"
        
        cmd = [
            "summarize", url, 
            "--length", "100",
            "--timeout", "25s",
            "--retries", "1"
        ]
        print(f"  调用summarize: {url[:60]}...")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        stdout, stderr = proc.communicate(timeout=30)
        
        if proc.returncode == 0:
            summary = stdout.decode('utf-8', errors='ignore').strip()
            print(f"  原始输出: {summary[:100]}...")
            
            # 清理格式
            summary = re.sub(r'^#+\s*', '', summary)
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = re.sub(r'[#*_`]', '', summary)
            
            # 提取核心内容（去掉元信息行）
            lines = summary.split('\n')
            content_lines = []
            for line in lines:
                # 跳过元信息行（包含时间、字数、模型等）
                if re.match(r'^\d+\.\d+s\s*·', line):
                    continue
                if 'words' in line and 'anthropic' in line.lower():
                    continue
                if line.strip():
                    content_lines.append(line)
            
            summary = ' '.join(content_lines)
            summary = summary.replace('\n', ' ').strip()
            
            if len(summary) > 120:
                summary = summary[:117] + "..."
            print(f"  处理后: {summary[:100]}...")
            return summary
        else:
            stderr_text = stderr.decode('utf-8', errors='ignore').strip()
            print(f"  ⚠️ summarize 错误: {stderr_text[:80]}")
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ summarize 超时")
        proc.kill()
    except Exception as e:
        print(f"  ⚠️ summarize 异常: {e}")
    
    if fallback_summary:
        print(f"  使用备选摘要")
        return fallback_summary
    return ""

# 测试几个URL
test_urls = [
    ("https://www.qbitai.com/2026/03/390924.html", "光轮智能：定义Physical AI基础设施"),
    ("https://36kr.com/p/3732001538490631?f=rss", "36氪文章"),
]

print("=" * 50)
print("测试 summarize 功能")
print("=" * 50)

for url, desc in test_urls:
    print(f"\n测试: {desc}")
    result = summarize_article(url, "这是备选摘要")
    print(f"结果: {result}")

print("\n" + "=" * 50)
print("测试完成")
