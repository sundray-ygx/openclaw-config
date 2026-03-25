#!/usr/bin/env python3
"""
修复2026-03-24记忆文件
"""

import os
import shutil
from datetime import datetime

WORKSPACE = "/home/openclaw/.openclaw/workspace"
MEMORY_DIR = f"{WORKSPACE}/memory"
DAILY_REPORTS = f"{WORKSPACE}/archive/daily"

def fix_memory_24():
    """修复3月24日记忆文件"""
    date_str = "2026-03-24"
    month = "2026-03"
    
    # 源文件路径
    report_file = f"{DAILY_REPORTS}/{month}/daily-report-{date_str}.md"
    memory_file = f"{MEMORY_DIR}/{date_str}.md"
    
    # 检查日报是否存在
    if not os.path.exists(report_file):
        print(f"❌ 日报不存在: {report_file}")
        return False
    
    # 读取日报内容
    with open(report_file, "r", encoding="utf-8") as f:
        report_content = f.read()
    
    # 生成记忆文件内容
    content = f"""# {date_str} 记忆

## 日报摘要
{report_content}

## 待跟进事项
- [ ] 

## 明日计划
- 

---
*补录于 {datetime.now().strftime("%H:%M")}*
"""
    
    # 写入记忆文件
    with open(memory_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ 已修复记忆文件: {memory_file}")
    return True

if __name__ == "__main__":
    fix_memory_24()
