#!/usr/bin/env python3
"""
OpenClaw资讯推送脚本 - 调试版本
"""

import urllib.request
import json
import subprocess

# 飞书配置 - 使用scheduler账号
FEISHU_APP_ID = "cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"

def get_feishu_token():
    """获取飞书token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("tenant_access_token")
    except Exception as e:
        print(f"获取token错误: {e}")
        return None

def get_github_events():
    """获取OpenClaw GitHub最新动态"""
    try:
        # 获取最新issues
        cmd = 'curl -s "https://api.github.com/repos/openclaw/openclaw/issues?state=open&sort=created&direction=desc&per_page=3" 2>/dev/null'
        print(f"执行命令: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        print(f"Issues返回码: {result.returncode}")
        print(f"Issues输出长度: {len(result.stdout)}")
        
        if result.returncode == 0 and result.stdout:
            try:
                issues = json.loads(result.stdout)
                print(f"获取到 {len(issues)} 个issues")
            except json.JSONDecodeError as e:
                print(f"Issues JSON解析错误: {e}")
                issues = []
        else:
            print(f"Issues获取失败: {result.stderr}")
            issues = []
        
        # 获取最新release
        cmd = 'curl -s "https://api.github.com/repos/openclaw/openclaw/releases/latest" 2>/dev/null'
        print(f"执行命令: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        print(f"Release返回码: {result.returncode}")
        print(f"Release输出长度: {len(result.stdout)}")
        
        if result.returncode == 0 and result.stdout:
            try:
                release = json.loads(result.stdout)
                print(f"获取到release: {release.get('tag_name', 'N/A')}")
            except json.JSONDecodeError as e:
                print(f"Release JSON解析错误: {e}")
                release = {}
        else:
            print(f"Release获取失败: {result.stderr}")
            release = {}
        
        return issues[:3], release
    except Exception as e:
        print(f"获取GitHub事件错误: {e}")
        return [], {}

def main():
    """主函数"""
    print("=" * 40)
    print("获取OpenClaw GitHub资讯...")
    print("=" * 40)
    
    issues, release = get_github_events()
    
    print("\n" + "=" * 40)
    print(f"Issues数量: {len(issues)}")
    for i, issue in enumerate(issues):
        print(f"  {i+1}. {issue.get('title', 'N/A')[:50]}")
    
    print(f"\nRelease: {release.get('tag_name', 'N/A') if release else 'None'}")
    print("=" * 40)

if __name__ == "__main__":
    main()
