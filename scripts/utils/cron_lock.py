#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务执行锁
防止定时任务重复执行
"""

import os
import sys
import time
import argparse


LOCK_DIR = '/tmp/openclaw-locks'


def ensure_lock_dir():
    """确保锁目录存在"""
    os.makedirs(LOCK_DIR, exist_ok=True)


def get_lock_path(name):
    """获取锁文件路径"""
    return os.path.join(LOCK_DIR, f'{name}.lock')


def acquire_lock(name, timeout=300):
    """
    尝试获取锁

    Args:
        name: 锁名称
        timeout: 超时时间（秒），默认 300 秒（5 分钟）

    Returns:
        bool: 成功返回 True，失败返回 False
    """
    ensure_lock_dir()
    lock_path = get_lock_path(name)

    # 检查锁是否已存在且未过期
    if os.path.exists(lock_path):
        try:
            lock_time = float(open(lock_path, 'r').read())
            elapsed = time.time() - lock_time

            if elapsed < timeout:
                # 锁仍然有效
                return False
            else:
                # 锁已过期，清理
                try:
                    os.remove(lock_path)
                except:
                    pass
        except:
            # 读取失败，尝试删除锁文件
            try:
                os.remove(lock_path)
            except:
                return False

    # 尝试创建锁文件
    try:
        with open(lock_path, 'w') as f:
            f.write(str(time.time()))
        return True
    except (IOError, OSError):
        return False


def release_lock(name):
    """
    释放锁

    Args:
        name: 锁名称

    Returns:
        bool: 成功返回 True，失败返回 False
    """
    lock_path = get_lock_path(name)

    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
        return True
    except (IOError, OSError):
        return False


def cleanup_expired_locks(timeout=300):
    """
    清理过期的锁文件

    Args:
        timeout: 过期时间（秒）

    Returns:
        int: 清理的锁文件数量
    """
    ensure_lock_dir()
    cleaned = 0
    current_time = time.time()

    try:
        for filename in os.listdir(LOCK_DIR):
            if not filename.endswith('.lock'):
                continue

            lock_path = os.path.join(LOCK_DIR, filename)
            try:
                lock_time = float(open(lock_path, 'r').read())
                elapsed = current_time - lock_time

                if elapsed >= timeout:
                    os.remove(lock_path)
                    cleaned += 1
                    print(f'清理过期锁: {filename}')
            except:
                # 无法读取的锁文件，也尝试删除
                try:
                    os.remove(lock_path)
                    cleaned += 1
                    print(f'清理损坏锁: {filename}')
                except:
                    pass
    except OSError:
        pass

    return cleaned


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='定时任务执行锁管理')
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # acquire 命令
    acquire_parser = subparsers.add_parser('acquire', help='获取锁')
    acquire_parser.add_argument('name', help='锁名称')
    acquire_parser.add_argument('--timeout', type=int, default=300, help='超时时间（秒）')

    # release 命令
    release_parser = subparsers.add_parser('release', help='释放锁')
    release_parser.add_argument('name', help='锁名称')

    # cleanup 命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理过期锁')
    cleanup_parser.add_argument('--timeout', type=int, default=300, help='过期时间（秒）')

    args = parser.parse_args()

    if args.command == 'acquire':
        if acquire_lock(args.name, args.timeout):
            sys.exit(0)
        else:
            sys.exit(1)

    elif args.command == 'release':
        if release_lock(args.name):
            sys.exit(0)
        else:
            sys.exit(1)

    elif args.command == 'cleanup':
        count = cleanup_expired_locks(args.timeout)
        print(f'共清理 {count} 个过期锁文件')
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
