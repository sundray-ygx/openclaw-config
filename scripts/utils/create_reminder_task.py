#!/usr/bin/env python3
"""
创建飞书任务提醒
"""
import json
import urllib.request
import urllib.parse

# 配置
FEISHU_APP_ID = "cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"

def get_feishu_token():
    """获取 tenant_access_token"""
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

def get_user_access_token(token, user_id):
    """获取用户的 user_access_token"""
    url = "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token"
    data = json.dumps({
        "grant_type": "authorization_code",
        "code": user_id  # 这里需要实际的授权码，简化处理
    }).encode()
    
    # 飞书任务API需要使用 user_access_token
    # 由于需要用户授权，我们直接使用 tenant_access_token 并确保应用有权限
    return token

def create_task(token, user_id, summary, description, due_time):
    """创建飞书任务 - 使用旧版任务API"""
    # 飞书任务API v1 (更稳定)
    url = "https://open.feishu.cn/open-apis/task/v1/tasks"
    
    # 构建任务数据
    task_data = {
        "summary": summary,
        "description": description,
        "due": {
            "timestamp": due_time.replace("T", " ").replace("+08:00", ""),  # 格式: 2026-03-20 08:58:00
            "is_all_day": False
        },
        "members": [
            {
                "id": user_id,
                "type": "user",
                "role": "assignee"
            }
        ],
        "origin": {
            "platform": "open_api",
            "href": "https://open.feishu.cn",
            "platform_i18n_name": {
                "zh_cn": "OpenClaw 提醒",
                "en_us": "OpenClaw Reminder"
            }
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(task_data, ensure_ascii=False).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            if result.get("code") == 0:
                print(f"✅ 任务创建成功!")
                print(f"任务GUID: {result.get('data', {}).get('task', {}).get('guid')}")
                return True
            else:
                print(f"❌ 创建失败: {result.get('msg')}")
                return False
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"❌ HTTP错误 {e.code}: {error_body}")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 40)
    print("创建飞书任务提醒...")
    print("=" * 40)
    
    token = get_feishu_token()
    if not token:
        print("获取token失败，退出")
        exit(1)
    
    # 任务信息
    summary = "⏰ 领取鹏城葵花+腾讯视频会员权益"
    description = """📱 领取内容：鹏城葵花+腾讯视频会员权益
🔗 领取链接：cmbt.cn/a/sBUYUA
⏰ 开放时间：3月20日 9:00

请及时领取，避免错过！"""
    
    # 3月20日 8:58（提前2分钟）
    due_time = "2026-03-20T08:58:00+08:00"
    
    success = create_task(token, USER_ID, summary, description, due_time)
    
    if success:
        print("\n✅ 提醒任务已设置成功！")
        print(f"提醒时间: 2026-03-20 08:58 (提前2分钟)")
    else:
        print("\n❌ 任务创建失败")
