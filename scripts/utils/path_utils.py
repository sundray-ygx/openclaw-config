#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径验证工具库
提供安全的文件操作工具
"""

import os
import sys


def validate_path(path):
    """
    验证路径状态

    Args:
        path: 文件或目录路径

    Returns:
        dict: 包含 exists, is_file, is_dir, readable, writable 等状态
    """
    result = {
        'path': path,
        'exists': False,
        'is_file': False,
        'is_dir': False,
        'readable': False,
        'writable': False,
        'error': None
    }

    try:
        if not os.path.exists(path):
            result['error'] = '路径不存在'
            return result

        result['exists'] = True
        result['is_file'] = os.path.isfile(path)
        result['is_dir'] = os.path.isdir(path)

        # 检查可读性
        result['readable'] = os.access(path, os.R_OK)

        # 检查可写性（目录检查写入权限，文件检查修改权限）
        result['writable'] = os.access(path, os.W_OK)

    except Exception as e:
        result['error'] = str(e)

    return result


def safe_read(path, default=''):
    """
    安全读取文件内容

    Args:
        path: 文件路径
        default: 读取失败时的默认值

    Returns:
        str: 文件内容或默认值
    """
    try:
        validation = validate_path(path)
        if not validation['exists']:
            return default
        if not validation['is_file']:
            return default
        if not validation['readable']:
            return default

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return default


def safe_write(path, content, create_dirs=True):
    """
    安全写入文件

    Args:
        path: 文件路径
        content: 要写入的内容（字符串或字节）
        create_dirs: 是否自动创建父目录

    Returns:
        bool: 成功返回 True，失败返回 False
    """
    try:
        # 确保父目录存在
        if create_dirs:
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        # 写入文件
        mode = 'wb' if isinstance(content, bytes) else 'w'
        encoding = None if mode == 'wb' else 'utf-8'

        with open(path, mode, encoding=encoding) as f:
            f.write(content)

        return True
    except Exception as e:
        print(f'写入失败 {path}: {e}', file=sys.stderr)
        return False


def safe_append(path, content, create_dirs=True):
    """
    安全追加内容到文件

    Args:
        path: 文件路径
        content: 要追加的内容（字符串或字节）
        create_dirs: 是否自动创建父目录

    Returns:
        bool: 成功返回 True，失败返回 False
    """
    try:
        # 确保父目录存在
        if create_dirs:
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        # 追加到文件
        mode = 'ab' if isinstance(content, bytes) else 'a'
        encoding = None if mode == 'ab' else 'utf-8'

        with open(path, mode, encoding=encoding) as f:
            f.write(content)

        return True
    except Exception as e:
        print(f'追加失败 {path}: {e}', file=sys.stderr)
        return False


def ensure_dir(path):
    """
    确保目录存在

    Args:
        path: 目录路径

    Returns:
        bool: 成功返回 True，失败返回 False
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f'创建目录失败 {path}: {e}', file=sys.stderr)
        return False


def get_file_size(path):
    """
    获取文件大小

    Args:
        path: 文件路径

    Returns:
        int: 文件大小（字节），失败返回 -1
    """
    try:
        return os.path.getsize(path)
    except Exception:
        return -1


def is_empty_file(path):
    """
    检查文件是否为空

    Args:
        path: 文件路径

    Returns:
        bool: 为空返回 True，否则返回 False
    """
    size = get_file_size(path)
    return size == 0


def backup_file(path, suffix='.bak'):
    """
    备份文件

    Args:
        path: 文件路径
        suffix: 备份文件后缀

    Returns:
        str: 备份文件路径，失败返回 None
    """
    try:
        backup_path = path + suffix
        with open(path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        return backup_path
    except Exception:
        return None


def main():
    """主函数 - 测试工具"""
    import argparse

    parser = argparse.ArgumentParser(description='路径验证工具')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # validate 命令
    validate_parser = subparsers.add_parser('validate', help='验证路径')
    validate_parser.add_argument('path', help='路径')

    # read 命令
    read_parser = subparsers.add_parser('read', help='读取文件')
    read_parser.add_argument('path', help='文件路径')
    read_parser.add_argument('--default', default='', help='默认值')

    # write 命令
    write_parser = subparsers.add_parser('write', help='写入文件')
    write_parser.add_argument('path', help='文件路径')
    write_parser.add_argument('content', help='内容')

    args = parser.parse_args()

    if args.command == 'validate':
        result = validate_path(args.path)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == 'read':
        content = safe_read(args.path, args.default)
        print(content)

    elif args.command == 'write':
        if safe_write(args.path, args.content):
            print(f'写入成功: {args.path}')
            sys.exit(0)
        else:
            print(f'写入失败: {args.path}')
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
