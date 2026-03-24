#!/usr/bin/env python3
"""
每日归档 - 23:00 执行
整理当日数据到 archive，更新 memory
"""

import os
import shutil
import json
from datetime import datetime, timedelta

WORKSPACE = "/home/openclaw/.openclaw/workspace"
MEMORY_DIR = f"{WORKSPACE}/memory"
ARCHIVE_DIR = f"{WORKSPACE}/archive"
DAILY_REPORTS = f"{WORKSPACE}/archive/daily"

def ensure_dirs():
    os.makedirs(MEMORY_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def get_month_str():
    return datetime.now().strftime("%Y-%m")

def archive_daily_reports():
    """归档日报到月份目录"""
    today = get_today_str()
    month = get_month_str()
    month_dir = f"{ARCHIVE_DIR}/{month}"
    os.makedirs(month_dir, exist_ok=True)
    
    # 移动今天的日报
    for filename in os.listdir(DAILY_REPORTS):
        if filename.startswith(f"daily-report-{today}"):
            src = f"{DAILY_REPORTS}/{filename}"
            dst = f"{month_dir}/{filename}"
            shutil.move(src, dst)
            print(f"归档: {filename}")

def update_memory():
    """更新记忆文件"""
    today = get_today_str()
    memory_file = f"{MEMORY_DIR}/{today}.md"
    
    # 读取今日日报内容
    report_content = ""
    for filename in os.listdir(DAILY_REPORTS):
        if filename.startswith(f"daily-report-{today}"):
            with open(f"{DAILY_REPORTS}/{filename}", "r") as f:
                report_content = f.read()
            break
    
    # 生成记忆文件
    content = f"""# {today} 记忆

## 日报摘要
{report_content if report_content else "今日无日报"}

## 待跟进事项
- [ ] 

## 明日计划
- 

---
*自动归档于 {datetime.now().strftime("%H:%M")}*
"""
    
    with open(memory_file, "w") as f:
        f.write(content)
    print(f"更新记忆: {memory_file}")

def main():
    ensure_dirs()
    print(f"开始归档: {get_today_str()}")
    
    try:
        archive_daily_reports()
        update_memory()
        print("归档完成")
    except Exception as e:
        print(f"归档失败: {e}")

if __name__ == "__main__":
    main()
