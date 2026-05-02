#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 处理工具链

检查 pandas/openpyxl 版本、锁定版本、运行测试。
优先使用标准库，依赖库缺失时给出友好提示。
"""

import os
import sys
import subprocess
from typing import Dict, List, Optional


# 依赖检查
PANDAS_AVAILABLE = False
OPENPYXL_AVAILABLE = None  # None=未检查, True=可用, False=不可用

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass

if PANDAS_AVAILABLE:
    try:
        import openpyxl
        OPENPYXL_AVAILABLE = True
    except ImportError:
        OPENPYXL_AVAILABLE = False


def check_pandas_version() -> Dict[str, Optional[str]]:
    """
    检查 pandas 和 openpyxl 版本

    Returns:
        Dict: 包含版本信息，不可用时为 None
    """
    result = {
        'pandas': None,
        'openpyxl': None,
        'status': 'ok'
    }

    if PANDAS_AVAILABLE:
        result['pandas'] = pd.__version__
    else:
        result['status'] = 'pandas_missing'

    if OPENPYXL_AVAILABLE:
        import openpyxl
        result['openpyxl'] = openpyxl.__version__
    elif PANDAS_AVAILABLE:
        result['status'] = 'openpyxl_missing'

    return result


def lock_versions(requirements_file: str = "requirements-excel.txt") -> bool:
    """
    将当前安装的 pandas 和 openpyxl 版本锁定到文件

    Args:
        requirements_file: 输出文件路径

    Returns:
        bool: 是否锁定成功
    """
    versions = check_pandas_version()

    if versions['pandas'] is None or versions['openpyxl'] is None:
        print("错误: pandas 或 openpyxl 未安装")
        return False

    content = f"pandas=={versions['pandas']}\nopenpyxl=={versions['openpyxl']}\n"

    try:
        with open(requirements_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ 版本已锁定到: {requirements_file}")
        print(content.strip())
        return True
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False


def run_tests(test_dir: str) -> Dict[str, List[str]]:
    """
    对指定目录下的 Excel 文件执行读取测试

    Args:
        test_dir: 测试目录路径

    Returns:
        Dict: 测试结果，包含 success 和 failed 文件列表
    """
    result = {
        'success': [],
        'failed': [],
        'skipped': []
    }

    if not PANDAS_AVAILABLE:
        print("错误: pandas 未安装，无法运行测试")
        print("提示: 运行 'pip install pandas openpyxl' 安装依赖")
        return result

    if not os.path.isdir(test_dir):
        print(f"错误: 目录不存在: {test_dir}")
        return result

    # 支持的扩展名
    extensions = {'.xlsx', '.xls', '.csv'}

    for filename in os.listdir(test_dir):
        filepath = os.path.join(test_dir, filename)

        # 跳过非文件和非 Excel 文件
        if not os.path.isfile(filepath):
            continue

        _, ext = os.path.splitext(filename)
        if ext.lower() not in extensions:
            continue

        print(f"\n测试: {filename}")

        try:
            if ext.lower() == '.csv':
                df = pd.read_csv(filepath, nrows=5)
            else:
                df = pd.read_excel(filepath, nrows=5)

            print(f"  ✓ 读取成功，形状: {df.shape}")
            print(f"  列: {list(df.columns)[:5]}...")
            result['success'].append(filename)

        except Exception as e:
            print(f"  ✗ 读取失败: {e}")
            result['failed'].append({
                'file': filename,
                'error': str(e)
            })

    return result


def install_dependencies() -> bool:
    """
    尝试安装 pandas 和 openpyxl

    Returns:
        bool: 是否安装成功
    """
    print("正在安装依赖: pandas, openpyxl")

    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'pandas', 'openpyxl'],
            check=True,
            timeout=300
        )
        print("✓ 依赖安装成功")
        return True
    except subprocess.TimeoutExpired:
        print("✗ 安装超时")
        return False
    except subprocess.CalledProcessError as e:
        print(f"✗ 安装失败: {e}")
        return False


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='Excel 处理工具链')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # 检查版本命令
    parser_version = subparsers.add_parser('version', help='检查 pandas/openpyxl 版本')

    # 锁定版本命令
    parser_lock = subparsers.add_parser('lock', help='锁定当前版本到文件')
    parser_lock.add_argument('-o', '--output', default='requirements-excel.txt',
                            help='输出文件路径')

    # 运行测试命令
    parser_test = subparsers.add_parser('test', help='运行 Excel 文件读取测试')
    parser_test.add_argument('dir', help='测试目录路径')

    # 安装依赖命令
    parser_install = subparsers.add_parser('install', help='安装 pandas 和 openpyxl')

    args = parser.parse_args()

    if args.command == 'version':
        versions = check_pandas_version()
        print("依赖版本检查:")
        print(f"  pandas: {versions['pandas'] or '未安装'}")
        print(f"  openpyxl: {versions['openpyxl'] or '未安装'}")
        print(f"  状态: {versions['status']}")

        if versions['status'] != 'ok':
            print("\n提示: 运行 'python excel_toolchain.py install' 安装缺失依赖")

    elif args.command == 'lock':
        lock_versions(args.output)

    elif args.command == 'test':
        result = run_tests(args.dir)
        print(f"\n测试总结:")
        print(f"  成功: {len(result['success'])}")
        print(f"  失败: {len(result['failed'])}")

        if result['failed']:
            print("\n失败详情:")
            for fail in result['failed']:
                print(f"  - {fail['file']}: {fail['error']}")

    elif args.command == 'install':
        install_dependencies()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
