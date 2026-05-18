#!/usr/bin/env python3
"""
工作日报生成脚本 V11 - AI 驱动版
核心思路：脚本收集数据，AI 生成有实质内容的日报总结。

数据流：
1. 收集：本地会话 + 飞书消息 + 系统状态
2. AI 分析：工作总结 + 系统状况 + 问题提炼
3. 推送：飞书卡片（精简） + memory 文件（完整）

与 V10 的区别：
- V10 = 数据搬运（原文截取填充模板）
- V11 = AI 总结（提炼工作内容、分析系统状况、识别风险）
"""

import os
import json
import re
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# ── 配置 ──

DAILY_REPORT_DIR = "/root/.openclaw/workspace/archive/daily"
MEMORY_DIR = "/root/.openclaw/workspace/memory"
SESSIONS_DIRS = [
    "/root/.openclaw/agents/scheduler/sessions",
    "/root/.openclaw/agents/main/sessions"
]

FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"
FEISHU_CHAT_CACHE = "/root/.openclaw/workspace/config/feishu-chat-cache.json"

AI_MODEL = "glm-5"
ZAI_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"


def _load_zai_key():
    """从 auth-profiles 加载 API key"""
    candidates = [
        '/root/.openclaw/agents/main/agent/auth-profiles.json',
        '/root/.openclaw/agents/scheduler/agent/auth-profiles.json',
    ]
    for path in candidates:
        try:
            with open(path, 'r') as f:
                profiles = json.load(f)
            return profiles['profiles']['zai:default']['key']
        except Exception:
            continue
    return ""

ZAI_API_KEY = _load_zai_key()


# ── AI 调用 ──

def call_ai(system_prompt, user_prompt, max_tokens=2000):
    """调用 zai/glm-5"""
    data = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"{ZAI_BASE_URL}/chat/completions",
             "-H", f"Authorization: Bearer {ZAI_API_KEY}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(data, ensure_ascii=False)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=180
        )
        if result.returncode == 0:
            resp = json.loads(result.stdout)
            msg = resp.get('choices', [{}])[0].get('message', {})
            content = msg.get('content', '') or msg.get('reasoning_content', '')
            return content.strip() if content else None
        else:
            print(f"  AI 调用失败: {result.stderr[:200]}")
            return None
    except Exception as e:
        print(f"  AI 调用异常: {e}")
        return None


# ── 飞书 ──

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode()).get("tenant_access_token")
    except Exception as e:
        print(f"  获取飞书token失败: {e}")
        return None


