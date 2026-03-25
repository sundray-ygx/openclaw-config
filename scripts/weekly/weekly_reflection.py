#!/usr/bin/env python3
"""
Weekly Reflection Report - 周反思报告生成器
汇总本周每日反思，提取核心教训，生成周报
"""

import os
import re
import json
import requests
from datetime import datetime, timedelta

REFLECTION_DIR = "/root/.openclaw/workspace/reflection"
ARCHIVE_DIR = "/root/.openclaw/workspace/archive/weekly"
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "cli_a93b96047e7a5bc3")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD")
FEISHU_USER_ID = os.getenv("FEISHU_USER_ID", "ou_c2cde251e01a87fc09ba7561f76d8606")


def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET})
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        return response.json().get("tenant_access_token")
    except:
        return None


def send_feishu(week_num, start_date, end_date, stats, archive_path):
    token = get_feishu_token()
    if not token:
        return False
    
    content = f"""📋 周反思报告 | 第{week_num}周 ({start_date} ~ {end_date})

**📊 本周统计**
• 新增反思: {stats['total']} 条
• 技术教训: {stats['tech']} 条
• 工作教训: {stats['work']} 条

**📁 详细报告**
{archive_path}

---
💡 由 OpenClaw Weekly Reflection 自动生成"""
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    message = {
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(url, headers=headers, json=message, params=params, timeout=10)
        return response.json().get("code") == 0
    except:
        return False


def load_reflections():
    reflections = []
    filepath = os.path.join(REFLECTION_DIR, "reflections.md")
    if not os.path.exists(filepath):
        return reflections
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    entries = re.split(r"\n---\n", content)
    for entry in entries:
        lines = entry.strip().split("\n")
        if len(lines) < 3:
            continue
        
        header = re.match(r"##\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+)", lines[0])
        if not header:
            continue
        
        date = header.group(1)
        category = header.group(2).strip()
        miss = root = fix = ""
        
        for line in lines[1:]:
            if line.startswith("**Miss:**"):
                miss = line[9:].strip()
            elif line.startswith("**Root:**"):
                root = line[9:].strip()
            elif line.startswith("**Fix:**"):
                fix = line[8:].strip()
        
        reflections.append({"date": date, "category": category, "miss": miss, "root": root, "fix": fix})
    
    return reflections


def categorize(week_refs):
    tech = []
    work = []
    tech_kw = ["technical", "code", "script", "api", "error", "timeout", "配置", "安装", "部署", "环境"]
    work_kw = ["communication", "process", "scope", "assumptions", "沟通", "流程", "计划", "对齐"]
    
    for r in week_refs:
        cat = r.get("category", "").lower()
        miss = r.get("miss", "")
        if any(k in cat or k in miss.lower() for k in tech_kw):
            tech.append(r)
        elif any(k in cat or k in miss.lower() for k in work_kw):
            work.append(r)
        else:
            work.append(r)
    
    return tech, work


def generate_report(week_num, start_date, end_date, week_refs, tech, work):
    content = f"""# 📋 周反思报告 | 第{week_num}周 ({start_date} ~ {end_date})

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 数据来源: Self Reflection System

---

## 📊 本周统计

| 指标 | 数值 |
|------|------|
| 新增反思记录 | {len(week_refs)} 条 |
| 技术教训 | {len(tech)} 条 |
| 工作教训 | {len(work)} 条 |

---

## 🔧 技术教训

"""
    
    if tech:
        for i, r in enumerate(tech, 1):
            content += f"### {i}. {r['miss'][:50]}\n\n"
            content += f"- **类别**: {r['category']}\n"
            content += f"- **日期**: {r['date']}\n"
            content += f"- **根因**: {r['root']}\n"
            content += f"- **解决方案**: {r['fix']}\n\n"
    else:
        content += "本周无技术教训记录\n\n"
    
    content += """---

## 💼 工作教训

"""
    
    if work:
        for i, r in enumerate(work, 1):
            content += f"### {i}. {r['miss'][:50]}\n\n"
            content += f"- **类别**: {r['category']}\n"
            content += f"- **日期**: {r['date']}\n"
            content += f"- **根因**: {r['root']}\n"
            content += f"- **解决方案**: {r['fix']}\n\n"
    else:
        content += "本周无工作教训记录\n\n"
    
    content += "---\n\n*报告由 OpenClaw Weekly Reflection 自动生成*\n"
    return content


def main():
    print("🚀 开始生成周反思报告...")
    
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    start_date = monday.strftime("%Y-%m-%d")
    end_date = sunday.strftime("%Y-%m-%d")
    week_num = now.isocalendar()[1]
    
    print(f"📅 本周: {start_date} ~ {end_date} (第{week_num}周)")
    
    all_refs = load_reflections()
    print(f"✅ 加载 {len(all_refs)} 条反思记录")
    
    week_refs = [r for r in all_refs if start_date <= r['date'] <= end_date]
    print(f"✅ 本周反思: {len(week_refs)} 条")
    
    tech, work = categorize(week_refs)
    print(f"✅ 技术: {len(tech)} 条, 工作: {len(work)} 条")
    
    report = generate_report(week_num, start_date, end_date, week_refs, tech, work)
    
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    archive_path = os.path.join(ARCHIVE_DIR, f"weekly-reflection-{start_date}.md")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 报告已保存: {archive_path}")
    
    print("📱 发送飞书通知...")
    stats = {"total": len(week_refs), "tech": len(tech), "work": len(work)}
    if send_feishu(week_num, start_date, end_date, stats, archive_path):
        print("✅ 飞书通知发送成功")
    else:
        print("⚠️ 飞书通知发送失败")
    
    print("🎉 完成!")


if __name__ == "__main__":
    main()
