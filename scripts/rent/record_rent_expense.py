#!/usr/bin/env python3
"""
16A503 租房支出账单录入脚本
支持图片识别和文本直接录入
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path

# 配置
RENT_EXPENSE_DIR = "/root/.openclaw/workspace/knowledge/rent-expense"

def parse_text_input(text):
    """从文本中提取费用信息"""
    data = {
        "room": "16A503",
        "month": datetime.now().strftime("%Y-%m"),
        "billing_date": datetime.now().strftime("%Y-%m-%d"),
        "rent": {"amount": 0, "period": "", "notes": ""},
        "property_fee": {"amount": 0, "period": "", "notes": ""},
        "water": {"amount": 0, "usage": 0, "unit": "m³", "period": "", "notes": ""},
        "electric": {"amount": 0, "usage": 0, "unit": "度", "period": "", "notes": ""},
        "gas": {"amount": 0, "usage": 0, "unit": "m³", "period": "", "notes": ""},
        "total": 0,
        "payment_status": "待缴",
        "paid_date": None,
        "notes": "",
        "created_at": datetime.now().isoformat()
    }

    # 提取房租
    rent_match = re.search(r'房租[:：\s]*(\d+(?:\.\d+)?)', text)
    if rent_match:
        data["rent"]["amount"] = float(rent_match.group(1))
    rent_period = re.search(r'房租.*?周期[:：\s]*([^\n]+)', text)
    if rent_period:
        data["rent"]["period"] = rent_period.group(1).strip()

    # 提取物业费
    property_match = re.search(r'物业费[:：\s]*(\d+(?:\.\d+)?)', text)
    if property_match:
        data["property_fee"]["amount"] = float(property_match.group(1))
    property_period = re.search(r'物业费.*?周期[:：\s]*([^\n]+)', text)
    if property_period:
        data["property_fee"]["period"] = property_period.group(1).strip()

    # 提取水费
    water_match = re.search(r'水费[:：\s]*(\d+(?:\.\d+)?)', text)
    if water_match:
        data["water"]["amount"] = float(water_match.group(1))
    water_usage = re.search(r'水费.*?用量[:：\s]*(\d+(?:\.\d+)?)\s*(m³|立方|吨)?', text)
    if water_usage:
        data["water"]["usage"] = float(water_usage.group(1))
        if water_usage.group(2):
            data["water"]["unit"] = water_usage.group(2)
    water_period = re.search(r'水费.*?周期[:：\s]*([^\n]+)', text)
    if water_period:
        data["water"]["period"] = water_period.group(1).strip()

    # 提取电费
    electric_match = re.search(r'电费[:：\s]*(\d+(?:\.\d+)?)', text)
    if electric_match:
        data["electric"]["amount"] = float(electric_match.group(1))
    electric_usage = re.search(r'电费.*?用量[:：\s]*(\d+(?:\.\d+)?)\s*(度|kWh)?', text)
    if electric_usage:
        data["electric"]["usage"] = float(electric_usage.group(1))
    electric_period = re.search(r'电费.*?周期[:：\s]*([^\n]+)', text)
    if electric_period:
        data["electric"]["period"] = electric_period.group(1).strip()

    # 提取燃气费
    gas_match = re.search(r'燃气费[:：\s]*(\d+(?:\.\d+)?)', text)
    if gas_match:
        data["gas"]["amount"] = float(gas_match.group(1))
    gas_usage = re.search(r'燃气费.*?用量[:：\s]*(\d+(?:\.\d+)?)\s*(m³|立方|吨)?', text)
    if gas_usage:
        data["gas"]["usage"] = float(gas_usage.group(1))
        if gas_usage.group(2):
            data["gas"]["unit"] = gas_usage.group(2)
    gas_period = re.search(r'燃气费.*?周期[:：\s]*([^\n]+)', text)
    if gas_period:
        data["gas"]["period"] = gas_period.group(1).strip()

    # 计算合计
    data["total"] = (
        data["rent"]["amount"] +
        data["property_fee"]["amount"] +
        data["water"]["amount"] +
        data["electric"]["amount"] +
        data["gas"]["amount"]
    )

    return data

def save_data(data):
    """保存数据到JSON文件"""
    filename = f'16a503-{data["month"]}.json'
    filepath = os.path.join(RENT_EXPENSE_DIR, filename)

    os.makedirs(RENT_EXPENSE_DIR, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath

def generate_markdown_report(data):
    """生成Markdown格式报告"""
    report = f"""# 16A503 租房支出账单 - {data['month']}

