#!/usr/bin/env python3
"""账单报表生成器 - 从 Notion API 拉取数据生成月度报表"""

import json, urllib.request, sys
from collections import defaultdict

NOTION_KEY = "ntn_REDACTED"
EXPENSE_DB = "2317772a40118156bc4dc62838b51e51"
INCOME_DB  = "2317772a4011815d9cb7f25986519f11"

MONTH_NAMES = {f"{i:02d}": f"{i}月" for i in range(1, 13)}

def query_notion(db_id, year="2026"):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    results = []
    body = {"page_size": 100, "filter": {"property": "Date", "date": {"on_or_after": f"{year}-01-01"}}}
    has_more = True
    start_cursor = None
    while has_more:
        if start_cursor:
            body["start_cursor"] = start_cursor
        req = urllib.request.Request(url, method="POST",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {NOTION_KEY}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
    return results

def extract(props, key, ptype):
    p = props.get(key, {})
    if ptype == "number": return p.get("number") or 0
    elif ptype == "select":
        s = p.get("select")
        return s.get("name", "") if s else ""
    elif ptype == "date":
        d = p.get("date")
        return d.get("start", "") if d else ""
    return ""

def generate_report(year="2026", top_n=3):
    expense_pages = query_notion(EXPENSE_DB, year)
    income_pages = query_notion(INCOME_DB, year)

    months_exp = defaultdict(lambda: defaultdict(float))
    months_inc = defaultdict(float)
    by_from = defaultdict(float)
    by_category = defaultdict(float)

    for p in expense_pages:
        props = p.get("properties", {})
        price = extract(props, "Price", "number")
        date = extract(props, "Date", "date")
        cat = extract(props, "Category", "select")
        src = extract(props, "From", "select")
        if date:
            m = date[:7]
            months_exp[m][cat] += price
            by_from[src] += price
            by_category[cat] += price

    for p in income_pages:
        props = p.get("properties", {})
        price = extract(props, "Price", "number")
        date = extract(props, "Date", "date")
        if date:
            months_inc[date[:7]] += price

    # Output
    lines = []
    lines.append(f"📊 {year}年 月度财务概览")
    lines.append("=" * 65)
    lines.append(f"{'月份':<6} {'收入':>12} {'支出':>12} {'结余':>12}")
    lines.append("-" * 65)

    total_inc = total_exp = 0
    for m in sorted(set(list(months_exp.keys()) + list(months_inc.keys()))):
        inc = months_inc.get(m, 0)
        exp = sum(months_exp.get(m, {}).values())
        total_inc += inc
        total_exp += exp
        mm = MONTH_NAMES.get(m[5:], m)
        lines.append(f"{mm:<6} ¥{inc:>10,.2f} ¥{exp:>10,.2f} ¥{inc-exp:>10,.2f}")
        cats = sorted(months_exp.get(m, {}).items(), key=lambda x: x[1], reverse=True)[:top_n]
        if cats:
            cat_str = " | ".join([f"{c}: ¥{a:,.0f}" for c, a in cats])
            lines.append(f"       ↳ {cat_str}")

    lines.append("-" * 65)
    lines.append(f"{'合计':<6} ¥{total_inc:>10,.2f} ¥{total_exp:>10,.2f} ¥{total_inc-total_exp:>10,.2f}")
    lines.append(f"\n储蓄率: {(total_inc-total_exp)/total_inc*100:.1f}%")

    # Platform breakdown
    lines.append(f"\n支出平台分布:")
    for f in sorted(by_from.keys(), key=lambda x: by_from[x], reverse=True):
        lines.append(f"  {f}: ¥{by_from[f]:,.2f} ({by_from[f]/total_exp*100:.1f}%)")

    # Category TOP10
    lines.append(f"\n支出分类 TOP10:")
    for cat, amt in sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:10]:
        lines.append(f"  {cat}: ¥{amt:,.2f} ({amt/total_exp*100:.1f}%)")

    return "\n".join(lines)

if __name__ == "__main__":
    year = sys.argv[1] if len(sys.argv) > 1 else "2026"
    print(generate_report(year))
