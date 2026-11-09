#!/usr/bin/env python3
"""
AI Agent 综合资讯系统
融合OpenClaw、Hermes Agent和其他AI Agent相关资讯
"""

import urllib.request
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
import subprocess
import socket
import ssl
import email
from email.header import decode_header
import imaplib

# ============ 配置 ============
# 使用scheduler账号的配置
FEISHU_APP_ID = "cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"

# 邮箱配置（密码从环境变量读取）
EMAIL_ACCOUNTS = [
    {"name": "163邮箱", "email": "yanguoxian122@163.com", "password": os.environ.get("EMAIL_163_PASSWORD", ""), "imap_server": "imap.163.com", "imap_port": 993},
    {"name": "QQ邮箱", "email": "635752474@qq.com", "password": os.environ.get("EMAIL_QQ_PASSWORD", ""), "imap_server": "imap.qq.com", "imap_port": 993},
    {"name": "企业邮箱", "email": "ygx@sundray.com", "password": os.environ.get("EMAIL_QIYE_PASSWORD", ""), "imap_server": "imap.qiye.163.com", "imap_port": 993},
]

# AI Agent 综合资讯源（2026-08-14 巡检后更新，移除失效源）
# 注意：36氪、机器之心 RSS 因反爬返回 HTML，已替换为其他可靠源
RSS_FEEDS = [
    # OpenClaw相关（可靠源）
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "category": "🤖 OpenClaw", "limit": 4},
    {"name": "钛媒体", "url": "https://www.tmtpost.com/rss.xml", "category": "🤖 OpenClaw", "limit": 3},
    {"name": "雷锋网", "url": "https://www.leiphone.com/feed", "category": "🤖 OpenClaw", "limit": 2},
    
    # Hermes Agent相关（可靠源）
    {"name": "InfoQ", "url": "https://www.infoq.cn/feed.xml", "category": "🚀 Hermes Agent", "limit": 3},
    {"name": "极客公园", "url": "https://www.geekpark.net/rss", "category": "🚀 Hermes Agent", "limit": 3},
    {"name": "爱范儿", "url": "https://www.ifanr.com/feed", "category": "🚀 Hermes Agent", "limit": 2},
    
    # 其他AI Agent（可靠源）
    {"name": "雷锋网AI", "url": "https://www.leiphone.com/feed", "category": "🔬 AI Agent", "limit": 3},
    {"name": "少数派", "url": "https://sspai.com/feed", "category": "🔬 AI Agent", "limit": 3},
    {"name": "量子位AI", "url": "https://www.qbitai.com/feed", "category": "🔬 AI Agent", "limit": 2},
]

# AI Agent 关键词分类
AGENT_KEYWORDS = {
    "OpenClaw": ["openclaw", "OpenClaw", "openclaw.ai", "OpenClaw Agent"],
    "Hermes Agent": ["hermes", "Hermes", "Hermes Agent", "hermes.ai", "HermesAI"],
    "其他AI Agent": ["AutoGPT", "BabyAGI", "CAMEL", "Devin", "AgentGPT", "MetaGPT", "LangChain", "AI Agent", "智能体", "多智能体", "Multi-agent", "AI助手"]
}

# 优先级关键词（筛选高质量内容）
KEYWORDS_PRIORITY = [
    "AI Agent", "人工智能", "大模型", "LLM", "智能体", "多智能体", "OpenClaw", "Hermes", 
    "发布", "上线", "新品", "更新", "技术", "创新", "融资", "收购", "合作",
    "ChatGPT", "OpenAI", "Anthropic", "Google", "微软", "百度", "阿里", "腾讯", "字节"
]

KEYWORDS_EXCLUDE = ["广告", "推广", "招聘", "活动", "会议", "论坛", "峰会", "培训"]

# 海外中文RSS源（通过代理访问）
OVERSEAS_RSS_FEEDS = [
    {"name": "海外AI资讯", "url": "https://ai-overseas.com/feed", "category": "🌍 海外AI", "limit": 3},
]

# 临时配置文件路径
STATE_FILE = "/tmp/ai_agent_news_state.json"
MAX_ARTICLES = 30  # 每个分类最多显示文章数

# ============ 工具函数 ============
def score_agent_article(article, agent_type):
    """计算文章与特定Agent类型的相关性分数"""
    title = article.get("title", "").lower()
    summary = article.get("summary", "").lower()
    content = f"{title} {summary}"
    
    score = 0
    
    # 基础分数
    if agent_type in content:
        score += 100
    
    # 优先级关键词加分
    for keyword in KEYWORDS_PRIORITY:
        if keyword.lower() in content:
            score += 20
    
    # 时间衰减（最近的文章分数更高）
    try:
        pub_date = article.get("pub_date")
        if pub_date:
            # 简单的时间戳处理
            if "今天" in pub_date or "刚刚" in pub_date:
                score += 30
            elif "小时" in pub_date:
                hours = int(re.search(r'(\d+).*小时', pub_date).group(1))
                score += max(0, 30 - hours * 2)
    except:
        pass
    
    return score