def get_cached_chat_id():
    if os.path.exists(FEISHU_CHAT_CACHE):
        try:
            with open(FEISHU_CHAT_CACHE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            user_cache = cache.get(FEISHU_USER_ID)
            if user_cache:
                return user_cache.get('chat_id')
        except Exception:
            pass
    return None


def get_feishu_messages(token, chat_id, start_time, end_time):
    """获取飞书聊天消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
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
    req = urllib.request.Request(full_url, headers={"Authorization": f"Bearer {token}"}, method="GET")

    messages = []
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            if result.get("code") == 0:
                for item in result.get("data", {}).get("items", []):
                    msg_type = item.get("msg_type", "")
                    content = item.get("body", {}).get("content", "")
                    create_time = item.get("create_time", "")
                    sender = item.get("sender", {}).get("id", "")
                    if msg_type == "text" and content:
                        try:
                            text = json.loads(content).get("text", "")
                        except Exception:
                            text = content
                        if text:
                            messages.append({
                                "role": "user" if sender == FEISHU_USER_ID else "assistant",
                                "content": text,
                                "timestamp": create_time,
                                "source": "feishu"
                            })
    except Exception as e:
        print(f"  获取飞书消息失败: {e}")
    return messages


def send_feishu_card(token, user_id, card_data):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    payload = {
        "receive_id": user_id,
        "msg_type": "interactive",
        "content": json.dumps(card_data, ensure_ascii=False)
    }
    req = urllib.request.Request(
        full_url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            if result.get("code") == 0:
                print("  ✅ 飞书卡片发送成功")
                return True
            else:
                print(f"  ❌ 飞书卡片发送失败: {result.get('msg')}")
                return False
    except Exception as e:
        print(f"  ❌ 飞书卡片发送异常: {e}")
        return False


# ── 数据收集 ──

def get_session_files(start_time, end_time):
    """获取时间范围内的会话文件"""
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
                mtime_ms = int(os.stat(filepath).st_mtime * 1000)
                if start_ts <= mtime_ms <= end_ts:
                    session_files.append(filepath)
            except Exception:
                continue
    return session_files


def parse_session_messages(filepath):
    """解析会话文件中的消息"""
    messages = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue

                msg = data.get('message', {})
                role = msg.get('role', '')
                content = msg.get('content', [])

                text_parts = []
                for part in content:
                    if part.get('type') == 'text':
                        text_parts.append(part.get('text', ''))
                full_text = ' '.join(text_parts).strip()

                if not full_text or len(full_text) < 10:
                    continue

                # 跳过系统噪音
                noise_markers = [
                    'Skills store policy', 'A scheduled reminder',
                    'operator configured', 'HEARTBEAT_OK',
                    'openclaw.inbound_meta', '[cron:'
                ]
                if any(x in full_text for x in noise_markers):
                    continue

                messages.append({
                    "role": role,
                    "content": full_text,
                    "timestamp": "",
                    "source": "local"
                })
    except Exception as e:
        print(f"  解析会话失败 {filepath}: {e}")
    return messages


def collect_system_status():
    """收集系统实时状态"""
    status = {"disk": "", "memory": "", "cron_ok": True}
    try:
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        lines = disk.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 6:
                status["disk"] = f"{parts[2]}/{parts[1]} ({parts[4]})"
    except Exception:
        pass
    try:
        mem = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        for line in mem.stdout.split('\n'):
            if line.startswith('Mem:'):
                parts = line.split()
                if len(parts) >= 3:
                    status["memory"] = f"{parts[2]}/{parts[1]}"
    except Exception:
        pass
    return status


def classify_errors(messages):
    """将错误消息归类"""
    categories = {
        "config": [],
        "script": [],
        "api": [],
        "other": []
    }
    for msg in messages:
        text = msg['content'].lower()
        if any(x in text for x in ['error', '失败', '错误', '异常', 'failed', 'timeout', 'traceback']):
            if 'config' in text or 'warning' in text or 'plugin' in text:
                categories["config"].append(msg['content'][:100])
            elif 'script' in text or 'python' in text or 'traceback' in text or 'import' in text:
                categories["script"].append(msg['content'][:100])
            elif 'api' in text or 'token' in text or 'http' in text or '401' in text or '403' in text:
                categories["api"].append(msg['content'][:100])
            else:
                categories["other"].append(msg['content'][:100])
    return categories


# ── AI 日报生成 ──

SYSTEM_PROMPT = """你是小助的日报生成模块。根据当天收集到的数据，生成一份有实质价值的工作日报。

核心原则：
1. 不要当数据搬运工——用户不需要看原始消息列表
2. 提炼工作内容——用户做了什么、解决了什么、推进了什么
3. 系统状况要简洁——有异常报异常，没异常一句话带过
4. 有判断力——内容少的日（周末/轻度使用）生成简短版
5. 说人话，不要模板感

输出格式（严格遵循）：

## 系统运行
（一句话概括系统健康状况。如有异常列出关键项，无异常则"系统运行正常"）

## 工作总结
（2-5 条，每条一句话概括一个工作事项。从用户交互内容中提炼，标注是飞书还是本地）
- • 事项描述 [来源]

## 问题与风险
（仅在有未解决问题时出现。列出需要关注的事项）

## 一句话日报
（一句话总结今天）"""


def generate_ai_report(date_str, all_messages, feishu_msgs_count, sys_status, error_categories):
    """用 AI 生成日报内容"""

    # 提取用户消息作为工作内容输入
    user_messages = []
    for msg in all_messages:
        if msg['role'] == 'user' and len(msg['content']) > 20:
            source = "飞书" if msg['source'] == 'feishu' else "本地"
            # 提取实际内容（去掉元数据）
            text = msg['content']
            if 'Sender (untrusted metadata):' in text:
                lines = text.split('\n')
                actual = [l for l in lines if l.strip() and not l.strip().startswith('```') and 'Sender' not in l and 'Conversation' not in l and 'message_id' not in l]
                text = ' '.join(actual).strip()
            if text and len(text) > 15:
                user_messages.append(f"[{source}] {text[:200]}")

    # 错误摘要
    error_summary = ""
    total_errors = sum(len(v) for v in error_categories.values())
    if total_errors > 0:
        parts = []
        for cat, items in error_categories.items():
            if items:
                parts.append(f"{cat}类 {len(items)} 个")
        error_summary = f"共 {total_errors} 个异常：{', '.join(parts)}"
        # 附加代表性的错误
        for cat, items in error_categories.items():
            if items:
                error_summary += f"\n{cat}代表: {items[0][:80]}"
    else:
        error_summary = "无异常"

    # 构建 prompt
    work_items = "\n".join(user_messages[:15]) if user_messages else "当日无用户交互"
    
    local_msg_count = sum(1 for m in all_messages if m['source'] == 'local')
    total_msgs = len(all_messages)

    user_prompt = f"""日期：{date_str}
消息量：本地 {local_msg_count} 条，飞书 {feishu_msgs_count} 条，共 {total_msgs} 条

用户交互内容：
{work_items}

系统资源：磁盘 {sys_status['disk'] or '未知'}，内存 {sys_status['memory'] or '未知'}

异常情况：
{error_summary}

请生成日报。"""

    return call_ai(SYSTEM_PROMPT, user_prompt, max_tokens=1500)


# ── 飞书卡片构建 ──

def build_card(date_str, ai_report, stats, sys_status):
    """将 AI 报告转为飞书卡片"""
    # 解析 AI 输出的各部分
    sections = {
        "system": "系统运行正常",
        "work": "",
        "problems": "",
        "summary": ""
    }

    current = None
    for line in ai_report.split('\n'):
        line = line.strip()
        if '## 系统运行' in line:
            current = "system"
            continue
        elif '## 工作总结' in line:
            current = "work"
            continue
        elif '## 问题与风险' in line:
            current = "problems"
            continue
        elif '## 一句话日报' in line:
            current = "summary"
            continue
        if current and line:
            if sections[current]:
                sections[current] += "\n" + line
            else:
                sections[current] = line

    # 构建卡片元素
    elements = []

    # 系统运行
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**🖥️ 系统运行**\n{sections['system']}\n磁盘: {sys_status['disk'] or '未知'} | 内存: {sys_status['memory'] or '未知'}"
        }
    })
    elements.append({"tag": "hr"})

    # 工作总结
    if sections['work']:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📋 工作总结**\n{sections['work']}"
            }
        })
        elements.append({"tag": "hr"})

    # 问题与风险
    if sections['problems']:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**⚠️ 问题与风险**\n{sections['problems']}"
            }
        })
        elements.append({"tag": "hr"})

    # 一句话日报
    if sections['summary']:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**💡 一句话日报**\n{sections['summary']}"
            }
        })

    # 数据概览（折叠）
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"📊 *数据：本地 {stats['local_msgs']} 条 | 飞书 {stats['feishu_msgs']} 条 | 异常 {stats['errors']} 条*"
        }
    })

    # 详细报告链接
    elements.append({
        "tag": "note",
        "elements": [
            {"tag": "plain_text", "content": f"📄 详细报告: memory/{date_str}.md"}
        ]
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"content": f"📊 工作日报 - {date_str}", "tag": "plain_text"}
        },
        "elements": elements
    }
    return card


# ── 兜底报告 ──

def build_fallback_card(date_str, stats, sys_status, error_categories):
    """AI 不可用时的兜底卡片"""
    total_errors = sum(len(v) for v in error_categories.values())

    system_text = "系统运行正常"
    if total_errors > 0:
        parts = [f"{k}类 {len(v)}个" for k, v in error_categories.items() if v]
        system_text = f"发现 {total_errors} 个异常：{', '.join(parts)}"

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"content": f"📊 工作日报 - {date_str}", "tag": "plain_text"}
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**🖥️ 系统运行**\n{system_text}\n磁盘: {sys_status['disk'] or '未知'} | 内存: {sys_status['memory'] or '未知'}\n\n⚠️ *AI 总结不可用，仅展示系统状况*"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📊 数据：本地 {stats['local_msgs']} 条 | 飞书 {stats['feishu_msgs']} 条 | 异常 {total_errors} 条"
                }
            }
        ]
    }
    return card


# ── 主流程 ──

def main(target_date_str=None):
    print("=" * 50)
    print("📊 工作日报 V11 - AI 驱动版")
    print("=" * 50)

    # 确定日期
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    else:
        target_date = datetime.now() - timedelta(days=1)

    date_str = target_date.strftime('%Y-%m-%d')
    start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    print(f"日报日期: {date_str}")
    print(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}")

    # 1. 收集本地会话
    print("\n📂 收集数据...")
    session_files = get_session_files(start_time, end_time)
    local_messages = []
    for fp in session_files:
        local_messages.extend(parse_session_messages(fp))
    print(f"  本地会话: {len(session_files)} 文件, {len(local_messages)} 条消息")

    # 2. 收集飞书消息
    feishu_messages = []
    token = get_feishu_token()
    if token:
        chat_id = get_cached_chat_id()
        if chat_id:
            feishu_messages = get_feishu_messages(token, chat_id, start_time, end_time)
            print(f"  飞书消息: {len(feishu_messages)} 条")
        else:
            print("  未找到 chat_id 缓存")
    else:
        print("  无法获取飞书 token")

    # 3. 合并消息
    all_messages = local_messages + feishu_messages

    # 4. 系统状态
    sys_status = collect_system_status()
    error_categories = classify_errors(all_messages)
    total_errors = sum(len(v) for v in error_categories.values())

    stats = {
        'local_msgs': len(local_messages),
        'feishu_msgs': len(feishu_messages),
        'errors': total_errors
    }

    # 5. AI 生成日报
    print("\n🤖 AI 生成日报内容...")
    ai_report = generate_ai_report(date_str, all_messages, len(feishu_messages), sys_status, error_categories)

    if ai_report and len(ai_report) > 50:
        print(f"  ✅ AI 日报生成完成 ({len(ai_report)} 字)")
    else:
        print("  ⚠️ AI 生成失败或内容过短，使用兜底模板")
        ai_report = None

    # 6. 推送飞书卡片
    print("\n📤 推送飞书卡片...")
    token = get_feishu_token()
    if token:
        if ai_report:
            card = build_card(date_str, ai_report, stats, sys_status)
        else:
            card = build_fallback_card(date_str, stats, sys_status, error_categories)
        send_feishu_card(token, FEISHU_USER_ID, card)
    else:
        print("  ❌ 无法获取飞书 token")

    # 7. 保存 memory 文件
    report_content = ai_report or "（AI 生成失败，仅保存原始数据）"

    memory_file = os.path.join(MEMORY_DIR, f"{date_str}.md")
    # 如果已有文件，不覆盖（可能已有反思等内容），追加日报部分
    existing = ""
    if os.path.exists(memory_file):
        with open(memory_file, 'r', encoding='utf-8') as f:
            existing = f.read()
        # 如果已有日报摘要，替换
        if '## 日报摘要' in existing:
            parts = existing.split('## 日报摘要', 1)
            before = parts[0]
            after_parts = parts[1].split('\n## ', 1)
            after = '\n## ' + after_parts[1] if len(after_parts) > 1 else ''
            existing = before + '## 日报摘要\n' + report_content + after

    if existing:
        if '## 日报摘要' not in existing:
            # 追加到文件末尾
            existing += f"\n\n## 日报摘要 (V11)\n{report_content}"
        with open(memory_file, 'w', encoding='utf-8') as f:
            f.write(existing)
    else:
        os.makedirs(MEMORY_DIR, exist_ok=True)
        with open(memory_file, 'w', encoding='utf-8') as f:
            f.write(f"# {date_str} 记忆\n\n## 日报摘要\n{report_content}\n")

    # 8. 归档
    year, month = date_str.split('-')[:2]
    month_dir = os.path.join(DAILY_REPORT_DIR, f"{year}-{month}")
    os.makedirs(month_dir, exist_ok=True)
    archive_file = os.path.join(month_dir, f"daily-report-{date_str}.md")
    with open(archive_file, 'w', encoding='utf-8') as f:
        f.write(f"# 工作日报 - {date_str} (V11)\n\n")
        f.write(report_content)
        f.write(f"\n\n---\n*数据: 本地 {stats['local_msgs']} 条, 飞书 {stats['feishu_msgs']} 条, 异常 {total_errors} 条*\n")
        f.write(f"*系统: 磁盘 {sys_status['disk']}, 内存 {sys_status['memory']}*\n")

    print(f"\n✅ 记忆文件: {memory_file}")
    print(f"✅ 归档文件: {archive_file}")


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    main(target)
