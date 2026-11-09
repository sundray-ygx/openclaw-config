#!/usr/bin/env python3
"""
16A503 租房支出统计脚本
按时间段查询统计，生成报告并推送到飞书
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from collections import defaultdict

# 配置
RENT_EXPENSE_DIR = "/root/.openclaw/workspace/knowledge/rent-expense"
FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"

def get_feishu_token():
    """获取飞书tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("tenant_access_token")
    except Exception as e:
        print(f"获取飞书token失败: {e}")
        return None

def load_expense_data(start_date, end_date):
    """加载指定时间范围内的支出数据"""
    expenses = []

    if not os.path.exists(RENT_EXPENSE_DIR):
        return expenses

    for filename in os.listdir(RENT_EXPENSE_DIR):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(RENT_EXPENSE_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查月份是否在范围内
            month = data.get('month', '')
            if start_date <= month <= end_date:
                expenses.append(data)
        except Exception as e:
            print(f"读取文件失败 {filepath}: {e}")

    return sorted(expenses, key=lambda x: x['month'])

def calculate_summary(expenses):
    """计算汇总数据"""
    if not expenses:
        return None

    summary = {
        'total_months': len(expenses),
        'total_amount': 0,
        'categories': {
            'rent': 0,
            'property_fee': 0,
            'water': 0,
            'electric': 0,
            'gas': 0
        },
        'monthly_totals': {},
        'start_month': expenses[0]['month'],
        'end_month': expenses[-1]['month']
    }

    for exp in expenses:
        month = exp['month']
        month_total = 0

        # 房租
        rent = exp.get('rent', {}).get('amount', 0)
        summary['categories']['rent'] += rent
        month_total += rent

        # 物业费
        property_fee = exp.get('property_fee', {}).get('amount', 0)
        summary['categories']['property_fee'] += property_fee
        month_total += property_fee

        # 水费
        water = exp.get('water', {}).get('amount', 0)
        summary['categories']['water'] += water
        month_total += water

        # 电费
        electric = exp.get('electric', {}).get('amount', 0)
        summary['categories']['electric'] += electric
        month_total += electric

        # 燃气费
        gas = exp.get('gas', {}).get('amount', 0)
        summary['categories']['gas'] += gas
        month_total += gas

        summary['monthly_totals'][month] = month_total
        summary['total_amount'] += month_total

    # 计算平均值
    summary['avg_monthly'] = summary['total_amount'] / len(expenses)

    # 计算占比
    for category in summary['categories']:
        summary['categories'][category] = {
            'total': summary['categories'][category],
            'avg': summary['categories'][category] / len(expenses),
            'percent': summary['categories'][category] / summary['total_amount'] * 100 if summary['total_amount'] > 0 else 0
        }

    return summary

def calculate_comparison(current_month, previous_month):
    """计算环比数据"""
    if not current_month or not previous_month:
        return None

    comparison = {
        'rent': {'change': 0, 'percent': 0},
        'property_fee': {'change': 0, 'percent': 0},
        'water': {'change': 0, 'percent': 0},
        'electric': {'change': 0, 'percent': 0},
        'gas': {'change': 0, 'percent': 0},
        'total': {'change': 0, 'percent': 0}
    }

    # 对比各项费用
    for category in ['rent', 'property_fee', 'water', 'electric', 'gas']:
        current = current_month.get(category, {}).get('amount', 0)
        previous = previous_month.get(category, {}).get('amount', 0)

        change = current - previous
        percent = (change / previous * 100) if previous > 0 else 0

        comparison[category]['current'] = current
        comparison[category]['previous'] = previous
        comparison[category]['change'] = change
        comparison[category]['percent'] = percent

    # 对比总额
    current_total = sum([current_month.get(c, {}).get('amount', 0) for c in ['rent', 'property_fee', 'water', 'electric', 'gas']])
    previous_total = sum([previous_month.get(c, {}).get('amount', 0) for c in ['rent', 'property_fee', 'water', 'electric', 'gas']])

    comparison['total']['current'] = current_total
    comparison['total']['previous'] = previous_total
    comparison['total']['change'] = current_total - previous_total
    comparison['total']['percent'] = (current_total - previous_total) / previous_total * 100 if previous_total > 0 else 0

    return comparison

def build_feishu_card(summary, comparison):
    """构建飞书卡片"""
    elements = []

    # 概览
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**📊 16A503 租房支出统计**\n\n**统计周期**: {summary['start_month']} 至 {summary['end_month']}（共{summary['total_months']}个月）\n\n**支出汇总**\n• 总支出: ¥{summary['total_amount']:.2f}\n• 月均支出: ¥{summary['avg_monthly']:.2f}"
        }
    })

    elements.append({"tag": "hr"})

    # 分类统计
    categories_text = "**📈 分类统计**\n\n"
    for category, data in summary['categories'].items():
        name_map = {
            'rent': '🏠 房租',
            'property_fee': '🏢 物业费',
            'water': '💧 水费',
            'electric': '⚡ 电费',
            'gas': '🔥 燃气费'
        }
        categories_text += f"• {name_map[category]}: ¥{data['total']:.2f} (月均¥{data['avg']:.2f}, 占比{data['percent']:.1f}%)\n"

    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": categories_text
        }
    })

    # 环比数据
    if comparison:
        elements.append({"tag": "hr"})
        comparison_text = "**📉 环比变化（本月 vs 上月）**\n\n"

        for category, data in comparison.items():
            if category == 'total':
                name = "💰 合计"
            else:
                name_map = {
                    'rent': '🏠 房租',
                    'property_fee': '🏢 物业费',
                    'water': '💧 水费',
                    'electric': '⚡ 电费',
                    'gas': '🔥 燃气费'
                }
                name = name_map[category]

            arrow = "📈" if data['change'] > 0 else "📉"
            comparison_text += f"• {name}: ¥{data['current']:.2f} vs ¥{data['previous']:.2f} = {arrow} ¥{data['change']:+.2f} ({data['percent']:+.1f}%)\n"

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": comparison_text
            }
        })

    # 月度明细
    if len(summary['monthly_totals']) > 0:
        elements.append({"tag": "hr"})
        monthly_text = "**📅 月度明细**\n\n"
        for month, total in sorted(summary['monthly_totals'].items()):
            monthly_text += f"• {month}: ¥{total:.2f}\n"

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": monthly_text
            }
        })

    card = {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "template": "blue",
            "title": {
                "content": "16A503 租房支出统计报告",
                "tag": "plain_text"
            }
        },
        "elements": elements
    }

    return card

