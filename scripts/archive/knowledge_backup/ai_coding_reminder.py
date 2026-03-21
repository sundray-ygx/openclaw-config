#!/usr/bin/env python3
"""
AI coding分享提醒
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
            "template": "blue"
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
    """发送分享提醒"""
    print("=" * 40)
    print("发送AI coding分享提醒...")
    print("=" * 40)
    
    token = get_feishu_token()
    if not token:
        print("❌ 获取token失败")
        return False
    
    title = "🤖 AI Coding 线下分享即将开始"
    
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**⏰ 提醒：AI Coding 分享交流即将开始！**"
            }
        },
        {
            "tag": "hr"
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "👤 **分享嘉宾**：深信服AI算力网关研发部 - 王鸿奇\n📍 **地点**：创新中心\n⏰ **时间**：今晚 19:00"
            }
        },
        {
            "tag": "hr"
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**📋 分享内容：**\n1️⃣ AI coding 基础介绍\n2️⃣ SDD"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "💡 **感兴趣的小伙伴请前往创新中心参加！**"
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
