#!/usr/bin/env python3
"""
Monthly Reflection Report - 月反思报告生成器
统计本月教训、类别分布、高频问题 Top 10、生成改进计划
"""

import os
import re
import json
import requests
from datetime import datetime, timedelta
from collections import Counter, defaultdict

REFLECTION_DIR = "/root/.openclaw/workspace/reflection"
ARCHIVE_DIR = "/root/.openclaw/workspace/archive/monthly"
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


def send_feishu(month_name, stats, top_issues, improvements, archive_path):
    token = get_feishu_token()
    if not token:
        return False
    
    # 类别分布
    category_dist = "\n".join([f"• {cat}: {count} 条" for cat, count in stats['by_category'].items()])
    
    # 高频问题 Top 5
    top5_text = "\n".join([f"{i+1}. {issue['title'][:30]}... ({issue['count']}次)" 
                          for i, issue in enumerate(top_issues[:5], 1)])
    
    content = f"""📊 月反思报告 | {month_name}

**📈 本月统计**
• 总反思记录: {stats['total']} 条
• 技术教训: {stats['tech']} 条
• 工作教训: {stats['work']} 条

**📂 类别分布**
{category_dist}

**🔥 高频问题 Top 5**
{top5_text}

**📁 详细报告**
{archive_path}

---
💡 由 OpenClaw Monthly Reflection 自动生成"""
    
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


def is_valid_reflection_entry(reflection):
    """过滤无效的反思记录"""
    miss = reflection.get("miss", "").strip()
    if not miss or len(miss) < 10:
        return False
    code_patterns = [r'^#!/', r'^import\s+', r'^def\s+', r'^class\s+']
    if any(re.search(p, miss) for p in code_patterns):
        return False
    if miss.startswith('error:') or miss.startswith('Error:'):
        return False
    if re.match(r'^\S+\s+\d+\.\d+\.\d+', miss):
        return False
    return True


def load_reflections():
    """加载所有反思记录（带数据质量过滤）"""
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
        
        reflections.append({
            "date": date,
            "category": category,
            "miss": miss,
            "root": root,
            "fix": fix
        })
    
    # 数据质量过滤
    valid_refs = [r for r in reflections if is_valid_reflection_entry(r)]
    filtered_count = len(reflections) - len(valid_refs)
    if filtered_count > 0:
        print(f"  ⚠️ 过滤 {filtered_count} 条无效记录")
    
    return valid_refs


def categorize_lesson(lesson):
    """判断是技术教训还是工作教训"""
    tech_kw = ["technical", "code", "script", "api", "error", "timeout", "配置", 
               "安装", "部署", "环境", "python", "docker", "git", "数据库"]
    work_kw = ["communication", "process", "scope", "assumptions", "沟通", 
               "流程", "计划", "对齐", "会议", "文档", "管理"]
    
    cat = lesson.get("category", "").lower()
    miss = lesson.get("miss", "").lower()
    
    if any(k in cat or k in miss for k in tech_kw):
        return "tech"
    elif any(k in cat or k in miss for k in work_kw):
        return "work"
    else:
        return "work"  # 默认归类为工作


def analyze_monthly_data(reflections, year, month):
    """分析月度数据"""
    # 筛选本月数据
    month_refs = [r for r in reflections if r["date"].startswith(f"{year}-{month:02d}")]
    
    stats = {
        "total": len(month_refs),
        "tech": 0,
        "work": 0,
        "by_category": Counter(),
        "by_week": defaultdict(int)
    }
    
    for r in month_refs:
        # 技术/工作分类
        lesson_type = categorize_lesson(r)
        stats[lesson_type] += 1
        
        # 类别分布
        stats["by_category"][r["category"]] += 1
        
        # 按周统计
        date = datetime.strptime(r["date"], "%Y-%m-%d")
        week_num = date.isocalendar()[1]
        stats["by_week"][f"第{week_num}周"] += 1
    
    return month_refs, stats


def extract_top_issues(reflections, top_n=10):
    """提取高频问题 Top N"""
    # 基于问题描述的关键词聚类
    issue_groups = defaultdict(list)
    
    for r in reflections:
        miss = r["miss"]
        # 提取关键词作为分组依据
        keywords = extract_keywords(miss)
        key = " ".join(sorted(keywords[:3]))  # 取前3个关键词排序后作为键
        issue_groups[key].append(r)
    
    # 按出现次数排序
    sorted_issues = sorted(issue_groups.items(), key=lambda x: len(x[1]), reverse=True)
    
    top_issues = []
    for key, group in sorted_issues[:top_n]:
        top_issues.append({
            "title": group[0]["miss"][:50],
            "count": len(group),
            "examples": group[:3],  # 保留前3个示例
            "keywords": key
        })
    
    return top_issues


def extract_keywords(text):
    """提取关键词"""
    # 简单关键词提取：去掉常见词，保留名词性词汇
    stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}
    words = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]+', text)
    return [w for w in words if w not in stop_words and len(w) > 1]


