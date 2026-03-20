#!/usr/bin/env python3
"""
Security Alert Sender - 发送飞书安全告警
"""

import os
import sys
import json
import requests
from datetime import datetime


def send_feishu_alert(skill_name: str, risk_score: int, findings: list, webhook_url: str = None):
    """发送飞书安全告警"""
    
    # 飞书 webhook URL（从环境变量读取）
    if not webhook_url:
        webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if not webhook_url:
        print("错误: FEISHU_WEBHOOK_URL 未设置", file=sys.stderr)
        return False
    
    # 构建告警内容
    if risk_score >= 10:
        level = "🔴 高危"
        action = "立即拒绝安装"
        color = "red"
    elif risk_score >= 5:
        level = "🟡 中危"
        action = "需人工审核"
        color = "yellow"
    else:
        level = "🟢 低危"
        action = "允许安装"
        color = "green"
    
    # 提取关键风险
    high_risks = [f for f in findings if f.get("level") == "high"]
    risk_summary = "\n".join([f"• {f['description']}: {f.get('code', 'N/A')[:50]}" 
                              for f in high_risks[:3]])
    
    message = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🚨 Skill 安全审计告警"
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**Skill**: {skill_name}\n**风险等级**: {level}\n**评分**: {risk_score}/100\n**建议操作**: {action}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**关键风险**:\n{risk_summary if risk_summary else '无高危风险'}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"审计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        response = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            json=message,
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ 告警已发送到飞书: {skill_name}")
            return True
        else:
            print(f"❌ 发送失败: HTTP {response.status_code}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"❌ 发送异常: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Send Security Alert to Feishu")
    parser.add_argument("skill_name", help="Skill 名称")
    parser.add_argument("risk_score", type=int, help="风险评分")
    parser.add_argument("--findings", help="风险发现 JSON 文件")
    parser.add_argument("--webhook", help="飞书 webhook URL")
    
    args = parser.parse_args()
    
    findings = []
    if args.findings and os.path.exists(args.findings):
        with open(args.findings, 'r') as f:
            findings = json.load(f)
    
    success = send_feishu_alert(args.skill_name, args.risk_score, findings, args.webhook)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()