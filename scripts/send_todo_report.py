#!/usr/bin/env python3
"""发送待办事项执行报告到飞书"""

import urllib.request
import urllib.parse
import json
import sys
from datetime import datetime

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
            if result.get("code") == 0:
                return result.get("tenant_access_token")
    except Exception as e:
        print(f"获取 token 异常：{e}")
    return None


def send_feishu_text(token, user_id, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    content = {"text": text}
    data = {
        "receive_id": user_id,
        "msg_type": "text",
        "content": json.dumps(content)
    }
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        full_url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("code") == 0
    except Exception as e:
        print(f"发送异常：{e}")
        return False


def main():
    token = get_feishu_token()
    if not token:
        return 1
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report = f"""✅ 待办事项执行报告
执行时间：{now}

═══════════════════════════

【1️⃣ 百炼 API 配额确认】
状态：⚠️ 无法直接查询
说明：API key 验证失败，无法通过 API 查询配额
建议：登录阿里云百炼控制台查看配额状态
      或观察定时任务是否还有 429 错误

【2️⃣ 调整超时任务 timeoutSeconds】
状态：✅ 已完成

调整记录:
• 周反思报告：120s → 300s
• 每周安全配置巡检：120s → 300s
• 月反思报告：300s → 600s

下次执行时间:
• 周反思：周日 20:00
• 安全巡检：周一 09:00
• 月反思：本月 28-31 日 21:00

【3️⃣ 执行记忆维护】
状态：✅ 已完成

维护内容:
• 更新 heartbeat-state.json
  lastMemoryMaintenance: 2026-01-01 → 2026-04-08
• 更新 projects.md
  添加 4/8 定时任务调整记录
• 更新 lessons.md
  添加"记忆维护过期"教训

执行月度 inbox 整理:
• inbox 目录已清空，无需整理

【4️⃣ 清理 skillhub 残留】
状态：✅ 已确认无残留
说明：openclaw.json 中未找到 skillhub 配置

【5️⃣ 监控内存使用】
状态：📊 持续观察
当前状态:
• 使用率：89% (1.6GB/1.8GB)
• 可用：214MB
• Swap: 1.0GB/4.0GB

建议：如持续高于 90%，考虑优化或扩容

═══════════════════════════

【执行总结】
✅ 完成：4/5 项
⚠️ 部分完成：1/5 项（百炼配额需人工确认）

下次记忆维护：2026-04-15（7 天后）"""
    
    if send_feishu_text(token, FEISHU_USER_ID, report):
        print("✅ 报告发送成功")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
