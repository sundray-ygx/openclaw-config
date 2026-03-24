#!/usr/bin/env python3
"""
重新生成指定日期的日报
"""

import os
import sys
from datetime import datetime, timedelta

# 添加daily目录到路径
sys.path.insert(0, '/root/scripts/daily')

from daily_report import generate_daily_report_for_date

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 regenerate_report.py YYYY-MM-DD")
        sys.exit(1)
    
    date_str = sys.argv[1]
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print(f"错误: 日期格式不正确，应为 YYYY-MM-DD")
        sys.exit(1)
    
    print(f"重新生成 {date_str} 的日报...")
    
    # 修改全局变量来指定日期
    import daily_report
    original_get_report_time_range = daily_report.get_report_time_range
    
    def custom_get_report_time_range():
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_time, end_time, date_str
    
    daily_report.get_report_time_range = custom_get_report_time_range
    
    try:
        daily_report.generate_daily_report()
        print(f"✅ {date_str} 日报重新生成完成")
    except Exception as e:
        print(f"❌ 生成失败: {e}")
    finally:
        daily_report.get_report_time_range = original_get_report_time_range
