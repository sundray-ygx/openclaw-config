#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置健康检查工具
检查 openclaw.json 配置的完整性和健康状态
"""

import os
import sys
import json
import subprocess


OPENCLAW_CONFIG = '/root/.openclaw/openclaw.json'
REQUIRED_FIELDS = [
    'models',
    'plugins',
    'gateway',
]


def check_json_syntax(config_path):
    """
    检查 JSON 语法是否正确

    Returns:
        dict: {'valid': bool, 'error': str or None}
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return {'valid': True, 'error': None}
    except FileNotFoundError:
        return {'valid': False, 'error': '配置文件不存在'}
    except json.JSONDecodeError as e:
        return {'valid': False, 'error': f'JSON 语法错误: {e}'}
    except Exception as e:
        return {'valid': False, 'error': f'未知错误: {e}'}


def load_config(config_path):
    """
    加载配置文件

    Returns:
        dict or None: 配置内容，失败返回 None
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def check_required_fields(config, required_fields):
    """
    检查必需字段是否存在

    Returns:
        dict: {'missing': list, 'present': list}
    """
    missing = []
    present = []

    for field in required_fields:
        if field in config:
            present.append(field)
        else:
            missing.append(field)

    return {'missing': missing, 'present': present}


def list_cron_jobs():
    """
    列出当前的 cron 任务

    Returns:
        list: cron 任务列表
    """
    try:
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            # 没有设置 crontab 也算正常
            if 'no crontab' in result.stderr.lower():
                return []
            return []

        jobs = []
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            jobs.append(line)

        return jobs

    except subprocess.TimeoutExpired:
        return []
    except FileNotFoundError:
        return []
    except Exception:
        return []


def calculate_health_score(issues):
    """
    计算健康分数（0-100）

    Args:
        issues: 问题列表

    Returns:
        int: 健康分数
    """
    if not issues:
        return 100

    # 根据问题严重程度扣分
    score = 100
    for issue in issues:
        if issue.get('severity') == 'critical':
            score -= 20
        elif issue.get('severity') == 'warning':
            score -= 5

    return max(0, score)


def main():
    """主函数"""
    report = {
        'config_path': OPENCLAW_CONFIG,
        'json_syntax': None,
        'required_fields': None,
        'cron_jobs': [],
        'issues': [],
        'health_score': 0
    }

    # 1. 检查 JSON 语法
    syntax_check = check_json_syntax(OPENCLAW_CONFIG)
    report['json_syntax'] = syntax_check

    if not syntax_check['valid']:
        report['issues'].append({
            'type': 'json_syntax',
            'severity': 'critical',
            'message': syntax_check['error']
        })
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 2. 加载配置并检查必需字段
    config = load_config(OPENCLAW_CONFIG)
    if config is None:
        report['issues'].append({
            'type': 'config_load',
            'severity': 'critical',
            'message': '无法加载配置文件'
        })
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)

    fields_check = check_required_fields(config, REQUIRED_FIELDS)
    report['required_fields'] = fields_check

    if fields_check['missing']:
        report['issues'].append({
            'type': 'missing_fields',
            'severity': 'critical',
            'message': f'缺少必需字段: {", ".join(fields_check["missing"])}'
        })

    # 3. 列出 cron 任务
    cron_jobs = list_cron_jobs()
    report['cron_jobs'] = cron_jobs
    report['cron_job_count'] = len(cron_jobs)

    # 添加信息性消息
    if cron_jobs:
        report['issues'].append({
            'type': 'info',
            'severity': 'info',
            'message': f'发现 {len(cron_jobs)} 个 cron 任务'
        })

    # 4. 计算健康分数
    report['health_score'] = calculate_health_score(report['issues'])

    # 输出报告
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # 根据健康分数返回退出码
    if report['health_score'] >= 80:
        sys.exit(0)
    elif report['health_score'] >= 50:
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == '__main__':
    main()
