#!/usr/bin/env python3
"""
IPD知识库批量更新工具

功能：
1. 统一更新IPD相关文档的组织架构信息
2. 验证更新后的数据一致性
3. 生成更新报告
4. 支持事务性更新（全部成功或全部回滚）
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

# 基础路径
WORKSPACE = "/root/.openclaw/workspace"
IPD_DIR = os.path.join(WORKSPACE, "knowledge", "work", "IPD")
EXTRACTED_DIR = os.path.join(IPD_DIR, "extracted")
BACKUP_DIR = os.path.join(IPD_DIR, ".backups")

# 需要更新的文档列表
UPDATE_TARGETS = [
    "03_权责全景表.md",
    "02_决策全景表.md",
    "04_准入准出全景表.md",
    "05_准入准出全景表(配件类-供应链填写).md",
    "06_质量运营全景表（建设中）.md",
    "08_IPD流程阶段全景图.md",
    "10_IPD流程优化执行计划.md",
]

# 日志
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def create_backup():
    """创建当前状态的完整备份"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}")

    if os.path.exists(EXTRACTED_DIR):
        shutil.copytree(EXTRACTED_DIR, backup_path)
        log(f"备份已创建: {backup_path}")
        return backup_path
    else:
        log("源目录不存在，跳过备份", "WARN")
        return None


def restore_backup(backup_path):
    """从备份恢复"""
    if backup_path and os.path.exists(backup_path):
        # 删除当前目录
        shutil.rmtree(EXTRACTED_DIR)
        # 恢复备份
        shutil.copytree(backup_path, EXTRACTED_DIR)
        log(f"已从备份恢复: {backup_path}")
        return True
    return False


def update_org_info(content, new_org_data):
    """
    更新文档中的组织架构信息

    new_org_data 格式示例:
    {
        "供应链代表": "张三",
        "硬件研发主管": "李四",
        "产线主管": "王五"
    }
    """
    updated_content = content

    for role, person in new_org_data.items():
        # 查找并替换：| 供应链代表 | xxx | -> | 供应链代表 | 张三 |
        import re
        pattern = rf'(\|\s*{re.escape(role)}\s*\|\s*)[^|]+(\s*\|)'
        replacement = rf'\g<1>{person}\g<2>'
        updated_content = re.sub(pattern, replacement, updated_content)

    return updated_content


def update_document(doc_file, new_org_data):
    """更新单个文档"""
    doc_path = os.path.join(EXTRACTED_DIR, doc_file)

    if not os.path.exists(doc_path):
        log(f"文档不存在，跳过: {doc_file}", "WARN")
        return False, None

    with open(doc_path, 'r', encoding='utf-8') as f:
        original_content = f.read()

    # 更新内容
    updated_content = update_org_info(original_content, new_org_data)

    # 检查是否有变化
    if updated_content == original_content:
        log(f"文档无需更新: {doc_file}")
        return True, None

    # 写入更新
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    log(f"文档已更新: {doc_file}")
    return True, doc_file


def validate_updates(updated_docs):
    """验证更新后的数据一致性"""
    log("开始验证更新...")

    # 简单验证：检查所有更新的文档是否存在且可读
    all_valid = True
    for doc_file in updated_docs:
        doc_path = os.path.join(EXTRACTED_DIR, doc_file)
        if not os.path.exists(doc_path):
            log(f"验证失败: 文档不存在 {doc_file}", "ERROR")
            all_valid = False
            continue

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                log(f"验证失败: 文档为空 {doc_file}", "ERROR")
                all_valid = False

    if all_valid:
        log("所有文档验证通过")
    else:
        log("部分文档验证失败", "ERROR")

    return all_valid


def generate_report(updated_docs, new_org_data, success=True):
    """生成更新报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "updated_docs": updated_docs,
        "org_data": new_org_data,
        "summary": {
            "total_targets": len(UPDATE_TARGETS),
            "updated_count": len(updated_docs),
            "skipped_count": len(UPDATE_TARGETS) - len(updated_docs)
        }
    }

    report_path = os.path.join(IPD_DIR, "update_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    log(f"更新报告已生成: {report_path}")
    return report


def main():
    """主函数"""
    log("=" * 50)
    log("IPD知识库批量更新工具")
    log("=" * 50)

    # 示例组织架构数据（实际使用时应从外部传入）
    new_org_data = {
        "供应链代表": "待填充",
        "硬件研发主管": "待填充",
        "产线主管": "待填充",
        "综合管理部": "待填充"
    }

    # 如果提供了命令行参数，使用命令行参数
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], 'r', encoding='utf-8') as f:
                new_org_data = json.load(f)
            log(f"从文件加载组织架构数据: {sys.argv[1]}")
        except Exception as e:
            log(f"加载配置文件失败: {e}", "ERROR")
            return 1

    # 创建备份
    backup_path = create_backup()

    # 更新文档
    updated_docs = []
    failed = False

    for doc_file in UPDATE_TARGETS:
        success, updated = update_document(doc_file, new_org_data)
        if success and updated:
            updated_docs.append(doc_file)
        elif not success:
            failed = True
            break

    # 如果有失败，回滚
    if failed:
        log("更新过程中出现错误，开始回滚...", "ERROR")
        restore_backup(backup_path)
        log("回滚完成", "ERROR")
        generate_report([], new_org_data, success=False)
        return 1

    # 验证更新
    if not validate_updates(updated_docs):
        log("验证失败，开始回滚...", "ERROR")
        restore_backup(backup_path)
        log("回滚完成", "ERROR")
        generate_report([], new_org_data, success=False)
        return 1

    # 生成报告
    report = generate_report(updated_docs, new_org_data, success=True)

    log("=" * 50)
    log("更新完成！")
    log(f"成功更新: {len(updated_docs)} 个文档")
    log(f"跳过: {len(UPDATE_TARGETS) - len(updated_docs)} 个文档")
    log("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
