#!/usr/bin/env python3
"""
AI Agent 综合资讯系统 V2 - 基于现有成功系统优化
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
import requests

# ============ 配置 ============
# 使用scheduler账号的配置
FEISHU_APP_ID = "cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET = "gK0tXR…SAsl"
FEISHU_USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"

# AI Agent 关键词分类
AGENT_KEYWORDS = {
    "OpenClaw": ["openclaw", "OpenClaw", "openclaw.ai", "OpenClaw Agent"],
    "Hermes Agent": ["hermes", "Hermes", "Hermes Agent", "hermes.ai", "HermesAI", "Hermes"],
    "其他AI Agent": ["AutoGPT", "BabyAGI", "CAMEL", "Devin", "AgentGPT", "MetaGPT", "LangChain", "AI Agent", "智能体", "多智能体", "Multi-agent", "AI助手", "Claude", "Gemini"]
}

# 优先级关键词（筛选高质量内容）
KEYWORDS_PRIORITY = [
    "AI Agent", "人工智能", "大模型", "LLM", "智能体", "多智能体", "OpenClaw", "Hermes", 
    "发布", "上线", "新品", "更新", "技术", "创新", "融资", "收购", "合作",
    "ChatGPT", "OpenAI", "Anthropic", "Google", "微软", "百度", "阿里", "腾讯", "字节",
    "发布", "开源", "版本", "功能", "特性"
]

KEYWORDS_EXCLUDE = ["广告", "推广", "招聘", "活动", "会议", "论坛", "峰会", "培训", "课程"]

# 使用现有的可靠RSS源
RSS_SOURCES = {
    "openclaw": [
        {"name": "量子位", "url": "https://www.qbitai.com/feed", "limit": 3},
        {"name": "36氪", "url": "https://36kr.com/feed", "limit": 3},
        {"name": "钛媒体", "url": "https://www.tmtpost.com/rss.xml", "limit": 3}
    ],
    "hermes": [
        {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss", "limit": 2},
        {"name": "新智元", "url": "https://www.jiqizhixin.com/feed", "limit": 2},
        {"name": "钛媒体", "url": "https://www.tmtpost.com/rss.xml", "limit": 2}
    ],
    "other_agents": [
        {"name": "DeepTech深科技", "url": "https://www.deep-tech.cn/feed", "limit": 3},
        {"name": "机器学习中文社区", "url": "https://www.machinelearningcn.com/feed", "limit": 2},
        {"name": "AI前线", "url": "https://www.aifrontier.cn/feed", "limit": 2}
    ]
}

# ============ 工具函数 ============
def score_agent_article(article, agent_type):
    """计算文章与特定Agent类型的相关性分数"""
    title = article.get("title", "").lower()
    summary = article.get("summary", "").lower()
    content = f"{title} {summary}"
    
    score = 0
    
    # 基础分数
    if agent_type.lower() in content:
        score += 100
    
    # 优先级关键词加分
    for keyword in KEYWORDS_PRIORITY:
        if keyword.lower() in content:
            score += 20
    
    # OpenClaw和Hermes特殊权重
    if agent_type == "OpenClaw" and "openclaw" in content:
        score += 50
    elif agent_type == "Hermes Agent" and "hermes" in content:
        score += 50
    
    # 排除负面关键词
    for exclude in KEYWORDS_EXCLUDE:
        if exclude.lower() in content:
            score -= 30
    
    return score

def fetch_rss_safe(url, source_name, timeout=15):
    """安全获取RSS内容，使用多种方法"""
    try:
        # 方法1: 使用requests库（更稳定）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/webp,*/*;q=0.5",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, verify=False)
        if response.status_code == 200:
            return response.content
            
    except Exception:
        pass
    
    try:
        # 方法2: 使用urllib.request
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception as e:
        print(f"获取RSS失败 ({source_name}): {e}")
        return None

def parse_rss_improved(xml_content, source_name, limit):
    """改进的RSS解析，支持多种格式"""
    try:
        if not xml_content:
            return []
            
        root = ET.fromstring(xml_content)
        articles = []
        
        # 支持多种RSS格式和命名空间
        namespaces = {
            '': '',
            'rss': 'http://purl.org/rss/1.0/',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        }
        
        # 尝试不同的路径查找item
        items = []
        for ns in namespaces.values():
            items.extend(root.findall('.//item', {'': ns}) if ns else root.findall('.//item'))
        
        # 去重并处理
        seen_titles = set()
        for item in items[:limit]:
            # 获取标题
            title_elem = item.find('title')
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else "无标题"
            
            # 去重
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            # 获取链接
            link_elem = item.find('link')
            link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            
            # 获取描述
            desc_elem = item.find('description')
            description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
            
            # 获取发布日期
            date_elem = item.find('pubDate')
            pub_date = date_elem.text.strip() if date_elem is not None and date_elem.text else ""
            
            articles.append({
                "title": title,
                "url": link,
                "summary": description[:200],
                "pub_date": pub_date,
                "source": source_name
            })
        
        return articles
    except Exception as e:
        print(f"解析RSS失败 ({source_name}): {e}")
        return []

def get_agent_news(agent_type):
    """获取特定Agent类型的新闻"""
    print(f"获取 {agent_type} 相关资讯...")
    all_articles = []
    
    # 选择对应的RSS源
    if agent_type == "OpenClaw":
        sources = RSS_SOURCES["openclaw"]
    elif agent_type == "Hermes Agent":
        sources = RSS_SOURCES["hermes"]
    else:
        sources = RSS_SOURCES["other_agents"]
    
    for source in sources:
        print(f"  获取 {source['name']} ({agent_type}相关)...")
        xml_content = fetch_rss_safe(source["url"], source["name"])
        if xml_content:
            articles = parse_rss_improved(xml_content, source["name"], source["limit"])
            for article in articles:
                # 计算相关分数
                article["score"] = score_agent_article(article, agent_type)
                article["category"] = f"{'🦞' if agent_type == 'OpenClaw' else '🚀' if agent_type == 'Hermes Agent' else '🔬'} {agent_type}"
                article["agent_type"] = agent_type
            all_articles.extend(articles)
    
    # 按分数排序，取前N条
    all_articles.sort(key=lambda x: x["score"], reverse=True)
    return all_articles[:8]

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

def generate_ai_agent_briefing():
    """生成AI Agent综合资讯简报"""
    
    # 1. 获取各类型Agent资讯
    openclaw_news = get_agent_news("OpenClaw")
    hermes_news = get_agent_news("Hermes Agent") 
    other_agent_news = get_agent_news("其他AI Agent")
    
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
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "*关键词：OpenClaw、AI Agent、智能体、Multi-agent*"}
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
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "*关键词：Hermes、智能助手、AI助手、自动化*"}
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
        elements.append({
            "tag": "div", 
            "text": {"tag": "lark_md", "content": "*关键词：AutoGPT、MetaGPT、LangChain、多智能体*"}
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
        "text": {"tag": "lark_md", "content": f"📊 总计：{total_articles} 条AI Agent相关资讯\n🔄 定时更新：每日8:00, 12:00, 18:00"}
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
    print("开始生成AI Agent综合资讯 V2...")
    
    # 生成简报
    elements = generate_ai_agent_briefing()
    
    # 发送到飞书
    if send_to_feishu(elements):
        print("AI Agent资讯 V2 发送完成")
    else:
        print("发送失败")

if __name__ == "__main__":
    main()