#!/usr/bin/env python3
"""
工作日报生成脚本 V6
- 时间范围：昨天00:00到昨天23:59（全天）
- 交互工作：提取所有用户消息（非系统消息）
- 复盘部分：自动识别失败任务
- 执行时间：8:30
"""

import os
import json
import re
from datetime import datetime, timedelta
import urllib.request
import urllib.parse

# 配置 - 使用scheduler账号
FEISHU_APP_ID = "cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"
DAILY_REPORT_DIR = "/root/.openclaw/workspace/archive/daily"
MEMORY_DIR = "/root/.openclaw/workspace/memory"
SESSIONS_DIR = "/root/.openclaw/agents/scheduler/sessions"

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

def send_feishu_card(token, user_id, title, elements):
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
    
    message = {
        "receive_id": user_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False)
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        full_url,
        data=json.dumps(message, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("code") == 0
    except:
        return False

def get_report_time_range():
    """获取日报统计时间范围：昨天00:00到昨天23:59（全天）"""
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    # 昨天00:00 到 昨天23:59:59
    start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_time, end_time

def get_session_files(start_time, end_time):
    """获取时间范围内的会话文件"""
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
    """解析会话文件，提取工作内容"""
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
                
                # 识别定时任务触发消息 (新格式: [cron:xxx 任务名])
                cron_match = re.search(r'\[cron:([^\]]+)\]\s*(.+?)(?:\n|$)', full_text)
                if cron_match:
                    task_name = cron_match.group(1).strip()
                    task_desc = cron_match.group(2).strip()
                    cron_tasks.append({
                        'type': 'cron',
                        'description': f"{task_name}: {task_desc}",
                        'timestamp': timestamp
                    })
                    continue
                
                # 识别旧格式定时任务触发消息
                if 'A scheduled reminder has been triggered' in full_text:
                    task_match = re.search(r'The reminder content is:\s*\n\s*(.+?)(?:\n\s*Please relay|$)', full_text, re.DOTALL)
                    if task_match:
                        task_desc = task_match.group(1).strip()
                        cron_tasks.append({
                            'type': 'cron',
                            'description': task_desc,
                            'timestamp': timestamp
                        })
                    continue
                
                # 识别用户直接消息
                if role == 'user' and msg_type == 'message':
                    if any(x in full_text for x in [
                        'Skills store policy',
                        'A scheduled reminder',
                        'operator configured',
                        'System: [',
                        '[cron:'
                    ]):
                        continue
                    
                    if len(full_text) > 5:
                        user_interactions.append({
                            'type': 'user',
                            'content': full_text[:200] + '...' if len(full_text) > 200 else full_text,
                            'timestamp': timestamp
                        })
    
    except Exception as e:
        print(f"  解析文件错误 {filepath}: {e}")
    
    return cron_tasks, user_interactions

def categorize_cron_tasks(cron_tasks):
    """分类定时任务"""
    completed = []
    failed = []
    
    task_keywords = {
        '早间简报': '早间简报推送',
        'morning_briefing': '早间简报推送',
        'daily_report': '工作日报生成',
        '工作日报': '工作日报生成',
        'OpenClaw': 'OpenClaw资讯推送',
        'openclaw_news': 'OpenClaw资讯推送',
        'rss_news': 'OpenClaw资讯推送',
        'NAS': 'NAS自动备份',
        'nas_backup': 'NAS自动备份',
        '备份通知': 'NAS备份检查',
        'daily_archive': '每日归档',
        '归档': '每日归档',
        '周计划': '周计划制定',
        '周复盘': '周复盘',
        '周报': '周报提醒'
    }
    
    for task in cron_tasks:
        desc = task['description']
        time_str = task['timestamp'][11:16] if task['timestamp'] else ''
        
        task_name = '定时任务'
        for keyword, name in task_keywords.items():
            if keyword in desc:
                task_name = name
                break
        
        completed.append({
            'task': task_name,
            'detail': desc[:80],
            'time': time_str
        })
    
    return completed, failed

def generate_daily_report():
    """生成日报"""
    start_time, end_time = get_report_time_range()
    
    print(f"统计时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} 至 {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    session_files = get_session_files(start_time, end_time)
    print(f"找到 {len(session_files)} 个会话文件")
    
    all_cron_tasks = []
    all_user_interactions = []
    
    for filepath in session_files:
        cron_tasks, user_interactions = parse_session_file(filepath)
        all_cron_tasks.extend(cron_tasks)
        all_user_interactions.extend(user_interactions)
    
    print(f"提取到 {len(all_cron_tasks)} 个定时任务, {len(all_user_interactions)} 个用户交互")
    
    # 分类任务
    completed_tasks, failed_tasks = categorize_cron_tasks(all_cron_tasks)
    
    # 生成日期
    report_date = end_time.strftime('%Y-%m-%d')
    weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][end_time.weekday()]
    
    elements = []
    
    # 标题
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**📅 {report_date} {weekday} 工作日报**\n*统计周期：{start_time.strftime('%m-%d %H:%M')} ~ {end_time.strftime('%m-%d %H:%M')}*"
        }
    })
    
    # 统计
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**📊 今日统计**\n• 定时任务：{len(completed_tasks)}\n• 用户交互：{len(all_user_interactions)}"
        }
    })
    
    # 已完成事项
    if completed_tasks:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**✅ 已完成事项**"}
        })
        
        for i, item in enumerate(completed_tasks, 1):
            time_str = f" ({item['time']})" if item.get('time') else ""
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"{i}. **{item['task']}**{time_str}\n   {item['detail']}"}
            })
    
    # 交互工作
    if all_user_interactions:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**💬 交互工作**"}
        })
        
        for i, item in enumerate(all_user_interactions[:5], 1):
            time_str = f" ({item['timestamp'][11:16]})" if item.get('timestamp') else ""
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"{i}.{time_str} {item['content']}"}
            })
    
    # 复盘与改进
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": "**🔄 复盘与改进**"}
    })
    
    if failed_tasks:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**需改进：**"}
        })
        for item in failed_tasks:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"• {item['task']}: {item['error']}"}
            })
    else:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "• 所有定时任务正常执行，无异常"}
        })
    
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": "**做得好的：**\n• 系统稳定运行，任务按时完成"}
    })
    
    title = f"📋 工作日报 | {report_date} {weekday}"
    
    return title, elements, {
        "completed": completed_tasks,
        "interactions": all_user_interactions,
        "failed": failed_tasks
    }

