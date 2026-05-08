#!/usr/bin/env python3
"""
Weekly Review V3 - 基于 AI 的深度周复盘

核心改进：
1. 数据源：memory 日志 + Notion 日复盘 + 每日反思 + 项目状态（多维数据源）
2. AI 做真正的周度分析（不是关键词匹配）
3. 跨日模式识别（发现一周内的趋势和关联）
4. 与上周复盘对比（追踪进展）
5. 保留 Notion 集成写入
"""

import os
import re
import json
import urllib.request
import urllib.parse
import sys
from datetime import datetime, timedelta

# 配置
MEMORY_DIR = "/root/.openclaw/workspace/memory"
REFLECTION_DIR = "/root/.openclaw/workspace/reflection"
PROJECTS_FILE = "/root/.openclaw/workspace/memory/projects.md"
LESSONS_FILE = "/root/.openclaw/workspace/memory/lessons.md"
ARCHIVE_WEEKLY_DIR = "/root/.openclaw/workspace/archive/weekly"

NOTION_API_KEY = "ntn_REDACTED"
NOTION_VERSION = "2022-06-28"

FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"

# AI 配置 - 使用 zai/glm-5
import subprocess

AI_MODEL = "zai/glm-5"


def get_ai_response(system_prompt, user_prompt, max_tokens=4000):
    """通过 OpenClaw CLI 调用 zai/glm-5"""
    # 构建完整的 prompt
    full_prompt = f"""{system_prompt}

{user_prompt}"""
    
    try:
        # 使用 openclaw 命令行工具调用 AI
        result = subprocess.run(
            ["openclaw", "ai", "complete", "--model", AI_MODEL, "--max-tokens", str(max_tokens)],
            input=full_prompt,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=180
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            return output
        else:
            print(f"  AI 调用失败: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"  AI 调用超时")
        return None
    except Exception as e:
        print(f"  AI 调用失败: {e}")
        return None


# ========== 数据收集 ==========

def get_week_range(target_date=None):
    """获取本周日期范围（周一到周五）"""
    if target_date is None:
        target_date = datetime.now()
    monday = target_date - timedelta(days=target_date.weekday())
    friday = monday + timedelta(days=4)
    return monday.strftime("%Y-%m-%d"), friday.strftime("%Y-%m-%d")


def get_week_number(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").isocalendar()[1]


def collect_memory_logs(start_date, end_date):
    """收集本周的 memory 日志"""
    logs = {}
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        filepath = os.path.join(MEMORY_DIR, f"{date_str}.md")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            # 只取关键部分，限制长度
            # 提取交互概要和项目部分
            summary_parts = []
            for section in ["日报摘要", "本地交互概要", "飞书交互概要", "PROJECT:", "待跟进"]:
                idx = content.find(section)
                if idx != -1:
                    # 取该 section 后 500 字符
                    summary_parts.append(content[idx:idx+500])

            logs[date_str] = {
                "full": content[:2000],  # 截断避免太长
                "summary": "\n".join(summary_parts)[:1500]
            }
        current += timedelta(days=1)
    return logs


def collect_daily_reflections(start_date, end_date):
    """收集本周的每日反思"""
    reflections = {}
    reflections_file = os.path.join(REFLECTION_DIR, "reflections.md")
    if not os.path.exists(reflections_file):
        return reflections

    with open(reflections_file, "r", encoding="utf-8") as f:
        content = f.read()

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        # 查找该日期的反思
        pattern = rf"## {date_str}\s*\n(.*?)(?=\n---|\n## \d{{4}}|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            reflections[date_str] = match.group(1).strip()[:1000]
        current += timedelta(days=1)

    return reflections


def collect_notion_reviews(start_date, end_date):
    """从 Notion 日复盘数据库读取数据"""
    db_id = os.getenv("NOTION_DAILY_REVIEW_DB_ID", "2bd7772a-4011-8033-b363-e7b41b72dcbd")
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }

    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    filter_data = {
        "and": [
            {"property": "日期", "date": {"on_or_after": start_date}},
            {"property": "日期", "date": {"on_or_before": end_date}}
        ]
    }
    sorts = [{"property": "日期", "direction": "ascending"}]

    req_data = json.dumps({"filter": filter_data, "sorts": sorts}).encode()
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            results = json.loads(response.read().decode()).get("results", [])

        reviews = []
        for page in results:
            props = page.get("properties", {})
            date_val = ""
            if props.get("日期", {}).get("date"):
                date_val = props["日期"]["date"].get("start", "")

            def get_text(field_name):
                field = props.get(field_name, {}).get("rich_text", [])
                return "".join([t.get("text", {}).get("content", "") for t in field])

            review_text = get_text("今日复盘")
            reflection_text = get_text("今日反思")
            plan_text = get_text("今天安排")

            if review_text or reflection_text or plan_text:
                reviews.append({
                    "date": date_val,
                    "review": review_text,
                    "reflection": reflection_text,
                    "plan": plan_text
                })
        return reviews
    except Exception as e:
        print(f"  Notion 读取失败: {e}")
        return []


def load_last_week_review():
    """加载上周复盘（用于对比进展）"""
    # 查找最近的周复盘归档文件
    if not os.path.exists(ARCHIVE_WEEKLY_DIR):
        return ""

    files = sorted([f for f in os.listdir(ARCHIVE_WEEKLY_DIR) if f.endswith('.md')], reverse=True)
    if not files:
        return ""

    # 取最近的（可能是本周或上周）
    filepath = os.path.join(ARCHIVE_WEEKLY_DIR, files[0])
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()[:2000]


def load_projects():
    """加载项目状态"""
    if not os.path.exists(PROJECTS_FILE):
        return ""
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        return f.read()[:2000]


# ========== AI 周复盘生成 ==========

def generate_weekly_review(context):
    """AI 生成深度周复盘"""

    system_prompt = """你是一位高管级周复盘分析教练。你的任务是分析一周的工作数据，产出系统性、有洞察力的周复盘报告。

你的分析维度：
1. **进展追踪** — 本周实际完成了什么？与计划对比如何？
2. **模式识别** — 一周内是否有反复出现的问题？是否有被忽视的趋势？
3. **效率分析** — 时间花在哪里？哪些是高价值的？哪些是浪费的？
4. **风险预警** — 有哪些未解决的隐患？哪些可能升级？
5. **战略对齐** — 日常工作是否在推动长期目标？

严格要求：
- **不要泛泛而谈** — 每个分析点必须基于具体数据
- **不要重复 Notion 已有的内容** — 要有增量洞察，不是搬运
- **要有判断** — 哪些做得好、哪些做得不好、为什么、怎么办，要有明确观点
- **要发现隐藏问题** — 不只是表面汇总，要看到数据背后的模式
- **要可执行** — 下周行动计划必须具体到"谁做什么什么时候完成"

输出格式：

## 周复盘报告

### 一、本周概况
（一句话总结本周基调：高效/平淡/混乱/突破？为什么？）

### 二、关键成果与突破
（列出最重要的 2-4 项成果，分析每项的影响力和推进程度）

### 三、进展分析
（与上周计划对比：哪些完成了？哪些延期了？为什么？）
（与长期目标对比：本周的工作是否在推动重要目标？）

### 四、问题与风险
（识别本周遇到的问题，分析根因，评估是否需要升级处理）
（发现潜在风险，提前预警）

### 五、效率与模式分析
（时间都花在哪了？有没有被低价值事务占用？）
（有没有反复出现的模式（好的或坏的）？）

### 六、下周行动计划
（具体、可执行的计划，包含优先级排序）
（不要列太多，3-5 个核心行动项即可）

### 七、核心洞察
（一句话：这周最大的收获或认知是什么？）"""

    # 构建用户 prompt
    memory_logs_text = ""
    for date, log in sorted(context["memory_logs"].items()):
        memory_logs_text += f"\n### {date}\n{log['summary']}\n"

    reflections_text = ""
    for date, ref in sorted(context["reflections"].items()):
        reflections_text += f"\n### {date}\n{ref}\n"

    notion_text = ""
    for review in context["notion_reviews"]:
        notion_text += f"\n### {review['date']}\n"
        if review["review"]:
            notion_text += f"复盘: {review['review']}\n"
        if review["reflection"]:
            notion_text += f"反思: {review['reflection']}\n"
        if review["plan"]:
            notion_text += f"安排: {review['plan']}\n"

    user_prompt = f"""请对第 {context['week_num']} 周（{context['start_date']} 至 {context['end_date']}）进行深度周复盘。

## 一、Memory 工作日志（每日摘要）
{memory_logs_text if memory_logs_text else "无数据"}

## 二、每日反思记录
{reflections_text if reflections_text else "无反思记录"}

## 三、Notion 日复盘
{notion_text if notion_text else "无 Notion 数据"}

## 四、当前项目状态
{context["projects"] if context["projects"] else "无项目记录"}

## 五、上周复盘摘要（用于对比进展）
{context["last_week_review"] if context["last_week_review"] else "无上周复盘"}

---
请生成深度、有判断力的周复盘报告。"""

    return get_ai_response(system_prompt, user_prompt, max_tokens=4000)


# ========== 输出 ==========

def generate_feishu_summary(context, review_text):
    """从 AI 复盘中提取精华生成飞书推送"""
    lines = [
        f"📋 第{context['week_num']}周复盘（{context['start_date']} 至 {context['end_date']}）",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]

    # 提取概况
    overview_match = re.search(r'## 一、本周概况\n+(.*?)(?=\n## )', review_text, re.DOTALL)
    if overview_match:
        lines.append("")
        lines.append(f"📊 {overview_match.group(1).strip()[:100]}")

    # 提取关键成果
    achievements_match = re.search(r'## 二、关键成果与突破\n+(.*?)(?=\n## )', review_text, re.DOTALL)
    if achievements_match:
        lines.append("")
        lines.append("🎯 关键成果")
        achievements_text = achievements_match.group(1).strip()
        for line in achievements_text.split('\n'):
            line = line.strip().lstrip('- ').lstrip('• ')
            if line and not line.startswith('#') and len(line) > 5:
                lines.append(f"• {line[:80]}")

    # 提取问题与风险
    risks_match = re.search(r'## 四、问题与风险\n+(.*?)(?=\n## )', review_text, re.DOTALL)
    if risks_match:
        lines.append("")
        lines.append("⚠️ 问题与风险")
        risks_text = risks_match.group(1).strip()
        risk_lines = [l.strip().lstrip('- ').lstrip('• ') for l in risks_text.split('\n')
                      if l.strip() and not l.strip().startswith('#') and len(l.strip()) > 5]
        for rl in risk_lines[:3]:
            lines.append(f"• {rl[:80]}")

    # 提取下周行动
    actions_match = re.search(r'## 六、下周行动计划\n+(.*?)(?=\n## |\Z)', review_text, re.DOTALL)
    if actions_match:
        lines.append("")
        lines.append("📌 下周行动")
        actions_text = actions_match.group(1).strip()
        action_lines = [l.strip().lstrip('- ').lstrip('• ') for l in actions_text.split('\n')
                        if l.strip() and not l.strip().startswith('#') and len(l.strip()) > 5]
        for al in action_lines[:5]:
            lines.append(f"• {al[:80]}")

    # 核心洞察
    insight_match = re.search(r'## 七、核心洞察\n+(.*?)(?=\Z)', review_text, re.DOTALL)
    if insight_match:
        lines.append("")
        lines.append(f"💡 {insight_match.group(1).strip()[:100]}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


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


def send_feishu_message(text):
    token = get_feishu_token()
    if not token:
        return False

    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    message_data = json.dumps({
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }).encode()
    req = urllib.request.Request(full_url, data=message_data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("code") == 0
    except Exception as e:
        print(f"  飞书发送失败: {e}")
        return False


def update_notion_weekly(start_date, review_text):
    """更新 Notion 周复盘页面"""
    db_id = os.getenv("NOTION_WEEKLY_REVIEW_DB_ID", "345f5210-acd8-4c1a-8d69-27a55263e4e7")
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }

    # 查找本周页面
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    filter_data = {"property": "开始日期", "date": {"equals": start_date}}
    req_data = json.dumps({"filter": filter_data}).encode()
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            results = json.loads(response.read().decode()).get("results", [])
    except Exception as e:
        print(f"  Notion 查询失败: {e}")
        return None

    if not results:
        print("  ⚠️ 未找到 Notion 周复盘页面")
        return None

    page_id = results[0]["id"]

    # 更新周复盘字段（截断到 Notion 限制 2000 字符）
    review_truncated = review_text[:1900]
    properties = {
        "周复盘": {
            "rich_text": [{"type": "text", "text": {"content": review_truncated}}]
        }
    }
    update_url = f"https://api.notion.com/v1/pages/{page_id}"
    update_data = json.dumps({"properties": properties}).encode()
    req = urllib.request.Request(update_url, data=update_data, headers=headers, method="PATCH")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            print(f"  ✅ Notion 周复盘已更新")
            return page_id
    except Exception as e:
        print(f"  Notion 更新失败: {e}")
        return None


def archive_weekly_review(context, review_text):
    """归档到本地"""
    os.makedirs(ARCHIVE_WEEKLY_DIR, exist_ok=True)
    filepath = os.path.join(ARCHIVE_WEEKLY_DIR,
                            f"weekly_review_{context['start_date']}_{context['end_date']}.md")

    content = f"""# 📋 第{context['week_num']}周复盘报告（{context['start_date']} 至 {context['end_date']}）

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 数据源: memory日志 + Notion日复盘 + 每日反思
> 方法: AI 深度分析

---

{review_text}

---

*报告由 Weekly Review V3 自动生成*
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ 归档完成: {filepath}")
    return filepath


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", help="指定日期（格式: 2026-04-20），默认本周")
    args = parser.parse_args()

    target_date = None
    if args.week:
        target_date = datetime.strptime(args.week, "%Y-%m-%d")

    print("📋 周复盘 V3 - AI 深度分析")
    print("=" * 40)

    # 1. 确定日期范围
    start_date, end_date = get_week_range(target_date)
    week_num = get_week_number(start_date)
    print(f"📅 本周: {start_date} 至 {end_date}（第{week_num}周）")

    # 2. 收集数据
    print("📂 收集数据...")
    memory_logs = collect_memory_logs(start_date, end_date)
    print(f"  Memory 日志: {len(memory_logs)} 天")

    reflections = collect_daily_reflections(start_date, end_date)
    print(f"  每日反思: {len(reflections)} 天")

    notion_reviews = collect_notion_reviews(start_date, end_date)
    print(f"  Notion 日复盘: {len(notion_reviews)} 条")

    last_week = load_last_week_review()
    projects = load_projects()

    # 3. 构建 context
    context = {
        "week_num": week_num,
        "start_date": start_date,
        "end_date": end_date,
        "memory_logs": memory_logs,
        "reflections": reflections,
        "notion_reviews": notion_reviews,
        "last_week_review": last_week,
        "projects": projects,
    }

    # 4. AI 生成周复盘
    print("🤖 AI 深度分析中...")
    review_text = generate_weekly_review(context)

    if not review_text:
        print("⚠️ AI 分析失败")
        sys.exit(1)

    print(f"  ✅ 分析完成，长度: {len(review_text)} 字")

    # 5. 归档
    archive_weekly_review(context, review_text)

    # 6. 更新 Notion
    print("📝 更新 Notion...")
    notion_page_id = update_notion_weekly(start_date, review_text)

    # 7. 发送飞书摘要
    print("📱 发送飞书摘要...")
    feishu_summary = generate_feishu_summary(context, review_text)
    if send_feishu_message(feishu_summary):
        print("  ✅ 飞书摘要已发送")
    else:
        print("  ⚠️ 飞书发送失败")

    print("🎉 周复盘完成!")


if __name__ == "__main__":
    main()
