#!/usr/bin/env python3
"""
外部服务调用重试机制

功能：
1. 自动重试失败的外部服务调用
2. 指数退避策略
3. 失败统计
4. 可配置的重试次数和退避时间
"""

import time
import json
from functools import wraps
from datetime import datetime
from typing import Callable, Any, Optional, Type


# 重试统计
retry_stats = {
    "total_calls": 0,
    "total_retries": 0,
    "failures": {},
    "last_updated": None
}


def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def update_retry_stats(service_name: str, retries: int, success: bool):
    """更新重试统计"""
    retry_stats["total_calls"] += 1
    retry_stats["total_retries"] += retries
    retry_stats["last_updated"] = datetime.now().isoformat()

    if service_name not in retry_stats["failures"]:
        retry_stats["failures"][service_name] = {
            "total_calls": 0,
            "total_retries": 0,
            "failures": 0,
            "successes": 0
        }

    retry_stats["failures"][service_name]["total_calls"] += 1
    retry_stats["failures"][service_name]["total_retries"] += retries

    if success:
        retry_stats["failures"][service_name]["successes"] += 1
    else:
        retry_stats["failures"][service_name]["failures"] += 1


def save_retry_stats(filepath: str = "/root/.openclaw/workspace/logs/retry_stats.json"):
    """保存重试统计"""
    try:
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(retry_stats, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"保存重试统计失败: {e}", "WARN")


def load_retry_stats(filepath: str = "/root/.openclaw/workspace/logs/retry_stats.json"):
    """加载重试统计"""
    global retry_stats
    try:
        import os
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                retry_stats = json.load(f)
    except Exception as e:
        log(f"加载重试统计失败: {e}", "WARN")


def get_retry_stats() -> dict:
    """获取重试统计"""
    return retry_stats.copy()


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    service_name: str = "unknown"
):
    """
    带指数退避的重试装饰器

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
        service_name: 服务名称（用于统计）
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # 成功时更新统计
                    if attempt > 0:
                        log(f"{service_name} 重试 {attempt} 次后成功", "INFO")
                    update_retry_stats(service_name, attempt, True)

                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # 计算退避时间
                        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                        log(f"{service_name} 失败 ({attempt + 1}/{max_retries + 1}), {delay:.1f}秒后重试: {e}", "WARN")
                        time.sleep(delay)
                    else:
                        # 所有重试都失败
                        log(f"{service_name} 重试 {max_retries} 次后仍然失败", "ERROR")
                        update_retry_stats(service_name, max_retries, False)
                        save_retry_stats()  # 保存统计

            # 所有重试都失败，抛出最后一个异常
            raise last_exception

        return wrapper

    return decorator


def retry_call(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    service_name: str = "unknown",
    **kwargs
) -> Any:
    """
    带重试的函数调用（不使用装饰器）

    Args:
        func: 要调用的函数
        *args: 函数参数
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
        service_name: 服务名称
        **kwargs: 函数关键字参数

    Returns:
        函数返回值
    """

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            result = func(*args, **kwargs)

            # 成功时更新统计
            if attempt > 0:
                log(f"{service_name} 重试 {attempt} 次后成功", "INFO")
            update_retry_stats(service_name, attempt, True)

            return result

        except exceptions as e:
            last_exception = e

            if attempt < max_retries:
                # 计算退避时间
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                log(f"{service_name} 失败 ({attempt + 1}/{max_retries + 1}), {delay:.1f}秒后重试: {e}", "WARN")
                time.sleep(delay)
            else:
                # 所有重试都失败
                log(f"{service_name} 重试 {max_retries} 次后仍然失败", "ERROR")
                update_retry_stats(service_name, max_retries, False)
                save_retry_stats()

    # 所有重试都失败，抛出最后一个异常
    raise last_exception


def print_retry_summary():
    """打印重试统计摘要"""
    print("\n" + "=" * 50)
    print("外部服务调用重试统计")
    print("=" * 50)
    print(f"总调用次数: {retry_stats['total_calls']}")
    print(f"总重试次数: {retry_stats['total_retries']}")
    print(f"平均重试次数: {retry_stats['total_retries'] / retry_stats['total_calls']:.2f}" if retry_stats['total_calls'] > 0 else "平均重试次数: 0")
    print(f"最后更新: {retry_stats['last_updated']}")

    if retry_stats['failures']:
        print("\n各服务统计:")
        print("-" * 50)
        for service, stats in retry_stats['failures'].items():
            total = stats['total_calls']
            successes = stats['successes']
            failures = stats['failures']
            retries = stats['total_retries']
            success_rate = (successes / total * 100) if total > 0 else 0
            avg_retries = (retries / total) if total > 0 else 0

            print(f"\n{service}:")
            print(f"  调用次数: {total}")
            print(f"  成功: {successes} ({success_rate:.1f}%)")
            print(f"  失败: {failures}")
            print(f"  总重试: {retries}")
            print(f"  平均重试: {avg_retries:.2f}")

    print("=" * 50 + "\n")


# 使用示例
if __name__ == "__main__":
    # 加载历史统计
    load_retry_stats()

    # 打印摘要
    print_retry_summary()

    # 测试装饰器用法
    @retry_with_backoff(max_retries=3, service_name="测试服务")
    def test_function(fail_times=2):
        """测试函数，前 fail_times 次调用会失败"""
        test_function.call_count = getattr(test_function, 'call_count', 0) + 1

        if test_function.call_count <= fail_times:
            raise Exception("模拟失败")
        return "成功!"

    # 测试
    try:
        result = test_function(fail_times=2)
        print(f"\n测试结果: {result}")
    except Exception as e:
        print(f"\n测试失败: {e}")

    # 再次打印摘要
    print_retry_summary()
