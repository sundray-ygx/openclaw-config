#!/usr/bin/env python3
"""
南北药行结账提醒
"""
import json
import urllib.request
import urllib.parse

# 配置
FEISHU_APP_ID = "cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"

def get_feishu_token():
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

def send_feishu_card(token, user_id, title, elements):
    """发送飞书卡片消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "orange"
        },
        "elements": elements
    }
    
    message = {
        "receive_id": user_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False)
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
            return result.get("code") == 0
    except Exception as e:
        print(f"发送失败: {e}")
        return False

def send_reminder():
    """发送结账提醒"""
    print("=" * 40)
    print("发送南北药行结账提醒...")
    print("=" * 40)
    
    token = get_feishu_token()
    if not token:
        print("❌ 获取token失败")
        return False
    
    title = "💊 南北药行结账提醒"
    
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**⏰ 提醒：该去南北药行结账了！**"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "📍 **地点**：南北药行\n📝 **事项**：结账单"
            }
        },
        {
            "tag": "hr"
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "⚡ **请及时处理，避免逾期！**"
            }
        }
    ]
    
    if send_feishu_card(token, FEISHU_USER_ID, title, elements):
        print("✅ 提醒发送成功！")
        return True
    else:
        print("❌ 提醒发送失败")
        return False

if __name__ == "__main__":
    send_reminder()
