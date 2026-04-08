#!/usr/bin/env python3
"""
早间简报 - 邮件 + 资讯 + 天气
每天早上8点发送
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
FEISHU_APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"

# 邮箱配置
EMAIL_ACCOUNTS = [
    {"name": "163邮箱", "email": "yanguoxian122@163.com", "password": "TXwt8fxsuKTcrQbK", "imap_server": "imap.163.com", "imap_port": 993},
    {"name": "QQ邮箱", "email": "635752474@qq.com", "password": "ardxgeqhzylcbefd", "imap_server": "imap.qq.com", "imap_port": 993},
    {"name": "企业邮箱", "email": "ygx@sundray.com", "password": "2hh2dPEMmGEx#m8d", "imap_server": "imap.qiye.163.com", "imap_port": 993},
]

# RSS 订阅源 - 国内资讯（AI/科技/产品相关）
RSS_FEEDS = [
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "category": "🤖 AI", "limit": 3},
    {"name": "36氪", "url": "https://36kr.com/feed", "category": "📱 产品", "limit": 3},
    {"name": "钛媒体", "url": "https://www.tmtpost.com/rss.xml", "category": "📱 产品", "limit": 3},
    {"name": "人人都是产品经理", "url": "https://www.woshipm.com/feed", "category": "📱 产品", "limit": 3},
]

# 关键词筛选（AI/产品/科技相关）
KEYWORDS_PRIORITY = ["AI", "人工智能", "大模型", "ChatGPT", "OpenAI", "产品", "发布", "上线", "新品", "科技", "创新", "融资", "字节", "阿里", "腾讯", "百度", "华为", "小米", "理想", "蔚来", "小鹏", "特斯拉", "苹果", "谷歌", "微软"]
KEYWORDS_EXCLUDE = ["广告", "推广", "招聘", "活动", "会议", "论坛", "峰会"]

# 海外中文RSS源（通过代理访问）
OVERSEAS_RSS_FEEDS = [
    {"name": "BBC中文", "url": "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml", "limit": 3},
    {"name": "大纪元", "url": "https://www.epochtimes.com/gb/xml/nsc413.rss", "limit": 3},
    {"name": "阿波罗网", "url": "https://www.aboluowang.com/news/china/rss.xml", "limit": 3},
]

# 状态文件
MAIL_STATE_FILE = "/root/mail-reports/mail_state.json"
SENT_STATE_FILE = "/root/mail-reports/briefing_sent.json"
SUMMARY_LENGTH = "100"

def check_already_sent_today():
    """检查今天是否已经发送过简报"""
    today = datetime.now().strftime('%Y-%m-%d')
    if os.path.exists(SENT_STATE_FILE):
        try:
            with open(SENT_STATE_FILE, 'r') as f:
                state = json.load(f)
            if state.get('last_sent_date') == today:
                print(f"⚠️ 今天 ({today}) 已经发送过简报，跳过重复发送")
                return True
        except:
            pass
    return False

def mark_as_sent_today():
    """标记今天已经发送过简报"""
    today = datetime.now().strftime('%Y-%m-%d')
    os.makedirs(os.path.dirname(SENT_STATE_FILE), exist_ok=True)
    with open(SENT_STATE_FILE, 'w') as f:
        json.dump({'last_sent_date': today}, f)

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

# ============ 天气 ============
def get_weather():
    """获取深圳天气（JSON格式，更可靠）"""
    try:
        import subprocess
        import json
        
        # 使用 JSON 格式获取天气（更可靠）
        result = subprocess.run(
            ['curl', '-s', 'wttr.in/深圳?format=j1'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15
        )
        
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout.decode('utf-8', errors='ignore'))
            current = data['current_condition'][0]
            weather = data['weather'][0]
            
            # 天气描述中文映射
            weather_cn = {
                'Sunny': '☀️ 晴',
                'Clear': '☀️ 晴',
                'Partly cloudy': '⛅ 多云',
                'Partly Cloudy': '⛅ 多云',
                'Cloudy': '☁️ 阴',
                'Overcast': '☁️ 阴',
                'Patchy rain nearby': '🌦️ 局部小雨',
                'Light rain': '🌧️ 小雨',
                'Moderate rain': '🌧️ 中雨',
                'Heavy rain': '⛈️ 大雨',
                'Patchy light rain': '🌦️ 零星小雨',
                'Mist': '🌫️ 雾',
                'Fog': '🌫️ 雾',
                'Thunderstorm': '⛈️ 雷雨',
            }
            
            weather_desc = current['weatherDesc'][0]['value']
            weather_icon = weather_cn.get(weather_desc, f"🌡️ {weather_desc}")
            
            # 构建天气信息
            temp = current['temp_C']
            feels_like = current['FeelsLikeC']
            humidity = current['humidity']
            precip = current['precipMM']
            wind = current['windspeedKmph']
            uv = current['uvIndex']
            
            weather_str = f"{weather_icon} {temp}°C (体感{feels_like}°C), 湿度{humidity}%, 降水{precip}mm, 风力{wind}km/h"
            
            # 生成出行建议
            advice = []
            
            # 基于天气
            if '雨' in weather_icon or float(precip) > 0:
                advice.append("🌧️ 带伞出行")
            elif '晴' in weather_icon and int(temp) > 28:
                advice.append("🧴 注意防晒")
            elif '雾' in weather_icon:
                advice.append("🚗 注意交通安全")
            
            # 基于温度
            if int(feels_like) > 30:
                advice.append("🥤 多喝水防中暑")
            elif int(feels_like) < 15:
                advice.append("🧥 注意保暖")
            
            # 基于紫外线
            if int(uv) >= 5:
                advice.append("☀️ 紫外线强，注意防护")
            
            # 基于风力
            if int(wind) > 20:
                advice.append("💨 风力较大")
            
            advice_str = " | ".join(advice) if advice else "✅ 天气适宜出行"
            
            return {
                "text": weather_str,
                "advice": advice_str,
                "temp": temp,
                "feels_like": feels_like,
                "humidity": humidity,
                "precip": precip,
                "wind": wind,
                "uv": uv,
                "desc": weather_desc
            }
            
    except Exception as e:
        print(f"  天气获取错误: {e}")
    
    # 降级方案：使用简单格式
    try:
        result = subprocess.run(
            ['curl', '-s', 'wttr.in/深圳?format=%l:+%c+%t,+%h'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10
        )
        if result.returncode == 0 and result.stdout:
            text = result.stdout.decode('utf-8', errors='ignore').strip()
            return {
                "text": text,
                "advice": "✅ 天气适宜出行",
                "temp": "?",
                "feels_like": "?",
                "humidity": "?",
                "precip": "0",
                "wind": "?",
                "uv": "?",
                "desc": "Unknown"
            }
    except:
        pass
    
    return {
        "text": "深圳: 获取失败",
        "advice": "⚠️ 天气信息获取失败",
        "temp": "?",
        "feels_like": "?",
        "humidity": "?",
        "precip": "0",
        "wind": "?",
        "uv": "?",
        "desc": "Unknown"
    }

# ============ 邮件 ============
def load_mail_state():
    if os.path.exists(MAIL_STATE_FILE):
        try:
            with open(MAIL_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_mail_state(state):
    os.makedirs(os.path.dirname(MAIL_STATE_FILE), exist_ok=True)
    with open(MAIL_STATE_FILE, 'w') as f:
        json.dump(state, f)

def decode_str(s):
    if s is None:
        return ""
    try:
        value, charset = decode_header(s)[0]
        if isinstance(value, bytes):
            return value.decode(charset or 'utf-8', errors='ignore')
        return value
    except:
        return str(s)

def clean_subject(subject):
    return re.sub(r'\s+', ' ', subject).strip()[:45]

def clean_sender(sender):
    match = re.search(r'<([^>]+)>', sender)
    if match:
        name = sender[:match.start()].strip().strip('"')
        return name if name else match.group(1).split('@')[0]
    return sender.split('@')[0] if '@' in sender else sender[:20]

def connect_163(email, password, server, port):
    """特殊处理 163 邮箱连接（需要 ID 命令）"""
    sock = socket.create_connection((server, port))
    sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1_2)
    
    welcome = sock.recv(1024).decode()
    
    # 发送 ID 命令
    sock.send(b'1 ID ("name" "Python-IMAP" "version" "1.0")\r\n')
    response = sock.recv(1024).decode()
    
    # 发送 LOGIN
    sock.send(f'2 LOGIN {email} {password}\r\n'.encode())
    response = sock.recv(1024).decode()
    
    if 'OK' not in response:
        sock.close()
        raise Exception(f"Login failed: {response}")
    
    # 发送 SELECT INBOX
    sock.send(b'3 SELECT INBOX\r\n')
    response = sock.recv(1024).decode()
    
    if 'OK' not in response:
        sock.close()
        raise Exception(f"Select inbox failed: {response}")
    
    # 创建 IMAP4 对象并替换 socket
    mail = imaplib.IMAP4_SSL(server, port)
    mail.sock = sock
    mail.file = sock.makefile('rb')
    mail.state = 'SELECTED'
    
    return mail

def fetch_emails_163(account, limit=10):
    """获取 163 邮箱邮件"""
    emails = []
    try:
        mail = connect_163(account["email"], account["password"], account["imap_server"], account["imap_port"])
        date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        mail.sock.send(f'4 SEARCH SINCE "{date}"\r\n'.encode())
        response = mail.sock.recv(4096).decode()
        
        if 'SEARCH' in response:
            msg_ids = re.findall(r'\d+', response)
            msg_ids = msg_ids[-limit:] if len(msg_ids) > limit else msg_ids
            
            for msg_id in reversed(msg_ids):
                try:
                    mail.sock.send(f'5 FETCH {msg_id} (BODY.PEEK[HEADER.FIELDS (MESSAGE-ID SUBJECT FROM)])\r\n'.encode())
                    resp = b''
                    while True:
                        chunk = mail.sock.recv(4096)
                        resp += chunk
                        if b'5 OK' in chunk or b'5 NO' in chunk:
                            break
                    
                    raw = resp.decode('utf-8', errors='ignore')
                    msg_id_match = re.search(r'Message-ID:\s*<([^>]+)>', raw, re.I)
                    subject_match = re.search(r'Subject:\s*(.+?)(?=\r?\n[A-Za-z-]+:|$)', raw, re.I | re.DOTALL)
                    from_match = re.search(r'From:\s*(.+?)(?=\r?\n[A-Za-z-]+:|$)', raw, re.I | re.DOTALL)
                    
                    emails.append({
                        "id": msg_id_match.group(1) if msg_id_match else f"{account['email']}_{msg_id}",
                        "subject": clean_subject(decode_str(subject_match.group(1))) if subject_match else "无主题",
                        "from": clean_sender(decode_str(from_match.group(1))) if from_match else "未知",
                    })
                except:
                    continue
        
        mail.sock.send(b'6 LOGOUT\r\n')
        mail.sock.close()
    except Exception as e:
        print(f"  163邮箱错误: {e}")
    return emails

def fetch_emails(account, limit=10):
    """获取邮件"""
    # 163 邮箱需要特殊处理
    if "163.com" in account["imap_server"] and "qiye" not in account["imap_server"]:
        return fetch_emails_163(account, limit)
    
    emails = []
    try:
        mail = imaplib.IMAP4_SSL(account["imap_server"], account["imap_port"])
        mail.login(account["email"], account["password"])
        mail.select("INBOX")
        
        date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        _, messages = mail.search(None, f'(SINCE "{date}")')
        
        if messages[0]:
            msg_ids = messages[0].split()[-limit:]
            
            for msg_id in reversed(msg_ids):
                try:
                    _, msg_data = mail.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID SUBJECT FROM)])")
                    raw = msg_data[0][1].decode('utf-8', errors='ignore')
                    msg = email.message_from_string(raw)
                    
                    msg_id_hdr = msg.get("Message-ID", "")
                    msg_id = re.search(r'<([^>]+)>', msg_id_hdr).group(1) if '<' in msg_id_hdr else msg_id_hdr
                    
                    emails.append({
                        "id": msg_id or f"{account['email']}_{msg_id}",
                        "subject": clean_subject(decode_str(msg["Subject"])),
                        "from": clean_sender(decode_str(msg["From"])),
                    })
                except:
                    continue
        
        mail.logout()
    except Exception as e:
        print(f"  {account['name']}错误: {e}")
    return emails

SPAM_KEYWORDS = ["广告", "推广", "优惠", "促销", "抽奖", "免费", "赠送", "点击", "限时", "特价", "折扣", "红包", "贷款助力", "闪电贷", "周年庆", "好礼", "APP推广"]

def is_spam(subject, sender):
    text = f"{subject} {sender}".lower()
    return any(kw in text for kw in SPAM_KEYWORDS)

def get_new_emails():
    """获取新邮件"""
    state = load_mail_state()
    all_new = []
    account_results = []
    
    for account in EMAIL_ACCOUNTS:
        print(f"  检查 {account['name']}...")
        emails = fetch_emails(account, limit=8)
        seen_ids = state.get(account['email'], [])
        
        new_emails = [e for e in emails if e['id'] not in seen_ids and not is_spam(e['subject'], e['from'])]
        state[account['email']] = [e['id'] for e in emails]
        
        if new_emails:
            account_results.append({
                "name": account['name'],
                "new": new_emails[:3]  # 每邮箱最多3条
            })
            all_new.extend(new_emails)
    
    save_mail_state(state)
    return account_results, len(all_new)

# ============ 资讯 ============
def fetch_rss(feed_url, use_proxy=False):
    """获取RSS内容，海外源使用代理"""
    try:
        if use_proxy:
            # 使用curl通过SOCKS5代理
            cmd = 'curl -sL --max-time 15 --socks5 127.0.0.1:1080 -H "User-Agent: Mozilla/5.0" "%s" 2>/dev/null' % feed_url
            result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = result.communicate(timeout=20)
            if result.returncode == 0:
                return stdout
        else:
            headers = {"User-Agent": "Mozilla/5.0"}
            req = urllib.request.Request(feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read()
    except:
        return None

def parse_overseas_rss(xml_content, source_name, limit):
    """解析海外中文RSS（处理命名空间）"""
    articles = []
    try:
        # 移除命名空间
        xml_str = xml_content.decode('utf-8', errors='ignore')
        xml_str = re.sub(r'xmlns[^=]*="[^"]*"', '', xml_str)
        xml_str = re.sub(r'xmlns:[^=]*="[^"]*"', '', xml_str)
        xml_str = re.sub(r'<([a-zA-Z0-9_]+):', r'<', xml_str)
        xml_str = re.sub(r'</([a-zA-Z0-9_]+):', r'</', xml_str)
        
        root = ET.fromstring(xml_str)
        
        for item in root.findall('.//item')[:limit]:
            title = item.find('title')
            desc = item.find('description')
            link = item.find('link')
            
            title_text = title.text if title is not None else ''
            desc_text = desc.text if desc is not None else ''
            link_text = link.text if link is not None else ''
            
            # 清理CDATA和HTML
            title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_text, flags=re.DOTALL)
            desc_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', desc_text, flags=re.DOTALL)
            desc_text = re.sub(r'<[^>]+>', '', desc_text)
            
            # 截取摘要
            if len(desc_text) > 100:
                desc_text = desc_text[:100] + '...'
            
            title_text = re.sub(r'[#*_`]', '', title_text).strip()[:50]
            
            articles.append({
                "title": title_text,
                "summary": desc_text.strip(),
                "url": link_text.strip(),
                "source": source_name
            })
    except Exception as e:
        print(f"  解析错误: {e}")
    return articles

def score_article(title, source):
    """根据关键词和来源给文章打分"""
    score = 0
    title_lower = title.lower()
    
    # 关键词匹配
    for kw in KEYWORDS_PRIORITY:
        if kw.lower() in title_lower:
            score += 10
    
    # 排除词
    for kw in KEYWORDS_EXCLUDE:
        if kw.lower() in title_lower:
            score -= 20
    
    # 来源权重
    if source in ["量子位", "机器之心"]:
        score += 5  # AI专业媒体加分
    
    return score

def parse_rss_simple(xml_content, source_name, limit, use_summarize=False):
    """解析RSS并按热度筛选，可选使用summarize生成AI摘要"""
    articles = []
    try:
        root = ET.fromstring(xml_content)
        if root.tag == "rss":
            channel = root.find("channel")
            if channel:
                for item in channel.findall("item"):
                    title = item.find("title")
                    link = item.find("link")
                    desc = item.find("description")
                    
                    title_text = title.text if title is not None else ""
                    title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_text, flags=re.DOTALL)
                    title_text = re.sub(r'<[^>]+>', '', title_text)
                    title_text = title_text.strip()
                    
                    if not title_text or len(title_text) < 5:
                        continue
                    
                    link_text = link.text if link is not None else ""
                    
                    # 获取RSS中的原始摘要作为备选
                    desc_text = desc.text if desc is not None else ""
                    desc_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', desc_text, flags=re.DOTALL)
                    desc_text = re.sub(r'<[^>]+>', '', desc_text)
                    desc_text = desc_text.strip()
                    if len(desc_text) > 100:
                        desc_text = desc_text[:97] + "..."
                    
                    score = score_article(title_text, source_name)
                    
                    articles.append({
                        "title": title_text[:50],
                        "url": link_text,
                        "source": source_name,
                        "score": score,
                        "summary": desc_text,  # 初始使用RSS摘要
                        "needs_summarize": use_summarize  # 标记是否需要AI摘要
                    })
    except Exception as e:
        print(f"  解析错误: {e}")
    
    # 按分数排序，取前limit条
    articles.sort(key=lambda x: x["score"], reverse=True)
    return articles[:limit]

def summarize_article(url, fallback_summary=""):
    """使用 summarize 生成 AI 摘要，带超时保护和降级"""
    try:
        # 使用 summarize 命令，设置25秒超时
        cmd = ["summarize", url, "--length", "short"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(timeout=30)
        
        if proc.returncode == 0:
            summary = stdout.decode('utf-8', errors='ignore').strip()
            # 清理格式
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = re.sub(r'[#*_`]', '', summary)
            summary = summary.replace('\n', ' ').strip()
            if len(summary) > 120:
                summary = summary[:117] + "..."
            return summary
        else:
            stderr_text = stderr.decode('utf-8', errors='ignore').strip()
            if stderr_text:
                print(f"    ⚠️ summarize 错误: {stderr_text[:80]}")
    except subprocess.TimeoutExpired:
        print(f"    ⚠️ summarize 超时: {url[:50]}...")
        proc.kill()
    except Exception as e:
        print(f"    ⚠️ summarize 错误: {e}")
    
    # 降级：使用 RSS 中的 description 作为备选
    if fallback_summary:
        return fallback_summary
    return ""

def get_news():
    """获取国内资讯（精选9条），使用summarize生成AI摘要"""
    all_articles = []
    for feed in RSS_FEEDS:
        print(f"  获取 {feed['name']}...")
        xml = fetch_rss(feed["url"], use_proxy=False)
        if xml:
            # 启用summarize功能
            items = parse_rss_simple(xml, feed["name"], feed.get("limit", 5), use_summarize=True)
            for item in items:
                item["category"] = feed["category"]
            all_articles.extend(items)
    
    # 按分数排序，取前9条
    all_articles.sort(key=lambda x: x["score"], reverse=True)
    selected = all_articles[:9]
    
    # 串行生成AI摘要（避免并发问题，带超时保护）
    print(f"  生成AI摘要 ({len(selected)}篇文章)...")
    success_count = 0
    for i, article in enumerate(selected, 1):
        if article.get("needs_summarize") and article.get("url"):
            print(f"    [{i}/{len(selected)}] {article['title'][:40]}...")
            ai_summary = summarize_article(article["url"], article.get("summary", ""))
            if ai_summary and ai_summary != article.get("summary", ""):
                article["summary"] = ai_summary
                success_count += 1
                print(f"      ✓ AI摘要生成成功")
            elif ai_summary:
                print(f"      ℹ 使用RSS摘要")
            else:
                print(f"      ⚠ 摘要生成失败，使用RSS摘要")
    
    print(f"  AI摘要生成完成: {success_count}/{len(selected)} 篇成功")
    return selected

def get_overseas_news():
    """获取海外中文资讯"""
    articles = []
    for feed in OVERSEAS_RSS_FEEDS:
        print(f"  获取 {feed['name']}...")
        xml = fetch_rss(feed["url"], use_proxy=True)
        if xml:
            items = parse_overseas_rss(xml, feed["name"], feed.get("limit", 3))
            articles.extend(items)
    return articles

# ============ 主函数 ============
def generate_briefing():
    """生成早间简报"""
    now = datetime.now()
    time_str = now.strftime('%m月%d日')
    weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][now.weekday()]
    
    elements = []
    
    # 1. 天气
    print("获取天气...")
    weather = get_weather()
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**🌤️ 深圳天气** {weather['text']}"
        }
    })
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**💡 出行建议** {weather['advice']}"
        }
    })
    
    # 2. 邮件
    print("获取邮件...")
    elements.append({"tag": "hr"})
    mail_results, mail_count = get_new_emails()
    
    if mail_count == 0:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**📭 邮件** 暂无新邮件"}
        })
    else:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**📧 邮件** 新增 {mail_count} 封"}
        })
        for acc in mail_results:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**【{acc['name']}】**"}
            })
            for e in acc['new']:
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"• **{e['from']}** - {e['subject']}"}
                })
    
    # 3. 海外中文资讯
    print("获取海外中文资讯...")
    elements.append({"tag": "hr"})
    overseas_articles = get_overseas_news()
    
    if not overseas_articles:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**🌍 海外资讯** 暂无更新"}
        })
    else:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**🌍 海外中文资讯** {len(overseas_articles)} 条精选"}
        })
        
        # 按源分组显示
        current_source = ""
        for article in overseas_articles:
            if article['source'] != current_source:
                current_source = article['source']
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**【{current_source}】**"}
                })
            
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"• **{article['title']}**\n  {article['summary']}\n  [阅读原文]({article['url']})"}
            })
    
    # 4. 国内资讯（精选9条）
    print("获取国内资讯...")
    elements.append({"tag": "hr"})
    news_articles = get_news()
    
    if not news_articles:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**📰 国内资讯** 暂无更新"}
        })
    else:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**📰 国内AI/科技资讯** {len(news_articles)} 条精选"}
        })
        
        for article in news_articles:
            # 标题
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"[{article['title']}]({article['url']})"}
            })
            # 摘要（直接使用RSS中的description）
            summary = article.get('summary', '')
            if summary:
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"*{summary}* ·{article['source']} {article['category']}"}
                })
            else:
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"*{article['source']} {article['category']}"}
                })
    
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"{time_str} {weekday} | 早安"}]
    })
    
    title = f"☀️ 早间简报 | {time_str} {weekday}"
    return title, elements

if __name__ == "__main__":
    print("=" * 40)
    print("生成早间简报...")
    print("=" * 40)
    
    # 检查今天是否已经发送过（防重发机制）
    if check_already_sent_today():
        print("\n⏭️ 跳过执行：今天已经发送过简报")
        sys.exit(0)
    
    title, elements = generate_briefing()
    
    print("\n" + "=" * 40)
    print(title)
    
    # 发送（可通过环境变量控制）
    skip_send = os.environ.get('SKIP_FEISHU_SEND', '').lower() == 'true'
    output_json = os.environ.get('OUTPUT_JSON', '').lower() == 'true'
    
    if output_json:
        # 输出JSON格式，供其他程序读取
        import json
        output = {
            "title": title,
            "elements": elements,
            "time_str": time_str,
            "weekday": weekday
        }
        print("\n===JSON_OUTPUT_START===")
        print(json.dumps(output, ensure_ascii=False))
        print("===JSON_OUTPUT_END===")
    
    if not skip_send:
        print("\n📤 发送到飞书...")
        token = get_feishu_token()
        if token:
            if send_feishu_card(token, FEISHU_USER_ID, title, elements):
                print("✅ 发送成功")
                # 标记今天已发送
                mark_as_sent_today()
            else:
                print("❌ 发送失败")
        else:
            print("❌ 获取token失败")
    else:
        print("\n⏭️ 跳过飞书发送（SKIP_FEISHU_SEND=true）")