**生成时间**: {data['billing_date']}
**合计金额**: ¥{data['total']:.2f}

---

## 🏠 房租

| 项目 | 金额 |
|------|------|
| 金额 | ¥{data['rent']['amount']:.2f} |
| 缴费周期 | {data['rent']['period'] or '-'} |

---

## 🏢 物业费

| 项目 | 金额 |
|------|------|
| 金额 | ¥{data['property_fee']['amount']:.2f} |
| 缴费周期 | {data['property_fee']['period'] or '-'} |

---

## 💧 水费

| 项目 | 金额 |
|------|------|
| 金额 | ¥{data['water']['amount']:.2f} |
| 用量 | {data['water']['usage']} {data['water']['unit']} |
| 缴费周期 | {data['water']['period'] or '-'} |

---

## ⚡ 电费

| 项目 | 金额 |
|------|------|
| 金额 | ¥{data['electric']['amount']:.2f} |
| 用量 | {data['electric']['usage']} {data['electric']['unit']} |
| 缴费周期 | {data['electric']['period'] or '-'} |

---

## 🔥 燃气费

| 项目 | 金额 |
|------|------|
| 金额 | ¥{data['gas']['amount']:.2f} |
| 用量 | {data['gas']['usage']} {data['gas']['unit']} |
| 缴费周期 | {data['gas']['period'] or '-'} |

---

## 📊 费用汇总

| 费用类型 | 金额 | 占比 |
|----------|------|------|
| 房租 | ¥{data['rent']['amount']:.2f} | {data['rent']['amount']/data['total']*100:.1f}% |
| 物业费 | ¥{data['property_fee']['amount']:.2f} | {data['property_fee']['amount']/data['total']*100:.1f}% |
| 水费 | ¥{data['water']['amount']:.2f} | {data['water']['amount']/data['total']*100:.1f}% |
| 电费 | ¥{data['electric']['amount']:.2f} | {data['electric']['amount']/data['total']*100:.1f}% |
| 燃气费 | ¥{data['gas']['amount']:.2f} | {data['gas']['amount']/data['total']*100:.1f}% |
| **合计** | **¥{data['total']:.2f}** | **100%** |

---

## 📝 备注

{data['notes'] or '无'}

---

**数据文件**: {data['room'].lower()}-{data['month']}.json
"""

    return report

def main():
    if len(sys.argv) < 2:
        print("用法: python3 record_rent_expense.py <费用文本>")
        sys.exit(1)

    text = ' '.join(sys.argv[1:])

    # 解析数据
    print(f"解析费用信息...")
    data = parse_text_input(text)

    # 保存数据
    print(f"保存数据到文件...")
    json_file = save_data(data)
    print(f"✅ 数据已保存: {json_file}")

    # 生成报告
    print(f"生成报告...")
    report = generate_markdown_report(data)

    # 保存报告
    report_file = json_file.replace('.json', '-个人查账版.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ 报告已保存: {report_file}")

    # 输出汇总
    print(f"\n📊 费用汇总:")
    print(f"  房租: ¥{data['rent']['amount']:.2f}")
    print(f"  物业费: ¥{data['property_fee']['amount']:.2f}")
    print(f"  水费: ¥{data['water']['amount']:.2f}")
    print(f"  电费: ¥{data['electric']['amount']:.2f}")
    print(f"  燃气费: ¥{data['gas']['amount']:.2f}")
    print(f"  合计: ¥{data['total']:.2f}")

if __name__ == "__main__":
    main()
