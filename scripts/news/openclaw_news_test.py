#!/usr/bin/env python3
"""
OpenClaw资讯推送脚本 - 测试版本（不发送）
"""

import subprocess
import json

def get_github_events():
    """获取OpenClaw GitHub最新动态"""
    try:
        # 获取最新issues - Python 3.6兼容写法
        cmd = 'curl -s "https://api.github.com/repos/openclaw/openclaw/issues?state=open&sort=created&direction=desc&per_page=3" 2>/dev/null'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        issues = json.loads(result.stdout.decode('utf-8')) if result.returncode == 0 and result.stdout else []
        
        # 获取最新release - Python 3.6兼容写法
        cmd = 'curl -s "https://api.github.com/repos/openclaw/openclaw/releases/latest" 2>/dev/null'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        release = json.loads(result.stdout.decode('utf-8')) if result.returncode == 0 and result.stdout else {}
        
        return issues[:3], release
    except Exception as e:
        print(f"获取GitHub数据错误: {e}")
        return [], {}

def main():
    print("=" * 40)
    print("获取OpenClaw GitHub资讯...")
    print("=" * 40)
    
    issues, release = get_github_events()
    
    print(f"\n✅ 获取到 {len(issues)} 个issues")
    for i, issue in enumerate(issues):
        print(f"  {i+1}. {issue.get('title', 'N/A')[:60]}")
        print(f"     URL: {issue.get('html_url', 'N/A')}")
    
    print(f"\n✅ 最新release: {release.get('tag_name', 'N/A') if release else 'None'}")
    if release:
        print(f"   发布时间: {release.get('published_at', 'N/A')[:10]}")
    
    print("\n" + "=" * 40)

if __name__ == "__main__":
    main()
