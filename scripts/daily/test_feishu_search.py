#!/usr/bin/env python3
"""
测试飞书API - 使用搜索消息API
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"


def get_feishu_token():
    """获取飞书tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("tenant_access_token")
    except Exception as e:
        print(f"获取token失败: {e}")
        return None


def search_messages(token, sender_id, start_time, end_time):
    """搜索消息"""
    start_ts = int(start_time.timestamp())
    end_ts = int(end_time.timestamp())
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages/search"
    params = {
        "sender_ids": sender_id,
        "sender_type": "user",
        "start_time": start_ts,
        "end_time": end_ts,
        "page_size": 50
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        full_url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            print(f"搜索消息API响应: code={result.get('code')}, msg={result.get('msg')}")
            if result.get("code") == 0:
                items = result.get("data", {}).get("items", [])
                print(f"找到 {len(items)} 条消息")
                return items
            else:
                print(f"错误详情: {result}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"HTTP错误 {e.code}: {error_body}")
    except Exception as e:
        print(f"搜索消息失败: {e}")
    
    return []


def get_bot_info(token):
    """获取机器人信息"""
    url = "https://open.feishu.cn/open-apis/bot/v3/info"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            print(f"机器人信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"获取机器人信息失败: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("飞书搜索消息API测试")
    print("=" * 50)
    
    token = get_feishu_token()
    if not token:
        print("无法获取token，退出")
        exit(1)
    
    print(f"✅ 获取token成功\n")
    
    # 获取机器人信息
    print("\n1. 获取机器人信息:")
    get_bot_info(token)
    
    # 昨天的时间范围
    yesterday = datetime.now() - timedelta(days=1)
    start_time = yesterday.replace(hour=0, minute=0, second=0)
    end_time = yesterday.replace(hour=23, minute=59, second=59)
    
    print(f"\n2. 搜索Boss昨天发送的消息:")
    print(f"   时间范围: {start_time} - {end_time}")
    messages = search_messages(token, FEISHU_USER_ID, start_time, end_time)
    
    if messages:
        print(f"\n消息预览:")
        for msg in messages[:3]:
            print(f"  - {msg.get('msg_type')}: {msg.get('body', {}).get('content', '')[:50]}...")
