#!/usr/bin/env python3
"""
自动归档到 inbox
- 读取日报和记忆内容
- 提取关键词，生成标签
- 保存到 knowledge/inbox/ 等待人工整理
"""

import os
import re
import json
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"
INBOX_DIR = f"{WORKSPACE}/knowledge/inbox"
MEMORY_DIR = f"{WORKSPACE}/memory"
ARCHIVE_DIR = f"{WORKSPACE}/archive"

# 关键词映射表
KEYWORD_MAP = {
    # 技术相关
    "tech": ["脚本", "python", "shell", "定时任务", "cron", "备份", "配置", "技能", "skill", "mcp", "api"],
    # 安全相关
    "security": ["安全", "防护", "篡改", "监控", "告警", "审计", "风险", "漏洞", "入侵"],
    # 工作相关
    "work": ["日报", "周报", "复盘", "计划", "任务", "项目", "会议", "汇报", "对齐"],
    # 效率相关
    "productivity": ["自动化", "效率", "优化", "改进", "工具", "流程", "模板"],
    # 经验教训
    "lessons": ["问题", "修复", "解决", "踩坑", "教训", "经验", "总结"],
}

def ensure_dirs():
    """确保目录存在"""
    os.makedirs(INBOX_DIR, exist_ok=True)

def extract_tags(content):
    """从内容中提取标签"""
    tags = []
    content_lower = content.lower()
    
    for category, keywords in KEYWORD_MAP.items():
        for keyword in keywords:
            if keyword.lower() in content_lower:
                tags.append(category)
                break
    
    return list(set(tags))  # 去重

def generate_inbox_filename(date_str, tags):
    """生成 inbox 文件名"""
    tag_str = "-".join(tags) if tags else "uncategorized"
    return f"{date_str}-{tag_str}.md"

def archive_memory_to_inbox(date_str):
    """将记忆归档到 inbox"""
    memory_file = f"{MEMORY_DIR}/{date_str}.md"
    
    if not os.path.exists(memory_file):
        print(f"记忆文件不存在: {memory_file}")
        return False
    
    with open(memory_file, "r") as f:
        content = f.read()
    
    # 提取标签
    tags = extract_tags(content)
    
    # 生成元数据
    metadata = {
        "source": "memory",
        "date": date_str,
        "tags": tags,
        "created_at": datetime.now().isoformat(),
        "status": "pending_review"
    }
    
    # 生成 inbox 内容
    inbox_content = f"""---
{json.dumps(metadata, indent=2, ensure_ascii=False)}
---

# 记忆归档 - {date_str}

**自动标签**: {', '.join(tags) if tags else '未分类'}

**建议归档位置**:
{chr(10).join(['- ' + tag for tag in tags]) if tags else '- 待人工判断'}

---

## 原始内容

{content}

---

## 人工整理说明

1. 阅读以上内容
2. 确认标签是否准确
3. 移动到对应目录: `knowledge/{{category}}/`
4. 重命名为: `YYYY-MM-DD-title.md`
5. 删除此 inbox 文件
"""
    
    # 保存到 inbox
    filename = generate_inbox_filename(date_str, tags)
    inbox_file = f"{INBOX_DIR}/{filename}"
    
    # 避免重复
    if os.path.exists(inbox_file):
        print(f"已存在: {inbox_file}")
        return False
    
    with open(inbox_file, "w") as f:
        f.write(inbox_content)
    
    print(f"✅ 已归档到 inbox: {filename}")
    return True

def send_feishu_notification(date_str, filename, tags):
    """发送飞书通知"""
    try:
        # 使用 openclaw 命令发送飞书消息
        tag_str = ', '.join(tags) if tags else '未分类'
        message = f"📥 记忆归档完成\\n\\n日期: {date_str}\\n文件: {filename}\\n标签: {tag_str}\\n\\n请查看 knowledge/inbox/ 并进行人工整理"
        
        cmd = f'openclaw message send --channel feishu --to ou_c2cde251e01a87fc09ba7561f76d8606 "{message}"'
        os.system(cmd)
        print(f"✅ 已发送飞书通知")
    except Exception as e:
        print(f"⚠️ 发送飞书通知失败: {e}")

def main():
    """主函数"""
    ensure_dirs()
    
    # 获取昨天的日期
    yesterday = (datetime.now() - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"开始归档 {yesterday} 的记忆到 inbox...")
    result = archive_memory_to_inbox(yesterday)
    
    if result:
        # 读取生成的文件名并发送通知
        memory_file = f"{MEMORY_DIR}/{yesterday}.md"
        with open(memory_file, "r") as f:
            content = f.read()
        tags = extract_tags(content)
        filename = generate_inbox_filename(yesterday, tags)
        send_feishu_notification(yesterday, filename, tags)
    
    print("完成!")

if __name__ == "__main__":
    main()
