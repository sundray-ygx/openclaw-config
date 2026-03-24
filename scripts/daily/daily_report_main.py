#!/usr/bin/env python3
"""
工作日报生成脚本 V7 - 小助(main)专用版本
- 时间范围：昨天00:00到23:59（全天）
"""

import os
import json
import re
from datetime import datetime, timedelta
import urllib.request
import urllib.parse

FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"
SESSIONS_DIR = "/home/openclaw/.openclaw/agents/main/sessions"

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("tenant_access_token")
    except:
        return None

def send_feishu_text(token, user_id, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    message = {"receive_id": user_id, "msg_type": "text", "content": json.dumps({"text": text}, ensure_ascii=False)}
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full_url, data=json.dumps(message, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("code") == 0
    except:
        return False

def get_report_time_range():
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start_time, end_time

def get_session_files(start_time, end_time):
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    session_files = []
    if not os.path.exists(SESSIONS_DIR):
        return session_files
    for filename in os.listdir(SESSIONS_DIR):
        if not filename.endswith('.jsonl'):
            continue
        filepath = os.path.join(SESSIONS_DIR, filename)
        try:
            stat = os.stat(filepath)
            mtime_ms = int(stat.st_mtime * 1000)
            if start_ts <= mtime_ms <= end_ts:
                session_files.append(filepath)
        except:
            continue
    return session_files

def parse_session_file(filepath):
    cron_tasks = []
    user_interactions = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except:
                    continue
                msg_type = data.get('type', '')
                msg = data.get('message', {})
                role = msg.get('role', '')
                content = msg.get('content', [])
                timestamp = data.get('timestamp', '')
                text_parts = []
                for part in content:
                    if part.get('type') == 'text':
                        text_parts.append(part.get('text', ''))
                full_text = ' '.join(text_parts)
                if 'A scheduled reminder has been triggered' in full_text:
                    task_match = re.search(r'The reminder content is:\s*\n\s*(.+?)(?:\n\s*Please relay|$)', full_text, re.DOTALL)
                    if task_match:
                        task_desc = task_match.group(1).strip()
                        cron_tasks.append({'type': 'cron', 'description': task_desc, 'timestamp': timestamp})
                    continue
                if role == 'user' and msg_type == 'message':
                    if any(x in full_text for x in ['Skills store policy', 'A scheduled reminder', 'operator configured', 'System: [']):
                        continue
                    if len(full_text) > 5:
                        user_interactions.append({'type': 'user', 'content': full_text[:200] + '...' if len(full_text) > 200 else full_text, 'timestamp': timestamp})
    except Exception as e:
        print(f"  解析错误 {filepath}: {e}")
    return cron_tasks, user_interactions

def categorize_cron_tasks(cron_tasks):
    completed = []
    task_keywords = {'早间简报': '早间简报', 'morning_briefing': '早间简报', 'daily_report': '工作日报', '工作日报': '工作日报', 'OpenClaw': 'OpenClaw资讯', 'openclaw_news': 'OpenClaw资讯', 'rss_news': 'OpenClaw资讯', 'NAS': 'NAS备份', 'nas_backup': 'NAS备份', '备份通知': '备份通知', 'daily_archive': '每日归档', '归档': '每日归档'}
    for task in cron_tasks:
        desc = task.get('description', '')
        matched = False
        for keyword, category in task_keywords.items():
            if keyword in desc:
                completed.append({'category': category, 'description': desc[:80] + '...' if len(desc) > 80 else desc})
                matched = True
                break
        if not matched:
            completed.append({'category': '其他任务', 'description': desc[:80] + '...' if len(desc) > 80 else desc})
    return completed

def generate_daily_report():
    start_time, end_time = get_report_time_range()
    date_str = start_time.strftime('%Y年%m月%d日')
    print(f"生成日报: {date_str}")
    print(f"时间范围: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
    
    session_files = get_session_files(start_time, end_time)
    print(f"找到 {len(session_files)} 个会话文件")
    
    all_cron_tasks = []
    all_user_interactions = []
    for filepath in session_files:
        cron_tasks, user_interactions = parse_session_file(filepath)
        all_cron_tasks.extend(cron_tasks)
        all_user_interactions.extend(user_interactions)
    
    print(f"定时任务: {len(all_cron_tasks)} 条")
    print(f"用户交互: {len(all_user_interactions)} 条")
    
    categorized_tasks = categorize_cron_tasks(all_cron_tasks)
    
    # 生成报告
    report_lines = [f"**小助工作日报 - {date_str}**", f"📅 统计周期：{start_time.strftime('%Y-%m-%d')} 00:00 至 23:59（全天）", f"📊 今日概览：", f"- 定时任务执行：{len(categorized_tasks)} 项", f"- 用户交互处理：{len(all_user_interactions)} 次", ""]
    
    if categorized_tasks:
        report_lines.append("✅ 定时任务：")
        for task in categorized_tasks:
            report_lines.append(f"- ⏰ {task['category']}：{task['description']}")
        report_lines.append("")
    
    if all_user_interactions:
        report_lines.append("💬 用户交互：")
        for i, interaction in enumerate(all_user_interactions[:5], 1):
            content = interaction['content'].replace('\n', ' ')
            report_lines.append(f"- {content[:60]}{'...' if len(content) > 60 else ''}")
        if len(all_user_interactions) > 5:
            report_lines.append(f"- ... 及其他 {len(all_user_interactions) - 5} 条交互")
        report_lines.append("")
    
    report_lines.append("📝 总结：")
    report_lines.append(f"昨日共处理 {len(categorized_tasks)} 项定时任务和 {len(all_user_interactions)} 次用户交互。工作平稳运行。")
    
    report = '\n'.join(report_lines)
    
    # 检查长度，飞书限制约196601字符，预留余量
    MAX_LENGTH = 180000
    if len(report) > MAX_LENGTH:
        report = report[:MAX_LENGTH] + "\n\n...（内容过长已截断）"
    
    return report

if __name__ == "__main__":
    print("=" * 40)
    print("生成工作日报")
    print("=" * 40)
    
    report = generate_daily_report()
    
    print("\n" + "=" * 40)
    print(report)
    print("=" * 40)
    
    # 发送到飞书
    print("\n📤 发送到飞书...")
    token = get_feishu_token()
    if token:
        if send_feishu_text(token, FEISHU_USER_ID, report):
            print("✅ 发送成功")
        else:
            print("❌ 发送失败")
    else:
        print("❌ 获取token失败")
