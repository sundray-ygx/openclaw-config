#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每周系统健康检查

检查磁盘空间、内存使用、僵尸进程、过期文件、cron健康。
用 subprocess 调用系统命令（df, free, ps）。
"""

import os
import re
import sys
import time
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List


# 配置常量
WORKSPACE_DIR = "/root/.openclaw/workspace"


def _run_cmd(cmd: List[str], timeout: int = 10) -> str:
    """执行系统命令并返回输出"""
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


def check_disk_space(min_free_gb: float = 5) -> Dict:
    """检查磁盘剩余空间"""
    output = _run_cmd(["df", "-BG", "/"])
    lines = output.split("\n")
    if len(lines) < 2:
        return {"status": "error", "message": "无法获取磁盘信息"}

    parts = lines[1].split()
    # Filesystem Size Used Avail Use% Mounted
    try:
        avail_gb = float(parts[3].replace("G", ""))
        use_pct = parts[4].replace("%", "")
    except (IndexError, ValueError):
        return {"status": "error", "message": "解析磁盘信息失败"}

    if avail_gb < min_free_gb:
        status = "danger"
    elif avail_gb < min_free_gb * 2:
        status = "warning"
    else:
        status = "healthy"

    return {
        "status": status,
        "available_gb": avail_gb,
        "use_percent": int(use_pct),
        "min_free_gb": min_free_gb,
        "message": f"可用 {avail_gb}G (阈值 {min_free_gb}G)"
    }


def check_memory_usage() -> Dict:
    """检查内存使用率"""
    output = _run_cmd(["free", "-m"])
    lines = output.split("\n")
    if len(lines) < 2:
        return {"status": "error", "message": "无法获取内存信息"}

    parts = lines[1].split()
    try:
        total = int(parts[1])
        used = int(parts[2])
        available = int(parts[6]) if len(parts) > 6 else total - used
        use_pct = round(used / total * 100, 1) if total > 0 else 0
    except (IndexError, ValueError):
        return {"status": "error", "message": "解析内存信息失败"}

    if use_pct > 90:
        status = "danger"
    elif use_pct > 75:
        status = "warning"
    else:
        status = "healthy"

    return {
        "status": status,
        "total_mb": total,
        "used_mb": used,
        "available_mb": available,
        "use_percent": use_pct,
        "message": f"内存使用 {use_pct}% ({used}/{total}MB)"
    }


def check_zombie_processes() -> Dict:
    """检查僵尸进程"""
    output = _run_cmd(["ps", "aux"])
    zombie_count = 0
    zombie_list = []

    for line in output.split("\n")[1:]:
        if "Z" in line.split()[7:8]:
            zombie_count += 1
            if len(zombie_list) < 5:
                zombie_list.append(line.strip())

    # 更可靠的方式：用 ps 统计 Z 状态
    output2 = _run_cmd(["ps", "-eo", "stat"])
    zombie_count = sum(1 for line in output2.split("\n") if line.strip().startswith("Z"))

    if zombie_count > 10:
        status = "danger"
    elif zombie_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "status": status,
        "zombie_count": zombie_count,
        "message": f"僵尸进程: {zombie_count} 个"
    }


def check_stale_files(directory: str, max_age_days: int = 30) -> Dict:
    """检查过期文件"""
    if not os.path.isdir(directory):
        return {"status": "error", "message": f"目录不存在: {directory}"}

    stale_files = []
    now = time.time()
    cutoff = now - max_age_days * 86400

    for root, dirs, files in os.walk(directory):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    stale_files.append(fpath)
            except OSError:
                continue

    if len(stale_files) > 20:
        status = "danger"
    elif len(stale_files) > 5:
        status = "warning"
    else:
        status = "healthy"

    return {
        "status": status,
        "stale_count": len(stale_files),
        "max_age_days": max_age_days,
        "sample": stale_files[:5],
        "message": f"过期文件: {len(stale_files)} 个 (>{max_age_days}天)"
    }


def check_cron_health() -> Dict:
    """调用 cron_registry 检查 cron 健康"""
    try:
        # 动态导入同目录的 cron_registry
        sys.path.insert(0, os.path.dirname(__file__))
        from cron_registry import scan_crons, check_continuity

        tasks = scan_crons()
        stale_tasks = []

        for task in tasks:
            continuity = check_continuity(task["name"])
            if continuity.get("is_stale") or continuity.get("status") in ("no_logs", "never_executed"):
                stale_tasks.append({
                    "name": task["name"],
                    "status": continuity.get("status")
                })

        if stale_tasks:
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "total_tasks": len(tasks),
            "stale_tasks": stale_tasks,
            "message": f"Cron任务: {len(tasks)}个, 异常: {len(stale_tasks)}个"
        }
    except Exception as e:
        return {"status": "error", "message": f"Cron检查失败: {e}"}


def generate_checklist() -> Dict:
    """生成完整检查清单"""
    checks = {
        "disk": check_disk_space(),
        "memory": check_memory_usage(),
        "zombie": check_zombie_processes(),
        "stale_files_workspace": check_stale_files(WORKSPACE_DIR),
        "cron_health": check_cron_health(),
    }

    # 汇总
    summary = {"healthy": 0, "warning": 0, "danger": 0, "error": 0}
    for result in checks.values():
        s = result.get("status", "error")
        summary[s] = summary.get(s, 0) + 1

    overall = "healthy"
    if summary["danger"] > 0 or summary["error"] > 0:
        overall = "danger"
    elif summary["warning"] > 0:
        overall = "warning"

    return {
        "generated_at": datetime.now().isoformat(),
        "overall": overall,
        "summary": summary,
        "checks": checks
    }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="每周系统健康检查")
    parser.add_argument("--json", action="store_true", help="以JSON输出")
    parser.add_argument("--min-free-gb", type=float, default=5, help="最小磁盘空间(GB)")
    parser.add_argument("--stale-days", type=int, default=30, help="过期文件天数")
    args = parser.parse_args()

    checklist = generate_checklist()

    if args.json:
        import json
        print(json.dumps(checklist, indent=2, ensure_ascii=False))
    else:
        # 格式化输出
        status_emoji = {"healthy": "✅", "warning": "⚠️", "danger": "🔴", "error": "❌"}
        print(f"系统健康检查 - {checklist['generated_at']}")
        print(f"总体状态: {status_emoji.get(checklist['overall'], '?')} {checklist['overall']}")
        print("-" * 50)

        for name, result in checklist["checks"].items():
            s = result.get("status", "error")
            emoji = status_emoji.get(s, "?")
            msg = result.get("message", "")
            print(f"  {emoji} [{name}] {msg}")

        print("-" * 50)
        s = checklist["summary"]
        print(f"汇总: ✅{s.get('healthy',0)} ⚠️{s.get('warning',0)} 🔴{s.get('danger',0)} ❌{s.get('error',0)}")


if __name__ == "__main__":
    main()
