#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件安装验证

检查 SKILL.md 完整性、目录结构、依赖项是否安装。
扫描所有已安装的 skill 目录。
"""

import os
import re
import sys
import subprocess
from typing import Dict, List, Optional


# Skill 搜索路径
SKILL_SEARCH_PATHS = [
    "/root/.openclaw/workspace/skills",
    "/root/.openclaw/extensions",
]


def validate_installation(skill_dir: str) -> Dict:
    """
    检查 skill 目录完整性

    Args:
        skill_dir: skill 目录路径

    Returns:
        Dict: 验证结果
    """
    issues = []
    info = {"dir": skill_dir}

    if not os.path.isdir(skill_dir):
        return {"valid": False, "issues": ["目录不存在"], "info": info}

    # 检查 SKILL.md
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        issues.append("缺少 SKILL.md")
    else:
        info["skill_md"] = skill_md
        md_result = validate_skill_md(skill_md)
        if not md_result["valid"]:
            issues.extend(md_result["issues"])

    # 检查 scripts 目录（可选）
    scripts_dir = os.path.join(skill_dir, "scripts")
    if os.path.isdir(scripts_dir):
        info["has_scripts"] = True
        scripts = [f for f in os.listdir(scripts_dir) if os.path.isfile(os.path.join(scripts_dir, f))]
        info["script_count"] = len(scripts)
    else:
        info["has_scripts"] = False

    # 检查 references 目录（可选）
    refs_dir = os.path.join(skill_dir, "references")
    info["has_references"] = os.path.isdir(refs_dir)

    # 列出目录内容
    info["files"] = os.listdir(skill_dir)

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "info": info
    }


def validate_skill_md(filepath: str) -> Dict:
    """
    验证 SKILL.md 格式

    检查必要字段：至少有 description 相关内容

    Args:
        filepath: SKILL.md 文件路径

    Returns:
        Dict: 验证结果
    """
    issues = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"valid": False, "issues": [f"无法读取: {e}"]}

    if not content.strip():
        issues.append("SKILL.md 为空")
        return {"valid": False, "issues": issues}

    # 检查基本结构：至少有标题
    if not re.search(r"^#\s+", content, re.MULTILINE):
        issues.append("缺少标题（# 开头）")

    # 检查是否有描述性内容（至少 50 个非空白字符）
    text = re.sub(r"[#\s\-\*\n]", "", content)
    if len(text) < 50:
        issues.append("内容过少，可能缺少描述")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "size": len(content)
    }


def check_dependencies(skill_dir: str) -> Dict:
    """
    检查 requirements.txt 依赖是否已安装

    Args:
        skill_dir: skill 目录路径

    Returns:
        Dict: 依赖检查结果
    """
    req_file = os.path.join(skill_dir, "requirements.txt")

    if not os.path.isfile(req_file):
        return {"has_requirements": False, "message": "无 requirements.txt"}

    # 解析 requirements.txt
    dependencies = []
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # 提取包名（去掉版本限制）
                pkg = re.split(r"[><=!~\[]", line)[0].strip()
                if pkg:
                    dependencies.append(pkg)

    # 逐个检查是否已安装
    installed = []
    missing = []

    for pkg in dependencies:
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {pkg}"],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                installed.append(pkg)
            else:
                missing.append(pkg)
        except Exception:
            missing.append(pkg)

    return {
        "has_requirements": True,
        "total": len(dependencies),
        "installed": installed,
        "missing": missing,
        "all_met": len(missing) == 0
    }


def list_all_skills() -> List[Dict]:
    """
    扫描所有已安装的 skill 目录

    Returns:
        List[Dict]: skill 列表，含验证结果
    """
    skills = []
    seen_names = set()

    for search_path in SKILL_SEARCH_PATHS:
        if not os.path.isdir(search_path):
            continue

        # 遍历子目录
        for entry in os.listdir(search_path):
            skill_dir = os.path.join(search_path, entry)
            if not os.path.isdir(skill_dir):
                continue
            if entry in seen_names:
                continue
            seen_names.add(entry)

            # 只包含有 SKILL.md 的目录
            skill_md = os.path.join(skill_dir, "SKILL.md")
            if os.path.isfile(skill_md):
                validation = validate_installation(skill_dir)
                skills.append({
                    "name": entry,
                    "path": skill_dir,
                    "valid": validation["valid"],
                    "issues": validation.get("issues", [])
                })

        # 也检查一级子目录的子目录（extensions 下的包）
        for entry in os.listdir(search_path):
            sub = os.path.join(search_path, entry)
            if not os.path.isdir(sub):
                continue
            for sub_entry in os.listdir(sub):
                skill_dir = os.path.join(sub, sub_entry)
                if not os.path.isdir(skill_dir):
                    continue
                name = f"{entry}/{sub_entry}"
                if name in seen_names:
                    continue
                seen_names.add(name)

                skill_md = os.path.join(skill_dir, "SKILL.md")
                if os.path.isfile(skill_md):
                    validation = validate_installation(skill_dir)
                    skills.append({
                        "name": name,
                        "path": skill_dir,
                        "valid": validation["valid"],
                        "issues": validation.get("issues", [])
                    })

    return skills


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="插件安装验证")
    subparsers = parser.add_subparsers(dest="command")

    p_validate = subparsers.add_parser("validate", help="验证单个 skill")
    p_validate.add_argument("dir", help="skill 目录路径")

    p_check = subparsers.add_parser("check-md", help="验证 SKILL.md")
    p_check.add_argument("file", help="SKILL.md 文件路径")

    p_deps = subparsers.add_parser("deps", help="检查依赖")
    p_deps.add_argument("dir", help="skill 目录路径")

    p_list = subparsers.add_parser("list", help="列出所有已安装 skill")

    args = parser.parse_args()

    if args.command == "validate":
        result = validate_installation(args.dir)
        status = "✅ 有效" if result["valid"] else "❌ 无效"
        print(f"Skill 验证: {status}")
        for issue in result.get("issues", []):
            print(f"  - {issue}")

    elif args.command == "check-md":
        result = validate_skill_md(args.file)
        status = "✅ 有效" if result["valid"] else "❌ 无效"
        print(f"SKILL.md 验证: {status} (大小: {result.get('size', 0)} bytes)")
        for issue in result.get("issues", []):
            print(f"  - {issue}")

    elif args.command == "deps":
        result = check_dependencies(args.dir)
        if not result["has_requirements"]:
            print("无 requirements.txt")
        else:
            print(f"依赖: {result['total']} 个")
            print(f"  已安装: {result['installed']}")
            print(f"  缺失: {result['missing']}")

    elif args.command == "list":
        skills = list_all_skills()
        print(f"已安装 Skill: {len(skills)} 个\n")
        for s in skills:
            icon = "✅" if s["valid"] else "❌"
            print(f"  {icon} {s['name']}")
            if s["issues"]:
                for issue in s["issues"]:
                    print(f"     - {issue}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
