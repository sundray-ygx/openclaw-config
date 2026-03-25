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
DAILY_REPORT_DIR = "/root/.openclaw/workspace/archive/daily"
MEMORY_DIR = "/root/.openclaw/workspace/memory"
SESSIONS_DIRS = [
    "/root/.openclaw/agents/scheduler/sessions",
    "/root/.openclaw/agents/main/sessions"
]

# 飞书配置
FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"  # Boss的open_id
FEISHU_CHAT_CACHE = "/home/openclaw/.openclaw/workspace/config/feishu-chat-cache.json"


def get_cached_chat_id(user_id):
    """从缓存文件获取chat_id"""
    if os.path.exists(FEISHU_CHAT_CACHE):
        try:
            with open(FEISHU_CHAT_CACHE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            user_cache = cache.get(user_id)
            if user_cache:
                return user_cache.get('chat_id')
        except Exception as e:
            print(f"  读取chat缓存失败: {e}")
    return None


def get_feishu_messages(token, chat_id, start_time, end_time):
    """获取飞书消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    
    # 转换时间为Unix时间戳（秒）
    start_ts = int(start_time.timestamp())
    end_ts = int(end_time.timestamp())
    
    params = {
        "container_id_type": "chat",
        "container_id": chat_id,
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
            if result.get("code") == 0:
                items = result.get("data", {}).get("items", [])
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
            
            # 解析时间 (飞书返回的是毫秒级时间戳)
            timestamp = msg.get('timestamp', '')
            time_str = '--:--'
            if timestamp:
                try:
                    # 飞书返回的是毫秒级时间戳，需要除以1000
                    ts = int(timestamp) / 1000
                    dt = datetime.fromtimestamp(ts)
                    time_str = dt.strftime('%H:%M')
                except:
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
            time_str = '--:--'
            if timestamp:
                try:
                    if msg.get('source') == 'feishu':
                        # 飞书返回的是毫秒级时间戳，需要除以1000
                        ts = int(timestamp) / 1000
                        dt = datetime.fromtimestamp(ts)
                        time_str = dt.strftime('%H:%M')
                    else:
                        time_str = timestamp[11:16]
                except:
                    time_str = '--:--'
            
            errors.append({
                'time': time_str,
                'text': text[:200] + '...' if len(text) > 200 else text,
                'source': msg.get('source', 'local')
            })
    return errors


def extract_reflection_from_memory(date_str):
    """从记忆文件提取复盘与改进内容"""
    memory_file = os.path.join("/home/openclaw/.openclaw/workspace/memory", f"{date_str}.md")
    
    if not os.path.exists(memory_file):
        return None
    
    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取复盘与改进部分
        reflection_match = re.search(r'## 🔄 复盘与改进\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
        if reflection_match:
            reflection_text = reflection_match.group(1).strip()
            # 清理空行和格式
            lines = [line.strip() for line in reflection_text.split('\n') if line.strip()]
            return '\n'.join(lines)
    except Exception as e:
        print(f"  读取记忆文件失败: {e}")
    
    return None


def generate_daily_report(target_date_str=None):
    """生成工作日报
    Args:
        target_date_str: 可选，指定日期格式 YYYY-MM-DD，默认为昨天
    """
    if target_date_str:
        # 指定日期
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        date_str = target_date_str
    else:
        # 默认昨天
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
        # 从缓存获取chat_id
        chat_id = get_cached_chat_id(FEISHU_USER_ID)
        if chat_id:
            print(f"  从缓存获取chat_id: {chat_id}")
            feishu_messages = get_feishu_messages(token, chat_id, start_time, end_time)
            print(f"飞书消息: {len(feishu_messages)} 条")
        else:
            print("  未找到缓存的chat_id，跳过飞书消息")
            print("  提示: 需要在飞书中与机器人交互一次，以记录chat_id")
    else:
        print("  无法获取飞书token，跳过飞书消息")
    
    # 4. 合并所有消息
    all_messages = local_messages + feishu_messages
    
    # 5. 提取各类信息
    cron_tasks = extract_cron_tasks(all_messages)
    local_interactions = extract_user_interactions(all_messages)
    feishu_interactions = extract_feishu_interactions(all_messages)
    errors = extract_errors(all_messages)
    
    # 6. 从记忆文件提取复盘与改进
    reflection_content = extract_reflection_from_memory(date_str)
    
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
    
    # 复盘与改进
    if reflection_content:
        report += """
## 🔄 复盘与改进

"""
        report += reflection_content + "\n"
    
    # 生成 memory 格式内容
    memory_content = f"""# {date_str} 记忆

## 日报摘要
{report}

## 🔄 复盘与改进

**做得好的：**
• 

**需改进：**
• 

## 待跟进事项
- [ ] 

## 明日计划
- 

---
*生成于 {datetime.now().strftime("%H:%M")}*
"""
    
    # 保存到 memory 目录（主输出）
    memory_file = os.path.join(MEMORY_DIR, f"{date_str}.md")
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(memory_file, 'w', encoding='utf-8') as f:
        f.write(memory_content)
    
    # 生成简化版存入 archive/daily/（仅关键指标）
    year, month = date_str.split('-')[:2]
    month_dir = os.path.join(DAILY_REPORT_DIR, f"{year}-{month}")
    os.makedirs(month_dir, exist_ok=True)
    
    summary_report = f"""# 工作日报摘要 - {date_str}

## 📊 关键指标
- **日期**: {date_str}
- **本地会话**: {len(session_files)} 个文件, {len(local_messages)} 条消息
- **飞书消息**: {len(feishu_messages)} 条
- **定时任务**: {len(cron_tasks)} 个
- **本地交互**: {len(local_interactions)} 次
- **飞书交互**: {len(feishu_interactions)} 次
- **错误/异常**: {len(errors)} 条

## 💬 关键交互
"""
    if local_interactions:
        summary_report += "### 本地\n"
        for i, interaction in enumerate(local_interactions[:5], 1):
            summary_report += f"{i}. **{interaction['time']}** {interaction['summary']}\n"
    
    if feishu_interactions:
        summary_report += "\n### 飞书\n"
        for i, interaction in enumerate(feishu_interactions[:5], 1):
            summary_report += f"{i}. **{interaction['time']}** {interaction['summary']}\n"
    
    summary_report += f"\n---\n*详细内容见 memory/{date_str}.md*"
    
    archive_file = os.path.join(month_dir, f"daily-report-{date_str}.md")
    with open(archive_file, 'w', encoding='utf-8') as f:
        f.write(summary_report)
    
    print(f"\n✅ 记忆文件已生成: {memory_file}")
    print(f"✅ 归档摘要已生成: {archive_file}")
    print(f"  - 本地会话: {len(session_files)} 文件, {len(local_messages)} 消息")
    print(f"  - 飞书消息: {len(feishu_messages)} 条")
    print(f"  - 定时任务: {len(cron_tasks)} 个")
    print(f"  - 本地交互: {len(local_interactions)} 次")
    print(f"  - 飞书交互: {len(feishu_interactions)} 次")
    print(f"  - 错误/异常: {len(errors)} 条")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # 支持命令行参数指定日期: python3 daily_report.py 2026-03-21
        generate_daily_report(sys.argv[1])
    else:
        generate_daily_report()