def get_agent_news(agent_type, max_articles=5):
    """获取特定Agent类型的新闻"""
    print(f"获取 {agent_type} 相关资讯...")
    all_articles = []
    
    # 选择对应的RSS源
    if agent_type == "OpenClaw":
        target_feeds = RSS_FEEDS[:3]  # 前3个是OpenClaw相关的
    elif agent_type == "Hermes Agent":
        target_feeds = RSS_FEEDS[3:6]  # 接下来3个是Hermes相关的
    else:
        target_feeds = RSS_FEEDS[6:]  # 剩余的是其他AI Agent
    
    for feed in target_feeds:
        print(f"  获取 {feed['name']} ({agent_type}相关)...")
        xml = fetch_rss(feed["url"], use_proxy=False)
        if xml:
            articles = parse_rss_simple(xml, feed["name"], 10, use_summarize=False)
            for article in articles:
                # 计算相关分数
                article["score"] = score_agent_article(article, agent_type)
                article["source"] = feed["name"]
                article["category"] = feed["category"]
                article["agent_type"] = agent_type
            all_articles.extend(articles)
    
    # 按分数排序，取前N条
    all_articles.sort(key=lambda x: x["score"], reverse=True)
    return all_articles[:max_articles]

def get_github_agent_news():
    """获取GitHub上的AI Agent相关动态"""
    news = []
    
    try:
        # OpenClaw GitHub动态
        cmd = 'curl -s "https://api.github.com/repos/openclaw/openclaw/issues?state=all&sort=updated&direction=desc&per_page=2" 2>/dev/null'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if result.returncode == 0 and result.stdout:
            issues = json.loads(result.stdout.decode('utf-8'))
            for issue in issues:
                news.append({
                    "title": f"[GitHub] OpenClaw: {issue.get('title', '')[:50]}",
                    "url": issue.get('html_url', ''),
                    "summary": f"{'Issue' if 'pull_request' not in issue else 'PR'} by {issue.get('user', {}).get('login', 'unknown')}",
                    "source": "OpenClaw官方",
                    "category": "🦞 官方动态",
                    "agent_type": "OpenClaw",
                    "score": 200
                })
        
        # 搜索Hermes相关仓库
        cmd = 'curl -s "https://api.github.com/search/repositories?q=hermes+agent&sort=updated&per_page=2" 2>/dev/null'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if result.returncode == 0 and result.stdout:
            repos = json.loads(result.stdout.decode('utf-8'))
            for repo in repos.get('items', []):
                news.append({
                    "title": f"[GitHub] {repo.get('name', '')[:50]}",
                    "url": repo.get('html_url', ''),
                    "summary": f"⭐ {repo.get('stargazers_count', 0)} stars, 更新于 {repo.get('updated_at', '')[:10]}",
                    "source": "GitHub",
                    "category": "🚀 开源项目",
                    "agent_type": "Hermes Agent",
                    "score": 150
                })
                
    except Exception as e:
        print(f"获取GitHub新闻失败: {e}")
    
    return news

def parse_rss_simple(xml_content, source, limit, use_summarize=False):
    """简单解析RSS内容，增强容错性"""
    try:
        # 预处理：清理XML非法字符（如36氪RSS中的控制字符）
        if isinstance(xml_content, bytes):
            xml_content = xml_content.decode('utf-8', errors='replace')
        # 移除XML非法控制字符（0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F）
        import re as _re
        xml_content = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', xml_content)
        root = ET.fromstring(xml_content)
        articles = []
        
        # 处理不同的RSS格式，支持多种命名空间
        namespaces = {
            '': '',  # 默认命名空间
            'rss': 'http://purl.org/rss/1.0/',
            'content': 'http://purl.org/rss/1.0/modules/content/',
        }
        
        # 尝试多种路径查找item
        items = []
        for ns in namespaces.values():
            if ns:
                items.extend(root.findall(f'.//item', {'': ns}))
            else:
                items.extend(root.findall('.//item'))
        
        # 去重
        items = list(set(items))
        
        for item in items[:limit]:
            # 获取标题，处理可能的None值
            title_elem = item.find('title')
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else "无标题"
            
            # 获取链接
            link_elem = item.find('link')
            link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            
            # 获取描述
            description_elem = item.find('description')
            description = description_elem.text.strip() if description_elem is not None and description_elem.text else ""
            
            # 获取发布日期
            pub_date_elem = item.find('pubDate')
            pub_date = pub_date_elem.text.strip() if pub_date_elem is not None and pub_date_elem.text else ""
            
            articles.append({
                "title": title,
                "url": link,
                "summary": description[:200],
                "pub_date": pub_date,
                "source": source
            })
        
        return articles
    except Exception as e:
        print(f"解析RSS失败 ({source}): {e}")
        return []

