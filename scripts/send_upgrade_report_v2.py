#!/usr/bin/env python3
"""发送 OpenClaw 升级报告到飞书"""

import urllib.request
import urllib.parse
import json
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
                print("✅ 文本消息发送成功")
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
    
    # 构建报告内容 - 使用纯文本格式
    report = """📊 OpenClaw 3.23 → 4.2 升级报告

【升级概览】
• 当前版本: 2026.4.7
• 升级跨度: 3.23 → 4.2
• 主要版本: 4.0 / 4.1 / 4.2

【核心新特性】

1️⃣ 持久化任务流 (4.2重磅)
• 托管模式 vs 镜像模式
• 状态/版本跟踪与恢复
• openclaw flows 命令集
• 子任务管理与取消意图

2️⃣ 多媒体生成能力
• 视频生成: xAI Grok、阿里万相、Runway
• 音乐生成: Google Lyria、MiniMax
• 新增工具: video_generate、music_generate

3️⃣ Dreaming 智能记忆
• 三阶段: Light/Deep/REM
• /dreaming 命令和 Dreams UI
• 自动整理笔记到 dreams.md
• 减少手动维护 MEMORY.md

4️⃣ 提供商扩展
• 新增: Qwen、Fireworks AI、StepFun
• MiniMax TTS、Ollama Web Search
• SearXNG 搜索聚合 (4.1+)
• Bedrock Guardrails 安全护栏

5️⃣ 飞书集成增强
• 文档评论事件流支持
• Drive 评论上下文解析
• 评论线程自动回复
• 话题路由和作用域继承

【破坏性变更 ⚠️】

4.0 版本:
• 移除遗留配置别名 (talk.voiceId等)
• Claude CLI 后端移除
• CLI 文本提供商后端移除

4.2 版本:
• xAI 搜索配置路径变更
• Firecrawl 配置路径变更

迁移命令: openclaw doctor --fix

【对当前业务的积极影响】
✅ 定时任务: Task Flow 持久化提升可靠性
✅ 记忆管理: Dreaming 减少手动维护
✅ 飞书集成: 文档评论支持增强协作
✅ 成本优化: 提示缓存降低 API 费用

【升级建议】

立即执行:
• openclaw doctor
• openclaw doctor --fix

短期规划 (1-2周):
• 启用 Dreaming: memory.dreaming.enabled
• 评估 Task Flow 迁移

中期规划 (1个月):
• 探索多媒体生成
• 优化飞书工作流

【总结】
4.x 系列是 OpenClaw 的重大升级，重点在任务持久化、多媒体生成、智能记忆和飞书深度集成。建议尽快运行 openclaw doctor --fix 完成配置迁移，并尝试启用 Dreaming 功能体验智能记忆管理。"""
    
    if send_feishu_text(token, FEISHU_USER_ID, report):
        print("✅ 报告发送完成")
        return 0
    else:
        print("❌ 报告发送失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