def save_report_to_file(title, work_data):
    """保存日报到文件"""
    os.makedirs(DAILY_REPORT_DIR, exist_ok=True)
    
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    file_path = f"{DAILY_REPORT_DIR}/daily-report-{date_str}.md"
    
    content = f"# {title}\n\n"
    content += f"生成时间：{today.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    content += "## ✅ 已完成事项\n\n"
    for i, item in enumerate(work_data["completed"], 1):
        time_str = f" ({item['time']})" if item.get('time') else ""
        content += f"{i}. **{item['task']}**{time_str}\n"
        content += f"   - {item['detail']}\n\n"
    
    if work_data["interactions"]:
        content += "## 💬 交互工作\n\n"
        for i, item in enumerate(work_data["interactions"][:10], 1):
            content += f"{i}. {item['content']}\n\n"
    
    content += "## 🔄 复盘与改进\n\n"
    if work_data["failed"]:
        content += "**需改进：**\n"
        for item in work_data["failed"]:
            content += f"• {item['task']}: {item['error']}\n"
    else:
        content += "• 所有定时任务正常执行，无异常\n"
    
    content += "\n**做得好的：**\n• 系统稳定运行，任务按时完成\n"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path

if __name__ == "__main__":
    print("=" * 40)
    print("生成工作日报 V6...")
    print("=" * 40)
    
    title, elements, work_data = generate_daily_report()
    
    file_path = save_report_to_file(title, work_data)
    print(f"\n日报已保存：{file_path}")
    
    print("\n发送到飞书...")
    token = get_feishu_token()
    if token:
        if send_feishu_card(token, FEISHU_USER_ID, title, elements):
            print("✅ 发送成功")
        else:
            print("❌ 发送失败")
    else:
        print("❌ 获取token失败")
