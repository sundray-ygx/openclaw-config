#!/usr/bin/env python3
"""
周计划制定提醒脚本
每周日 20:00 执行，提醒用户完善 weekly-planning Skill
"""

import os
import json
import requests

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "cli_a93b96047e7a5bc3")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD")
FEISHU_USER_ID = os.getenv("FEISHU_USER_ID", "ou_c2cde251e01a87fc09ba7561f76d8606")

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET})
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        result = response.json()
        return result.get("tenant_access_token")
    except Exception as e:
        print(f"获取token失败: {e}")
        return None

def send_reminder():
    token = get_token()
    if not token:
        print("获取飞书token失败")
        return False
    
    content = """⏰ 周计划制定提醒

每周日 20:00 是周计划制定时间，但 weekly-planning Skill 尚未完善。

📋 当前状态：
• 原周计划提醒任务已禁用
• 周复盘任务运行正常（每周五 18:30）

🔧 待完善的 Skill：
位置：/root/.openclaw/workspace/growth/productivity/weekly-planning/

需要实现的功能：
1. 从 OKR 看板读取项目数据
2. 筛选产品经理/团队管理领域项目
3. 飞书推送候选项目供选择
4. 用户确认后生成周计划
5. 周一自动生成日计划

✅ 确认完善后：
回复"启用周计划"，我将：
1. 删除此提醒任务
2. 启用真正的周计划制定任务

💡 如需修改 Skill，请告诉我具体需求。"""

    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    message = {
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=message, params=params, timeout=10)
        result = response.json()
        if result.get("code") == 0:
            print("✅ 提醒消息发送成功")
            return True
        else:
            print(f"❌ 飞书API错误: {result}")
            return False
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

if __name__ == "__main__":
    send_reminder()
