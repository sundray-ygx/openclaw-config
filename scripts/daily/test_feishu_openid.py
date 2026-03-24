#!/usr/bin/env python3
"""
测试飞书API - 使用open_id获取单聊消息
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


def get_messages_by_openid(token, open_id):
    """使用open_id获取单聊消息"""
    from datetime import datetime, timedelta
    
    # 昨天的时间范围
    yesterday = datetime.now() - timedelta(days=1)
    start_time = yesterday.replace(hour=0, minute=0, second=0)
    end_time = yesterday.replace(hour=23, minute=59, second=59)
    
    start_ts = int(start_time.timestamp())
    end_ts = int(end_time.timestamp())
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {
        "container_id_type": "open_id",
        "container_id": open_id,
        "start_time": start_ts,
        "end_time": end_ts,
        "page_size": 50
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    print(f"请求URL: {full_url[:100]}...")
    
    req = urllib.request.Request(
        full_url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            print(f"API响应: code={result.get('code')}, msg={result.get('msg')}")
            if result.get("code") == 0:
                items = result.get("data", {}).get("items", [])
                print(f"✅ 获取到 {len(items)} 条消息")
                return items
            else:
                print(f"❌ 错误: {result.get('msg')}")
                print(f"完整响应: {json.dumps(result, indent=2)}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"❌ HTTP错误 {e.code}: {error_body}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    return []


if __name__ == "__main__":
    print("=" * 60)
    print("飞书API测试 - 使用open_id获取单聊消息")
    print("=" * 60)
    
    token = get_feishu_token()
    if not token:
        print("无法获取token，退出")
        exit(1)
    
    print(f"✅ 获取token成功\n")
    
    # 昨天的时间范围
    yesterday = datetime.now() - timedelta(days=1)
    print(f"查询时间: {yesterday.strftime('%Y-%m-%d')}")
    print(f"Boss open_id: {FEISHU_USER_ID}\n")
    
    print("获取消息...")
    messages = get_messages_by_openid(token, FEISHU_USER_ID)
    
    if messages:
        print(f"\n消息预览 (前3条):")
        for i, msg in enumerate(messages[:3], 1):
            msg_type = msg.get("msg_type")
            sender = msg.get("sender", {}).get("id", "unknown")
            content = msg.get("body", {}).get("content", "")
            
            # 解析文本内容
            if content:
                try:
                    content_obj = json.loads(content)
                    text = content_obj.get("text", content)
                except:
                    text = content
            else:
                text = "[无内容]"
            
            sender_name = "Boss" if sender == FEISHU_USER_ID else "小助"
            print(f"\n{i}. [{sender_name}] {msg_type}")
            print(f"   {text[:80]}...")
