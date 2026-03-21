#!/usr/bin/env python3
"""
RSS新闻抓取脚本 - 海外中文资讯（3个源）
合并到早间简报
"""

import xml.etree.ElementTree as ET
import re
import json
import subprocess
from datetime import datetime

# RSS源配置 - 3个中文源
RSS_SOURCES = [
    {
        "name": "BBC中文",
        "url": "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml",
        "limit": 3
    },
    {
        "name": "大纪元",
        "url": "https://www.epochtimes.com/gb/xml/nsc413.rss",
        "limit": 3
    },
    {
        "name": "阿波罗网",
        "url": "https://www.aboluowang.com/news/china/rss.xml",
        "limit": 3
    }
]

def fetch_rss(url, timeout=15):
    """使用curl通过代理获取RSS内容"""
    try:
        cmd = 'curl -sL --max-time %d --socks5 127.0.0.1:1080 -H "User-Agent: Mozilla/5.0" "%s" 2>/dev/null' % (timeout, url)
        result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = result.communicate(timeout=timeout+5)
        if result.returncode == 0:
            return stdout.decode('utf-8', errors='ignore')
        else:
            return None
    except Exception as e:
        print("Error fetching %s: %s" % (url, str(e)))
        return None

def parse_rss(xml_content, limit=3):
    """解析RSS XML内容"""
    if not xml_content:
        return []
    
    items = []
    try:
        # 移除所有命名空间声明
        xml_content = re.sub(r'xmlns[^=]*="[^"]*"', '', xml_content)
        xml_content = re.sub(r'xmlns:[^=]*="[^"]*"', '', xml_content)
        # 移除未定义的命名空间前缀
        xml_content = re.sub(r'<([a-zA-Z0-9_]+):', r'<', xml_content)
        xml_content = re.sub(r'</([a-zA-Z0-9_]+):', r'</', xml_content)
        
        root = ET.fromstring(xml_content)
        
        # 查找item元素
        for item in root.findall('.//item')[:limit]:
            title = item.find('title')
            desc = item.find('description')
            link = item.find('link')
            
            title_text = title.text if title is not None else ''
            desc_text = desc.text if desc is not None else ''
            link_text = link.text if link is not None else ''
            
            # 清理CDATA标记
            title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_text, flags=re.DOTALL)
            desc_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', desc_text, flags=re.DOTALL)
            
            # 去除HTML标签
            desc_text = re.sub(r'<[^>]+>', '', desc_text)
            
            # 截取摘要（50-100字）
            if len(desc_text) > 100:
                desc_text = desc_text[:100] + '...'
            
            items.append({
                'title': title_text.strip(),
                'description': desc_text.strip(),
                'link': link_text.strip()
            })
    except Exception as e:
        print("Error parsing XML: %s" % str(e))
    
    return items

def generate_summary():
    """生成新闻摘要"""
    all_news = []
    
    for source in RSS_SOURCES:
        print("Fetching %s..." % source['name'])
        xml_content = fetch_rss(source['url'])
        items = parse_rss(xml_content, source['limit'])
        
        if items:
            all_news.append({
                'source': source['name'],
                'items': items
            })
    
    return all_news

def format_markdown(news_data):
    """格式化为Markdown文本（用于合并到简报）"""
    lines = []
    lines.append("\n📰 **海外中文资讯**\n")
    
    for source in news_data:
        lines.append("**【%s】**" % source['source'])
        for item in source['items']:
            title = item['title'].replace('[', '【').replace(']', '】')
            desc = item['description'].replace('[', '【').replace(']', '】')
            lines.append("• %s" % title)
            lines.append("  %s" % desc)
        lines.append("")  # 空行
    
    return "\n".join(lines)

def format_for_feishu(news_data):
    """格式化为飞书卡片"""
    elements = []
    
    # 标题
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "**📰 海外中文资讯精选**\n*更新时间：%s*" % datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    })
    elements.append({"tag": "hr"})
    
    # 各源新闻
    for source in news_data:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**【%s】**" % source['source']
            }
        })
        
        for item in source['items']:
            title = item['title'].replace('[', '【').replace(']', '】')
            desc = item['description'].replace('[', '【').replace(']', '】')
            link = item['link']
            
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "• **%s**\n  %s\n  [阅读原文](%s)" % (title, desc, link)
                }
            })
        
        elements.append({"tag": "hr"})
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🌍 海外中文资讯"},
            "template": "blue"
        },
        "elements": elements
    }
    
    return card

if __name__ == "__main__":
    print("Fetching RSS news...")
    news_data = generate_summary()
    
    if news_data:
        # 输出Markdown格式（用于合并）
        md_content = format_markdown(news_data)
        print("===MARKDOWN===")
        print(md_content)
        print("===CARD===")
        # 输出卡片格式
        card = format_for_feishu(news_data)
        print(json.dumps(card, ensure_ascii=False))
    else:
        print("No news fetched")
