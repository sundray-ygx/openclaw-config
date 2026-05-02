#!/usr/bin/env python3
"""
Daily Reflection V3 - 基于 AI 的深度反思生成器

核心改进：
1. 不再从固定格式提取"教训"，而是收集当日完整工作上下文
2. 交给 AI 做真正的反思（不是模板匹配）
3. 对比历史反思避免重复
4. 输出可执行的改进行动项
"""

import os
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

MEMORY_DIR = "/root/.openclaw/workspace/memory"
REFLECTION_DIR = "/root/.openclaw/workspace/reflection"
LESSONS_FILE = "/root/.openclaw/workspace/memory/lessons.md"
FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"

# AI API 配置（使用内置的百炼 API）
AI_API_URL = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"

# 从 openclaw.json 读取 API Key
def _load_api_key():
    try:
        import json as _json
        with open('/root/.openclaw/openclaw.json', 'r') as _f:
            _cfg = _json.load(_f)
        return _cfg['models']['providers']['bailian']['apiKey']
    except Exception:
        return os.environ.get("DASHSCOPE_API_KEY", "")

AI_API_KEY = _load_api_key()
AI_MODEL = "qwen3-coder-plus"


def get_ai_response(system_prompt, user_prompt, max_tokens=2000):
    """调用 AI API 生成反思"""
    data = json.dumps({
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode()

    req = urllib.request.Request(AI_API_URL, data=data, headers={
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  AI API 调用失败: {e}")
        return None


def collect_daily_context(date_str):
    """收集当日完整工作上下文"""
    context = {
        "date": date_str,
        "daily_log": "",
        "interactions": [],
        "errors": [],
        "tasks_executed": [],
        "projects": []
    }

    # 1. 读取当日记忆日志
    memory_file = os.path.join(MEMORY_DIR, f"{date_str}.md")
    if os.path.exists(memory_file):
        with open(memory_file, "r", encoding="utf-8") as f:
            context["daily_log"] = f.read()

    # 2. 提取工作交互（去掉系统心跳和噪音）
    if context["daily_log"]:
        lines = context["daily_log"].split('\n')
        for line in lines:
            # 提取用户实际交互
            if "**" in line and ("GMT+8]" in line or "本地交互" in line):
                clean = re.sub(r'\*\*[^*]+\*\*', '', line).strip()
                clean = re.sub(r'^\d+\.\s*', '', clean).strip()
                if clean and "HEARTBEAT" not in clean and len(clean) > 15:
                    context["interactions"].append(clean)

            # 提取定时任务执行
            if "定时任务执行记录" in line or "cron" in line.lower():
                context["tasks_executed"].append(line.strip())

            # 提取项目相关
            if "[PROJECT:" in line:
                context["projects"].append(line.strip())

    # 3. 提取真正的错误（过滤噪音）
    if context["daily_log"]:
        error_section = re.search(
            r'## ⚠️ 错误与异常\s*\n(.*?)(?=\n## |\Z)',
            context["daily_log"], re.DOTALL
        )
        if error_section:
            error_text = error_section.group(1)
            for line in error_text.split('\n'):
                line = line.strip()
                # 过滤掉文件内容、代码片段、JSON等噪音
                if not line or line.startswith('```') or line.startswith('#!/') or line.startswith('import '):
                    continue
                if line.startswith('- 💻') or line.startswith('- 📱'):
                    # 提取实际错误信息，去掉文件内容和代码
                    content = re.sub(r'^-\s*[💻📱]\s*\*\*[^*]+\*\*\s*', '', line).strip()
                    # 过滤代码片段和过长内容
                    if (content and len(content) > 10 and len(content) < 200
                            and not content.startswith('{') and not content.startswith('#!/')
                            and not content.startswith('"""') and 'def ' not in content[:10]
                            and 'class ' not in content[:10]
                            and not content.startswith('import ')
                            and 'Traceback' not in content
                            and 'open-apis' not in content):
                        context["errors"].append(content)

    return context


def load_recent_reflections(days=7):
    """加载最近几天的反思，用于去重"""
    reflections_file = os.path.join(REFLECTION_DIR, "reflections.md")
    if not os.path.exists(reflections_file):
        return ""

    # 只读取最近部分
    with open(reflections_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 取最近的反思（前 3000 字符即可）
    entries = content.split("---")
    recent = "---".join(entries[:min(8, len(entries))])
    return recent[:3000]


def load_lessons():
    """加载已有经验教训"""
    if not os.path.exists(LESSONS_FILE):
        return ""
    with open(LESSONS_FILE, "r", encoding="utf-8") as f:
        return f.read()[:2000]


def generate_reflection(context, recent_reflections, existing_lessons):
    """用 AI 生成深度反思"""

    # 构建工作摘要（限制长度避免 token 爆炸）
    work_summary = ""
    if context["daily_log"]:
        # 只取关键部分
        work_summary = context["daily_log"][:3000]

    interaction_list = "\n".join([f"- {i}" for i in context["interactions"][:10]])
    error_list = "\n".join([f"- {e}" for e in context["errors"][:5]])
    project_list = "\n".join([f"- {p}" for p in context["projects"][:5]])

    system_prompt = """你是一位深度反思教练。你的任务是分析一天的工作记录，产出有价值的反思。

严格要求：
1. **不要泛泛而谈** — 每个反思点必须对应具体的事件、决策或行为
2. **不要重复** — 对比历史反思，如果某个点已经反思过，就不要再提
3. **要深入根因** — 不是表面描述"出了什么错"，而是分析"为什么会这样"，连问3个为什么
4. **要可执行** — 改进建议必须是具体的行动项，不是"加强注意"这种废话
5. **要发现亮点** — 做得好的事情也要记录，分析为什么做得好，提炼可复用的方法

输出格式（严格遵循）：

## 反思报告

### 今日关键事件
（列出今天最重要的 2-4 件事，每件一句话）

### 深度反思

#### 反思点 1：[标题]
- **触发事件**：（具体什么事触发了这个反思）
- **根因分析**：（为什么5分析，至少2层深度）
- **可执行改进**：（具体的、可立即执行的行动项）
- **预期效果**：（改进后能带来什么变化）

（如果有更多反思点，继续添加）

### 做得好的
（1-2件做得好的事，分析为什么好，提炼方法）

### 本日行动项
（从反思中提炼 1-3 个具体的、可立即执行的行动项）
每个行动项必须包含分类标签：
- [🔧自动] 可自动执行的技术任务（写脚本、改配置）
- [📋流程] 需人工决策的流程改进
- [⚙️配置] 可半自动完成的配置调整
格式示例：[🔧自动] 开发数据完整性检查脚本

### 行动项进展回顾
（检查上次反思的行动项，逐一说明是否已完成/进行中/已搁置）"""

    user_prompt = f"""请对以下 {context['date']} 的工作进行深度反思。

## 当日工作日志
{work_summary}

## 主要交互
{interaction_list if interaction_list else "无特殊交互"}

## 项目进展
{project_list if project_list else "无项目记录"}

## 当日错误
{error_list if error_list else "无明显错误"}

## 最近反思历史（用于去重，避免重复相同反思点）
{recent_reflections if recent_reflections else "无历史反思"}

## 已有经验教训（避免重复已有经验）
{existing_lessons if existing_lessons else "无"}

## 待处理行动项（检查进展，在"行动项进展回顾"部分逐一说明）
{{pending_actions}}

---
请基于以上信息，生成深度、具体、不重复的反思报告。在"行动项进展回顾"部分，逐一检查上面的待处理行动项，判断其状态（已完成/进行中/已搁置），并简要说明判断依据。如果今天确实是平淡的一天，没有值得反思的点，就直接说"今日无特殊反思点"。不要为了反思而反思。"""

    pending_actions = get_pending_actions_context()
    user_prompt = user_prompt.replace("{pending_actions}", pending_actions)

    return get_ai_response(system_prompt, user_prompt, max_tokens=2000)


def save_reflection(date_str, reflection_text):
    """保存反思到文件"""
    os.makedirs(REFLECTION_DIR, exist_ok=True)
    filepath = os.path.join(REFLECTION_DIR, "reflections.md")

    # 读取现有内容
    existing = ""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = f.read()

    # 构建新条目
    entry = f"""
---

## {date_str}

{reflection_text}

"""

    # 在文件开头（标题后）插入新记录
    if "# Reflections Log" in existing:
        parts = existing.split("# Reflections Log", 1)
        after_title = parts[1]
        # 找到第一个 --- 后插入
        first_sep = after_title.find("---")
        if first_sep != -1:
            new_content = (parts[0] + "# Reflections Log" +
                           after_title[:first_sep + 3] + entry + after_title[first_sep + 3:])
        else:
            new_content = parts[0] + "# Reflections Log\n" + entry + after_title
    else:
        new_content = f"# Reflections Log\n\n> Most recent first.\n{entry}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  ✅ 反思已保存到 {filepath}")


def extract_action_items(reflection_text):
    """从反思中提取行动项（带分类标签）"""
    action_items = []
    in_action_section = False

    for line in reflection_text.split('\n'):
        if '本日行动项' in line:
            in_action_section = True
            continue
        if in_action_section:
            if line.startswith('###') or line.startswith('## '):
                break
            if line.strip().startswith('-') or line.strip().startswith('[') or line.strip()[0:1].isdigit():
                clean = re.sub(r'^[-\d.]\s*', '', line.strip())
                if clean and len(clean) > 5:
                    action_items.append(clean)

    return action_items[:3]


def classify_action_item(item_text):
    """分析行动项分类"""
    item_lower = item_text.lower()
    auto_keywords = ['开发脚本', '写脚本', '创建脚本', '批量', '自动化', '检查脚本',
                     '监控脚本', '工具', '爬虫', '数据处理']
    config_keywords = ['配置', '参数', '权限', '设置', '调整配置', '修改配置']

    for kw in auto_keywords:
        if kw in item_text:
            return '🔧自动'
    for kw in config_keywords:
        if kw in item_text:
            return '⚙️配置'
    return '📋流程'


def load_pending_actions():
    """加载待处理的行动项"""
    tracker_file = os.path.join(MEMORY_DIR, 'action-tracker.json')
    if not os.path.exists(tracker_file):
        return []
    try:
        with open(tracker_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [a for a in data.get('actions', []) if a.get('status') == '⏳ 进行中']
    except Exception:
        return []


def save_action_items(date_str, action_items):
    """保存行动项到 tracker 和 todo-state"""
    tracker_file = os.path.join(MEMORY_DIR, 'action-tracker.json')
    todo_file = os.path.join(MEMORY_DIR, 'todo-state.json')

    # 1. 读取或初始化 tracker
    tracker = {'actions': []}
    if os.path.exists(tracker_file):
        try:
            with open(tracker_file, 'r', encoding='utf-8') as f:
                tracker = json.load(f)
        except Exception:
            pass

    # 2. 添加新行动项
    new_count = 0
    for i, item in enumerate(action_items):
        category = classify_action_item(item)
        action = {
            'id': f'{date_str}-action-{i}',
            'text': item,
            'category': category,
            'status': '⏳ 进行中',
            'created_at': date_str,
            'source': 'daily_reflection',
            'check_count': 0
        }
        # 去重：同类文本不重复添加
        exists = any(a['text'] == item for a in tracker['actions'])
        if not exists:
            tracker['actions'].append(action)
            new_count += 1

    # 3. 保存 tracker
    with open(tracker_file, 'w', encoding='utf-8') as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)

    # 4. 写入 todo-state（复用已有提醒机制）
    try:
        with open(todo_file, 'r', encoding='utf-8') as f:
            todo_data = json.load(f)
    except Exception:
        todo_data = {'reminders': []}

    for i, item in enumerate(action_items):
        category = classify_action_item(item)
        # 24小时后提醒
        remind_dt = datetime.now() + timedelta(days=1)
        remind_time = remind_dt.strftime('%Y-%m-%dT%H:%M:%S+08:00')

        reminder = {
            'id': f'{date_str}-action-{i}',
            'title': f'[反思行动] {item[:40]}',
            'remind_time': remind_time,
            'status': '⏳ 待提醒',
            'created_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00'),
            'description': f'{category} {item}',
            'source': 'daily_reflection',
            'ref_date': date_str
        }
        # 去重
        exists = any(r['id'] == reminder['id'] for r in todo_data['reminders'])
        if not exists:
            todo_data['reminders'].append(reminder)

    with open(todo_file, 'w', encoding='utf-8') as f:
        json.dump(todo_data, f, indent=2, ensure_ascii=False)

    return new_count


def check_action_progress(date_str, context_log):
    """检查待处理行动项的进展（通过搜索日志判断是否已完成）"""
    pending = load_pending_actions()
    if not pending:
        return {}

    tracker_file = os.path.join(MEMORY_DIR, 'action-tracker.json')
    try:
        with open(tracker_file, 'r', encoding='utf-8') as f:
            tracker = json.load(f)
    except Exception:
        return {}

    progress = {}
    for action in pending:
        action_id = action['id']
        text = action['text']
        # 提取关键词（去掉分类标签）
        keywords = re.sub(r'^\[.+?\]\s*', '', text)
        # 取核心词（去停用词）
        core_words = [w for w in keywords if len(w) > 1 and w not in ('的', '了', '和', '与', '等', '要', '到', '在', '对')]

        # 在日志中搜索关键词出现次数
        match_count = sum(1 for w in core_words if w in context_log)
        action['check_count'] = action.get('check_count', 0) + 1

        if match_count >= len(core_words) * 0.6:
            # 大部分关键词在日志中出现，视为可能完成
            progress[action_id] = '✅ 可能完成'
        elif action['check_count'] >= 7:
            # 7天未确认，标记搁置
            progress[action_id] = '⏸️ 已搁置'
        else:
            progress[action_id] = '⏳ 进行中'

        # 更新状态
        for a in tracker['actions']:
            if a['id'] == action_id:
                a['status'] = progress[action_id]
                a['check_count'] = action['check_count']
                break

    with open(tracker_file, 'w', encoding='utf-8') as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)

    return progress


def get_pending_actions_context():
    """获取待处理行动项，作为反思上下文传入 AI"""
    pending = load_pending_actions()
    if not pending:
        return "无待处理行动项"

    lines = []
    for a in pending[:5]:
        lines.append(f"- [{a['category']}] {a['text']}（创建于 {a['created_at']}，已检查 {a.get('check_count', 0)} 次）")
    return "\n".join(lines)


def update_action_status_in_tracker(action_id, new_status):
    """更新行动项状态"""
    tracker_file = os.path.join(MEMORY_DIR, 'action-tracker.json')
    try:
        with open(tracker_file, 'r', encoding='utf-8') as f:
            tracker = json.load(f)
        for a in tracker['actions']:
            if a['id'] == action_id:
                a['status'] = new_status
                break
        with open(tracker_file, 'w', encoding='utf-8') as f:
            json.dump(tracker, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def extract_action_progress(reflection_text):
    """从反思中提取行动项进展更新"""
    progress = {}
    in_section = False
    current_id = None

    for line in reflection_text.split('\n'):
        if '行动项进展回顾' in line:
            in_section = True
            continue
        if in_section and (line.startswith('### 本日行动项') or line.startswith('### 关键洞察')):
            break
        if in_section and line.strip().startswith('-'):
            text = line.strip().lstrip('- ')
            if '已完成' in text or '✅' in text:
                progress['status'] = '✅ 已完成'
            elif '搁置' in text or '不再' in text or '放弃' in text:
                progress['status'] = '⏸️ 已搁置'
            elif '进行中' in text or '部分' in text:
                progress['status'] = '⏳ 进行中'

    return progress


def generate_feishu_report(date_str, reflection_text, action_items):
    """生成飞书推送报告（精简版）"""
    lines = [
        f"🪞 每日反思 - {date_str}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]

    # 提取关键事件
    in_section = False
    key_events = []
    for line in reflection_text.split('\n'):
        if '今日关键事件' in line:
            in_section = True
            continue
        if in_section:
            if line.startswith('###'):
                in_section = False
                continue
            if line.strip().startswith('-'):
                key_events.append(line.strip().lstrip('- '))

    if key_events:
        lines.append("")
        lines.append("📌 关键事件")
        for event in key_events[:4]:
            lines.append(f"• {event}")

    # 提取反思点标题
    reflection_points = re.findall(r'#### 反思点 \d+：(.+)', reflection_text)

    if reflection_points:
        lines.append("")
        lines.append("🔮 反思要点")
        for i, point in enumerate(reflection_points, 1):
            lines.append(f"{i}. {point}")

    # 行动项
    if action_items:
        lines.append("")
        lines.append("✅ 行动项")
        for i, item in enumerate(action_items, 1):
            category = classify_action_item(item)
            # 清理分类标签避免重复显示
            display = re.sub(r'^\[.+?\]\s*', '', item)
            lines.append(f"{i}. {category} {display}")

    # 关键洞察
    insight_match = re.search(r'### 关键洞察\n+(.+)', reflection_text)
    if insight_match:
        lines.append("")
        lines.append(f"💡 {insight_match.group(1).strip()}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📁 完整反思：{REFLECTION_DIR}/reflections.md")

    return "\n".join(lines)


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


def send_feishu_message(message_text):
    """发送消息到飞书"""
    token = get_feishu_token()
    if not token:
        print("⚠️ 无法获取飞书token，跳过推送")
        return False

    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    full_url = f"{url}?{urllib.parse.urlencode(params)}"

    message_data = json.dumps({
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({"text": message_text})
    }).encode()

    req = urllib.request.Request(full_url, data=message_data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if result.get("code") == 0:
                print(f"  ✅ 飞书报告发送成功")
                return True
            else:
                print(f"  ⚠️ 飞书发送失败: {result.get('msg')}")
                return False
    except Exception as e:
        print(f"  ⚠️ 飞书发送失败: {e}")
        return False


def main():
    print("🪞 每日反思 V3 - AI 深度反思")
    print("=" * 40)

    # 获取昨天日期
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    print(f"📅 反思日期: {date_str}")

    # 1. 收集当日工作上下文
    print("📂 收集工作上下文...")
    context = collect_daily_context(date_str)
    print(f"  交互记录: {len(context['interactions'])} 条")
    print(f"  错误记录: {len(context['errors'])} 条")
    print(f"  项目记录: {len(context['projects'])} 条")

    if not context["daily_log"]:
        print("⚠️ 当日无工作日志，跳过反思")
        return

    # 2. 加载历史反思（去重用）
    print("📋 加载历史反思...")
    recent_reflections = load_recent_reflections(7)
    existing_lessons = load_lessons()

    # 3. AI 生成深度反思
    print("🤖 AI 深度反思生成中...")
    reflection_text = generate_reflection(context, recent_reflections, existing_lessons)

    if not reflection_text:
        print("⚠️ AI 反思生成失败")
        return

    # 检查是否无反思点
    if "无特殊反思点" in reflection_text:
        print("  ℹ️ 今日无特殊反思点，跳过")
        return

    print(f"  ✅ 反思生成完成，长度: {len(reflection_text)} 字")

    # 4. 保存反思
    save_reflection(date_str, reflection_text)

    # 5. 提取行动项
    action_items = extract_action_items(reflection_text)

    # 6. 保存行动项到 tracker + todo
    if action_items:
        new_count = save_action_items(date_str, action_items)
        if new_count > 0:
            print(f"  ✅ 已将 {new_count} 个新行动项写入待办系统")
        else:
            print(f"  ℹ️ {len(action_items)} 个行动项已存在，跳过")

    # 7. 检查历史行动项进展
    progress = check_action_progress(date_str, context['daily_log'])
    ai_progress = extract_action_progress(reflection_text)
    if progress or ai_progress:
        print(f"  📊 行动项进展检查: {len(progress)} 项待跟踪")

    # 8. 生成并发送飞书报告
    print("📱 生成飞书报告...")
    report = generate_feishu_report(date_str, reflection_text, action_items)
    send_feishu_message(report)

    print("🎉 反思完成!")


if __name__ == "__main__":
    main()