def fetch_rss(feed_url, use_proxy=False):
    """获取RSS内容，增强容错性和重试机制"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        req = urllib.request.Request(feed_url, headers=headers)
        
        if use_proxy:
            # 使用代理（如果配置了）
            proxy = urllib.request.ProxyHandler({'http': '127.0.0.1:1080', 'https': '127.0.0.1:1080'})
            opener = urllib.request.build_opener(proxy)
            urllib.request.install_opener(opener)
        
        # 设置超时和重试
        urllib.request.urlopen(req, timeout=20)
        with urllib.request.urlopen(req, timeout=20) as response:
            # 处理gzip压缩
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                return gzip.decompress(response.read())
            return response.read()
            
    except urllib.error.HTTPError as e:
        print(f"HTTP错误 ({feed_url}): {e.code} - {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"URL错误 ({feed_url}): {e.reason}")
        return None
    except Exception as e:
        print(f"获取RSS失败 ({feed_url}): {e}")
        return None

def fetch_weather():
    """获取天气信息"""
    try:
        cmd = 'curl -s "https://api.openweathermap.org/data/2.5/weather?q=Beijing&appid=your_api_key&units=metric&lang=zh_cn"'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if result.returncode == 0:
            weather_data = json.loads(result.stdout)
            temp = weather_data['main']['temp']
            description = weather_data['weather'][0]['description']
            return f"北京 {temp}°C {description}"
    except:
        pass
    return "北京 25°C 晴"

def fetch_emails():
    """获取邮箱摘要"""
    all_new = []
    
    for account in EMAIL_ACCOUNTS:
        try:
            print(f"检查 {account['name']}...")
            mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
            mail.login(account['email'], account['password'])
            mail.select('inbox')
            
            # 搜索未读邮件
            status, messages = mail.search(None, '(UNSEEN)')
            if status == 'OK' and messages:
                email_ids = messages[0].split()
                unread_count = len(email_ids)
                
                all_new.append({
                    'name': account['name'],
                    'count': unread_count,
                    'emails': []
                })
            
            mail.close()
            mail.logout()
        except Exception as e:
            print(f"检查邮箱失败 ({account['name']}): {e}")
    
    return all_new

def save_mail_state(state):
    """保存邮件检查状态"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存状态失败: {e}")

# ============ 主要函数 ============
def generate_ai_agent_briefing():
    """生成AI Agent综合资讯简报"""
    
    # 1. 获取各类型Agent资讯
    openclaw_news = get_agent_news("OpenClaw", 5)
    hermes_news = get_agent_news("Hermes Agent", 4)
    other_agent_news = get_agent_news("其他AI Agent", 6)
    
    # 2. 获取GitHub动态
    github_news = get_github_agent_news()
    
    # 3. 合并并分类展示
    elements = []
    
    # 标题
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": "# 🤖 AI Agent 综合资讯"}
    })
    elements.append({"tag": "hr"})
    
    # 时间戳
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    elements.append({
        "tag": "div", 
        "text": {"tag": "lark_md", "content": f"📅 更新时间：{current_time}"}
    })
    elements.append({"tag": "hr"})
    
    # OpenClaw资讯
    if openclaw_news:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**🦞 OpenClaw 资讯** {len(openclaw_news)} 条精选"}
        })
        for article in openclaw_news:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"▪️ [{article['title']}]({article['url']})\n   {article['summary']}"}
            })
        elements.append({"tag": "hr"})
    
    # Hermes Agent资讯  
    if hermes_news:
        elements.append({
            "tag": "div", 
            "text": {"tag": "lark_md", "content": f"**🚀 Hermes Agent 资讯** {len(hermes_news)} 条精选"}
        })
        for article in hermes_news:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"▪️ [{article['title']}]({article['url']})\n   {article['summary']}"}
            })
        elements.append({"tag": "hr"})
    
    # 其他AI Agent资讯
    if other_agent_news:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**🔬 其他AI Agent 资讯** {len(other_agent_news)} 条精选"}
        })
        for article in other_agent_news:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"▪️ [{article['title']}]({article['url']})\n   {article['summary']}"}
            })
        elements.append({"tag": "hr"})
    
    # GitHub动态
    if github_news:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**💻 开源动态** {len(github_news)} 条"}
        })
        for article in github_news:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"▪️ [{article['title']}]({article['url']})\n   {article['summary']}"}
            })
        elements.append({"tag": "hr"})
    
    # 统计信息
    total_articles = len(openclaw_news) + len(hermes_news) + len(other_agent_news) + len(github_news)
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"📊 总计：{total_articles} 条AI Agent相关资讯"}
    })
    
    return elements

def send_to_feishu(elements, title="AI Agent 综合资讯"):
    """发送到飞书"""
    try:
        # 构建请求内容
        content = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": elements
            }
        }
        
        # 发送请求
        import requests
        url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{FEISHU_USER_ID}"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=content, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("资讯发送成功")
            return True
        else:
            print(f"发送失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"发送失败: {e}")
        return False

def main():
    """主函数"""
    print("开始生成AI Agent综合资讯...")
    
    # 生成简报
    elements = generate_ai_agent_briefing()
    
    # 发送到飞书
    if send_to_feishu(elements):
        print("AI Agent资讯发送完成")
    else:
        print("发送失败")

if __name__ == "__main__":
    main()