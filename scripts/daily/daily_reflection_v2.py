#!/usr/bin/env python3
"""
Daily Reflection V2 - 每日反思生成器（改进版）
基于当日会话历史和记忆文件，生成结构化、具体的反思报告

改进点：
1. 从空洞→具体：提取具体场景、数据、影响
2. 增加关联经验：提炼可复用的方法论
3. 结构化呈现：数据概览、做得好的、需改进、关联经验
"""

import os
import re
import json
import urllib.request
from datetime import datetime, timedelta
from collections import Counter

REFLECTION_DIR = "/root/.openclaw/workspace/reflection"
MEMORY_DIR = "/root/.openclaw/workspace/memory"
FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"


def extract_lessons_from_memory(date_str):
    """从记忆文件提取教训 - 改进版：提取具体内容而非套话"""
    lessons = []
    memory_file = os.path.join(MEMORY_DIR, f"{date_str}.md")
    
    if not os.path.exists(memory_file):
        return lessons
    
    with open(memory_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 提取复盘与改进部分 - 改进：提取完整上下文
    # 支持多种格式："做得好的：" 或 "做得好的："
    reflection_match = re.search(r'## 🔄 复盘与改进\s*\n.*?\*\*做得好的：?\*\*\s*\n(.*?)(?=\n\*\*需改进：?\*\*|\n## |\Z)', content, re.DOTALL)
    improve_match = re.search(r'\*\*需改进的?：?\*\*\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    
    if reflection_match:
        good_text = reflection_match.group(1).strip()
        for line in good_text.split('\n'):
            line = line.strip()
            if line and (line.startswith('•') or line.startswith('-')):
                lesson_content = line[1:].strip()
                # 过滤掉空洞的描述
                if not is_vague(lesson_content):
                    lessons.append({
                        "type": "good",
                        "content": lesson_content,
                        "category": categorize_lesson(lesson_content),
                        "context": extract_context(content, lesson_content)
                    })
    
    if improve_match:
        improve_text = improve_match.group(1).strip()
        for line in improve_text.split('\n'):
            line = line.strip()
            if line and (line.startswith('•') or line.startswith('-')):
                lesson_content = line[1:].strip()
                if not is_vague(lesson_content):
                    lessons.append({
                        "type": "improve",
                        "content": lesson_content,
                        "category": categorize_lesson(lesson_content),
                        "context": extract_context(content, lesson_content)
                    })
    
    # 如果没有找到复盘记录，从待跟进事项提取
    if not lessons:
        todo_match = re.search(r'## 待跟进事项\s*\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
        if todo_match:
            todo_text = todo_match.group(1).strip()
            for line in todo_text.split('\n'):
                line = line.strip()
                if line and line.startswith('- ['):
                    # 提取复选框内容
                    task_content = re.sub(r'^-\s*\[.\]\s*', '', line).strip()
                    if task_content and not is_vague(task_content):
                        lessons.append({
                            "type": "improve",
                            "content": task_content,
                            "category": categorize_lesson(task_content),
                            "context": "待跟进任务"
                        })
    
    # 从错误/异常部分提取具体错误
    errors_match = re.search(r'## ⚠️ 错误与异常\s*\n\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if errors_match:
        errors_text = errors_match.group(1).strip()
        error_lines = [line.strip() for line in errors_text.split('\n') if line.strip().startswith('-')]
        for line in error_lines[:3]:
            # 提取具体错误信息
            clean_error = re.sub(r'^-\s*[💻📱]\s*\*\*[^*]+\*\*\s*', '', line).strip()
            # 过滤掉代码块和过长的内容
            if clean_error and len(clean_error) > 10 and len(clean_error) < 200 and not is_vague(clean_error):
                # 检查是否是代码片段（以 #!/ 或 import 或 def 开头）
                if not any(clean_error.startswith(prefix) for prefix in ['#!/', 'import ', 'def ', '"""', 'class ']):
                    lessons.append({
                        "type": "improve",
                        "content": clean_error[:150],
                        "category": "technical",
                        "context": "系统错误日志"
                    })
    
    return lessons


def is_vague(content):
    """判断内容是否空洞或不是有效教训"""
    # 过滤空内容
    if not content or len(content.strip()) < 5:
        return True
    
    # 过滤代码片段
    code_patterns = ['#!/', 'import ', 'def ', 'class ', '"""', "'''", '{\n', '[\n']
    if any(content.startswith(p) for p in code_patterns):
        return True
    
    # 过滤日志/文件内容
    if content.startswith('💻') or content.startswith('📱') or content.startswith('# '):
        return True
    
    # 过滤JSON内容
    if content.startswith('{') and ('"status"' in content or '"tool"' in content):
        return True
    
    # 过滤空洞描述
    vague_patterns = [
        r'^未充分准备',
        r'^考虑不周全',
        r'^需要改进$',
        r'^有待提高',
        r'^不够完善',
        r'^可以更好',
        r'^系统稳定运行',
        r'^所有定时任务',
        r'^[\s\n]*$'  # 空内容
    ]
    for pattern in vague_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    return False


def extract_context(full_content, lesson_content):
    """提取教训的上下文信息"""
    # 查找包含该教训的段落
    paragraphs = full_content.split('\n\n')
    for para in paragraphs:
        if lesson_content in para or any(word in para for word in lesson_content.split()[:3]):
            # 返回该段落的前200字符作为上下文
            return para[:200].replace('\n', ' ')
    return ""


def categorize_lesson(content):
    """自动分类教训"""
    tech_kw = ["technical", "code", "script", "api", "error", "timeout", "配置", 
               "安装", "部署", "环境", "python", "docker", "git", "数据库", "脚本",
               "路径", "目录", "文件", "权限", "token", "认证", "网络", "服务器"]
    work_kw = ["communication", "process", "scope", "assumptions", "沟通", 
               "流程", "计划", "对齐", "会议", "文档", "管理", "复盘", "协作"]
    data_kw = ["数据", "记录", "归档", "备份", "统计", "分析", "日志", "监控"]
    
    content_lower = content.lower()
    
    if any(k in content_lower for k in tech_kw):
        return "technical"
    elif any(k in content_lower for k in data_kw):
        return "data"
    elif any(k in content_lower for k in work_kw):
        return "process"
    else:
        return "assumptions"


def determine_level(content):
    """确定教训级别"""
    p0_kw = ["致命", "严重", "崩溃", "无法", "阻断", "全部失败", "数据丢失", "重大", "安全"]
    p1_kw = ["重要", "影响", "延迟", "错误", "失败", "问题", "连续", "多次"]
    
    if any(k in content for k in p0_kw):
        return "P0致命"
    elif any(k in content for k in p1_kw):
        return "P1严重"
    return "P2一般"


def generate_structured_reflection(lesson, date_str):
    """生成结构化反思记录 - 改进版：具体场景 + 根因 + 可执行方案"""
    category = lesson.get("category", "assumptions")
    level = determine_level(lesson["content"])
    content = lesson["content"]
    context = lesson.get("context", "")
    
    # 智能根因分析 - 基于具体内容
    root_cause = analyze_root_cause(content, context, category)
    
    # 智能解决方案 - 可执行、具体
    solution = generate_solution(content, root_cause, category)
    
    # 提取可复用经验
    reusable_experience = extract_reusable_experience(content, root_cause, category)
    
    return {
        "date": date_str,
        "category": category,
        "level": level,
        "type": lesson["type"],
        "miss": content,
        "context": context,
        "root": root_cause,
        "fix": solution,
        "experience": reusable_experience
    }


def analyze_root_cause(content, context, category):
    """智能根因分析"""
    # 技术类根因
    if category == "technical":
        if "路径" in content or "目录" in content:
            return "工作目录/路径配置未标准化，存在多环境混用"
        elif "配置" in content:
            return "配置项未文档化，依赖口头约定或隐性假设"
        elif "超时" in content or "失败" in content:
            return "缺乏任务状态监控和失败告警机制"
        elif "权限" in content:
            return "权限管理不规范，未按最小权限原则配置"
        elif "token" in content.lower() or "认证" in content:
            return "认证凭据管理不当，可能存在过期或泄露风险"
        else:
            return "技术实现缺乏容错设计，未考虑边界情况"
    
    # 数据类根因
    elif category == "data":
        if "归档" in content or "备份" in content:
            return "数据生命周期管理不完善，缺乏自动化监控"
        elif "记录" in content:
            return "数据记录标准不明确，格式/位置不统一"
        elif "统计" in content:
            return "数据统计口径不一致，缺乏标准化定义"
        else:
            return "数据管理流程未文档化，执行依赖个人习惯"
    
    # 流程类根因
    elif category == "process":
        if "沟通" in content or "对齐" in content:
            return "沟通机制不完善，关键信息未同步或确认"
        elif "计划" in content or "排期" in content:
            return "任务规划未考虑依赖关系和缓冲时间"
        elif "文档" in content:
            return "文档更新不及时，与实际情况存在偏差"
        else:
            return "流程执行缺乏检查清单，容易遗漏关键步骤"
    
    # 默认根因
    if "时间" in content or "周期" in content:
        return "时间/周期定义不明确，缺乏标准化约定"
    elif "数据" in content:
        return "缺乏历史数据积累，无法支撑决策"
    elif "配置" in content:
        return "配置项未明确文档化"
    elif "沟通" in content or "对齐" in content:
        return "沟通不充分，信息未同步"
    else:
        return "未充分识别潜在风险，缺乏预检查机制"


def generate_solution(content, root_cause, category):
    """生成可执行的解决方案"""
    solutions = []
    
    # 基于根因生成具体方案
    if "配置" in root_cause:
        solutions.append("建立配置检查清单，关键路径/环境变量文档化")
        solutions.append("在代码中增加配置校验，启动时检查必要配置项")
    
    if "监控" in root_cause or "告警" in root_cause:
        solutions.append("为关键定时任务增加状态监控和失败告警")
        solutions.append("建立任务执行日志，记录开始/结束/异常状态")
    
    if "文档化" in root_cause:
        solutions.append("更新相关文档，明确标准操作流程")
        solutions.append("在关键位置添加注释说明，减少口头依赖")
    
    if "标准化" in root_cause:
        solutions.append("制定统一规范，消除多版本混用")
        solutions.append("建立模板/示例，降低执行差异")
    
    if "沟通" in root_cause:
        solutions.append("建立信息同步机制，关键变更需确认")
        solutions.append("使用异步文档记录决策，减少信息丢失")
    
    if "检查清单" in root_cause:
        solutions.append("设计检查清单，覆盖关键步骤和风险点")
        solutions.append("在关键节点设置检查点，强制确认后再继续")
    
    if "容错" in root_cause:
        solutions.append("增加异常处理逻辑， graceful degradation")
        solutions.append("设计降级方案，核心功能在异常时仍可运行")
    
    if not solutions:
        if category == "technical":
            solutions.append("增加单元测试覆盖边界情况")
            solutions.append("代码审查时关注异常处理")
        elif category == "data":
            solutions.append("建立数据质量检查机制")
            solutions.append("定期审计数据完整性")
        else:
            solutions.append("建立检查清单，增加预检查环节")
            solutions.append("定期复盘，持续优化流程")
    
    return "；".join(solutions[:2])


def extract_reusable_experience(content, root_cause, category):
    """提取可复用的经验"""
    experiences = []
    
    # 配置相关
    if "配置" in content or "配置" in root_cause:
        experiences.append({
            "type": "配置文档化",
            "practice": "关键路径、环境变量必须文档化，避免口头约定",
            "apply_to": "所有涉及路径/配置的功能"
        })
    
    # 监控相关
    if "监控" in root_cause or "失败" in content or "超时" in content:
        experiences.append({
            "type": "任务可观测",
            "practice": "定时任务必须配套状态监控和失败告警",
            "apply_to": "所有自动化任务"
        })
    
    # 重复问题
    if "连续" in content or "多次" in content or "重复" in content:
        experiences.append({
            "type": "防冗余设计",
            "practice": "同一问题出现2次+，需建立检查清单或自动化检测",
            "apply_to": "高频操作/关键流程"
        })
    
    # 沟通相关
    if "沟通" in content or "对齐" in content:
        experiences.append({
            "type": "信息同步",
            "practice": "关键信息变更需书面确认，避免'我以为'",
            "apply_to": "跨团队协作/需求变更"
        })
    
    # 时间相关
    if "时间" in content or "周期" in content:
        experiences.append({
            "type": "时间标准化",
            "practice": "时间范围使用标准格式（如 00:00-23:59），避免歧义",
            "apply_to": "所有时间相关的配置和文档"
        })
    
    # 数据相关
    if category == "data":
        experiences.append({
            "type": "数据生命周期",
            "practice": "关键数据需有归档策略和完整性校验",
            "apply_to": "业务数据/日志/备份"
        })
    
    if not experiences:
        experiences.append({
            "type": "预检查机制",
            "practice": "关键操作前执行检查清单，识别潜在风险",
            "apply_to": "所有关键流程"
        })
    
    return experiences


def calculate_lesson_stats(lessons):
    """计算教训统计数据"""
    stats = {
        "total": len(lessons),
        "good_count": len([l for l in lessons if l["type"] == "good"]),
        "improve_count": len([l for l in lessons if l["type"] == "improve"]),
        "categories": Counter([l["category"] for l in lessons]),
        "levels": Counter([determine_level(l["content"]) for l in lessons]),
        "repeated": find_repeated_lessons(lessons)
    }
    return stats


def find_repeated_lessons(lessons):
    """找出重复出现的教训主题"""
    # 读取历史反思记录
    reflections_file = os.path.join(REFLECTION_DIR, "reflections.md")
    if not os.path.exists(reflections_file):
        return []
    
    with open(reflections_file, "r", encoding="utf-8") as f:
        history = f.read()
    
    repeated = []
    for lesson in lessons:
        # 提取关键词
        keywords = extract_keywords(lesson["content"])
        # 在历史记录中查找
        matches = 0
        for kw in keywords:
            if kw in history:
                matches += history.count(kw)
        if matches >= 2:  # 出现2次以上视为重复
            repeated.append({
                "content": lesson["content"][:50],
                "keywords": keywords,
                "frequency": matches
            })
    
    return repeated


def extract_keywords(content):
    """提取内容关键词"""
    # 简单的关键词提取：名词短语
    keywords = []
    important_words = ["配置", "路径", "目录", "任务", "监控", "告警", "数据", 
                       "归档", "备份", "文档", "沟通", "对齐", "超时", "失败"]
    for word in important_words:
        if word in content:
            keywords.append(word)
    return keywords


def append_to_reflections(reflection):
    """追加到 reflections.md"""
    filepath = os.path.join(REFLECTION_DIR, "reflections.md")
    
    # 构建经验部分
    exp_text = ""
    if reflection.get("experience"):
        exp_text = "\n**Experience:**\n"
        for exp in reflection["experience"]:
            exp_text += f"- **{exp['type']}**: {exp['practice']}（适用于：{exp['apply_to']}）\n"
    
    entry = f"""## {reflection['date']} | {reflection['category']}
**Type:** {reflection['type']} | **Level:** {reflection['level']}
**Miss:** {reflection['miss']}
**Context:** {reflection.get('context', 'N/A')[:100]}
**Root:** {reflection['root']}
**Fix:** {reflection['fix']}{exp_text}
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


def generate_feishu_report(date_str, stats, good_lessons, improve_lessons, reflections):
    """生成飞书报告 - 结构化呈现"""
    
    # 数据概览部分
    lines = [
        f"📊 每日反思报告 - {date_str}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        "",
        "📈 数据概览",
        f"• 今日提取教训：{stats['total']} 条",
        f"• 类型分布：{' | '.join([f'{k} {v}条' for k, v in stats['categories'].most_common()])}",
    ]
    
    if stats['repeated']:
        lines.append(f"• 重复主题：{len(stats['repeated'])} 个（需重点关注）")
    
    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        "",
        "✅ 做得好的",
        ""
    ])
    
    # 做得好的部分
    for i, lesson in enumerate(good_lessons[:3], 1):
        ref = [r for r in reflections if r['miss'] == lesson['content']]
        if ref:
            r = ref[0]
            lines.append(f"{i}. {r['miss']}")
            if r.get('context'):
                lines.append(f"   • 背景：{r['context'][:80]}{'...' if len(r['context']) > 80 else ''}")
        else:
            lines.append(f"{i}. {lesson['content']}")
        lines.append("")
    
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "⚠️ 需改进的",
        ""
    ])
    
    # 需改进的部分
    for i, lesson in enumerate(improve_lessons[:3], 1):
        ref = [r for r in reflections if r['miss'] == lesson['content']]
        if ref:
            r = ref[0]
            lines.append(f"{i}. {r['miss']}")
            lines.append(f"   • 根因：{r['root']}")
            lines.append(f"   • 改进：{r['fix']}")
        else:
            lines.append(f"{i}. {lesson['content']}")
        lines.append("")
    
    # 关联经验
    all_experiences = []
    for r in reflections:
        if r.get('experience'):
            all_experiences.extend(r['experience'])
    
    if all_experiences:
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "💡 关联经验（可复用）",
            "",
            "| 经验类型 | 具体做法 |",
            "|---------|---------|"
        ])
        
        seen = set()
        for exp in all_experiences[:5]:
            key = exp['type']
            if key not in seen:
                seen.add(key)
                lines.append(f"| {exp['type']} | {exp['practice']} |")
        
        lines.append("")
    
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📁 完整记录：{REFLECTION_DIR}/reflections.md"
    ])
    
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
                print(f"✅ 飞书报告发送成功")
                return True
            else:
                print(f"⚠️ 飞书发送失败: {result.get('msg')}")
                return False
    except Exception as e:
        print(f"⚠️ 飞书发送失败: {e}")
        return False


def main():
    print("🚀 开始生成每日反思 V2...")
    
    # 获取昨天日期
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    
    print(f"📅 分析日期: {date_str}")
    
    # 从记忆文件提取教训
    lessons = extract_lessons_from_memory(date_str)
    print(f"✅ 从记忆文件提取 {len(lessons)} 条教训")
    
    if not lessons:
        print("⚠️ 未找到可记录的教训")
        return
    
    # 计算统计
    stats = calculate_lesson_stats(lessons)
    print(f"📊 统计：总计{stats['total']}条，做得好{stats['good_count']}条，需改进{stats['improve_count']}条")
    
    # 生成结构化反思
    reflections = []
    for lesson in lessons:
        reflection = generate_structured_reflection(lesson, date_str)
        reflections.append(reflection)
        print(f"📝 生成反思: {reflection['miss'][:40]}...")
        
        # 只记录需改进的到 reflections.md
        if lesson["type"] == "improve":
            append_to_reflections(reflection)
            print(f"✅ 已追加到 reflections.md")
    
    # 分类
    good_lessons = [l for l in lessons if l["type"] == "good"]
    improve_lessons = [l for l in lessons if l["type"] == "improve"]
    
    # 生成飞书报告
    print("📱 生成飞书报告...")
    report = generate_feishu_report(date_str, stats, good_lessons, improve_lessons, reflections)
    
    # 发送飞书报告
    print("📤 发送飞书报告...")
    send_feishu_message(report)
    
    print("🎉 完成!")


if __name__ == "__main__":
    main()