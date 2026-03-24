#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse
from datetime import datetime

FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_CHAT_ID = "oc_cc41677495d651af079e5c6286306c23"

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("tenant_access_token")
    except:
        return None

# 获取昨天一条消息看看时间戳格式
yesterday = datetime.now() - __import__('datetime').timedelta(days=1)
start_ts = int(yesterday.replace(hour=0, minute=0, second=0).timestamp())
end_ts = int(yesterday.replace(hour=23, minute=59, second=59).timestamp())

token = get_feishu_token()
url = "https://open.feishu.cn/open-apis/im/v1/messages"
params = {
    "container_id_type": "chat",
    "container_id": FEISHU_CHAT_ID,
    "start_time": start_ts,
    "end_time": end_ts,
    "page_size": 5
}

full_url = f"{url}?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(full_url, headers={"Authorization": f"Bearer {token}"}, method="GET")

try:
    with urllib.request.urlopen(req, timeout=15) as response:
        result = json.loads(response.read().decode())
        items = result.get("data", {}).get("items", [])
        print(f"获取到 {len(items)} 条消息\n")
        for item in items[:3]:
            print(f"消息ID: {item.get('message_id')}")
            print(f"create_time: {item.get('create_time')} (类型: {type(item.get('create_time'))})")
            print(f"create_time_iso: {item.get('create_time_iso')}")
            print(f"content: {item.get('body', {}).get('content', '')[:50]}...")
            print()
except Exception as e:
    print(f"错误: {e}")
