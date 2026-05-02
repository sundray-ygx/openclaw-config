#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 文件预处理工具

检测文件格式、验证结构、执行预处理（编码转换、格式统一、空值处理）。
支持降级处理：xlsx → xls → csv
"""

import os
import csv
from typing import Dict, List, Optional, Tuple


# 依赖检查
PANDAS_AVAILABLE = False
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pass


def detect_format(filepath: str) -> Dict:
    """
    检测文件类型并检查文件头

    Args:
        filepath: 文件路径

    Returns:
        Dict: 包含 file_type, headers, is_valid, message
    """
    if not os.path.exists(filepath):
        return {
            'file_type': None,
            'is_valid': False,
            'message': '文件不存在'
        }

    filename = os.path.basename(filepath)
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    # 检测文件类型
    file_type = None
    if ext in {'.xlsx', '.xls', '.csv'}:
        file_type = ext[1:]  # 去掉点

    if file_type is None:
        return {
            'file_type': None,
            'is_valid': False,
            'message': f'不支持的文件类型: {ext}'
        }

    # 读取文件头
    headers = None
    try:
        if file_type == 'csv':
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                headers = next(reader, [])

        elif PANDAS_AVAILABLE:
            if file_type == 'xlsx' or file_type == 'xls':
                df = pd.read_excel(filepath, nrows=0)
                headers = df.columns.tolist()

    except Exception as e:
        return {
            'file_type': file_type,
            'is_valid': False,
            'message': f'读取文件头失败: {e}',
            'headers': None
        }

    # 检查文件头是否为空
    if not headers or len(headers) == 0:
        return {
            'file_type': file_type,
            'is_valid': False,
            'message': '文件头为空',
            'headers': None
        }

    return {
        'file_type': file_type,
        'is_valid': True,
        'message': '文件头检测正常',
        'headers': headers,
        'header_count': len(headers)
    }


def validate_structure(filepath: str, expected_headers: List[str]) -> Dict:
    """
    验证文件的列结构

    Args:
        filepath: 文件路径
        expected_headers: 期望的列名列表

    Returns:
        Dict: 验证结果
    """
    detection = detect_format(filepath)

    if not detection['is_valid']:
        return {
            'is_valid': False,
            'message': detection['message'],
            'missing_columns': expected_headers,
            'extra_columns': []
        }

    actual_headers = detection['headers']

    # 标准化列名（去除空格，统一大小写）
    actual_normalized = [h.strip().lower() for h in actual_headers]
    expected_normalized = [h.strip().lower() for h in expected_headers]

    # 检查缺失列
    missing = [expected_headers[i] for i, h in enumerate(expected_normalized)
               if h not in actual_normalized]

    # 检查多余列
    extra = [actual_headers[i] for i, h in enumerate(actual_normalized)
             if h not in expected_normalized]

    is_valid = len(missing) == 0

    return {
        'is_valid': is_valid,
        'message': '列结构验证通过' if is_valid else f'缺少 {len(missing)} 个必需列',
        'missing_columns': missing,
        'extra_columns': extra,
        'actual_headers': actual_headers
    }


def preprocess(filepath: str, output_dir: str,
               encoding: str = 'utf-8-sig',
               fillna_value: str = '') -> Tuple[bool, str]:
    """
    执行文件预处理（编码转换、格式统一、空值处理）

    支持降级处理：xlsx → xls → csv

    Args:
        filepath: 输入文件路径
        output_dir: 输出目录
        encoding: 输出编码
        fillna_value: 空值填充值

    Returns:
        Tuple[bool, str]: (是否成功, 输出文件路径或错误信息)
    """
    if not os.path.exists(filepath):
        return False, '文件不存在'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()

    # 输出文件名统一为 .csv
    output_path = os.path.join(output_dir, f"{name}_preprocessed.csv")

    df = None

    # 尝试按优先级读取
    if ext == '.xlsx' and PANDAS_AVAILABLE:
        try:
            df = pd.read_excel(filepath)
        except Exception as e:
            print(f"读取 xlsx 失败，尝试降级: {e}")

    if df is None and ext in {'.xlsx', '.xls'} and PANDAS_AVAILABLE:
        try:
            df = pd.read_excel(filepath)
        except Exception as e:
            print(f"读取 xls 失败: {e}")

    if df is None and ext == '.csv':
        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
        except UnicodeDecodeError:
            # 尝试其他编码
            for enc in ['gbk', 'gb2312', 'latin1']:
                try:
                    df = pd.read_csv(filepath, encoding=enc)
                    print(f"使用编码 {enc} 读取成功")
                    break
                except:
                    continue

    if df is None:
        # 如果 pandas 不可用，尝试纯 CSV 处理
        if ext == '.csv':
            try:
                df = pd.read_csv(filepath, encoding='utf-8-sig')
            except:
                pass

        if df is None:
            return False, '所有读取方式均失败'

    # 预处理：处理空值
    df = df.fillna(fillna_value)

    # 预处理：去除列名首尾空格
    df.columns = df.columns.str.strip()

    # 保存为 CSV
    try:
        df.to_csv(output_path, index=False, encoding=encoding)
        return True, output_path
    except Exception as e:
        return False, f'保存文件失败: {e}'


def batch_preprocess(input_dir: str, output_dir: str,
                    encoding: str = 'utf-8-sig') -> Dict[str, List[str]]:
    """
    批量预处理目录下的所有 Excel/CSV 文件

    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        encoding: 输出编码

    Returns:
        Dict: 批量处理结果
    """
    result = {
        'success': [],
        'failed': []
    }

    if not os.path.isdir(input_dir):
        print(f"错误: 目录不存在: {input_dir}")
        return result

    extensions = {'.xlsx', '.xls', '.csv'}

    for filename in os.listdir(input_dir):
        filepath = os.path.join(input_dir, filename)

        if not os.path.isfile(filepath):
            continue

        _, ext = os.path.splitext(filename)
        if ext.lower() not in extensions:
            continue

        print(f"\n处理: {filename}")

        success, message = preprocess(filepath, output_dir, encoding)

        if success:
            print(f"  ✓ 成功: {message}")
            result['success'].append(filename)
        else:
            print(f"  ✗ 失败: {message}")
            result['failed'].append({
                'file': filename,
                'error': message
            })

    return result


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='Excel 文件预处理工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # 检测格式命令
    parser_detect = subparsers.add_parser('detect', help='检测文件格式')
    parser_detect.add_argument('file', help='文件路径')

    # 验证结构命令
    parser_validate = subparsers.add_parser('validate', help='验证列结构')
    parser_validate.add_argument('file', help='文件路径')
    parser_validate.add_argument('headers', nargs='+', help='期望的列名')

    # 预处理命令
    parser_preprocess = subparsers.add_parser('preprocess', help='预处理单个文件')
    parser_preprocess.add_argument('file', help='输入文件路径')
    parser_preprocess.add_argument('output_dir', help='输出目录')
    parser_preprocess.add_argument('--encoding', default='utf-8-sig',
                                   help='输出编码 (默认: utf-8-sig)')

    # 批量预处理命令
    parser_batch = subparsers.add_parser('batch', help='批量预处理')
    parser_batch.add_argument('input_dir', help='输入目录')
    parser_batch.add_argument('output_dir', help='输出目录')
    parser_batch.add_argument('--encoding', default='utf-8-sig',
                              help='输出编码 (默认: utf-8-sig)')

    args = parser.parse_args()

    if args.command == 'detect':
        result = detect_format(args.file)
        print(f"文件: {args.file}")
        print(f"类型: {result['file_type']}")
        print(f"状态: {result['message']}")
        if result.get('headers'):
            print(f"列数: {result['header_count']}")
            print(f"列名: {result['headers']}")

    elif args.command == 'validate':
        result = validate_structure(args.file, args.headers)
        print(f"文件: {args.file}")
        print(f"验证结果: {result['message']}")
        if result['missing_columns']:
            print(f"缺失列: {result['missing_columns']}")
        if result['extra_columns']:
            print(f"多余列: {result['extra_columns']}")

    elif args.command == 'preprocess':
        success, message = preprocess(args.file, args.output_dir, args.encoding)
        if success:
            print(f"✓ 预处理成功: {message}")
        else:
            print(f"✗ 预处理失败: {message}")

    elif args.command == 'batch':
        result = batch_preprocess(args.input_dir, args.output_dir, args.encoding)
        print(f"\n批量处理总结:")
        print(f"  成功: {len(result['success'])}")
        print(f"  失败: {len(result['failed'])}")

        if result['failed']:
            print("\n失败详情:")
            for fail in result['failed']:
                print(f"  - {fail['file']}: {fail['error']}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
