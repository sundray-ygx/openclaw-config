#!/usr/bin/env python3
"""
RSS 资讯汇总脚本 v2 - 使用 summarize 生成 AI 摘要
"""

import urllib.request
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import html
import subprocess

# ============ 配置 ============
FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"

# RSS 订阅源
RSS_FEEDS = [
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "category": "🤖 AI", "limit": 3},
    {"name": "虎嗅网", "url": "https://www.huxiu.com/rss/0.xml", "category": "📰 商业", "limit": 3},
    {"name": "钛媒体", "url": "https://www.tmtpost.com/rss.xml", "category": "📰 商业", "limit": 2},
    {"name": "人人都是产品经理", "url": "https://www.woshipm.com/feed", "category": "📱 产品", "limit": 2},
    {"name": "少数派", "url": "https://sspai.com/feed", "category": "📱 产品", "limit": 2},
]

SUMMARY_LENGTH = "80"  # 摘要字数限制

def get_feishu_token():
    """获取飞书 token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("tenant_access_token")
    except:
        return None

def send_feishu_card(token, user_id, title, elements):
    """发送飞书卡片消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "green"
        },
        "elements": elements
    }
    
    message = {
        "receive_id": user_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False)
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        full_url,
        data=json.dumps(message, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("code") == 0
    except:
        return False

def fetch_rss(feed_url):
    """获取 RSS"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(feed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except Exception as e:
        print(f"  ✗ 抓取失败: {e}")
        return None

def parse_rss(xml_content, source_name, limit):
    """解析 RSS，获取标题和链接"""
    articles = []
    try:
        root = ET.fromstring(xml_content)
        
        if root.tag == "rss":
            channel = root.find("channel")
            if channel:
                for item in channel.findall("item")[:limit]:
                    title = item.find("title")
                    link = item.find("link")
                    
                    title_text = title.text if title is not None else "无标题"
                    title_text = re.sub(r'[#*_`]', '', title_text).strip()[:50]
                    
                    articles.append({
                        "title": title_text,
                        "url": link.text if link is not None else "",
                        "source": source_name
                    })
        
        elif "feed" in root.tag:
            ns = "{http://www.w3.org/2005/Atom}"
            for entry in root.findall(f"{ns}entry")[:limit]:
                title = entry.find(f"{ns}title")
                link = entry.find(f"{ns}link")
                
                title_text = title.text if title is not None else "无标题"
                title_text = re.sub(r'[#*_`]', '', title_text).strip()[:50]
                
                link_url = link.get("href") if link is not None else ""
                
                articles.append({
                    "title": title_text,
                    "url": link_url,
                    "source": source_name
                })
    except Exception as e:
        print(f"  ✗ 解析错误: {e}")
    
    return articles

def summarize_article(url):
    """使用 summarize 生成 AI 摘要"""
    try:
        # 设置环境变量
        env = os.environ.copy()
        env["PATH"] = "/usr/local/bin:" + env.get("PATH", "")
        
        # 调用 summarize
        cmd = ["summarize", url, "--length", SUMMARY_LENGTH, "--model", "anthropic/claude-3-5-sonnet-20241022"]
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        stdout, stderr = proc.communicate(timeout=60)
        
        if proc.returncode == 0:
            summary = stdout.decode('utf-8', errors='ignore').strip()
            # 清理摘要 - 移除 markdown 标题和格式
            summary = re.sub(r'^#+\s*', '', summary)  # 移除标题标记
            summary = re.sub(r'<[^>]+>', '', summary)  # 移除 HTML
            summary = re.sub(r'[#*_`]', '', summary)  # 移除 markdown
            summary = summary.replace('\n', ' ').strip()
            # 限制长度
            if len(summary) > 100:
                summary = summary[:97] + "..."
            return summary
        else:
            error = stderr.decode('utf-8', errors='ignore')[:50]
            print(f"  summarize 失败: {error}")
            return ""
    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"  summarize 超时")
        return ""
    except Exception as e:
        print(f"  summarize 错误: {e}")
        return ""

def generate_summary():
    """生成资讯汇总"""
    now = datetime.now()
    time_str = now.strftime('%m月%d日')
    
    # 按分类收集
    categorized = {}
    total_count = 0
    
    for feed in RSS_FEEDS:
        print(f"正在抓取: {feed['name']}...")
        xml = fetch_rss(feed["url"])
        if xml:
            articles = parse_rss(xml, feed["name"], feed.get("limit", 3))
            cat = feed["category"]
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].extend(articles)
            total_count += len(articles)
            print(f"  ✓ 获取 {len(articles)} 篇 [{cat}]")
    
    if total_count == 0:
        elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": "**📭 暂无新资讯**"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": "所有 RSS 源抓取失败或暂无更新。"}}
        ]
        title = f"📰 资讯简报 | {time_str}"
        return title, elements
    
    # 构建卡片元素
    elements = []
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**📰 共 {total_count} 条精选资讯**"}})
    
    # 按分类输出
    category_order = ["🤖 AI", "📱 产品", "📰 商业"]
    
    for cat in category_order:
        if cat not in categorized or not categorized[cat]:
            continue
        
        articles = categorized[cat]
        elements.append({"tag": "hr"})
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**{cat}** ({len(articles)}篇)"}})
        
        for article in articles:
            # 生成 AI 摘要
            print(f"  生成摘要: {article['title'][:30]}...")
            summary = summarize_article(article['url'])
            
            # 标题 + 链接
            title_line = f"[{article['title']}]({article['url']})"
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": title_line}})
            
            # 摘要
            if summary:
                summary_text = f"*{summary}* ·{article['source']}"
            else:
                summary_text = f"*{article['source']}*"
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": summary_text}})
    
    elements.append({"tag": "hr"})
    elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": "来源: 量子位/虎嗅/钛媒体/PM/少数派"}]})
    
    title = f"📰 资讯简报 | {time_str}"
    return title, elements

if __name__ == "__main__":
    print("=" * 40)
    print("开始生成资讯汇总...")
    print("=" * 40)
    
    title, elements = generate_summary()
    
    print("\n" + "=" * 40)
    print(title)
    
    # 发送到飞书
    print("\n📤 发送到飞书...")
    token = get_feishu_token()
    if token:
        if send_feishu_card(token, FEISHU_USER_ID, title, elements):
            print("✅ 发送成功")
        else:
            print("❌ 发送失败")
    else:
        print("❌ 获取token失败")
