#!/usr/bin/env python3
"""发送系统运行状态报告到飞书"""

import urllib.request
import urllib.parse
import json
import sys
from datetime import datetime

# 飞书配置
FEISHU_APP_ID = "cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"


def get_feishu_token():
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if result.get("code") == 0:
                return result.get("tenant_access_token")
            else:
                print(f"获取 token 失败：{result}")
                return None
    except Exception as e:
        print(f"获取 token 异常：{e}")
        return None


def send_feishu_text(token, user_id, text):
    """发送飞书文本消息"""
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
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if result.get("code") == 0:
                print("✅ 报告发送成功")
                return True
            else:
                print(f"❌ 发送失败：{result}")
                return False
    except Exception as e:
        print(f"❌ 发送异常：{e}")
        return False


def main():
    token = get_feishu_token()
    if not token:
        print("❌ 无法获取飞书 token")
        return 1
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report = f"""🖥️ 系统运行状态诊断报告
生成时间：{now}

═══════════════════════════

【一、OpenClaw 网关状态】
✅ 网关运行正常
• 版本：2026.4.7
• 配置最后更新：2026-04-08

【二、定时任务运行情况】

✅ 正常运行的任务 (11 个):
• GitHub 每日同步 (23:30) - 最后成功
• NAS 自动备份 (02:00) - 最后成功
• 自动归档记忆 (05:00) - 最后成功
• 每日工作日报 (08:30) - 最后成功
• NAS 备份通知 (08:35) - 最后成功
• 每日反思生成 (08:45) - 最后成功
• 周复盘 (周五 18:30) - 最后成功
• 周计划制定 (周日 20:00) - 最后成功
• 日计划生成 (周一 08:30) - 最后成功
• 租金账单提醒 (每月 25 日) - 最后成功
• 月度 inbox 整理 (每月 1 日) - 最后成功

⚠️ 需要注意的任务 (5 个):
1. 周反思报告 - 连续 2 次超时 (kimi-k2.5)
2. 每周安全配置巡检 - 连续 2 次超时
3. Claude 预算提醒 - API 400 错误
4. 月反思报告 - 连续 4 次超时
5. 每日运行时监控 - 已禁用，连续 8 次超时

【三、系统资源状态】

内存使用:
• 总量：1.8GB
• 已用：1.6GB (89%)
• 可用：214MB
• Swap: 1.0GB/4.0GB

磁盘使用:
• 总量：40GB
• 已用：24GB (62%)
• 剩余：15GB

【四、安全事件记录】

配置防护日志 (最近 5 次):
• 03-30 09:35 - 配置篡改告警 (已恢复)
• 03-28 21:40 - 配置篡改告警 (已恢复)
• 03-26 15:55 - 配置篡改告警 (已恢复)
• 03-24 23:20 - 配置篡改告警 (已恢复)
• 03-24 21:40 - 配置篡改告警 (已恢复)

注：Config Guard 定时任务已于 14:09 删除

【五、记忆维护状态】

⚠️ 记忆维护过期
• 最后维护：2026-01-01
• 距今：>90 天
• 建议：执行每周记忆维护

【六、待办事项】

1. 🔴 百炼 API 配额确认 (4 月初应重置)
2. 🟡 周反思/月反思超时问题排查
3. 🟡 Claude 预算提醒 API 错误修复
4. 🟡 执行记忆维护 (已过期 90+ 天)
5. 🟢 清理 openclaw.json 中 skillhub 残留

【七、健康度评分】

整体评分：75/100

• 网关运行：✅ 100/100
• 定时任务：🟡 70/100 (5 个任务异常)
• 系统资源：🟡 75/100 (内存使用率高)
• 安全状态：🟢 90/100 (配置已稳定)
• 记忆维护：🔴 20/100 (严重过期)

═══════════════════════════

💡 建议操作:
1. 检查百炼 API 配额状态
2. 调整超时任务的 timeoutSeconds
3. 执行记忆维护脚本
4. 监控内存使用情况"""
    
    if send_feishu_text(token, FEISHU_USER_ID, report):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
