#!/usr/bin/env python3
"""
OpenClaw资讯推送脚本
每天8:05自动执行，推送与OpenClaw相关的AI/科技资讯
"""

import urllib.request
import json
import subprocess
import xml.etree.ElementTree as ET
import re
from datetime import datetime

# 飞书配置 - 使用scheduler账号
FEISHU_APP_ID = "cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"

# 关键词（用于筛选与OpenClaw相关的资讯）
KEYWORDS = ["openclaw", "OpenClaw", "AI Agent", "AI代理", "智能体", "Multi-agent", "多智能体"]

# RSS订阅源（AI/科技资讯）
RSS_FEEDS = [
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "category": "🤖 AI"},
    {"name": "钛媒体", "url": "https://www.tmtpost.com/rss.xml", "category": "📱 科技"},
    {"name": "人人都是产品经理", "url": "https://www.woshipm.com/feed", "category": "📱 产品"},
]

def get_feishu_token():
    """获取飞书token"""
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
            "template": "blue"
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
    """获取RSS内容"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(feed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except:
        return None

def parse_rss(xml_content, source_name, category):
    """解析RSS并提取文章"""
    articles = []
    try:
        # 处理命名空间
        xml_str = xml_content.decode('utf-8', errors='ignore')
        xml_str = re.sub(r'xmlns[^=]*="[^"]*"', '', xml_str)
        xml_str = re.sub(r'xmlns:[^=]*="[^"]*"', '', xml_str)
        xml_str = re.sub(r'<([a-zA-Z0-9_]+):', r'<', xml_str)
        xml_str = re.sub(r'</([a-zA-Z0-9_]+):', r'</', xml_str)

        root = ET.fromstring(xml_str)

        for item in root.findall('.//item')[:10]:
            title = item.find('title')
            link = item.find('link')
            desc = item.find('description')

            title_text = title.text if title is not None else ''
            link_text = link.text if link is not None else ''
            desc_text = desc.text if desc is not None else ''

            # 清理CDATA和HTML
            title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_text, flags=re.DOTALL)
            desc_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', desc_text, flags=re.DOTALL)
            desc_text = re.sub(r'<[^>]+>', '', desc_text)

            title_text = re.sub(r'[#*_`]', '', title_text).strip()
            desc_text = desc_text.strip()

            if len(title_text) < 5:
                continue

            articles.append({
                "title": title_text[:60],
                "url": link_text.strip(),
                "summary": desc_text[:100] + "..." if len(desc_text) > 100 else desc_text,
                "source": source_name,
                "category": category
            })
    except Exception as e:
        print(f"  解析{source_name}错误: {e}")

    return articles

def score_article(article):
    """根据关键词匹配度给文章打分"""
    score = 0
    title_lower = article['title'].lower()
    summary_lower = article.get('summary', '').lower()
    text = title_lower + " " + summary_lower

    # OpenClaw直接匹配（最高优先级）
    if 'openclaw' in text:
        score += 100

    # AI Agent相关
    if any(kw.lower() in text for kw in ['ai agent', 'ai代理', '智能体']):
        score += 50

    # Multi-agent相关
    if any(kw.lower() in text for kw in ['multi-agent', '多智能体', 'multi agent']):
        score += 40

    # 大模型相关
    if any(kw.lower() in text for kw in ['大模型', 'llm', 'gpt', 'claude', 'ai模型']):
        score += 20

    # 自动化/工作流相关
    if any(kw.lower() in text for kw in ['自动化', '工作流', 'workflow', 'automation']):
        score += 15

    # 来源权重
    if article['source'] in ['量子位', '机器之心']:
        score += 10

    return score

def get_github_openclaw_news():
    """获取OpenClaw GitHub最新动态"""
    news = []
    try:
        # 获取最新issues
        cmd = 'curl -s "https://api.github.com/repos/openclaw/openclaw/issues?state=all&sort=updated&direction=desc&per_page=2" 2>/dev/null'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if result.returncode == 0 and result.stdout:
            issues = json.loads(result.stdout.decode('utf-8'))
            for issue in issues:
                news.append({
                    "title": f"[GitHub] {issue.get('title', '')[:50]}",
                    "url": issue.get('html_url', ''),
                    "summary": f"{'Issue' if 'pull_request' not in issue else 'PR'} by {issue.get('user', {}).get('login', 'unknown')}",
                    "source": "OpenClaw官方",
                    "category": "🦞 官方",
                    "score": 200
                })

        # 获取最新release
        cmd = 'curl -s "https://api.github.com/repos/openclaw/openclaw/releases/latest" 2>/dev/null'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if result.returncode == 0 and result.stdout:
            release = json.loads(result.stdout.decode('utf-8'))
            if release and 'tag_name' in release:
                news.append({
                    "title": f"[Release] {release.get('tag_name', '')}",
                    "url": release.get('html_url', ''),
                    "summary": f"新版本: {release.get('name', '')[:40]}",
                    "source": "OpenClaw官方",
                    "category": "🦞 官方",
                    "score": 250
                })
    except Exception as e:
        print(f"获取GitHub数据错误: {e}")

    return news

def get_rss_news():
    """从RSS源获取相关资讯"""
    all_articles = []

    for feed in RSS_FEEDS:
        print(f"  获取 {feed['name']}...")
        xml = fetch_rss(feed["url"])
        if xml:
            articles = parse_rss(xml, feed["name"], feed["category"])
            for article in articles:
                article["score"] = score_article(article)
            all_articles.extend(articles)

    # 按分数排序，取前10条
    all_articles.sort(key=lambda x: x["score"], reverse=True)
    return all_articles[:10]

def generate_news_card():
    """生成资讯卡片"""
    print("获取OpenClaw GitHub动态...")
    github_news = get_github_openclaw_news()

    print("获取RSS资讯...")
    rss_news = get_rss_news()

    # 合并并去重
    all_news = github_news + rss_news
    seen_urls = set()
    unique_news = []
    for news in all_news:
        if news['url'] not in seen_urls:
            seen_urls.add(news['url'])
            unique_news.append(news)

    # 按分数排序，取前8条
    unique_news.sort(key=lambda x: x["score"], reverse=True)
    top_news = unique_news[:8]

    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": "**🔔 OpenClaw 相关资讯精选**"}},
        {"tag": "div", "text": {"tag": "lark_md", "content": "*关键词：OpenClaw、AI Agent、智能体、Multi-agent*"}},
        {"tag": "hr"}
    ]

    if not top_news:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "暂无相关资讯"}})
    else:
        current_category = ""
        for news in top_news:
            # 按分类分组
            if news['category'] != current_category:
                current_category = news['category']
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**{current_category}**"}
                })

            # 标题和链接
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"• [{news['title']}]({news['url']})"}
            })
            # 摘要和来源
            if news.get('summary'):
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"  *{news['summary']}* ·{news['source']}"}
                })

    elements.append({"tag": "hr"})
    elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": f"OpenClaw资讯推送 · {datetime.now().strftime('%m月%d日')}"}]})

    return "🦞 OpenClaw 资讯", elements

def main():
    """主函数"""
    print("=" * 40)
    print("生成OpenClaw资讯...")
    print("=" * 40)

    token = get_feishu_token()
    if not token:
        print("获取token失败")
        return False

    title, elements = generate_news_card()

    print("\n发送到飞书...")
    if send_feishu_card(token, FEISHU_USER_ID, title, elements):
        print("发送成功")
        return True
    else:
        print("发送失败")
        return False

if __name__ == "__main__":
    main()
