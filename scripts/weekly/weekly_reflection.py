#!/usr/bin/env python3
"""
Weekly Reflection V2 - 基于 AI 的深度周反思生成器

核心改进：
1. 不再依赖固定格式的反思文件（V2格式），直接从memory日志提取
2. 兼容V3反思格式（深度反思内容）
3. 用AI生成有实质内容的周度复盘
4. 采用GRAI复盘法
"""

import os
import re
import json
import subprocess
from datetime import datetime, timedelta

MEMORY_DIR = "/root/.openclaw/workspace/memory"
REFLECTION_FILE = "/root/.openclaw/workspace/reflection/reflections.md"
ARCHIVE_DIR = "/root/.openclaw/workspace/archive/weekly"
LESSONS_FILE = "/root/.openclaw/workspace/memory/lessons.md"

FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"

AI_MODEL = "glm-5"
ZAI_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"


def _load_zai_key():
    try:
        with open('/root/.openclaw/agents/main/agent/auth-profiles.json', 'r') as f:
            profiles = json.load(f)
        return profiles['profiles']['zai:default']['key']
    except Exception:
        return ""


ZAI_API_KEY = _load_zai_key()


def get_ai_response(system_prompt, user_prompt, max_tokens=3000):
    """通过 zai OpenAI 兼容接口调用 glm-5"""
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
            [
                "curl", "-s", "-X", "POST",
                f"{ZAI_BASE_URL}/chat/completions",
                "-H", f"Authorization: Bearer {ZAI_API_KEY}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(data, ensure_ascii=False)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=180
        )

        if result.returncode == 0:
            response = json.loads(result.stdout)
            message = response.get('choices', [{}])[0].get('message', {})
            content = message.get('content', '') or message.get('reasoning_content', '')
            return content.strip() if content else None
        else:
            print(f"  AI 调用失败: {result.stderr[:200]}")
            return None
    except subprocess.TimeoutExpired:
        print(f"  AI 调用超时")
        return None
    except Exception as e:
        print(f"  AI 调用失败: {e}")
        return None


def collect_week_data(start_date, end_date):
    """收集本周所有原始数据"""
    week_data = {}

    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        day_info = {
            "date": date_str,
            "memory_log": "",
            "daily_report_summary": "",
            "reflection": "",
            "key_interactions": [],
            "errors_count": 0,
            "local_interactions": 0,
            "feishu_interactions": 0,
        }

        # 1. 读取 memory 日志
        memory_file = os.path.join(MEMORY_DIR, f"{date_str}.md")
        if os.path.exists(memory_file):
            with open(memory_file, "r", encoding="utf-8") as f:
                day_info["memory_log"] = f.read()

            # 提取关键指标
            log = day_info["memory_log"]
            m = re.search(r"本地交互['\":：\s]*(\d+)", log)
            if m:
                day_info["local_interactions"] = int(m.group(1))
            m = re.search(r"飞书交互['\":：\s]*(\d+)", log)
            if m:
                day_info["feishu_interactions"] = int(m.group(1))
            m = re.search(r"错误/异常['\":：\s]*(\d+)", log)
            if m:
                day_info["errors_count"] = int(m.group(1))

            # 提取关键交互（去掉系统噪音）
            for line in log.split('\n'):
                # 飞书交互
                m = re.match(r'\d+\.\s*\*\*(\d{2}:\d{2})\*\*\s*(.+)', line)
                if m and len(m.group(2)) > 15 and 'HEARTBEAT' not in m.group(2):
                    day_info["key_interactions"].append(f"[飞书 {m.group(1)}] {m.group(2)[:150]}")

                # 本地交互（有实际内容的）
                m = re.match(r'\d+\.\s*\*\*\d{2}:\d{2}\*\*\s*\[.*?GMT\+8\]\s*(.+)', line)
                if m and len(m.group(1)) > 15:
                    content = m.group(1)[:150]
                    if 'HEARTBEAT' not in content and 'Read HEARTBEAT' not in content:
                        day_info["key_interactions"].append(f"[本地] {content}")

        # 2. 提取该日的V3反思（兼容新格式）
        if os.path.exists(REFLECTION_FILE):
            with open(REFLECTION_FILE, "r", encoding="utf-8") as f:
                ref_content = f.read()

            # V3格式：## 2026-05-16\n\n## 反思报告\n...（直到下一个日期标题）
            pattern = rf"## {date_str}\s*\n\n(.*?)(?=\n## 20|\Z)"
            m = re.search(pattern, ref_content, re.DOTALL)
            if m:
                reflection_text = m.group(1).strip()
                # 去掉AI的思考过程（加粗的分析内容），保留反思结果
                if len(reflection_text) > 50:
                    day_info["reflection"] = reflection_text[:3000]

        if day_info["memory_log"] or day_info["reflection"]:
            week_data[date_str] = day_info

        current += timedelta(days=1)

    return week_data


