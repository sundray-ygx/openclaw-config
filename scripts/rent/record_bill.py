#!/usr/bin/env python3
"""
13B402 水电气数据录入脚本

功能：
1. 交互式录入水电气数据
2. 生成 JSON 数据文件
3. 支持读取账单截图（OCR）
"""

import os
import json
from datetime import datetime

# 配置
RENT_DATA_DIR = "/root/.openclaw/workspace/knowledge/rent"


def input_billing_data():
    """交互式输入账单数据"""

    print("📋 13B402 水电气数据录入")
    print("=" * 40)

    month = input("账单月份（格式：2026-04，默认本月）：") or datetime.now().strftime("%Y-%m")

    print("\n💧 水费信息")
    water = {
        "meter_start": int(input("  上期读数：")),
        "meter_end": int(input("  本期读数：")),
        "amount": float(input("  金额：")),
        "reading_date_start": input("  开始日期（格式：2026-03-01）："),
        "reading_date_end": input("  结束日期（格式：2026-04-01）："),
    }
    water["usage"] = water["meter_end"] - water["meter_start"]
    water["unit"] = "m³"

    print("\n⚡ 电费信息")
    electric = {
        "meter_start": float(input("  上期读数：")),
        "meter_end": float(input("  本期读数：")),
        "amount": float(input("  金额：")),
        "reading_date_start": input("  开始日期（格式：2026-03-01）："),
        "reading_date_end": input("  结束日期（格式：2026-03-31）："),
    }
    electric["usage"] = int(electric["meter_end"] - electric["meter_start"])
    electric["unit"] = "度"

    print("\n🔥 燃气费信息")
    gas_paid = input("  是否已缴清（y/n，默认n）：").lower() == "y"
    gas = {
        "meter_start": int(input("  上期读数（m³）：")),
        "meter_end": int(input("  本期读数（m³）：")),
        "amount": float(input("  金额：")),
        "paid": gas_paid,
        "reading_date_start": input("  开始日期（格式：2026-03-18）："),
        "reading_date_end": input("  结束日期（格式：2026-04-18）："),
    }
    gas["usage"] = gas["meter_end"] - gas["meter_start"]
    gas["unit"] = "m³"

    # 计算天数
    from dateutil import parser as date_parser
    gas_days = (date_parser.parse(gas["reading_date_end"]).date() -
                date_parser.parse(gas["reading_date_start"]).date()).days + 1
    gas["days"] = gas_days

    # 汇总
    data = {
        "room": "13B402",
        "month": month,
        "billing_date": datetime.now().strftime("%Y-%m-%d"),
        "water": water,
        "electric": electric,
        "gas": gas,
        "total": water["amount"] + electric["amount"] + gas["amount"],
        "status": "已缴清" if gas_paid else "待缴",
        "created_at": datetime.now().isoformat()
    }

    return data


def save_billing_data(data):
    """保存账单数据"""
    os.makedirs(RENT_DATA_DIR, exist_ok=True)

    file_path = os.path.join(RENT_DATA_DIR, f"13b402-{data['month']}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return file_path


def main():
    data = input_billing_data()

    print("\n" + "=" * 40)
    print("📊 数据汇总：")
    print(f"  水费：{data['water']['usage']} m³，¥{data['water']['amount']}")
    print(f"  电费：{data['electric']['usage']} 度，¥{data['electric']['amount']}")
    print(f"  燃气费：{data['gas']['usage']} m³，¥{data['gas']['amount']}")
    print(f"  合计：¥{data['total']}")

    confirm = input("\n确认保存？(y/n)：").lower()
    if confirm == "y":
        file_path = save_billing_data(data)
        print(f"\n✅ 数据已保存到：{file_path}")
        print(f"\n下一步：运行账单生成脚本")
        print(f"  python3 scripts/rent/generate_bill.py --month {data['month']} --send --save")
    else:
        print("\n❌ 已取消")


if __name__ == "__main__":
    main()
