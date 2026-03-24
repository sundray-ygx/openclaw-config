#!/usr/bin/env python3
"""
测试飞书API - 获取正确的chat_id
"""

import json
import urllib.request
import urllib.parse

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


def list_chats(token):
    """列出所有会话"""
    url = "https://open.feishu.cn/open-apis/im/v1/chats?page_size=100"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            print(f"列会话API响应: code={result.get('code')}, msg={result.get('msg')}")
            if result.get("code") == 0:
                items = result.get("data", {}).get("items", [])
                print(f"\n找到 {len(items)} 个会话:")
                for item in items:
                    chat_id = item.get("chat_id")
                    chat_type = item.get("chat_type")
                    name = item.get("name", "N/A")
                    members = item.get("members", [])
                    member_ids = [m.get("member_id") for m in members]
                    print(f"  - chat_id: {chat_id}")
                    print(f"    type: {chat_type}, name: {name}")
                    print(f"    members: {member_ids}")
                    if FEISHU_USER_ID in member_ids:
                        print(f"    *** 这是与Boss的会话 ***")
                    print()
            else:
                print(f"错误: {result.get('msg')}")
    except Exception as e:
        print(f"列出会话失败: {e}")


def get_p2p_chat_id(token, user_id):
    """通过用户ID获取单聊会话ID"""
    url = f"https://open.feishu.cn/open-apis/im/v1/chats?user_id_type=open_id&page_size=100"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if result.get("code") == 0:
                items = result.get("data", {}).get("items", [])
                for item in items:
                    if item.get("chat_type") == "p2p":
                        members = item.get("members", [])
                        member_ids = [m.get("member_id") for m in members]
                        if user_id in member_ids:
                            return item.get("chat_id")
    except Exception as e:
        print(f"获取单聊会话失败: {e}")
    
    return None


def get_chat_history(token, chat_id):
    """获取会话历史消息"""
    from datetime import datetime, timedelta
    
    # 昨天的时间范围
    yesterday = datetime.now() - timedelta(days=1)
    start_time = yesterday.replace(hour=0, minute=0, second=0)
    end_time = yesterday.replace(hour=23, minute=59, second=59)
    
    start_ts = int(start_time.timestamp())
    end_ts = int(end_time.timestamp())
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {
        "container_id_type": "chat",
        "container_id": chat_id,
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
            print(f"\n获取消息API响应: code={result.get('code')}, msg={result.get('msg')}")
            if result.get("code") == 0:
                items = result.get("data", {}).get("items", [])
                print(f"获取到 {len(items)} 条消息")
                for item in items[:5]:  # 只显示前5条
                    msg_type = item.get("msg_type")
                    sender = item.get("sender", {}).get("id")
                    content = item.get("body", {}).get("content", "")
                    print(f"  - type: {msg_type}, sender: {sender}")
                    print(f"    content: {content[:100]}...")
                return items
            else:
                print(f"错误: {result.get('msg')}")
    except Exception as e:
        print(f"获取消息失败: {e}")
    
    return []


if __name__ == "__main__":
    print("=" * 50)
    print("飞书API测试")
    print("=" * 50)
    
    token = get_feishu_token()
    if not token:
        print("无法获取token，退出")
        exit(1)
    
    print(f"✅ 获取token成功\n")
    
    # 1. 列出所有会话
    print("\n1. 列出所有会话:")
    list_chats(token)
    
    # 2. 获取与Boss的单聊会话ID
    print("\n2. 获取与Boss的单聊会话ID:")
    chat_id = get_p2p_chat_id(token, FEISHU_USER_ID)
    if chat_id:
        print(f"✅ 找到单聊会话: {chat_id}")
        
        # 3. 获取消息
        print(f"\n3. 获取昨天消息:")
        messages = get_chat_history(token, chat_id)
    else:
        print("❌ 未找到单聊会话")
