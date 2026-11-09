#!/usr/bin/env python3
"""发送 OpenClaw 升级报告到飞书"""

import urllib.request
import json
import os
import sys

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
                print(f"获取token失败: {result}")
                return None
    except Exception as e:
        print(f"获取token异常: {e}")
        return None


def send_feishu_text(token, user_id, text):
    """发送飞书文本消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    
    content = {
        "text": text
    }
    
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
                print("✅ 文本消息发送成功")
                return True
            else:
                print(f"❌ 发送失败: {result}")
                return False
    except Exception as e:
        print(f"❌ 发送异常: {e}")
        return False


import urllib.parse

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
    
    data = {
        "receive_id": user_id,
        "msg_type": "interactive",
        "card": json.dumps(card)
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
                print("✅ 卡片消息发送成功")
                return True
            else:
                print(f"❌ 发送失败: {result}")
                return False
    except Exception as e:
        print(f"❌ 发送异常: {e}")
        return False


def main():
    token = get_feishu_token()
    if not token:
        print("❌ 无法获取飞书 token")
        return 1
    
    # 构建报告内容
    title = "📊 OpenClaw 3.23 → 4.2 升级报告"
    
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**升级概览**\n• 当前版本: 2026.4.7\n• 升级跨度: 3.23 → 4.2\n• 主要版本: 4.0 / 4.1 / 4.2"
            }
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**🚀 核心新特性**"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**1. 持久化任务流 (4.2 重磅)**\n• 托管模式 vs 镜像模式\n• 状态/版本跟踪与恢复\n• openclaw flows 命令集\n• 子任务管理与取消意图"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**2. 多媒体生成能力**\n• 视频生成: xAI Grok、阿里万相、Runway\n• 音乐生成: Google Lyria、MiniMax\n• 新增工具: video_generate、music_generate"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**3. Dreaming 智能记忆 🧠**\n• 三阶段: Light/Deep/REM\n• /dreaming 命令和 Dreams UI\n• 自动整理笔记到 dreams.md\n• 减少手动维护 MEMORY.md"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**4. 提供商扩展**\n• 新增: Qwen、Fireworks AI、StepFun\n• MiniMax TTS、Ollama Web Search\n• SearXNG 搜索聚合 (4.1+)\n• Bedrock Guardrails 安全护栏"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**5. 飞书集成增强**\n• 文档评论事件流支持\n• Drive 评论上下文解析\n• 评论线程自动回复\n• 话题路由和作用域继承"
            }
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**⚠️ 破坏性变更**"
            }
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**4.0 版本:**\n• 移除遗留配置别名 (talk.voiceId等)\n• Claude CLI 后端移除\n• CLI 文本提供商后端移除\n\n**4.2 版本:**\n• xAI 搜索配置路径变更\n• Firecrawl 配置路径变更\n\n**迁移命令:** `openclaw doctor --fix`"
            }
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**✅ 对当前业务的积极影响**\n• 定时任务: Task Flow 持久化提升可靠性\n• 记忆管理: Dreaming 减少手动维护\n• 飞书集成: 文档评论支持增强协作\n• 成本优化: 提示缓存降低 API 费用"
            }
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**📋 升级建议**\n\n**立即执行:**\n`openclaw doctor`\n`openclaw doctor --fix`\n\n**短期规划 (1-2周):**\n• 启用 Dreaming: memory.dreaming.enabled\n• 评估 Task Flow 迁移\n\n**中期规划 (1个月):**\n• 探索多媒体生成\n• 优化飞书工作流"
            }
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**📌 总结**\n4.x 系列是 OpenClaw 的重大升级，重点在任务持久化、多媒体生成、智能记忆和飞书深度集成。建议尽快运行 `openclaw doctor --fix` 完成配置迁移。"
            }
        }
    ]
    
    if send_feishu_card(token, FEISHU_USER_ID, title, elements):
        print("✅ 报告发送完成")
        return 0
    else:
        print("❌ 报告发送失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
