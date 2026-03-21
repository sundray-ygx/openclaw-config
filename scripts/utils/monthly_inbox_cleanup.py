#!/usr/bin/env python3
"""
月度 inbox 整理提醒
- 扫描 inbox 目录
- 生成待整理清单
- 发送飞书提醒
"""

import os
import json
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"
INBOX_DIR = f"{WORKSPACE}/knowledge/inbox"

def scan_inbox():
    """扫描 inbox 目录"""
    if not os.path.exists(INBOX_DIR):
        return []
    
    files = []
    for filename in os.listdir(INBOX_DIR):
        if filename.endswith(".md"):
            filepath = f"{INBOX_DIR}/{filename}"
            stat = os.stat(filepath)
            files.append({
                "name": filename,
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
            })
    
    return files

def generate_report(files):
    """生成整理报告"""
    if not files:
        return "📁 Knowledge inbox 目录已清空，无需整理。"
    
    report = f"""📦 Knowledge Inbox 月度整理提醒

当前有 {len(files)} 个文件待整理：

"""
    for f in files:
        report += f"- {f['name']} ({f['size']} bytes, {f['mtime']})\n"
    
    report += """
整理步骤：
1. 进入 `/root/.openclaw/workspace/knowledge/inbox/`
2. 阅读每个文件内容
3. 确认自动标签是否准确
4. 移动到对应目录：
   - `lessons/` - 经验教训
   - `tech/` - 技术知识
   - `work/` - 工作相关
   - `security/` - 安全相关
   - `productivity/` - 效率提升
5. 重命名为：`YYYY-MM-DD-title.md`
6. 删除 inbox 中的原文件

建议：每个文件花费 2-3 分钟判断即可，不要过度纠结。
"""
    return report

def main():
    files = scan_inbox()
    report = generate_report(files)
    print(report)
    
    # 保存报告到临时文件（供飞书发送）
    report_file = "/tmp/knowledge-inbox-report.txt"
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"\n报告已保存到: {report_file}")

if __name__ == "__main__":
    main()
