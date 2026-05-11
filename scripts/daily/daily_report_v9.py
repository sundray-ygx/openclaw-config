#!/usr/bin/env python3
"""
工作日报生成脚本 V9 - 增强版
- 时间范围：昨天00:00到昨天23:59（全天）
- 数据源：
  1. 本地会话文件（scheduler + main）
  2. 飞书IM单聊消息
- 包含内容：摘要信息（定时任务、用户交互概要、飞书交互、错误统计）
- 执行时间：8:30
"""

import os
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# 配置
DAILY_REPORT_DIR = "/home/openclaw/.openclaw/workspace/archive/daily"
SESSIONS_DIRS = [
    "/home/openclaw/.openclaw/agents/scheduler/sessions",
    "/home/openclaw/.openclaw/agents/main/sessions"
]

# 飞书配置
FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"  # Boss的open_id
FEISHU_CHAT_ID = "oc_5e05a8f6e3e6e6c344a9c2e2b7b5a3a6"  # 与小助的单聊chat_id


def search_feishu_messages(token, sender_id, start_time, end_time):
    """搜索飞书消息（跨会话）"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages/search"
    
    # 转换时间为Unix时间戳（秒）
    start_ts = int(start_time.timestamp())
    end_ts = int(end_time.timestamp())
    
    params = {
        "sender_ids": sender_id,
        "sender_type": "user",
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
    
    messages = []
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            print(f"  飞书搜索API响应: code={result.get('code')}, msg={result.get('msg')}")
            if result.get("code") == 0:
                items = result.get("data", {}).get("items", [])
                print(f"  搜索到 {len(items)} 条消息")
                for item in items:
                    msg_type = item.get("msg_type", "")
                    content = item.get("body", {}).get("content", "")
                    create_time = item.get("create_time", "")
                    sender = item.get("sender", {}).get("id", "")
                    
                    # 只处理文本消息
                    if msg_type == "text" and content:
                        # 解析content（它是JSON字符串）
                        try:
                            content_obj = json.loads(content)
                            text = content_obj.get("text", "")
                        except:
                            text = content
                        
                        if text:
                            messages.append({
                                "role": "user" if sender == sender_id else "assistant",
                                "content": text,
                                "timestamp": create_time,
                                "source": "feishu"
                            })
            else:
                print(f"  飞书搜索API错误: {result.get('msg')}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  HTTP错误 {e.code}: {error_body}")
    except Exception as e:
        print(f"  搜索飞书消息失败: {e}")
    
    return messages


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
        print(f"  获取飞书token失败: {e}")
        return None


def get_feishu_messages(token, user_id, start_time, end_time):
    """获取飞书单聊消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    
    # 转换时间为Unix时间戳（秒）
    start_ts = int(start_time.timestamp())
    end_ts = int(end_time.timestamp())
    
    params = {
        "container_id_type": "chat",
        "container_id": user_id,
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
    
    messages = []
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            print(f"  飞书API响应: code={result.get('code')}, msg={result.get('msg')}")
            if result.get("code") == 0:
                items = result.get("data", {}).get("items", [])
                print(f"  获取到 {len(items)} 条消息")
                for item in items:
                    msg_type = item.get("msg_type", "")
                    content = item.get("body", {}).get("content", "")
                    create_time = item.get("create_time", "")
                    sender = item.get("sender", {}).get("id", "")
                    
                    # 只处理文本消息
                    if msg_type == "text" and content:
                        # 解析content（它是JSON字符串）
                        try:
                            content_obj = json.loads(content)
                            text = content_obj.get("text", "")
                        except:
                            text = content
                        
                        if text:
                            messages.append({
                                "role": "user" if sender == FEISHU_USER_ID else "assistant",
                                "content": text,
                                "timestamp": create_time,
                                "source": "feishu"
                            })
            else:
                print(f"  飞书API错误: {result.get('msg')}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  HTTP错误 {e.code}: {error_body}")
    except Exception as e:
        print(f"  获取飞书消息失败: {e}")
    
    return messages


def get_report_time_range():
    """获取日报统计时间范围：昨天00:00到昨天23:59（全天）"""
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start_time, end_time, yesterday.strftime('%Y-%m-%d')


def get_session_files(start_time, end_time):
    """获取时间范围内的会话文件（从多个目录收集）"""
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    session_files = []
    
    for sessions_dir in SESSIONS_DIRS:
        if not os.path.exists(sessions_dir):
            continue
        
        for filename in os.listdir(sessions_dir):
            if not filename.endswith('.jsonl'):
                continue
            
            filepath = os.path.join(sessions_dir, filename)
            try:
                stat = os.stat(filepath)
                mtime_ms = int(stat.st_mtime * 1000)
                if start_ts <= mtime_ms <= end_ts:
                    session_files.append(filepath)
            except:
                continue
    
    return session_files


def parse_session_messages(filepath):
    """解析会话文件，提取所有消息"""
    messages = []
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
                full_text = ''.join(text_parts)
                
                if full_text and len(full_text) > 3:
                    messages.append({
                        'role': role,
                        'type': msg_type,
                        'content': full_text,
                        'timestamp': timestamp,
                        'source': 'local'
                    })
    except Exception as e:
        print(f"  解析错误 {filepath}: {e}")
    
    return messages


def extract_cron_tasks(messages):
    """从消息中提取定时任务"""
    cron_tasks = []
    for msg in messages:
        text = msg['content']
        cron_match = re.search(r'\[cron:([^\]]+)\]\s*(.+?)(?:\n|$)', text)
        if cron_match:
            task_name = cron_match.group(1).strip()
            task_desc = cron_match.group(2).strip()
            cron_tasks.append({
                'name': task_name,
                'description': task_desc,
                'timestamp': msg['timestamp']
            })
    return cron_tasks


def extract_user_interactions(messages):
    """提取用户交互概要（本地会话）"""
    interactions = []
    for msg in messages:
        if msg.get('source') != 'local':
            continue
        if msg['role'] == 'user' and msg['type'] == 'message':
            text = msg['content']
            # 过滤系统消息
            if any(x in text for x in [
                'Skills store policy',
                'A scheduled reminder',
                'operator configured',
                'System: [',
                '[cron:'
            ]):
                continue
            
            # 过滤纯元数据消息（内容太短）
            if len(text) < 50:
                continue
            
            time_str = msg['timestamp'][11:16] if msg['timestamp'] else '--:--'
            
            # 如果包含metadata，尝试提取实际用户问题
            if 'Sender (untrusted metadata):' in text:
                lines = text.split('\n')
                actual_content = []
                in_metadata = False
                for line in lines:
                    if 'Sender (untrusted metadata):' in line:
                        in_metadata = True
                        continue
                    if in_metadata:
                        if line.strip() == '```':
                            in_metadata = False
                            continue
                        if line.strip().startswith('```json'):
                            continue
                    if not in_metadata and line.strip():
                        actual_content.append(line)
                
                if actual_content:
                    content = ' '.join(actual_content).strip()
                    if len(content) > 10:
                        summary = content[:100] + '...' if len(content) > 100 else content
                        interactions.append({
                            'time': time_str,
                            'summary': summary.replace('\n', ' ')
                        })
                        continue
            
            # 普通消息直接提取
            summary = text[:100] + '...' if len(text) > 100 else text
            interactions.append({
                'time': time_str,
                'summary': summary.replace('\n', ' ')
            })
    return interactions


def extract_feishu_interactions(messages):
    """提取飞书交互概要"""
    interactions = []
    for msg in messages:
        if msg.get('source') != 'feishu':
            continue
        if msg['role'] == 'user':
            text = msg['content']
            # 过滤太短的
            if len(text) < 5:
                continue
            
            # 解析时间
            timestamp = msg.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M')
                except:
                    time_str = '--:--'
            else:
                time_str = '--:--'
            
            summary = text[:100] + '...' if len(text) > 100 else text
            interactions.append({
                'time': time_str,
                'summary': summary.replace('\n', ' ')
            })
    return interactions


def extract_errors(messages):
    """从消息中提取错误/异常"""
    errors = []
    error_keywords = ['失败', '错误', '异常', '超时', '❌', 'error', 'timeout', 'failed', 'Error']
    for msg in messages:
        text = msg['content']
        if any(err in text.lower() for err in error_keywords):
            timestamp = msg.get('timestamp', '')
            if timestamp and msg.get('source') == 'feishu':
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M')
                except:
                    time_str = '--:--'
            else:
                time_str = timestamp[11:16] if timestamp else '--:--'
            
            errors.append({
                'time': time_str,
                'text': text[:200] + '...' if len(text) > 200 else text,
                'source': msg.get('source', 'local')
            })
    return errors


def generate_daily_report():
    """生成工作日报"""
    start_time, end_time, date_str = get_report_time_range()
    print(f"生成日报: {date_str}")
    print(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    # 1. 获取本地会话文件
    session_files = get_session_files(start_time, end_time)
    print(f"找到 {len(session_files)} 个本地会话文件")
    
    # 2. 解析本地会话
    local_messages = []
    for filepath in session_files:
        messages = parse_session_messages(filepath)
        local_messages.extend(messages)
    print(f"本地消息: {len(local_messages)} 条")
    
    # 3. 获取飞书消息
    print("获取飞书消息...")
    feishu_messages = []
    token = get_feishu_token()
    if token:
        # 使用搜索API获取Boss发送的消息
        feishu_messages = search_feishu_messages(token, FEISHU_USER_ID, start_time, end_time)
        print(f"飞书消息: {len(feishu_messages)} 条")
    else:
        print("  无法获取飞书token，跳过飞书消息")
    
    # 4. 合并所有消息
    all_messages = local_messages + feishu_messages
    
    # 5. 提取各类信息
    cron_tasks = extract_cron_tasks(all_messages)
    local_interactions = extract_user_interactions(all_messages)
    feishu_interactions = extract_feishu_interactions(all_messages)
    errors = extract_errors(all_messages)
    
    # 6. 生成报告内容
    report = f"""# 工作日报 - {date_str}

## 📊 概览
- **日期**: {date_str}
- **本地会话**: {len(session_files)} 个文件, {len(local_messages)} 条消息
- **飞书消息**: {len(feishu_messages)} 条
- **定时任务**: {len(cron_tasks)} 个
- **本地交互**: {len(local_interactions)} 次
- **飞书交互**: {len(feishu_interactions)} 次
- **错误/异常**: {len(errors)} 条

## ⏰ 定时任务执行记录
"""
    
    if cron_tasks:
        for task in cron_tasks:
            time_str = task['timestamp'][11:16] if task['timestamp'] else '--:--'
            report += f"- **{time_str}** `{task['name']}`: {task['description'][:80]}\n"
    else:
        report += "_当日无定时任务记录_\n"
    
    # 本地交互
    report += """
## 💬 本地交互概要
"""
    if local_interactions:
        for i, interaction in enumerate(local_interactions[:10], 1):
            report += f"{i}. **{interaction['time']}** {interaction['summary']}\n"
        if len(local_interactions) > 10:
            report += f"_... 及其他 {len(local_interactions) - 10} 条_\n"
    else:
        report += "_当日无本地交互记录_\n"
    
    # 飞书交互
    report += """
## 📱 飞书交互概要
"""
    if feishu_interactions:
        for i, interaction in enumerate(feishu_interactions[:10], 1):
            report += f"{i}. **{interaction['time']}** {interaction['summary']}\n"
        if len(feishu_interactions) > 10:
            report += f"_... 及其他 {len(feishu_interactions) - 10} 条_\n"
    else:
        report += "_当日无飞书交互记录_\n"
    
    # 错误
    if errors:
        report += """
## ⚠️ 错误与异常

"""
        for error in errors:
            source_icon = "📱" if error['source'] == 'feishu' else "💻"
            report += f"- {source_icon} **{error['time']}** {error['text']}\n"
    
    # 保存报告
    year, month = date_str.split('-')[:2]
    month_dir = os.path.join(DAILY_REPORT_DIR, f"{year}-{month}")
    os.makedirs(month_dir, exist_ok=True)
    report_file = os.path.join(month_dir, f"daily-report-{date_str}.md")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 日报已生成: {report_file}")
    print(f"  - 本地会话: {len(session_files)} 文件, {len(local_messages)} 消息")
    print(f"  - 飞书消息: {len(feishu_messages)} 条")
    print(f"  - 定时任务: {len(cron_tasks)} 个")
    print(f"  - 本地交互: {len(local_interactions)} 次")
    print(f"  - 飞书交互: {len(feishu_interactions)} 次")
    print(f"  - 错误/异常: {len(errors)} 条")


if __name__ == "__main__":
    generate_daily_report()
