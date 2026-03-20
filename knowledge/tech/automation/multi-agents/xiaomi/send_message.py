#!/usr/bin/env python3
"""
小秘 - 发送飞书消息
使用独立的飞书机器人
"""

import urllib.request
import json

# 小秘机器人配置
FEISHU_APP_ID = "cli_a93c07153039dbd9"
FEISHU_APP_SECRET = "eufRlwK6Ts5moI1aSXhr3epW1xIfmFmt"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"

def get_token():
    """获取飞书 token"""
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

def send_text(token, text):
    """发送文本消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    
    message = {
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False)
    }
    
    import urllib.parse
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
            return result.get("code") == 0
    except Exception as e:
        print(f"发送失败: {e}")
        return False

def main():
    token = get_token()
    if not token:
        print("获取token失败")
        return
    
    # 测试消息
    text = "⏰ 这是小秘的测试消息\n\n我是小秘，你的定时任务助手。\n我会准时提醒你：早报、周报、归档等任务。"
    
    if send_text(token, text):
        print("✅ 消息发送成功")
    else:
        print("❌ 消息发送失败")

if __name__ == "__main__":
    main()
