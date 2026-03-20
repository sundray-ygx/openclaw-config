#!/usr/bin/env python3
"""
周报提醒 - 周五 17:00 发送
"""

import urllib.request
import json
import datetime
import urllib.parse
import os

# 从环境变量读取配置
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
FEISHU_USER_ID = os.environ.get("FEISHU_USER_ID")

# 验证环境变量
if not all([FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_USER_ID]):
    print("错误：缺少必要的环境变量")
    print("请设置 FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_USER_ID")
    exit(1)

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

def send_reminder():
    token = get_feishu_token()
    if not token:
        print("获取 token 失败")
        return
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    
    message = {
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({
            "text": "⏰ 周报提醒\n\n周五了，该写本周周报啦！\n\n使用 /weekly-review 生成本周总结"
        }, ensure_ascii=False)
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        full_url,
        data=json.dumps(message, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            print(f"发送结果: {result}")
    except Exception as e:
        print(f"发送失败: {e}")

if __name__ == "__main__":
    send_reminder()
