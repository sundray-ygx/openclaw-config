#!/usr/bin/env python3
"""
Security Alert Sender - 使用飞书插件发送安全告警
通过 sessions_send 工具发送到飞书
"""

import os
import sys
import json
import argparse
from datetime import datetime


def generate_alert_message(skill_name: str, risk_score: int, findings: list) -> str:
    """生成告警消息内容"""
    
    if risk_score >= 10:
        level = "🔴 高危"
        action = "立即拒绝安装"
    elif risk_score >= 5:
        level = "🟡 中危"
        action = "需人工审核"
    else:
        level = "🟢 低危"
        action = "允许安装"
    
    # 提取关键风险（仅高危）
    high_risks = [f for f in findings if f.get("level") == "high"]
    risk_list = []
    for f in high_risks[:5]:  # 最多显示5个
        risk_list.append(f"• {f['description']}\n  文件: {f.get('file', 'N/A')} 第{f.get('line', 'N/A')}行")
    
    risk_summary = "\n".join(risk_list) if risk_list else "无高危风险"
    
    message = f"""🚨 Skill 安全审计告警

━━━━━━━━━━━━━━━━━━━━━
📦 Skill: {skill_name}
📊 风险等级: {level}
🔢 评分: {risk_score}/100
⚡ 建议操作: {action}
━━━━━━━━━━━━━━━━━━━━━

🔍 关键风险:
{risk_summary}

⏰ 审计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 处理建议:
• 高危风险: 立即拒绝安装，检查代码
• 中危风险: 人工审核后决定
• 低危风险: 记录日志，允许安装

📋 详细报告: memory/security-audit-{datetime.now().strftime('%Y-%m-%d')}.md
"""
    
    return message


def main():
    parser = argparse.ArgumentParser(description="Generate Feishu Security Alert")
    parser.add_argument("skill_name", help="Skill 名称")
    parser.add_argument("risk_score", type=int, help="风险评分")
    parser.add_argument("--findings", help="风险发现 JSON 文件")
    parser.add_argument("--output", "-o", help="输出消息文件路径")
    
    args = parser.parse_args()
    
    findings = []
    if args.findings and os.path.exists(args.findings):
        with open(args.findings, 'r') as f:
            findings = json.load(f)
    
    message = generate_alert_message(args.skill_name, args.risk_score, findings)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(message)
        print(f"告警消息已保存: {args.output}")
    else:
        print(message)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
