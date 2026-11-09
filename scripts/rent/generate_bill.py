#!/usr/bin/env python3
"""
13B402 租金账单自动生成脚本

功能：
1. 按账单周期直接计算水电气费（不分摊）
2. 生成标准格式账单通知
3. 支持保存到文件和发送飞书

使用方式：
  python3 generate_bill.py --month 2026-04 --rent-start 2026-03-26 --rent-end 2026-04-26 [--rent-paid] [--send] [--save]

账单数据文件：knowledge/rent/13b402-YYYY-MM.json
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# ========== 配置 ==========
RENT_DATA_DIR = "/root/.openclaw/workspace/knowledge/rent"
ROOM_CONFIG = {
    "room": "13B402",
    "rent": 4300,
    "property_fee": 159.99,
    "rent_day": 26,  # 每月26日收租
}

FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"


# ========== 飞书发送 ==========
def send_feishu_message(text):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as response:
        token = json.loads(response.read().decode()).get("tenant_access_token")

    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    message_data = json.dumps({
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }).encode()
    req = urllib.request.Request(full_url, data=message_data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }, method="POST")
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read().decode())
        return result.get("code") == 0


# ========== 日期格式化 ==========
def short_date(date_str):
    """2026-03-26 → 3.26"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.month}.{d.day}"


def short_period(start_str, end_str):
    """3.1-4.1"""
    return f"{short_date(start_str)}-{short_date(end_str)}"


# ========== 生成账单 ==========
def generate_bill(bill_data, rent_start, rent_end, rent_paid=False):
    """生成标准格式账单通知"""

    water = bill_data["water"]
    electric = bill_data["electric"]
    gas = bill_data["gas"]

    property_fee = ROOM_CONFIG["property_fee"]
    total = property_fee + water["amount"] + electric["amount"] + gas["amount"]

    # 下月租期
    rent_end_dt = datetime.strptime(rent_end, "%Y-%m-%d")
    next_rent_end = (rent_end_dt + timedelta(days=30)).strftime("%Y-%m-%d")

    # 待出账单：当前账单周期结束后的部分
    next_water_start = datetime.strptime(water["reading_date_end"], "%Y-%m-%d") + timedelta(days=1)
    next_electric_start = datetime.strptime(electric["reading_date_end"], "%Y-%m-%d") + timedelta(days=1)
    next_gas_start = datetime.strptime(gas["reading_date_end"], "%Y-%m-%d") + timedelta(days=1)

    lines = [
        f"🏠 {ROOM_CONFIG['room']} 房租账单通知",
        f"📅 租期：{short_date(rent_start)} - {short_date(rent_end)}",
        "",
        "【费用明细】",
        f"1. 物业费：¥{property_fee}（{short_date(rent_start)}-{short_date(rent_end)}）",
        f"2. 水费：¥{water['amount']} 💧（{short_period(water['reading_date_start'], water['reading_date_end'])}，{water['usage']}m³）",
        f"3. 电费：¥{electric['amount']} ⚡（{short_period(electric['reading_date_start'], electric['reading_date_end'])}，{electric['usage']}度）",
        f"4. 燃气费：¥{gas['amount']} 🔥（{short_period(gas['reading_date_start'], gas['reading_date_end'])}，{gas['usage']}m³）",
        "",
        f"💰 本月应付：¥{total}",
    ]

    if rent_paid:
        lines.append(f"✅ 下月租金（{short_date(rent_end)}-{short_date(next_rent_end)}）：已收 ¥{ROOM_CONFIG['rent']}")
    else:
        lines.append(f"✅ 下月租金（{short_date(rent_end)}-{short_date(next_rent_end)}）：待确认")

    lines += [
        "📝 待出账单（下月结算）：",
        f"• 水费（{short_date(water['reading_date_end'])}-{short_date(rent_end)}）",
        f"• 电费（{short_date(electric['reading_date_end'])}-{short_date(rent_end)}）",
        f"• 燃气费（{short_date(gas['reading_date_end'])}-{short_date(rent_end)}）",
    ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成13B402租金账单")
    parser.add_argument("--month", help="账单月份（格式：2026-04）", default=None)
    parser.add_argument("--rent-start", help="租期开始日期", default=None)
    parser.add_argument("--rent-end", help="租期结束日期", default=None)
    parser.add_argument("--rent-paid", help="下月租金已收", action="store_true")
    parser.add_argument("--send", help="发送到飞书", action="store_true")
    parser.add_argument("--save", help="保存到文件", action="store_true")
    args = parser.parse_args()

    # 确定月份
    month = args.month or datetime.now().strftime("%Y-%m")

    # 加载数据
    bill_file = os.path.join(RENT_DATA_DIR, f"13b402-{month}.json")
    if not os.path.exists(bill_file):
        print(f"❌ 未找到账单数据：{bill_file}")
        sys.exit(1)

    with open(bill_file, "r", encoding="utf-8") as f:
        bill_data = json.load(f)

    # 确定租期（默认上月26日-本月26日）
    if args.rent_start and args.rent_end:
        rent_start = args.rent_start
        rent_end = args.rent_end
    else:
        month_dt = datetime.strptime(month, "%Y-%m")
        rent_start = (month_dt.replace(day=1) - timedelta(days=2)).strftime("%Y-%m-%d")  # 上月最后一天-1 → 26号附近
        # 更精确：本月往前推算到26号
        prev_month = month_dt - timedelta(days=1)
        rent_start = f"{prev_month.year}-{prev_month.month:02d}-{ROOM_CONFIG['rent_day']}"
        rent_end = f"{month_dt.year}-{month_dt.month:02d}-{ROOM_CONFIG['rent_day']}"

    # 生成
    bill_text = generate_bill(bill_data, rent_start, rent_end, args.rent_paid)
    print(bill_text)
    print()

    if args.save:
        save_file = os.path.join(RENT_DATA_DIR, f"13b402-{month}-账单通知.md")
        with open(save_file, "w", encoding="utf-8") as f:
            f.write(bill_text)
        print(f"✅ 已保存：{save_file}")

    if args.send:
        if send_feishu_message(bill_text):
            print("✅ 已发送飞书")
        else:
            print("❌ 飞书发送失败")


if __name__ == "__main__":
    main()
