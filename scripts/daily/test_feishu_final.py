#!/usr/bin/env python3
"""
最终测试 - 检查所有可能的方案
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


def try_get_messages_with_chat_id(token, chat_id):
    """尝试使用chat_id获取消息"""
    yesterday = datetime.now() - timedelta(days=1)
    start_ts = int(yesterday.replace(hour=0, minute=0, second=0).timestamp())
    end_ts = int(yesterday.replace(hour=23, minute=59, second=59).timestamp())
    
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
            return result.get("code"), result.get("msg"), result.get("data", {}).get("items", [])
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        error_json = json.loads(error_body)
        return error_json.get("code"), error_json.get("msg"), []
    except Exception as e:
        return -1, str(e), []


if __name__ == "__main__":
    print("=" * 60)
    print("飞书API最终测试")
    print("=" * 60)
    
    token = get_feishu_token()
    if not token:
        print("❌ 无法获取token")
        exit(1)
    
    print("✅ 获取token成功\n")
    
    # 测试已知的群聊
    chat_ids = [
        "oc_c788f331e1f6e925e647f661a4576a8b",  # 贤哥牛马集合群
        "oc_c9d6f7c548f63275d20da009e9c58597",  # 牛马群
    ]
    
    print("测试已知的群聊:")
    for chat_id in chat_ids:
        print(f"\n  测试 chat_id: {chat_id}")
        code, msg, items = try_get_messages_with_chat_id(token, chat_id)
        print(f"    结果: code={code}, msg={msg}")
        if items:
            print(f"    ✅ 成功获取 {len(items)} 条消息")
        else:
            print(f"    ❌ 无消息或失败")
    
    # 尝试构造单聊chat_id (通常格式为 oc_xxx + user_id 的组合)
    print("\n\n尝试构造单聊chat_id:")
    # 单聊chat_id通常是 oc_ + hash 格式，无法直接构造
    # 需要调用创建单聊会话的API或从事件中获取
    
    print("\n" + "=" * 60)
    print("结论:")
    print("=" * 60)
    print("""
当前飞书应用权限限制：
1. ✅ 可以获取tenant_access_token
2. ✅ 可以列出群聊会话
3. ❌ 无法获取单聊会话的chat_id
4. ❌ 无法通过open_id直接获取消息

解决方案（需要Boss在飞书开放平台操作）：

方案A - 推荐：
1. 登录飞书开放平台: https://open.feishu.cn/
2. 进入应用: aliyun助手 (cli_a93b96047e7a5bc3)
3. 在"权限管理"中，确保已添加以下权限:
   - im:message (读取和发送消息)
   - im:message.history:readonly (读取聊天记录)
   - im:chat:readonly (读取会话信息)
   
4. 在"事件订阅"中，订阅以下事件:
   - im.message.receive_v1 (接收消息)
   
5. 让Boss在飞书中与机器人单聊发送一条消息，
   然后通过事件回调获取chat_id

方案B - 替代方案：
如果无法获取单聊chat_id，可以:
1. 创建一个专门的"日报记录"群聊
2. 将Boss和机器人加入群聊
3. 日报从这个群聊获取消息记录

方案C - 技术方案：
修改OpenClaw飞书适配器，在每次消息交互时:
1. 记录消息的chat_id
2. 将chat_id保存到本地配置文件
3. 日报脚本读取保存的chat_id
""")