def send_feishu_card(token, user_id, card):
    """发送飞书卡片"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"

    params = {
        "receive_id_type": "open_id"
    }
    full_url = f"{url}?{urllib.parse.urlencode(params)}"

    payload = {
        "receive_id": user_id,
        "msg_type": "interactive",
        "content": json.dumps(card)
    }

    req = urllib.request.Request(
        full_url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            if result.get("code") == 0:
                print("✅ 飞书卡片发送成功")
                return True
            else:
                print(f"❌ 飞书卡片发送失败: {result.get('msg')}")
                return False
    except Exception as e:
        print(f"❌ 发送飞书卡片失败: {e}")
        return False

def main():
    import sys

    # 解析参数
    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date = sys.argv[2] if len(sys.argv) > 2 else None

    # 默认查询最近3个月
    if not start_date:
        end = datetime.now()
        start = end - timedelta(days=90)
        start_date = start.strftime("%Y-%m")
        end_date = end.strftime("%Y-%m")

    print(f"统计周期: {start_date} 至 {end_date}")

    # 加载数据
    expenses = load_expense_data(start_date, end_date)
    print(f"加载到 {len(expenses)} 条记录")

    if not expenses:
        print("没有找到符合条件的记录")
        return

    # 计算汇总
    summary = calculate_summary(expenses)
    print(f"总支出: ¥{summary['total_amount']:.2f}")
    print(f"月均支出: ¥{summary['avg_monthly']:.2f}")

    # 计算环比（最后两个月）
    comparison = None
    if len(expenses) >= 2:
        comparison = calculate_comparison(expenses[-1], expenses[-2])
        print(f"环比变化: {comparison['total']['percent']:+.1f}%")

    # 构建卡片
    card = build_feishu_card(summary, comparison)

    # 发送飞书
    token = get_feishu_token()
    if token:
        send_feishu_card(token, FEISHU_USER_ID, card)
    else:
        print("❌ 无法获取飞书token")

    # 保存报告到文件
    report_file = os.path.join(RENT_EXPENSE_DIR, f"summary-{start_date}-to-{end_date}.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 16A503 租房支出统计报告\n\n")
        f.write(f"**统计周期**: {start_date} 至 {end_date}\n\n")
        f.write(f"**总支出**: ¥{summary['total_amount']:.2f}\n")
        f.write(f"**月均支出**: ¥{summary['avg_monthly']:.2f}\n\n")

        f.write("## 分类统计\n\n")
        for category, data in summary['categories'].items():
            name_map = {
                'rent': '🏠 房租',
                'property_fee': '🏢 物业费',
                'water': '💧 水费',
                'electric': '⚡ 电费',
                'gas': '🔥 燃气费'
            }
            f.write(f"- {name_map[category]}: ¥{data['total']:.2f} (月均¥{data['avg']:.2f}, 占比{data['percent']:.1f}%)\n")

        f.write("\n## 月度明细\n\n")
        for month, total in sorted(summary['monthly_totals'].items()):
            f.write(f"- {month}: ¥{total:.2f}\n")

        if comparison:
            f.write("\n## 环比变化\n\n")
            for category, data in comparison.items():
                if category == 'total':
                    name = "💰 合计"
                else:
                    name_map = {
                        'rent': '🏠 房租',
                        'property_fee': '🏢 物业费',
                        'water': '💧 水费',
                        'electric': '⚡ 电费',
                        'gas': '🔥 燃气费'
                    }
                    name = name_map[category]
                arrow = "↑" if data['change'] > 0 else "↓"
                f.write(f"- {name}: ¥{data['current']:.2f} vs ¥{data['previous']:.2f} = {arrow}¥{data['change']:+.2f} ({data['percent']:+.1f}%)\n")

    print(f"✅ 报告已保存: {report_file}")

if __name__ == "__main__":
    main()