def build_ai_prompt(week_data, week_num, start_date, end_date):
    """构建AI生成周反思的prompt"""

    # 汇总本周数据
    total_local = sum(d["local_interactions"] for d in week_data.values())
    total_feishu = sum(d["feishu_interactions"] for d in week_data.values())
    total_errors = sum(d["errors_count"] for d in week_data.values())
    active_days = len(week_data)

    all_interactions = []
    all_reflections = []

    for date_str, day in sorted(week_data.items()):
        if day["key_interactions"]:
            all_interactions.append(f"\n### {date_str}")
            for inter in day["key_interactions"][:8]:  # 每天最多8条
                all_interactions.append(f"- {inter}")

        if day["reflection"]:
            all_reflections.append(f"\n### {date_str} 反思")
            # 提取反思中的关键点（不要全部，太长）
            ref = day["reflection"]
            # 取反思报告的关键事件和反思点
            key_events = re.search(r"### 今日关键事件\n(.*?)(?=\n###|\Z)", ref, re.DOTALL)
            if key_events:
                all_reflections.append(key_events.group(1)[:500])
            reflection_points = re.findall(r"#### 反思点[^：：]*[：：]\s*(.+?)(?=\n####|\Z)", ref, re.DOTALL)
            for rp in reflection_points[:3]:
                all_reflections.append(f"- 反思: {rp[:200]}")

    # 读取历史教训作为上下文
    lessons_context = ""
    if os.path.exists(LESSONS_FILE):
        with open(LESSONS_FILE, "r", encoding="utf-8") as f:
            lessons_context = f.read()[:1500]

    system_prompt = """你是一名深度反思分析师，负责为一位数通网络企业的研发管理人员生成周度复盘报告。

你的报告必须：
1. 有实质内容——每句话都要对应具体事件，不要空话
2. 采用GRAI复盘法（Goal-Result-Analysis-Insight）
3. 从事件中提炼可复用的经验教训
4. 指出做得好的和做得不好的，有理有据
5. 给出下周的具体建议

不要：
- 说"本周系统稳定运行"这种废话
- 用"需要改进"、"有待提升"这类模糊词汇
- 编造不存在的事件

输出格式：Markdown，包含标题、GRAI四个板块、下周建议。"""

    user_prompt = f"""## 第{week_num}周数据 ({start_date} ~ {end_date})

### 本周统计
- 活跃天数: {active_days}
- 本地交互: {total_local}次
- 飞书交互: {total_feishu}次
- 错误/异常: {total_errors}条

### 本周关键交互
{"".join(all_interactions)}

### 本周每日反思摘要
{"".join(all_reflections)}

### 已知历史教训（避免重复）
{lessons_context}

---

请基于以上数据，生成第{week_num}周的深度复盘报告。重点关注：
1. 本周完成了什么实质性工作？
2. 遇到了什么问题？根因是什么？
3. 有什么值得沉淀的经验？
4. 下周应该关注什么？"""

    return system_prompt, user_prompt


