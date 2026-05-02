#!/usr/bin/env python3
"""
错误分类统计工具

用于日报脚本，对错误进行分类和分级：
1. 按来源分类（系统错误/外部API错误/脚本错误/配置错误）
2. 按严重程度分级（ERROR/WARN/INFO）
3. 统计各类错误的数量和趋势
"""

import re
from datetime import datetime
from typing import Dict, List, Tuple
from enum import Enum


class ErrorLevel(Enum):
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


class ErrorCategory(Enum):
    SYSTEM = "系统错误"
    API = "外部API错误"
    SCRIPT = "脚本错误"
    CONFIG = "配置错误"
    NETWORK = "网络错误"
    DATA = "数据错误"
    EXPECTED = "预期异常"
    UNKNOWN = "未知错误"


# 错误分类规则
ERROR_PATTERNS = [
    # 系统错误
    (ErrorCategory.SYSTEM, ErrorLevel.ERROR, [
        r'Permission denied',
        r'No such file or directory',
        r'IOError',
        r'OSError',
        r'KeyboardInterrupt',
        r'SystemExit'
    ]),

    # 外部API错误
    (ErrorCategory.API, ErrorLevel.ERROR, [
        r'HTTP Error \d{3}',
        r'Connection timeout',
        r'Request failed',
        r'API.*error',
        r'502 Bad Gateway',
        r'503 Service Unavailable',
        r'504 Gateway Timeout'
    ]),

    # 脚本错误
    (ErrorCategory.SCRIPT, ErrorLevel.ERROR, [
        r'NameError',
        r'TypeError',
        r'ValueError',
        r'AttributeError',
        r'KeyError',
        r'IndexError',
        r'SyntaxError',
        r'IndentationError',
        r'Traceback'
    ]),

    # 配置错误
    (ErrorCategory.CONFIG, ErrorLevel.WARN, [
        r'config.*not found',
        r'missing.*config',
        r'invalid.*config',
        r'plugin not found',
        r'setting.*missing'
    ]),

    # 网络错误
    (ErrorCategory.NETWORK, ErrorLevel.WARN, [
        r'Network is unreachable',
        r'Connection refused',
        r'DNS.*failed',
        r'Hostname.*not found',
        r'SSL.*error'
    ]),

    # 数据错误
    (ErrorCategory.DATA, ErrorLevel.WARN, [
        r'data.*corrupt',
        r'invalid.*data',
        r'parse.*error',
        r'decode.*error'
    ]),

    # 预期异常（可以降级为INFO）
    (ErrorCategory.EXPECTED, ErrorLevel.INFO, [
        r'file not found.*expected',
        r'optional.*missing',
        r'skipped.*not found',
        r'cache.*miss',
        r'预期异常'
    ]),
]


def classify_error(error_message: str) -> Tuple[ErrorCategory, ErrorLevel]:
    """
    对错误消息进行分类

    Args:
        error_message: 错误消息

    Returns:
        (category, level) 分类结果
    """
    error_message_lower = error_message.lower()

    # 检查每个分类规则
    for category, level, patterns in ERROR_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                return category, level

    # 如果没有匹配到，返回未知
    return ErrorCategory.UNKNOWN, ErrorLevel.ERROR


def analyze_errors(error_lines: List[str]) -> Dict:
    """
    分析错误列表

    Args:
        error_lines: 错误行列表

    Returns:
        分析结果字典
    """
    stats = {
        "total": len(error_lines),
        "by_category": {},
        "by_level": {},
        "errors": []
    }

    # 初始化统计
    for category in ErrorCategory:
        stats["by_category"][category] = 0
    for level in ErrorLevel:
        stats["by_level"][level] = 0

    # 分析每个错误
    for error_line in error_lines:
        category, level = classify_error(error_line)

        stats["by_category"][category] += 1
        stats["by_level"][level] += 1

        stats["errors"].append({
            "message": error_line,
            "category": category.value,
            "level": level.value
        })

    return stats


def should_log_as_info(error_message: str) -> bool:
    """
    判断错误是否应该降级为INFO级别

    Args:
        error_message: 错误消息

    Returns:
        True 如果应该降级为INFO
    """
    category, level = classify_error(error_message)
    return level == ErrorLevel.INFO


def generate_error_report(stats: Dict) -> str:
    """
    生成错误报告

    Args:
        stats: 分析结果

    Returns:
        格式化的报告文本
    """
    report = []
    report.append("\n" + "=" * 50)
    report.append("错误分类统计报告")
    report.append("=" * 50)
    report.append(f"总错误数: {stats['total']}")
    report.append("")

    # 按严重程度统计
    report.append("按严重程度:")
    for level in [ErrorLevel.ERROR, ErrorLevel.WARN, ErrorLevel.INFO]:
        count = stats['by_level'][level]
        if count > 0:
            report.append(f"  {level.value}: {count}")
    report.append("")

    # 按类别统计
    report.append("按类别:")
    for category in [ErrorCategory.SYSTEM, ErrorCategory.API, ErrorCategory.SCRIPT,
                     ErrorCategory.CONFIG, ErrorCategory.NETWORK, ErrorCategory.DATA,
                     ErrorCategory.EXPECTED, ErrorCategory.UNKNOWN]:
        count = stats['by_category'][category]
        if count > 0:
            report.append(f"  {category.value}: {count}")
    report.append("")

    # 最重要的错误（ERROR级别）
    error_level_errors = [e for e in stats['errors'] if e['level'] == ErrorLevel.ERROR.value]
    if error_level_errors:
        report.append("严重错误 (需要关注):")
        for error in error_level_errors[:5]:  # 最多显示5个
            report.append(f"  [{error['category']}] {error['message'][:80]}...")
        if len(error_level_errors) > 5:
            report.append(f"  ... 还有 {len(error_level_errors) - 5} 个")
        report.append("")

    # 可以降级的错误
    info_level_errors = [e for e in stats['errors'] if e['level'] == ErrorLevel.INFO.value]
    if info_level_errors:
        report.append(f"可降级为INFO的错误 ({len(info_level_errors)}个):")
        for error in info_level_errors[:3]:
            report.append(f"  - {error['message'][:60]}...")
        if len(info_level_errors) > 3:
            report.append(f"  ... 还有 {len(info_level_errors) - 3} 个")
        report.append("")

    report.append("=" * 50)

    return "\n".join(report)


# 使用示例
if __name__ == "__main__":
    # 测试用例
    test_errors = [
        "HTTP Error 404: Not Found",
        "FileNotFoundError: config.json not found",
        "Permission denied: /etc/hosts",
        "Connection timeout: api.example.com",
        "TypeError: 'NoneType' object is not subscriptable",
        "plugin not found: skillhub",
        "optional file missing, skipping...",
        "Network is unreachable",
        "KeyError: 'api_key'",
        "data parse error: invalid JSON"
    ]

    # 分析
    stats = analyze_errors(test_errors)

    # 生成报告
    print(generate_error_report(stats))

    # 测试单个错误分类
    print("\n单个错误分类测试:")
    for error in test_errors:
        category, level = classify_error(error)
        print(f"  [{level.value}] {error[:50]}... -> {category.value}")
