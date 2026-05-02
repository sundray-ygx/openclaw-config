#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务执行登记簿

用于扫描、记录和检查 cron 任务的执行情况。
支持从 /etc/cron.d/openclaw-cron 和 crontab -l 扫描任务。
执行日志记录到 jsonl 格式文件。
"""

import os
import re
import json
import time
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional


# 配置常量
CRON_SYSTEM_FILE = "/etc/cron.d/openclaw-cron"
EXEC_LOG_FILE = "/root/.openclaw/workspace/memory/cron-exec-log.jsonl"


def scan_crons() -> List[Dict[str, str]]:
    """
    扫描所有 cron 任务来源

    Returns:
        List[Dict]: 任务列表，每个任务包含 name, schedule, command
    """
    tasks = []

    # 扫描系统级 cron 文件
    if os.path.exists(CRON_SYSTEM_FILE):
        try:
            with open(CRON_SYSTEM_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue

                    # 解析 cron 行
                    parts = line.split()
                    if len(parts) >= 6:
                        schedule = ' '.join(parts[:5])
                        command = ' '.join(parts[5:])

                        # 尝试从命令中提取任务名称
                        task_name = extract_task_name(command)

                        tasks.append({
                            'name': task_name,
                            'schedule': schedule,
                            'command': command,
                            'source': CRON_SYSTEM_FILE
                        })
        except Exception as e:
            print(f"扫描系统 cron 文件失败: {e}")

    # 扫描用户级 crontab
    try:
        result = subprocess.run(
            ['crontab', '-l'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) >= 6:
                    schedule = ' '.join(parts[:5])
                    command = ' '.join(parts[5:])
                    task_name = extract_task_name(command)

                    tasks.append({
                        'name': task_name,
                        'schedule': schedule,
                        'command': command,
                        'source': 'crontab'
                    })
    except Exception as e:
        print(f"扫描用户 crontab 失败: {e}")

    return tasks


def extract_task_name(command: str) -> str:
    """
    从命令中提取任务名称

    Args:
        command: cron 命令字符串

    Returns:
        str: 任务名称
    """
    # 尝试匹配 openclaw 相关命令
    match = re.search(r'openclaw\s+(\S+)', command)
    if match:
        return match.group(1)

    # 尝试提取脚本名
    match = re.search(r'/([^/]+?)(?:\.\w+)?\s', command)
    if match:
        return match.group(1)

    # 默认返回命令的前20个字符
    return command[:20] if command else 'unknown'


def record_execution(task_name: str, status: str, duration: float) -> bool:
    """
    记录任务执行日志到 jsonl 文件

    Args:
        task_name: 任务名称
        status: 执行状态 (success/failure/timeout)
        duration: 执行时长（秒）

    Returns:
        bool: 是否记录成功
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(EXEC_LOG_FILE), exist_ok=True)

    log_entry = {
        'task_name': task_name,
        'status': status,
        'duration': duration,
        'timestamp': datetime.now().isoformat(),
        'unix_timestamp': time.time()
    }

    try:
        with open(EXEC_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        return True
    except Exception as e:
        print(f"记录执行日志失败: {e}")
        return False


def check_continuity(task_name: str, max_gap_hours: int = 48) -> Dict:
    """
    检查任务是否超过指定时间未执行

    Args:
        task_name: 任务名称
        max_gap_hours: 最大允许间隔（小时）

    Returns:
        Dict: 检查结果，包含 last_execution, gap_hours, is_stale
    """
    if not os.path.exists(EXEC_LOG_FILE):
        return {
            'task_name': task_name,
            'status': 'no_logs',
            'message': '没有执行日志'
        }

    try:
        last_timestamp = None
        with open(EXEC_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get('task_name') == task_name:
                        last_timestamp = entry.get('unix_timestamp')
                except json.JSONDecodeError:
                    continue

        if last_timestamp is None:
            return {
                'task_name': task_name,
                'status': 'never_executed',
                'message': '从未执行过'
            }

        now = time.time()
        gap_hours = (now - last_timestamp) / 3600
        is_stale = gap_hours > max_gap_hours

        return {
            'task_name': task_name,
            'status': 'stale' if is_stale else 'healthy',
            'last_execution': datetime.fromtimestamp(last_timestamp).isoformat(),
            'gap_hours': round(gap_hours, 2),
            'max_gap_hours': max_gap_hours,
            'is_stale': is_stale
        }

    except Exception as e:
        return {
            'task_name': task_name,
            'status': 'error',
            'message': str(e)
        }


def generate_report() -> Dict:
    """
    生成所有任务执行状况摘要

    Returns:
        Dict: 报告摘要
    """
    tasks = scan_crons()
    report = {
        'generated_at': datetime.now().isoformat(),
        'total_tasks': len(tasks),
        'tasks': [],
        'summary': {
            'healthy': 0,
            'stale': 0,
            'no_logs': 0,
            'never_executed': 0,
            'error': 0
        }
    }

    for task in tasks:
        continuity = check_continuity(task['name'])
        task_info = {
            'name': task['name'],
            'schedule': task['schedule'],
            'source': task['source'],
            'continuity': continuity
        }
        report['tasks'].append(task_info)

        # 统计汇总
        status = continuity.get('status', 'unknown')
        if status in report['summary']:
            report['summary'][status] += 1

    return report


def main():
    """命令行入口"""
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python cron_registry.py scan              - 扫描所有 cron 任务")
        print("  python cron_registry.py record <name> <status> <duration>  - 记录执行")
        print("  python cron_registry.py check <name> [hours]  - 检查任务连续性")
        print("  python cron_registry.py report            - 生成执行报告")
        sys.exit(1)

    action = sys.argv[1]

    if action == 'scan':
        tasks = scan_crons()
        print(f"找到 {len(tasks)} 个 cron 任务:")
        for task in tasks:
            print(f"  - {task['name']}: {task['schedule']}")
            print(f"    命令: {task['command'][:60]}...")
            print(f"    来源: {task['source']}\n")

    elif action == 'record':
        if len(sys.argv) < 5:
            print("用法: python cron_registry.py record <name> <status> <duration>")
            sys.exit(1)
        task_name = sys.argv[2]
        status = sys.argv[3]
        duration = float(sys.argv[4])
        if record_execution(task_name, status, duration):
            print(f"✓ 记录成功: {task_name} - {status} - {duration}s")
        else:
            print("✗ 记录失败")

    elif action == 'check':
        if len(sys.argv) < 3:
            print("用法: python cron_registry.py check <name> [max_gap_hours]")
            sys.exit(1)
        task_name = sys.argv[2]
        max_gap = int(sys.argv[3]) if len(sys.argv) > 3 else 48
        result = check_continuity(task_name, max_gap)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif action == 'report':
        report = generate_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))

    else:
        print(f"未知操作: {action}")
        sys.exit(1)


if __name__ == '__main__':
    main()