def send_feishu_card(week_num, start_date, end_date, report_content):
    """发送飞书卡片"""
    import urllib.request

    # 获取token
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    token_data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(token_url, data=token_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            token = json.loads(resp.read()).get("tenant_access_token")
    except Exception as e:
        print(f"  获取飞书token失败: {e}")
        return False

    # 截取摘要（飞书卡片不能太长）
    # 提取关键统计和前几个板块
    summary_lines = []
    in_section = False
    section_count = 0
    for line in report_content.split('\n'):
        if line.startswith('#'):
            summary_lines.append(line)
        elif line.startswith('## ') or line.startswith('### '):
            section_count += 1
            if section_count > 6:
                break
            summary_lines.append(line)
            in_section = True
        elif in_section and line.strip():
            summary_lines.append(line[:200])

    summary = '\n'.join(summary_lines[:80])

    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📋 周反思报告 | 第{week_num}周 ({start_date} ~ {end_date})"},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "markdown",
                "content": summary[:4000]
            }
        ]
    }

    send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    message = {
        "receive_id": FEISHU_USER_ID,
        "msg_type": "interactive",
        "content": json.dumps(card_content, ensure_ascii=False)
    }

    req = urllib.request.Request(
        send_url,
        data=json.dumps(message, ensure_ascii=False).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("code") == 0
    except Exception as e:
        print(f"  发送飞书失败: {e}")
        return False


def main():
    print("🚀 开始生成周反思报告 V2...")

    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    start_date = monday.strftime("%Y-%m-%d")
    end_date = sunday.strftime("%Y-%m-%d")
    week_num = now.isocalendar()[1]

    print(f"📅 本周: {start_date} ~ {end_date} (第{week_num}周)")

    # 1. 收集数据
    print("📊 收集本周数据...")
    week_data = collect_week_data(start_date, end_date)
    print(f"  活跃天数: {len(week_data)}")

    if not week_data:
        print("⚠️ 本周无数据，跳过")
        return

    # 2. 构建AI prompt
    print("🤖 构建AI分析...")
    system_prompt, user_prompt = build_ai_prompt(week_data, week_num, start_date, end_date)

    # 3. 调用AI生成报告
    print("🤖 调用AI生成深度反思...")
    report = get_ai_response(system_prompt, user_prompt, max_tokens=3000)

    if not report:
        print("⚠️ AI生成失败，使用模板报告")
        report = f"# 周反思报告 | 第{week_num}周\n\nAI生成失败，请手动查看本周数据。\n\n"
        report += f"活跃天数: {len(week_data)}\n"
        for date_str, day in sorted(week_data.items()):
            report += f"\n## {date_str}\n"
            report += f"- 本地交互: {day['local_interactions']}, 飞书: {day['feishu_interactions']}, 错误: {day['errors_count']}\n"
            for inter in day['key_interactions'][:5]:
                report += f"- {inter}\n"

    # 4. 添加元信息
    full_report = f"""# 📋 周反思报告 | 第{week_num}周 ({start_date} ~ {end_date})

> 生成时间: {now.strftime('%Y-%m-%d %H:%M')}
> 数据来源: Memory日志 + V3深度反思
> 方法论: GRAI复盘法

---

{report}

---

*报告由 OpenClaw Weekly Reflection V2 生成*
"""

    # 5. 保存
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    archive_path = os.path.join(ARCHIVE_DIR, f"weekly-reflection-{start_date}.md")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(full_report)
    print(f"✅ 报告已保存: {archive_path}")

    # 6. 发送飞书
    print("📱 发送飞书卡片...")
    if send_feishu_card(week_num, start_date, end_date, report):
        print("✅ 飞书卡片发送成功")
    else:
        print("⚠️ 飞书卡片发送失败")

    print("🎉 完成!")


if __name__ == "__main__":
    main()
