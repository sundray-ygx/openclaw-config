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

### 关键洞察
（一句话总结今天的核心收获）"""

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

---
请基于以上信息，生成深度、具体、不重复的反思报告。如果今天确实是平淡的一天，没有值得反思的点，就直接说"今日无特殊反思点"。不要为了反思而反思。"""

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
    """从反思中提取行动项"""
    action_items = []
    in_action_section = False

    for line in reflection_text.split('\n'):
        if '本日行动项' in line or '行动项' in line:
            in_action_section = True
            continue
        if in_action_section:
            if line.startswith('###') or line.startswith('## '):
                break
            if line.strip().startswith('-') or line.strip().startswith('1') or line.strip().startswith('2') or line.strip().startswith('3'):
                clean = re.sub(r'^[-\d.]\s*', '', line.strip())
                if clean and len(clean) > 5:
                    action_items.append(clean)

    return action_items[:3]


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
            lines.append(f"{i}. {item}")

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

    # 6. 生成并发送飞书报告
    print("📱 生成飞书报告...")
    report = generate_feishu_report(date_str, reflection_text, action_items)
    send_feishu_message(report)

    print("🎉 反思完成!")


if __name__ == "__main__":
    main()