def generate_improvements(stats, top_issues):
    """生成改进计划"""
    improvements = {
        "immediate": [],  # 立即执行
        "this_month": [],  # 本月完成
        "next_month": []  # 下月规划
    }
    
    # 基于高频问题生成改进建议
    if top_issues:
        top_issue = top_issues[0]
        improvements["immediate"].append(f"重点解决高频问题：{top_issue['title'][:30]}...（出现{top_issue['count']}次）")
    
    # 基于类别分布生成建议
    if stats["by_category"].get("technical", 0) > 3:
        improvements["this_month"].append("建立技术问题预防清单，避免重复踩坑")
    
    if stats["by_category"].get("process", 0) > 3:
        improvements["this_month"].append("优化工作流程，减少流程类问题")
    
    if stats["by_category"].get("communication", 0) > 2:
        improvements["this_month"].append("加强沟通规范，确保信息同步到位")
    
    # 基于技术/工作比例生成建议
    if stats["tech"] > stats["work"]:
        improvements["next_month"].append("技术债务清理月，集中解决技术类问题")
    elif stats["work"] > stats["tech"]:
        improvements["next_month"].append("流程优化月，重点改进工作方式")
    
    # 默认建议
    if not improvements["immediate"]:
        improvements["immediate"].append("持续记录每日反思，保持问题敏感度")
    if not improvements["this_month"]:
        improvements["this_month"].append("建立个人知识库，沉淀经验教训")
    if not improvements["next_month"]:
        improvements["next_month"].append("引入自动化工具，减少人为错误")
    
    return improvements


def generate_report(year, month, month_refs, stats, top_issues, improvements):
    """生成月反思报告"""
    month_name = f"{year}年{month}月"
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    content = f"""# 📊 月反思报告 | {month_name}

> 生成时间: {now}
> 数据来源: Self Reflection System
> 数据质量: {stats['total']} 条有效记录

---

## 📈 本月统计

| 指标 | 数值 |
|------|:----:|
| 总反思记录 | {stats['total']} 条 |
| 技术教训 | {stats['tech']} 条 |
| 工作教训 | {stats['work']} 条 |

---

## 📂 类别分布

"""
    
    # 类别分布
    for cat, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
        content += f"- **{cat}**: {count} 条\n"
    
    content += f"""
---

## 📅 按周分布

"""
    
    # 按周分布
    for week, count in sorted(stats['by_week'].items()):
        content += f"- {week}: {count} 条\n"
    
    content += """
---

## 🔥 高频问题 Top 10

"""
    
    # 高频问题
    if top_issues:
        for i, issue in enumerate(top_issues, 1):
            content += f"""### {i}. {issue['title']}

- **出现次数**: {issue['count']} 次
- **关键词**: {issue['keywords']}

"""
    else:
        content += "本月无高频问题记录\n"
    
    content += """
---

## 📋 详细反思记录

"""
    
    # 详细记录
    if month_refs:
        for r in month_refs:
            content += f"""### {r['date']} | {r['category']}

- **问题**: {r['miss']}
- **根因**: {r['root']}
- **解决方案**: {r['fix']}

---

"""
    else:
        content += "本月无反思记录\n"
    
    content += """
---

## 🎯 改进计划

### 立即执行

"""
    for item in improvements['immediate']:
        content += f"- [ ] {item}\n"
    
    content += """
### 本月完成

"""
    for item in improvements['this_month']:
        content += f"- [ ] {item}\n"
    
    content += """
### 下月规划

"""
    for item in improvements['next_month']:
        content += f"- [ ] {item}\n"
    
    content += """
---

## 💡 本月洞察

"""
    
    # 自动生成洞察
    insights = []
    if stats['total'] > 10:
        insights.append(f"本月共记录 {stats['total']} 条反思，反思密度较高，说明对问题的敏感度良好。")
    if stats['tech'] > stats['work']:
        insights.append("技术类问题多于工作类，建议加强技术债务管理。")
    elif stats['work'] > stats['tech']:
        insights.append("工作类问题多于技术类，建议优化工作流程和沟通机制。")
    if top_issues and top_issues[0]['count'] > 2:
        insights.append(f"高频问题'{top_issues[0]['title'][:20]}...'出现 {top_issues[0]['count']} 次，需要重点关注。")
    
    if insights:
        for insight in insights:
            content += f"- {insight}\n"
    else:
        content += "- 本月反思记录较少，建议加强日常问题记录。\n"
    
    content += """
---

*报告由 OpenClaw Monthly Reflection 自动生成*
"""
    
    return content


def main():
    print("🚀 开始生成本月反思报告...")
    
    # 获取本月日期范围
    now = datetime.now()
    year = now.year
    month = now.month
    
    print(f"📅 本月: {year}年{month}月")
    
    # 加载所有反思记录
    all_refs = load_reflections()
    print(f"✅ 加载 {len(all_refs)} 条反思记录")
    
    # 分析本月数据
    month_refs, stats = analyze_monthly_data(all_refs, year, month)
    print(f"✅ 本月反思: {stats['total']} 条")
    print(f"✅ 技术: {stats['tech']} 条, 工作: {stats['work']} 条")
    
    # 提取高频问题
    top_issues = extract_top_issues(month_refs)
    print(f"✅ 高频问题 Top 10 已提取")
    
    # 生成改进计划
    improvements = generate_improvements(stats, top_issues)
    print(f"✅ 改进计划已生成")
    
    # 生成报告
    report = generate_report(year, month, month_refs, stats, top_issues, improvements)
    
    # 保存报告
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    archive_path = os.path.join(ARCHIVE_DIR, f"monthly-reflection-{year}-{month:02d}.md")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 报告已保存: {archive_path}")
    
    # 发送飞书通知
    print("📱 发送飞书通知...")
    month_name = f"{year}年{month}月"
    if send_feishu(month_name, stats, top_issues, improvements, archive_path):
        print("✅ 飞书通知发送成功")
    else:
        print("⚠️ 飞书通知发送失败")
    
    print("🎉 完成!")


if __name__ == "__main__":
    main()