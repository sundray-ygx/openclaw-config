#!/usr/bin/env python3
"""
RSS 资讯汇总脚本
直接抓取 RSS 订阅，生成摘要，发送到飞书
"""

import urllib.request
import urllib.parse
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime

# 确保 PATH 包含 /usr/local/bin (summarize 安装位置)
os.environ['PATH'] = '/usr/local/bin:' + os.environ.get('PATH', '')

# 从环境变量读取 API Key（更安全）
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ANTHROPIC_BASE_URL = os.environ.get('ANTHROPIC_BASE_URL', 'https://open.bigmodel.cn/api/coding/paas/v4')

# ============ 配置 ============
FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"

# RSS 订阅源列表（按分类组织）
RSS_FEEDS = [
    # ========== 技术/AI ==========
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "category": "技术/AI"},
    {"name": "博客园", "url": "https://www.cnblogs.com/rss", "category": "技术/AI"},
    {"name": "开源中国", "url": "https://www.oschina.net/news/rss", "category": "技术/AI"},
    # ========== 产品 ==========
    {"name": "人人都是产品经理", "url": "https://www.woshipm.com/feed", "category": "产品"},
    {"name": "少数派", "url": "https://sspai.com/feed", "category": "产品"},
    # ========== 新闻 ==========
    {"name": "钛媒体", "url": "https://www.tmtpost.com/rss.xml", "category": "新闻"},
    {"name": "虎嗅网", "url": "https://www.huxiu.com/rss/0.xml", "category": "新闻"},
    {"name": "36氪", "url": "https://www.36kr.com/feed", "category": "新闻"},
]

MAX_ARTICLES_PER_FEED = 5  # 每个源最多5篇
SUMMARY_LENGTH = "150"  # 摘要长度: 150字符（更精简）

def fetch_rss(feed_url):
    """获取 RSS 内容"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        req = urllib.request.Request(feed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()
    except Exception as e:
        return None

def parse_rss(xml_content, source_name):
    """解析 RSS XML"""
    articles = []
    try:
        root = ET.fromstring(xml_content)
        
        # 处理 RSS 2.0
        if root.tag == "rss":
            channel = root.find("channel")
            if channel is not None:
                for item in channel.findall("item")[:MAX_ARTICLES_PER_FEED]:
                    title = item.find("title")
                    link = item.find("link")
                    pub_date = item.find("pubDate")
                    
                    articles.append({
                        "title": title.text if title is not None else "无标题",
                        "url": link.text if link is not None else "",
                        "date": pub_date.text if pub_date is not None else "",
                        "source": source_name
                    })
        
        # 处理 Atom
        elif "feed" in root.tag:
            for entry in root.findall("{http://www.w3.org/2005/Atom}entry")[:MAX_ARTICLES_PER_FEED]:
                title = entry.find("{http://www.w3.org/2005/Atom}title")
                link = entry.find("{http://www.w3.org/2005/Atom}link")
                pub_date = entry.find("{http://www.w3.org/2005/Atom}updated")
                
                link_url = link.get("href") if link is not None else ""
                
                articles.append({
                    "title": title.text if title is not None else "无标题",
                    "url": link_url,
                    "date": pub_date.text if pub_date is not None else "",
                    "source": source_name
                })
    except Exception as e:
        print(f"解析错误: {e}")
    
    return articles

def summarize_article(url):
    """使用 summarize 生成文章摘要（AI总结，非原文提取）"""
    import subprocess
    import re
    
    # 修复博客园 URL（移除末尾缺失的路径）
    if 'cnblogs.com' in url and url.endswith('/'):
        url = url.rstrip('/')
    
    # 设置 GLM API key 和 base URL 环境变量
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    env["ANTHROPIC_BASE_URL"] = ANTHROPIC_BASE_URL
    
    try:
        # 使用 summarize 生成 AI 摘要
        # 使用 Anthropic 兼容接口（GLM-4.7）
        cmd = [
            "summarize", url, 
            "--length", SUMMARY_LENGTH,
            "--model", "anthropic/claude-3-5-sonnet-20241022"
        ]
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        stdout, stderr = proc.communicate(timeout=60)
        
        if proc.returncode == 0:
            # 清理摘要内容
            summary = stdout.decode('utf-8', errors='ignore').strip()
            # 移除 HTML 标签
            summary = re.sub(r'<[^>]+>', '', summary)
            # 限制长度（更精简，约120字符）
            return summary[:150]
        else:
            error_msg = stderr.decode('utf-8', errors='ignore')
            return f"摘要生成失败: {error_msg[:80]}"
    except Exception as e:
        return f"摘要错误: {str(e)[:80]}"

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

def send_feishu_message(token, content):
    """发送飞书消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    message = {
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        full_url,
        data=json.dumps(message).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("code") == 0
    except:
        return False

def generate_news_summary():
    """生成资讯汇总（按分类呈现）"""
    summary = []
    summary.append("📰 每日资讯摘要")
    summary.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    summary.append("")
    
    # 按分类存储文章
    categorized_articles = {
        "技术/AI": [],
        "产品": [],
        "新闻": []
    }
    
    # 抓取所有 RSS 源
    for feed in RSS_FEEDS:
        print(f"正在抓取: {feed['name']}...")
        xml_content = fetch_rss(feed["url"])
        category = feed.get("category", "新闻")
        if xml_content:
            articles = parse_rss(xml_content, feed["name"])
            for article in articles:
                article["category"] = category
            categorized_articles[category].extend(articles)
            print(f"  ✓ 获取 {len(articles)} 篇文章 [{category}]")
        else:
            print(f"  ✗ 抓取失败 [{category}]")
    
    total_count = sum(len(articles) for articles in categorized_articles.values())
    if total_count == 0:
        summary.append("📭 暂无新文章")
        return "\n".join(summary)
    
    summary.append(f"共 {total_count} 篇文章\n")
    
    # 按分类输出：技术/AI → 产品 → 新闻
    category_order = ["技术/AI", "产品", "新闻"]
    category_emoji = {"技术/AI": "🤖", "产品": "📱", "新闻": "📰"}
    
    for category in category_order:
        articles = categorized_articles[category]
        if not articles:
            continue
        
        summary.append(f"\n{'='*40}")
        summary.append(f"{category_emoji.get(category, '📄')} {category}资讯 ({len(articles)}篇)")
        summary.append(f"{'='*40}\n")
        
        # 每个分类最多显示前10篇
        for i, article in enumerate(articles[:10], 1):
            summary.append(f"【{i}】{article['title']}")
            summary.append(f"来源: {article['source']}")
            
            if article.get('url'):
                # 生成摘要
                print(f"  生成摘要 [{category}]: {article['title'][:30]}...")
                article_summary = summarize_article(article['url'])
                summary.append(f"摘要: {article_summary}")
                summary.append(f"链接: {article['url']}")
            
            summary.append("")
    
    return "\n".join(summary)

if __name__ == "__main__":
    report = generate_news_summary()
    print("\n" + "="*50)
    print(report)
    
    # 保存报告
    output_dir = "/root/news-reports"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/news-summary-{datetime.now().strftime('%Y%m%d')}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n✅ 报告已保存: {output_file}")
    
    # 发送到飞书
    print("\n📤 发送到飞书...")
    token = get_feishu_token()
    if token and send_feishu_message(token, report):
        print("✅ 飞书发送成功")
    else:
        print("❌ 飞书发送失败")
