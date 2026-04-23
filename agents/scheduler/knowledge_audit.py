#!/usr/bin/env python3
"""
知识库梳理分析脚本
分析 inbox 中的文件，生成梳理方案
"""

import os
import re
import json
from datetime import datetime
from collections import Counter

KNOWLEDGE_DIR = "/root/.openclaw/workspace/knowledge"
INBOX_DIR = os.path.join(KNOWLEDGE_DIR, "inbox")

# 定义目标目录及其用途
CATEGORIES = {
    "lessons": "经验教训和心得",
    "work": "工作相关内容（OKR、任务、组织结构等）",
    "tech": "技术相关内容（开发、自动化、工具等）",
    "productivity": "生产力提升相关",
    "security": "安全相关",
    "people": "人物相关",
    "projects": "项目相关"
}

def analyze_inbox_files():
    """分析 inbox 中的所有文件"""
    files = []
    for filename in os.listdir(INBOX_DIR):
        if filename.endswith('.md'):
            filepath = os.path.join(INBOX_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取元数据
            metadata = extract_metadata(content)
            files.append({
                'filename': filename,
                'filepath': filepath,
                'metadata': metadata,
                'size': os.path.getsize(filepath)
            })

    return files

def extract_metadata(content):
    """提取文件中的元数据"""
    metadata = {
        'tags': [],
        'suggested_locations': [],
        'date': None,
        'title': None
    }

    # 提取 JSON 元数据
    json_match = re.search(r'---\s*\n(.*?)\n---', content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            metadata['tags'] = data.get('tags', [])
            metadata['suggested_locations'] = data.get('suggested归档位置', data.get('tags', []))
            metadata['date'] = data.get('date')
        except:
            pass

    # 提取标题
    title_match = re.search(r'#\s+(.+)', content)
    if title_match:
        metadata['title'] = title_match.group(1).strip()

    return metadata

def generate_audit_report(files):
    """生成梳理报告"""
    report = []
    total_files = len(files)
    total_size = sum(f['size'] for f in files)

    # 统计标签
    all_tags = []
    location_counter = Counter()

    for f in files:
        all_tags.extend(f['metadata']['tags'])
        for loc in f['metadata']['suggested_locations']:
            if loc in CATEGORIES:
                location_counter[loc] += 1

    tag_counter = Counter(all_tags)

    report.append("# 知识库梳理分析报告\n")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**分析文件数**: {total_files}\n")
    report.append(f"**总大小**: {total_size / 1024:.2f} KB\n\n")

    report.append("## 📊 统计概览\n\n")
    report.append("### 标签分布\n")
    for tag, count in tag_counter.most_common(10):
        report.append(f"- {tag}: {count} 个文件\n")

    report.append("\n### 建议归档位置分布\n")
    for location, count in location_counter.most_common():
        report.append(f"- **{location}** ({CATEGORIES.get(location, '未知')}): {count} 个文件\n")

    report.append("\n## 📁 待整理文件清单\n\n")

    # 按建议位置分组
    files_by_location = {}
    for f in files:
        for loc in f['metadata']['suggested_locations']:
            if loc in CATEGORIES:
                if loc not in files_by_location:
                    files_by_location[loc] = []
                files_by_location[loc].append(f)
                break  # 只使用第一个匹配的位置
        else:
            # 如果没有匹配的位置，放入未分类
            if 'uncategorized' not in files_by_location:
                files_by_location['uncategorized'] = []
            files_by_location['uncategorized'].append(f)

    # 生成每个位置的文件清单
    for location, files_list in sorted(files_by_location.items()):
        if location == 'uncategorized':
            report.append(f"### 📂 未分类文件 ({len(files_list)} 个)\n\n")
        else:
            report.append(f"### 📂 {location} - {CATEGORIES.get(location, '未知')} ({len(files_list)} 个)\n\n")

        for f in sorted(files_list, key=lambda x: x['filename']):
            tags_str = ', '.join(f['metadata']['tags']) if f['metadata']['tags'] else '无'
            title = f['metadata'].get('title', '无标题')
            report.append(f"- **{f['filename']}**\n")
            report.append(f"  - 标题: {title}\n")
            report.append(f"  - 标签: {tags_str}\n")
            report.append(f"  - 大小: {f['size']} bytes\n")
            report.append(f"  - 建议位置: {', '.join(f['metadata']['suggested_locations'])}\n\n")

    report.append("\n## 🎯 梳理建议\n\n")
    report.append("### 自动化梳理方案\n")
    report.append("1. **基于标签的自动归档**\n")
    report.append("   - 根据文件中的 `tags` 字段自动移动到对应目录\n")
    report.append("   - 重命名格式: `YYYY-MM-DD-title.md`\n\n")

    report.append("2. **人工审核机制**\n")
    report.append("   - 对未分类文件进行人工审核\n")
    report.append("   - 对标签冲突的文件进行人工判断\n\n")

    report.append("### 执行步骤\n")
    report.append("1. 备份当前 inbox 目录\n")
    report.append("2. 执行自动归档脚本\n")
    report.append("3. 人工审核归档结果\n")
    report.append("4. 更新知识库索引\n")
    report.append("5. 删除已归档的 inbox 文件\n\n")

    return ''.join(report)

def main():
    print("🔍 开始分析知识库 inbox...")

    if not os.path.exists(INBOX_DIR):
        print(f"❌ Inbox 目录不存在: {INBOX_DIR}")
        return

    files = analyze_inbox_files()
    report = generate_audit_report(files)

    # 保存报告
    report_path = os.path.join(KNOWLEDGE_DIR, "knowledge-audit-report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 分析完成！")
    print(f"📊 共分析 {len(files)} 个文件")
    print(f"📄 报告已保存至: {report_path}")

    # 显示摘要
    print("\n" + "="*50)
    print("📋 摘要信息:")
    print("="*50)
    for line in report.split('\n'):
        if '分析文件数' in line or '总大小' in line or '###' in line:
            print(line)

if __name__ == "__main__":
    main()
