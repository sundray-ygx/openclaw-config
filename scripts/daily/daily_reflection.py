#!/usr/bin/env python3
"""
Daily Reflection - 每日反思生成器
基于当日会话历史和记忆文件，生成结构化反思记录
"""

import os
import re
import json
from datetime import datetime, timedelta

REFLECTION_DIR = "/root/reflection"
MEMORY_DIR = "/home/openclaw/.openclaw/workspace/memory"


def extract_lessons_from_memory(date_str):
    """从记忆文件提取教训"""
    lessons = []
    memory_file = os.path.join(MEMORY_DIR, f"{date_str}.md")
    
    if not os.path.exists(memory_file):
        return lessons
    
    with open(memory_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 提取复盘与改进部分
    reflection_match = re.search(r'## 🔄 复盘与改进\s*\n\s*\*\*做得好的：\*\*\s*\n(.*?)(?=\n\*\*需改进：\*\*|\n## |\Z)', content, re.DOTALL)
    improve_match = re.search(r'\*\*需改进：\*\*\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    
    if reflection_match:
        good_text = reflection_match.group(1).strip()
        for line in good_text.split('\n'):
            line = line.strip()
            if line and line.startswith('•'):
                lessons.append({
                    "type": "good",
                    "content": line[1:].strip(),
                    "category": "process"
                })
    
    if improve_match:
        improve_text = improve_match.group(1).strip()
        for line in improve_text.split('\n'):
            line = line.strip()
            if line and line.startswith('•'):
                lessons.append({
                    "type": "improve",
                    "content": line[1:].strip(),
                    "category": "process"
                })
    
    return lessons


def analyze_session_history(date_str):
    """分析会话历史，提取潜在教训"""
    # 这里可以接入实际的会话历史分析
    # 目前返回空，作为扩展点
    return []


def categorize_lesson(content):
    """自动分类教训"""
    tech_kw = ["technical", "code", "script", "api", "error", "timeout", "配置", 
               "安装", "部署", "环境", "python", "docker", "git", "数据库", "脚本"]
    work_kw = ["communication", "process", "scope", "assumptions", "沟通", 
               "流程", "计划", "对齐", "会议", "文档", "管理", "复盘"]
    
    content_lower = content.lower()
    
    if any(k in content_lower for k in tech_kw):
        return "technical"
    elif any(k in content_lower for k in work_kw):
        return "process"
    else:
        return "assumptions"


def determine_level(content):
    """确定教训级别"""
    p0_kw = ["致命", "严重", "崩溃", "无法", "阻断", "全部失败", "数据丢失", "重大"]
    p1_kw = ["重要", "影响", "延迟", "错误", "失败", "问题"]
    
    if any(k in content for k in p0_kw):
        return "P0致命"
    elif any(k in content for k in p1_kw):
        return "P1严重"
    return "P2一般"


def generate_structured_reflection(lesson, date_str):
    """生成结构化反思记录"""
    category = categorize_lesson(lesson["content"])
    level = determine_level(lesson["content"])
    
    # 基于内容自动生成根因和解决方案
    content = lesson["content"]
    
    # 简单规则：如果是"做得好的"，根因是"正确执行"，解决方案是"继续保持"
    # 如果是"需改进"，根因是"未充分准备/考虑"，解决方案是"建立检查清单"
    if lesson["type"] == "good":
        root = "正确执行，流程清晰"
        fix = "继续保持，沉淀为最佳实践"
    else:
        root = "未充分准备，考虑不周全"
        fix = "建立检查清单，增加预检查环节"
    
    # 更智能的根因分析
    if "时间" in content or "周期" in content:
        root = "时间定义不明确，缺乏标准化"
        fix = "明确时间范围定义，使用标准格式（如 00:00-23:59）"
    elif "数据" in content or "记录" in content:
        root = "缺乏历史数据积累"
        fix = "建立持续记录机制，定期归档整理"
    elif "配置" in content or "设置" in content:
        root = "配置项未明确文档化"
        fix = "建立配置检查清单，文档化关键配置"
    elif "沟通" in content or "对齐" in content:
        root = "沟通不充分，信息未同步"
        fix = "建立沟通规范，增加确认环节"
    
    return {
        "date": date_str,
        "category": category,
        "level": level,
        "miss": content,
        "root": root,
        "fix": fix
    }


def append_to_reflections(reflection):
    """追加到 reflections.md"""
    filepath = os.path.join(REFLECTION_DIR, "reflections.md")
    
    entry = f"""## {reflection['date']} | {reflection['category']}
**Miss:** {reflection['miss']}
**Root:** {reflection['root']}
**Fix:** {reflection['fix']}

---

"""
    
    # 读取现有内容
    existing = ""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = f.read()
    
    # 在标题后插入新记录
    if "# Reflections Log" in existing:
        parts = existing.split("# Reflections Log", 1)
        new_content = parts[0] + "# Reflections Log\n\n> Most recent first. Archive monthly to `archive/YYYY-MM.md`.\n\n---\n\n" + entry + parts[1].split("\n---\n", 1)[-1]
    else:
        new_content = f"""# Reflections Log

> Most recent first. Archive monthly to `archive/YYYY-MM.md`.

---

{entry}"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)


def update_memory_stats():
    """更新 memory.md 统计"""
    memory_file = os.path.join(REFLECTION_DIR, "memory.md")
    
    if not os.path.exists(memory_file):
        return
    
    with open(memory_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 更新最后反思时间
    today = datetime.now().strftime('%Y-%m-%d')
    next_day = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    content = re.sub(r'- Last reflection: .*', f'- Last reflection: {today}', content)
    content = re.sub(r'- Next scheduled: .*', f'- Next scheduled: {next_day} 04:00 CST', content)
    
    # 增加总反思数
    total_match = re.search(r'- Total reflections: (\d+)', content)
    if total_match:
        current_total = int(total_match.group(1))
        content = re.sub(r'- Total reflections: \d+', f'- Total reflections: {current_total + 1}', content)
    
    with open(memory_file, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    print("🚀 开始生成每日反思...")
    
    # 获取昨天日期
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    
    print(f"📅 分析日期: {date_str}")
    
    # 从记忆文件提取教训
    lessons = extract_lessons_from_memory(date_str)
    print(f"✅ 从记忆文件提取 {len(lessons)} 条教训")
    
    # 分析会话历史
    session_lessons = analyze_session_history(date_str)
    lessons.extend(session_lessons)
    
    if not lessons:
        print("⚠️ 未找到可记录的教训")
        return
    
    # 生成结构化反思
    for lesson in lessons:
        if lesson["type"] == "improve":  # 只记录需要改进的
            reflection = generate_structured_reflection(lesson, date_str)
            print(f"📝 生成反思: {reflection['miss'][:30]}...")
            
            # 追加到 reflections.md
            append_to_reflections(reflection)
            print(f"✅ 已追加到 reflections.md")
    
    # 更新统计
    update_memory_stats()
    print(f"✅ 已更新 memory.md 统计")
    
    print("🎉 完成!")


if __name__ == "__main__":
    main()