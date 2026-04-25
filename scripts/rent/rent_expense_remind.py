#!/usr/bin/env python3
"""
16A503 租房支出账单提醒脚本
每月27日14:00执行，提醒发送本月租房账单
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

# 飞书配置
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
        print(f"获取飞书token失败: {e}")
        return None

def send_feishu_message(token, user_id, content):
    """发送飞书文本消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"

    params = {
        "receive_id_type": "open_id"
    }
    full_url = f"{url}?{urllib.parse.urlencode(params)}"

    payload = {
        "receive_id": user_id,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }

    req = urllib.request.Request(
        full_url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            if result.get("code") == 0:
                print("✅ 飞书提醒发送成功")
                return True
            else:
                print(f"❌ 飞书提醒发送失败: {result.get('msg')}")
                return False
    except Exception as e:
        print(f"❌ 发送飞书提醒失败: {e}")
        return False

if __name__ == "__main__":
    # 获取当前月份
    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    # 提醒内容
    reminder = f"""📋 16A503 租房支出账单提醒

本月（{current_month}）账单准备时间到了，请发送以下信息：

🏠 房租：金额、缴费周期
🏢 物业费：金额、缴费周期
💧 水费：金额、用量、缴费周期
⚡ 电费：金额、用量、缴费周期
🔥 燃气费：金额、用量、缴费周期

收到信息后我会：
1. 录入数据并归档
2. 计算合计金额
3. 更新支出统计

请直接发送账单截图或费用明细。"""

    # 获取token并发送
    token = get_feishu_token()
    if token:
        send_feishu_message(token, FEISHU_USER_ID, reminder)
    else:
        print("❌ 无法获取飞书token")
