#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClawHub 命令验证

验证包名格式、检查是否已安装、安装前检查、包装 clawhub 命令。
"""

import os
import re
import sys
import subprocess
import shutil
from typing import Dict, List, Optional


# Skill 安装路径
SKILL_DIRS = [
    "/root/.openclaw/workspace/skills",
    "/root/.openclaw/extensions",
]


def validate_package_name(name: str) -> Dict:
    """
    验证包名格式

    规则：小写字母、数字、连字符，不以连字符开头/结尾

    Args:
        name: 包名

    Returns:
        Dict: 验证结果
    """
    if not name:
        return {"valid": False, "message": "包名为空"}

    # 允许的字符：小写字母、数字、连字符
    pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'

    if not re.match(pattern, name):
        return {
            "valid": False,
            "message": "包名只能包含小写字母、数字和连字符，不能以连字符开头或结尾"
        }

    if len(name) < 2:
        return {"valid": False, "message": "包名至少 2 个字符"}

    if len(name) > 64:
        return {"valid": False, "message": "包名不能超过 64 个字符"}

    return {"valid": True, "message": "包名格式正确"}


def check_installed(skill_name: str) -> Dict:
    """
    检查 skill 是否已安装

    Args:
        skill_name: skill 名称

    Returns:
        Dict: 检查结果
    """
    for search_dir in SKILL_DIRS:
        if not os.path.isdir(search_dir):
            continue

        # 直接匹配
        skill_path = os.path.join(search_dir, skill_name)
        if os.path.isdir(skill_path) and os.path.isfile(os.path.join(skill_path, "SKILL.md")):
            return {
                "installed": True,
                "path": skill_path,
                "source": search_dir
            }

        # 检查子目录（extensions/package/skill 结构）
        for pkg_dir in os.listdir(search_dir):
            pkg_path = os.path.join(search_dir, pkg_dir)
            if not os.path.isdir(pkg_path):
                continue
            skill_path = os.path.join(pkg_path, skill_name)
            if os.path.isdir(skill_path) and os.path.isfile(os.path.join(skill_path, "SKILL.md")):
                return {
                    "installed": True,
                    "path": skill_path,
                    "source": f"{search_dir}/{pkg_dir}"
                }

    return {"installed": False, "path": None}


def validate_before_install(name: str) -> Dict:
    """
    安装前检查

    检查：包名格式、磁盘空间、是否已安装同名包

    Args:
        name: 包名

    Returns:
        Dict: 检查结果
    """
    issues = []

    # 检查包名格式
    name_result = validate_package_name(name)
    if not name_result["valid"]:
        issues.append(f"包名无效: {name_result['message']}")

    # 检查是否已安装
    installed = check_installed(name)
    if installed["installed"]:
        issues.append(f"已安装: {installed['path']}")

    # 检查磁盘空间（至少 100MB）
    try:
        stat = shutil.disk_usage("/root/.openclaw/workspace")
        free_mb = stat.free / (1024 * 1024)
        if free_mb < 100:
            issues.append(f"磁盘空间不足: 仅剩 {free_mb:.0f}MB")
    except Exception:
        pass  # 无法检查时不阻塞

    # 检查 clawhub 命令是否可用
    if not shutil.which("clawhub"):
        issues.append("clawhub 命令未找到，请先安装 clawhub CLI")

    return {
        "can_install": len(issues) == 0,
        "issues": issues,
        "name_valid": name_result["valid"],
        "already_installed": installed["installed"]
    }


def wrap_clawhub_command(args: List[str]) -> int:
    """
    包装 clawhub 命令，添加前置验证

    Args:
        args: 传给 clawhub 的参数列表

    Returns:
        int: 退出码
    """
    if not args:
        print("用法: clawhub_validator.py <clawhub args>")
        return 1

    # 解析命令
    action = args[0]

    if action == "install":
        if len(args) < 2:
            print("错误: 缺少包名")
            return 1

        name = args[1]
        print(f"安装前验证: {name}")

        validation = validate_before_install(name)
        if not validation["can_install"]:
            print("❌ 验证未通过:")
            for issue in validation["issues"]:
                print(f"  - {issue}")
            return 1

        print("✅ 验证通过，执行安装...")

    elif action in ("search", "info", "list"):
        pass  # 只读操作，不需要验证

    # 执行 clawhub 命令
    cmd = ["clawhub"] + args
    try:
        result = subprocess.run(cmd, timeout=300)
        return result.returncode
    except FileNotFoundError:
        print("错误: clawhub 命令未找到")
        return 1
    except subprocess.TimeoutExpired:
        print("错误: 命令超时")
        return 1


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="ClawHub 命令验证")
    subparsers = parser.add_subparsers(dest="command")

    p_name = subparsers.add_parser("validate-name", help="验证包名")
    p_name.add_argument("name")

    p_check = subparsers.add_parser("check", help="检查是否已安装")
    p_check.add_argument("name")

    p_pre = subparsers.add_parser("pre-install", help="安装前检查")
    p_pre.add_argument("name")

    p_run = subparsers.add_parser("run", help="包装执行 clawhub 命令")
    p_run.add_argument("args", nargs="+", help="clawhub 参数")

    args = parser.parse_args()

    if args.command == "validate-name":
        result = validate_package_name(args.name)
        status = "✅" if result["valid"] else "❌"
        print(f"{status} {result['message']}")

    elif args.command == "check":
        result = check_installed(args.name)
        if result["installed"]:
            print(f"✅ 已安装: {result['path']}")
        else:
            print("❌ 未安装")

    elif args.command == "pre-install":
        result = validate_before_install(args.name)
        if result["can_install"]:
            print("✅ 可以安装")
        else:
            print("❌ 安装前检查未通过:")
            for issue in result["issues"]:
                print(f"  - {issue}")

    elif args.command == "run":
        sys.exit(wrap_clawhub_command(args.args))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
