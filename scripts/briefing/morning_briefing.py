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
import html as html_mod

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

# AI趋势/创业/产品经理 RSS 源（2026-10-29 用户核定清单，全部实测可用；海外板块已取消）
RSS_FEEDS = [
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "category": "AI趋势", "limit": 4},
    {"name": "创业邦", "url": "https://www.cyzone.cn/rss/", "category": "创业", "limit": 3},
    {"name": "创业学院", "url": "https://www.woshipm.com/category/chuangye/feed", "category": "创业", "limit": 3},
    {"name": "钛媒体", "url": "https://www.tmtpost.com/rss.xml", "category": "产品经理", "limit": 3},
    {"name": "人人都是产品经理", "url": "https://www.woshipm.com/feed", "category": "产品经理", "limit": 3},
]

# AI Agent 相关关键词（OpenClaw + Hermes Agent）
AGENT_KEYWORDS = {
    "OpenClaw": ["openclaw", "OpenClaw", "openclaw.ai", "OpenClaw Agent"],
    "Hermes Agent": ["hermes", "Hermes", "Hermes Agent", "hermes.ai", "HermesAI", "hermes agent"],
    "AI Agent": ["AI Agent", "AI代理", "智能体", "Multi-agent", "多智能体", "AutoGPT", "BabyAGI", "MetaGPT", "LangChain", "Devin"]
}

# 四大重点维度（关键词按区分度加权：专有词权重高，"AI"这种万能词权重低）
FOCUS_DIMENSIONS = {
    "AI趋势": {
        "strong": ["大模型", "人工智能", "ChatGPT", "OpenAI", "AGI", "深度学习", "机器学习", "算力", "智能体", "Agent"],
        "weak": ["AI", "模型", "推理", "算法"],
    },
    "创业": {
        "strong": ["创业", "融资", "估值", "独角兽", "孵化器", "种子轮", "A轮", "B轮", "创始人", "IPO", "上市", "并购", "投资人", "VC"],
        "weak": ["创业公司", "商业模式"],
    },
    "产品经理": {
        "strong": ["产品经理", "需求", "交互", "用户体验", "产品设计", "功能", "内测", "迭代", "留存", "转化", "用户增长", "PM"],
        "weak": ["产品", "用户", "设计"],
    },
}
# 弱词权重（强词=1.0，弱词=0.35）——避免"AI"这种万能词吃掉所有文章
DIM_WEAK_WEIGHT = 0.35


def _tag_dimension(article):
    """给文章打维度标签：AI趋势 / 创业 / 产品经理 / 其他
    加权评分：强词 1.0，弱词 0.35，按分数最高者归类。（2026-10-29 海外维度已取消）"""
    agent_type = article.get("agent_type", "")
    if agent_type in ("OpenClaw", "Hermes Agent"):
        return "AI趋势"
    title = article.get("title", "") + " " + (article.get("summary", "") or "")[:80]
    scores = {}
    for dim, kws in FOCUS_DIMENSIONS.items():
        s = 0.0
        for k in kws.get("strong", []):
            if k in title:
                s += 1.0
        for k in kws.get("weak", []):
            if k in title:
                s += DIM_WEAK_WEIGHT
        if s > 0:
            scores[dim] = s
    if scores:
        best = max(scores.items(), key=lambda x: x[1])
        # 分数太低（只有弱词单命中）时按源兜底
        if best[1] >= 0.6:
            return best[0]
    # 按源归类（2026-10-29 更新为核定源清单）
    src = article.get("source", "")
    if src in ("创业邦", "创业学院"):
        return "创业"
    if src in ("人人都是产品经理", "钛媒体"):
        return "产品经理"
    if src == "量子位":
        return "AI趋势"
    return "其他"

# 关键词筛选（AI/产品/创业相关，用于打分）
KEYWORDS_PRIORITY = ["AI", "大模型", "ChatGPT", "OpenAI", "产品", "发布", "上线", "新品", "科技", "创新", "融资", "创业", "字节", "阿里", "腾讯", "百度", "华为", "小米", "理想", "蔚来", "小鹏", "特斯拉", "苹果", "谷歌", "微软"]
KEYWORDS_EXCLUDE = ["广告", "推广", "招聘", "活动", "会议", "论坛", "峰会"]

# 焦点聚类停用词
CLUSTER_STOPWORDS = {"ai", "大模型", "科技", "互联网", "公司", "平台", "服务", "产品", "用户", "技术", "推出", "发布", "上线", "新的", "首个", "全新", "最新", "重磅", "深度"}


def select_by_dimension(pool, dim_quota=None):
    """D5: 按维度配额精选（2026-10-29：3+3+3，海外维度已取消）。
    配额填不满时，从剩余最高分文章补位，保证总条数达标。"""
    if dim_quota is None:
        dim_quota = {"AI趋势": 3, "创业": 3, "产品经理": 3}
    for a in pool:
        a["_dim"] = _tag_dimension(a)
    dim_groups = {}
    for a in sorted(pool, key=lambda x: x.get("_final", 0), reverse=True):
        d = a.get("_dim", "其他")
        dim_groups.setdefault(d, []).append(a)

    result = []
    used_ids = set()
    order = ["AI趋势", "创业", "产品经理"]
    for d in order:
        for a in dim_groups.get(d, [])[:dim_quota.get(d, 2)]:
            result.append(a)
            used_ids.add(id(a))

    # 补位：优先补未达标的维度（创业/产品经理），再按分数兜底
    total = sum(dim_quota.values())
    if len(result) < total:
        deficit_dims = [d for d in order if len(dim_groups.get(d, [])) < dim_quota.get(d, 2)]
        for d in deficit_dims:
            for a in dim_groups.get(d, []):
                if len(result) >= total:
                    break
                if id(a) not in used_ids:
                    result.append(a)
                    used_ids.add(id(a))
        # 还不够就按分数兜底
        if len(result) < total:
            remain = [a for a in sorted(pool, key=lambda x: x.get("_final", 0), reverse=True)
                      if id(a) not in used_ids]
            for a in remain:
                if len(result) >= total:
                    break
                result.append(a)
                used_ids.add(id(a))
    return result

# 海外 RSS 板块已于 2026-10-29 经用户决策整体取消（原 OVERSEAS_RSS_FEEDS/get_overseas_news 移除）

# ============ Agent Reach 集成（2026-10-28 P0-P2 增强，Boss 批准） ============
REACH_BIN = "/root/.local/bin/agent-reach"
REACH_ENV = {**os.environ, "ALL_PROXY": "socks5h://127.0.0.1:1080",
             "HTTPS_PROXY": "socks5h://127.0.0.1:1080", "HTTP_PROXY": "socks5h://127.0.0.1:1080"}

def reach(args, timeout=45):
    """调用 agent-reach CLI；失败返回 None（静默降级，绝不影响早报其余板块）"""
    try:
        r = subprocess.run([REACH_BIN] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True,
                           timeout=timeout, env=REACH_ENV)
        out = (r.stdout or "").strip()
        if r.returncode == 0 and out.startswith("{"):
            d = json.loads(out)
            if d.get("ok"):
                return d
    except Exception:
        pass
    return None

def reach_search_repos(query, limit=3):
    """agent-reach github search → [{full_name,url,stars,desc}]"""
    d = reach(["github", "search", query, "--limit", str(limit)])
    out = []
    for it in (d or {}).get("items") or []:
        raw = it.get("raw") or {}
        out.append({"full_name": raw.get("full_name") or it.get("title", ""),
                    "url": it.get("url", ""),
                    "stars": raw.get("stargazers_count", 0),
                    "desc": (it.get("text") or raw.get("description") or "")[:80]})
    return out

def reach_read_issue(issue_url):
    """agent-reach github read：取 issue/PR 正文首段+作者（比标题列表更有信息量）"""
    d = reach(["github", "read", issue_url], timeout=40)
    items = (d or {}).get("items") or []
    if items:
        it = items[0]
        body = re.sub(r"\s+", " ", (it.get("text") or "")).strip()
        return {"author": it.get("author", ""), "body": body[:100]}
    return None

def reach_bilibili(query="AI 大模型", limit=4):
    """agent-reach bilibili search → B站 AI 资讯（过滤课程营销类标题）"""
    d = reach(["bilibili", "search", query, "--limit", str(limit + 3)])
    spam_words = ("教程", "全集", "全套", "零基础", "网课", "课程", "集训营", "培训", "上岸", "大促", "双11", "促销", "补档", "踩坑")
    out = []
    for it in (d or {}).get("items") or []:
        title = (it.get("title") or "").strip()
        if not title or any(w in title for w in spam_words):
            continue
        out.append({"title": title[:50], "url": it.get("url", ""),
                    "author": it.get("author") or "", "desc": (it.get("text") or "")[:60]})
        if len(out) >= limit:
            break
    return out

def reach_read_body(url, max_chars=150):
    """agent-reach read：RSS 摘要缺失/过短时补正文首段"""
    d = reach(["read", url], timeout=35)
    for it in (d or {}).get("items") or []:
        t = re.sub(r"\s+", " ", (it.get("text") or "")).strip()
        if len(t) > 80:
            return t[:max_chars] + "..."
    return None

def enrich_short_summaries(articles, threshold=200, max_enrich=2):
    """P1 兜底：对摘要过短条目补正文（每批限 max_enrich 条控制总时长）"""
    enriched = 0
    for a in articles:
        if enriched >= max_enrich:
            break
        if len(a.get("summary", "")) < threshold and a.get("url", "").startswith("http"):
            body = reach_read_body(a["url"])
            if body:
                a["summary"] = body
                enriched += 1
                print(f"      ↳ Reach 补正文: {a.get('title', '')[:30]}")
    return articles

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

# ============ OpenClaw 资讯 ============
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
                summary = f"{'Issue' if 'pull_request' not in issue else 'PR'} by {issue.get('user', {}).get('login', 'unknown')}"
                # P0 增强：agent-reach 读取 issue 正文首段，比纯标题信息量高（失败静默降级）
                detail = reach_read_issue(issue.get('html_url', ''))
                if detail and detail.get('body'):
                    summary += f" | {detail['body'][:80]}"
                news.append({
                    "title": f"[GitHub] {issue.get('title', '')[:50]}",
                    "url": issue.get('html_url', ''),
                    "summary": summary,
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
        print(f"  获取GitHub数据错误: {e}")

    return news

def get_github_hermes_news():
    """获取Hermes Agent GitHub最新动态（2026-10-28 P0：改走 agent-reach，免速率限制+结构化输出）"""
    news = []
    try:
        # 搜索Hermes相关仓库（agent-reach github search）
        for repo in reach_search_repos("hermes agent", 3):
            news.append({
                "title": f"[GitHub] {repo['full_name'][:50]}",
                "url": repo["url"],
                "summary": f"⭐ {repo['stars']} stars · {repo['desc'][:80]}",
                "source": "GitHub",
                "category": "🚀 Hermes",
                "agent_type": "Hermes Agent",
                "score": 150
            })

        # 搜索OpenClaw相关仓库（额外）
        for repo in reach_search_repos("openclaw", 3):
            if repo["full_name"] != "openclaw/openclaw":  # 去重
                news.append({
                    "title": f"[GitHub] {repo['full_name'][:50]}",
                    "url": repo["url"],
                    "summary": f"⭐ {repo['stars']} stars · {repo['desc'][:80]}",
                    "source": "GitHub",
                    "category": "🦞 OpenClaw生态",
                    "agent_type": "OpenClaw",
                    "score": 180
                })

        # 搜索AI Agent热门仓库
        for repo in reach_search_repos("AI agent", 3):
            news.append({
                "title": f"[GitHub] {repo['full_name'][:50]}",
                "url": repo["url"],
                "summary": f"⭐ {repo['stars']} stars · {repo['desc'][:80]}",
                "source": "GitHub",
                "category": "🔬 AI Agent",
                "agent_type": "AI Agent",
                "score": 120
            })

    except Exception as e:
        print(f"  获取Hermes/AI Agent GitHub数据错误: {e}")

    return news

def score_agent_article(article):
    """根据AI Agent关键词匹配度给文章打分（支持OpenClaw、Hermes等）"""
    score = 0
    title_lower = article.get('title', '').lower()
    summary_lower = article.get('summary', '').lower()
    text = title_lower + " " + summary_lower

    # OpenClaw直接匹配（最高优先级）
    if 'openclaw' in text:
        score += 100

    # Hermes直接匹配
    if 'hermes' in text:
        score += 80

    # AI Agent相关
    if any(kw.lower() in text for kw in ['ai agent', 'ai代理', '智能体']):
        score += 50

    # Multi-agent相关
    if any(kw.lower() in text for kw in ['multi-agent', '多智能体', 'multi agent']):
        score += 40

    # Agent框架相关
    if any(kw.lower() in text for kw in ['agent', 'framework', 'langchain', 'autogpt', 'metagpt']):
        score += 25

    # 大模型相关
    if any(kw.lower() in text for kw in ['大模型', 'llm', 'gpt', 'claude', 'ai模型', 'gemini']):
        score += 20

    # 自动化/工作流相关
    if any(kw.lower() in text for kw in ['自动化', '工作流', 'workflow', 'automation']):
        score += 15

    # 来源权重
    if article.get('source', '') in ['量子位', '机器之心', '新智元']:
        score += 10

    return score

def get_agent_news():
    """从RSS源获取AI Agent相关资讯（OpenClaw + Hermes Agent + 其他AI Agent）"""
    all_articles = []

    for feed in RSS_FEEDS:
        print(f"  获取 {feed['name']} (AI Agent相关)...")
        xml = fetch_rss(feed["url"], use_proxy=False)
        if xml:
            articles = parse_rss_simple(xml, feed["name"], 10, use_summarize=False)
            for article in articles:
                # 计算AI Agent相关分数
                article["score"] = score_agent_article(article)
                article["source"] = feed["name"]
                article["category"] = feed["category"]
                
                # 标记Agent类型
                text = (article.get("title", "") + " " + article.get("summary", "")).lower()
                if "openclaw" in text:
                    article["agent_type"] = "OpenClaw"
                elif "hermes" in text:
                    article["agent_type"] = "Hermes Agent"
                else:
                    article["agent_type"] = "AI Agent"
            all_articles.extend(articles)

    # 合并OpenClaw GitHub新闻
    openclaw_github = get_github_openclaw_news()
    for item in openclaw_github:
        item["agent_type"] = "OpenClaw"
    all_articles.extend(openclaw_github)

    # 合并Hermes/AI Agent GitHub新闻
    hermes_github = get_github_hermes_news()
    all_articles.extend(hermes_github)

    # 按分数排序，取前12条
    all_articles.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_articles[:12]

# ============ 资讯 ============
def fetch_rss(feed_url, use_proxy=False):
    """获取RSS内容，海外源使用代理"""
    try:
        if use_proxy:
            # 使用curl通过SOCKS5代理（socks5-host=远端解析DNS，避免本地DNS污染海外域名）
            cmd = 'curl -sL --max-time 15 --socks5-hostname 127.0.0.1:1080 -H "User-Agent: Mozilla/5.0" "%s" 2>/dev/null' % feed_url
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
    """[已废弃 2026-10-29] 海外板块取消，保留空实现避免外部引用报错"""
    return []

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

def _normalize_xml(xml_content):
    """py3.6 兼容（2026-10-29）：GBK 等多字节编码声明 expat 不支持；
    且部分 feed 声明与实际编码不符（如 cyzone 声明 gbk 实为 utf-8，
    误解码会吃掉 CDATA 结束符 ']' 破坏结构）——按坏字符数+CDATA 配对数择优选编码，
    最后统一改写声明为 utf-8 供 ET 解析。"""
    if isinstance(xml_content, bytes):
        head = xml_content[:200].decode("ascii", errors="ignore")
        m = re.search(r'encoding=["\']([a-zA-Z0-9_-]+)["\']', head)
        declared = m.group(1).lower() if m else "utf-8"
        best_s, best_score = None, None
        for enc in dict.fromkeys([declared, "utf-8"]):
            try:
                t = xml_content.decode(enc, errors="replace")
            except LookupError:
                continue
            score = t.count("\ufffd") * 10 + abs(t.count("<![CDATA[") - t.count("]]>"))
            if best_score is None or score < best_score:
                best_s, best_score = t, score
        s = best_s if best_s is not None else xml_content.decode("utf-8", errors="replace")
    else:
        s = xml_content
    s = re.sub(r'(<\?xml[^>]*encoding=["\'])[a-zA-Z0-9_-]+(["\'])', r'\g<1>utf-8\g<2>', s, count=1)
    return s.encode("utf-8")


def parse_rss_simple(xml_content, source_name, limit, use_summarize=False):
    """解析RSS并按热度筛选，可选使用summarize生成AI摘要"""
    articles = []
    try:
        xml_content = _normalize_xml(xml_content)
        root = ET.fromstring(xml_content)
        if root.tag == "rss":
            channel = root.find("channel")
            if channel:
                for item in channel.findall("item"):
                    title = item.find("title")
                    link = item.find("link")
                    desc = item.find("description")
                    
                    title_text = (title.text or "") if title is not None else ""
                    title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_text, flags=re.DOTALL)
                    title_text = re.sub(r'<[^>]+>', '', title_text)
                    title_text = title_text.strip()
                    
                    if not title_text or len(title_text) < 5:
                        continue
                    
                    link_text = (link.text or "") if link is not None else ""
                    
                    # 获取RSS中的原始摘要作为备选
                    desc_text = (desc.text or "") if desc is not None else ""
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
        # 修复(2026-08-13): 使用绝对路径，cron 环境 PATH 不含 /usr/local/bin
        cmd = ["/usr/local/bin/summarize", url, "--length", "short"]
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

    # P1 兜底（2026-10-28）：AI 摘要失败或 RSS 摘要过短的条目，用 agent-reach 补正文
    print("  Reach 正文兜底...")
    enrich_short_summaries(selected, threshold=200, max_enrich=3)

    return selected

# ============ 主函数 ============
# ============ LLM 精炼（热榜/Release 摘要，2026-10-28 集成） ============
LLM_ENDPOINT = "https://api.ygxpro.online/v1/chat/completions"
LLM_MODEL = "deepseek-v4-flash"


def _get_llm_keys():
    """候选 key 列表（2026-10-29 修复：环境里的 OPENAI_API_KEY 可能属于其他服务，
    对本网关 401 且被静默吞掉——改为多候选按序尝试，.env 的 NEWAPI key 优先于环境 OPENAI key）。"""
    file_keys = {}
    try:
        with open(os.path.expanduser("~/.hermes/.env")) as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    file_keys[k.strip()] = v.strip()
    except Exception:
        pass
    cands = []
    for k in (os.environ.get("NEWAPI_API_KEY", ""),
              file_keys.get("NEWAPI_API_KEY", ""),
              file_keys.get("OPENAI_API_KEY", ""),
              os.environ.get("OPENAI_API_KEY", ""),
              os.environ.get("VOLCENGINE_API_KEY", "")):
        k = (k or "").strip()
        if k and k not in cands:
            cands.append(k)
    return cands


def _llm_summarize(prompt, max_len=80, timeout=12):
    """轻量 LLM 调用（new-api 网关 deepseek-v4-flash），失败返回 None。
    2026-10-29：多候选 key 逐个尝试（401/403 换下一个），避免单个无效环境变量导致全部静默降级。
    注意：网关可能路由到推理模型，reasoning_content 会吃掉 token 预算，
    因此 max_tokens 给足，并在 content 为空时从 reasoning 尾部提取答案。"""
    import requests
    for key in _get_llm_keys():
        try:
            r = requests.post(LLM_ENDPOINT, json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1600,
                "temperature": 0.3,
            }, headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
            if r.status_code in (401, 403):
                continue  # key 无效，换下一个候选
            if r.status_code != 200:
                return None
            msg = r.json()["choices"][0]["message"]
            text = (msg.get("content") or "").strip()
            if not text:
                reason = (msg.get("reasoning_content") or "").strip()
                # 从推理尾部抓最终答案（引号包裹的最后一段）
                quotes = re.findall(r'["“「]([^"”」]{10,120})["”」]', reason)
                if quotes:
                    text = max(quotes, key=len)
                else:
                    text = reason[-max_len:] if reason else ""
            text = re.sub(r"\s+", "", text)
            if len(text) > max_len:
                text = text[:max_len]
            return text or None
        except Exception:
            continue
    return None


def refine_trending_desc(category, intro_body, highlight_body, max_len=75):
    """D1: 把热榜「项目是干什么的」+「特别亮眼」+ 分类 精炼成一句话。
    输出格式：【分类】解决X问题，适用于Y，上手Z。失败返回空串（由调用方降级规则提取）。"""
    intro = re.sub(r"\s+", "", intro_body)[:400]
    high = re.sub(r"\s+", "", highlight_body)[:300]
    prompt = f"""你是信息精炼助手。基于以下GitHub项目资料，输出一句话，包含这三点：
1.解决什么问题
2.适用什么应用场景
3.如何应用（上手方式）
格式：【{category}】…解决…，适用于…，…。
要求：不超过{max_len}字，不换行，不要列表，不用markdown。

资料：
【项目介绍】{intro}
【亮点】{high}
输出："""
    return _llm_summarize(prompt, max_len=max_len, timeout=25) or ""


def refine_release_summary(repo_name, title, body, max_len=70):
    """D2: 把 release notes 提炼成"解决了什么/新增了什么"一句话。
    支持 HTML（Atom feed）与 markdown（API）两种正文格式：
    优先取 Highlights 的首条 li/bullet，去掉 PR 编号噪音。"""
    if not body:
        return ""
    text = body
    # HTML → 纯文本：li 转换行标记，去掉所有标签
    if "<li" in text or "<p" in text:
        text = re.sub(r"</li>", "\n", text)
        text = re.sub(r"<li[^>]*>", "\n- ", text)
        text = re.sub(r"</p>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = html_mod.unescape(text)
    # 去掉 PR/issue 链接编号噪音，如 (#180668, #181695)
    text = re.sub(r"\(\s*#[0-9,\s#]+\s*\)", "", text)
    text = re.sub(r"#[0-9]{4,}", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # markdown 链接
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # 提取 bullet
    bullets = re.findall(r"^\s*[-*]\s+(.+?)$", text, re.MULTILINE)
    if not bullets:
        bullets = [l.strip() for l in text.split("\n") if l.strip() and not l.strip().endswith(":")]
    # 过滤纯标题行（Highlights/Breaking/What's Changed 等）
    JUNK = {"highlights", "breaking changes", "what's changed", "features", "fixes", "improvements", "其他", "更新", "新特性"}
    bullets = [b for b in bullets if b.strip().lower().rstrip(":") not in JUNK and len(b.strip()) > 8]
    parts = []
    for b in bullets[:2]:
        b = re.sub(r"\s+", " ", b).strip(" -·")
        # 去掉 weak `<strong>x:</strong>` 残留的冒号引导，保留内容
        if len("；".join(parts) + b) + 1 > max_len:
            if not parts:
                parts.append(b[:max_len])
            break
        parts.append(b)
    return "；".join(parts)[:max_len]


# ============ 双仓库 GitHub 更新（openclaw + hermes-agent，Atom feed 免限流） ============
def get_repo_updates(repo, atype=None, max_items=2):
    """用 GitHub releases Atom feed 取更新（无需认证、不限流、含完整 release notes）。"""
    atype = atype or ("OpenClaw" if "openclaw" in repo.lower() else "Hermes Agent")
    label = "🦞" if atype == "OpenClaw" else "🚀"
    news = []
    url = f"https://github.com/{repo}/releases.atom"
    try:
        r = subprocess.run(
            ["curl", "-sL", "--socks5-hostname", "127.0.0.1:1080", "-m", "20",
             "-H", "User-Agent: Mozilla/5.0", url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
        xml = (r.stdout or b"").decode("utf-8", "replace")
        if not xml.startswith("<?xml"):
            return news
        # 解析 entry
        entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
        parsed = []
        for e in entries[:12]:
            mt = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
            ml = re.search(r'<link rel="alternate"[^>]*href="([^"]+)"', e)
            mc = re.search(r'<content type="html">(.*?)</content>', e, re.DOTALL)
            mu = re.search(r"<updated>(.*?)</updated>", e)
            if not mt:
                continue
            parsed.append({
                "title": html_mod.unescape(mt.group(1)).strip(),
                "url": ml.group(1) if ml else f"https://github.com/{repo}/releases",
                "body": html_mod.unescape(mc.group(1)) if mc else "",
                "date": (mu.group(1) or "")[:10] if mu else "",
            })
        # 优先稳定版：剔除 canary/rc（除非只有 canary）
        stable = [p for p in parsed if "canary" not in p["title"].lower()
                  and "-rc" not in p["title"].lower() and "rc." not in p["title"].lower()]
        picked = (stable or parsed)[:max_items]
        for p in picked:
            title = p["title"]
            # ① 规则提取（英文原文要点）
            rule_desc = refine_release_summary(repo, title, p["body"], max_len=70)
            # ② LLM 中文精炼：解决了什么问题/新增什么能力/价值
            desc = ""
            if p["body"]:
                plain = re.sub(r"<[^>]+>", " ", p["body"])
                plain = html_mod.unescape(plain)
                plain = re.sub(r"\s+", " ", plain)[:800]
                prompt = (f"{atype} 项目发布 {title}。下面是更新说明。"
                          f"请用一句中文（60字内）说明：这次更新解决了什么问题或新增了什么能力、对使用者有什么价值。"
                          f"不要分点、不要英文原句照搬、不要解释。\n更新说明：{plain}\n输出：")
                cand = _llm_summarize(prompt, max_len=64, timeout=25)
                if cand and len(re.findall(r"[\u4e00-\u9fa5]", cand)) >= 18:
                    desc = cand
            if not desc:
                desc = rule_desc
            # 正文无有效信息（canary 空 notes）时降级说明
            if not desc or desc.replace(" ", "") in ("", title.replace(" ", "")):
                desc = "新版本发布（细节见 release 页）"
            news.append({
                "title": f"{label} {title[:34]}",
                "url": p["url"],
                "summary": f"{p['date']} {desc}".strip(),
                "source": repo,
                "category": f"{label} {atype}",
                "agent_type": atype,
                "score": 260,
            })
    except Exception as e:
        print(f"  取 {repo} release 错误: {e}")
    return news


def get_github_dual_updates():
    """D2: 双仓库更新——openclaw + NousResearch/hermes-agent（独立板块，各取最新 1 条 release）"""
    all_n = []
    for repo in ("openclaw/openclaw", "NousResearch/hermes-agent"):
        all_n.extend(get_repo_updates(repo, max_items=1))
    return all_n


# ============ 焦点聚类（D3：跨源同题材合并，突出热点） ============
def _cluster_keywords(text):
    """从标题提取 2~4 字中文词 + 英文词（2 字以上），过滤停用词"""
    if not text:
        return set()
    # 英文词
    en = re.findall(r"[a-zA-Z]{3,}", text.lower())
    # 中文 2~4 字片段（简单窗口）
    cn = set()
    cn_text = re.sub(r"[^\u4e00-\u9fa5]", "", text)
    for w in range(2, 5):
        for i in range(len(cn_text) - w + 1):
            cn.add(cn_text[i:i + w])
    words = set(en) | cn
    words -= CLUSTER_STOPWORDS
    return words


def cluster_focus_articles(pool, limit=8):
    """D3: 跨源聚合。两两比较共享关键词数 ≥2 视为同焦点，计算"多源命中数"，焦点组置顶。
    返回按 焦点热度 > 单篇打分 排序的文章列表，每篇附 _focus_count（同题材篇数）。"""
    kw_list = [_cluster_keywords(a.get("title", "") + (a.get("summary", "") or "")[:60]) for a in pool]
    n = len(pool)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if not kw_list[i] or not kw_list[j]:
                continue
            shared = len(kw_list[i] & kw_list[j])
            # 共享 ≥2 个非停用关键词 → 同焦点
            if shared >= 2:
                union(i, j)

    groups = {}
    for i in range(n):
        r = find(i)
        groups.setdefault(r, []).append(i)

    # 给每篇标注焦点热度 = 组大小
    focus_count = {}
    for ids in groups.values():
        sz = len(ids)
        for i in ids:
            focus_count[i] = sz

    for i, a in enumerate(pool):
        a["_focus"] = focus_count.get(i, 1)
        a["_final"] = a.get("_final", 0) + (focus_count.get(i, 1) - 1) * 30  # 多源加权

    # 来源均衡：同类目最多 3 条，避免单一源霸榜
    src_count = {}
    result = []
    for a in sorted(pool, key=lambda x: x.get("_final", 0), reverse=True):
        cat = a.get("category", a.get("source", ""))
        if src_count.get(cat, 0) >= 3:
            continue
        src_count[cat] = src_count.get(cat, 0) + 1
        result.append(a)
        if len(result) >= limit:
            break
    return result


def clean_summary(text, max_len=60):
    """清洗 RSS 摘要：去图片/链接/引用符/作者行/HTML，压缩空白。"""
    if not text:
        return ""
    t = text
    # 图片（URL 里可能带括号，先按 ![ 到最后一层 ) 粗切）
    t = re.sub(r"!\[[^\]]*\]\([^\s)]*(?:\([^)]*\)[^\s)]*)*\)", "", t)
    t = re.sub(r"!\[[^\]]*\]", "", t)                    # 残留图片标记
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)      # 链接保留文字
    t = re.sub(r"<[^>]+>", "", t)                        # HTML 标签
    t = html_mod.unescape(t)
    t = re.sub(r"^\s*[>·•\-]\s*", "", t, flags=re.MULTILINE)  # 引用/列表符
    t = re.sub(r"\(?\s*https?://[^\s)]*\)?", "", t)          # 残留裸链接
    t = re.sub(r"\s+", " ", t).strip()
    # 去掉常见开头噪音：文|xxx / 作者｜xxx / 编辑｜xxx / 图源 / emoji 列表符
    t = re.sub(r"^(文|作者|编辑|来源|图源)\s*[|｜:：].{0,20}?\s+", "", t)
    t = re.sub(r"^[💵📱🔥👀💡🚀📌\s|｜:：,，、\-]+", "", t)
    # 标点边界截断（2026-10-29：硬切 60 字会产生半句话——改为优先在标点处收口）
    if len(t) > max_len:
        cut = max(t.rfind(p, 0, max_len) for p in "。！？；;，,")
        t = t[:cut + 1] if cut >= max_len * 0.5 else t[:max_len]
    return t


# ============ 主函数重构：D3 焦点聚合 + D5 各维度均衡 ============
def get_top_headlines(limit=9):
    """D3+D5：国内 RSS → 焦点聚类 → 9 条精选（AI趋势/创业/产品经理 各 3 条）。
    2026-10-29：海外板块取消；GitHub 双仓库更新移至独立板块，不再入池。"""
    pool = []

    # 国内 RSS（5 源：量子位=AI趋势 / 创业邦+创业学院=创业 / 钛媒体+woshipm=产品）
    for feed in RSS_FEEDS:
        print(f"  获取 {feed['name']}...")
        xml = fetch_rss(feed["url"], use_proxy=False)
        if xml:
            items = parse_rss_simple(xml, feed["name"], feed.get("limit", 4), use_summarize=False)
            for it in items:
                it["category"] = feed["category"]
                it["source"] = feed["name"]
            pool.extend(items)

    # 基础分：每篇文章计算相关性分
    for a in pool:
        s = a.get("score", 0) + score_agent_article(a)
        a["_final"] = s

    # 去重
    seen, deduped = set(), []
    for a in sorted(pool, key=lambda x: x["_final"], reverse=True):
        k1 = re.sub(r"\s+", "", (a.get("title") or "").lower())[:20]
        k2 = (a.get("url") or "").split("?")[0]
        if k1 in seen or (k2 and k2 in seen):
            continue
        seen.add(k1)
        if k2:
            seen.add(k2)
        deduped.append(a)

    # D3: 焦点聚类（同题材加权 + 多源标🔥，但不做最终选品）
    for a in deduped:
        a["_focus"] = 1  # 默认
    # 简单聚类后加权重
    kw_list = [_cluster_keywords(a.get("title", "") + (a.get("summary", "") or "")[:60]) for a in deduped]
    focus_hit = [0] * len(deduped)
    for i in range(len(deduped)):
        for j in range(i + 1, len(deduped)):
            if kw_list[i] and kw_list[j] and len(kw_list[i] & kw_list[j]) >= 2:
                focus_hit[i] += 1
                focus_hit[j] += 1
    for i, a in enumerate(deduped):
        a["_focus"] = focus_hit[i] + 1
        a["_final"] = a["_final"] + focus_hit[i] * 30

    # D5: 按维度配额选品 + GitHub 双仓库保底（Boss 明确要求必现，每仓库各 1 条）
    # 先把早报/快讯类聚合文压缩到 1 条（否则配额会被它们占满、去重后又补不回来）
    ROUNDUP_KW_PRE = ("早报", "快讯", "晚报", "日报", "午报")

    def _is_roundup_pre(t):
        return any(k in t for k in ROUNDUP_KW_PRE) or t.count("；") >= 2 or t.count("|") >= 3

    _roundups = [a for a in deduped if _is_roundup_pre(a.get("title", ""))]
    _others = [a for a in deduped if not _is_roundup_pre(a.get("title", ""))]
    if _roundups:
        deduped = _others + _roundups[:1]

    # D5: 维度配额选品（3+3+3；GitHub 双仓库已移至独立板块）
    selected = select_by_dimension(deduped,
        dim_quota={"AI趋势": 3, "创业": 3, "产品经理": 3})
    selected = selected[:limit]

    # Reach 兜底补正文
    enrich_short_summaries(selected, threshold=200, max_enrich=2)
    # LLM 摘要精炼（2026-10-29 恢复历史决策：每条生成流畅中文一句话，替代 RSS 原文硬截断）
    print(f"  LLM 摘要精炼 ({len(selected)}条)...")
    for i, a in enumerate(selected, 1):
        raw = (a.get("summary") or "").strip()
        title = a.get("title", "")
        llm_ok = False
        if title and (len(re.sub(r"<[^>]+>", "", raw)) < 40 or raw.endswith("...") or not raw):
            prompt = ("请根据科技新闻标题和摘要，用一句流畅完整的中文概括核心信息"
                      "（谁做了什么、有什么影响或看点），80字内，不要分点，不要照搬英文原句。"
                      f"\n标题：{title}\n摘要：{re.sub(r'<[^>]+>', '', raw)[:300]}\n输出：")
            cand = _llm_summarize(prompt, max_len=85, timeout=20)
            if cand and len(re.findall(r"[\u4e00-\u9fa5]", cand)) >= 15:
                a["summary"] = cand
                llm_ok = True
        if not llm_ok:
            a["summary"] = a.get("summary") or ""
        print(f"    [{i}/{len(selected)}] {'LLM✓' if llm_ok else 'RSS原文'} {title[:30]}")
    for a in selected:
        a["summary"] = clean_summary(a.get("summary", ""), 90)

    # 近重复合并：同题材多条只留最高分，🔥数累加（避免早报/快讯重复刷屏）
    def _tri(s):
        s = re.sub(r"[\s\W_]+", "", (s or "").lower())
        return {s[i:i + 3] for i in range(len(s) - 2)}
    merged = []
    for a in selected:
        ta = _tri(a.get("title", ""))
        dup = None
        for m in merged:
            tb = _tri(m.get("title", ""))
            if not ta or not tb:
                continue
            jac = len(ta & tb) / len(ta | tb)
            # 早报/快讯类聚合文（标题含「早报/快讯/晚报」）阈值放宽
            is_roundup = any(k in (a.get("title", "") + m.get("title", "")) for k in ("早报", "快讯", "晚报", "日报"))
            if jac >= (0.3 if is_roundup else 0.45):
                dup = m
                break
        if dup is not None:
            dup["_focus"] = max(dup.get("_focus", 1), a.get("_focus", 1)) + 1
            continue
        merged.append(a)

    # 早报/快讯类聚合文只保留 1 条（含多个「；」分条的多故事速览也算）
    ROUNDUP_KW = ("早报", "快讯", "晚报", "日报", "午报")

    def _is_roundup(title):
        if any(k in title for k in ROUNDUP_KW):
            return True
        # 多故事聚合：2 个以上分号分隔
        return title.count("；") >= 2 or title.count("|") >= 3

    roundup_kept = False
    dedup_roundup = []
    for a in merged:
        if _is_roundup(a.get("title", "")):
            if roundup_kept:
                continue
            roundup_kept = True
        dedup_roundup.append(a)
    merged = dedup_roundup

    # 合并后不足 8 条时，从候选池补齐（跳过已用/近重复）
    if len(merged) < 8:
        used_titles = [m.get("title", "") for m in merged]
        used_urls = {m.get("url", "") for m in merged}
        for cand in sorted(deduped, key=lambda x: x.get("_final", 0), reverse=True):
            if len(merged) >= 8:
                break
            if cand.get("url") in used_urls:
                continue
            # 已有早报类就不再补早报类
            if roundup_kept and any(k in cand.get("title", "") for k in ROUNDUP_KW):
                continue
            tc = _tri(cand.get("title", ""))
            if any(tc and (len(tc & _tri(t)) / max(1, len(tc | _tri(t)))) >= 0.45
                   for t in used_titles if t):
                continue
            cand["summary"] = clean_summary(cand.get("summary", ""), 60)
            cand["_dim"] = cand.get("_dim") or _tag_dimension(cand)
            merged.append(cand)
            used_titles.append(cand.get("title", ""))
            used_urls.add(cand.get("url", ""))
    return merged

# ============ GitHub 热榜（TTlook111/github-trending-daily，2026-10-28 集成） ============
TRENDING_REPO_RAW = "https://raw.githubusercontent.com/TTlook111/github-trending-daily/main/{y}/{m}/{date}.md"

def fetch_trending_report(max_back=3):
    """取最近一期热榜日报：今天→昨天→前天逐日回退。返回 (日期字符串, markdown) 或 (None, None)"""
    for back in range(max_back):
        d = datetime.now() - timedelta(days=back)
        date_s = d.strftime('%Y-%m-%d')
        url = TRENDING_REPO_RAW.format(y=d.strftime('%Y'), m=d.strftime('%m'), date=date_s)
        try:
            r = subprocess.run(
                ['curl', '-sL', '--max-time', '20', '--socks5-hostname', '127.0.0.1:1080',
                 '-H', 'User-Agent: Mozilla/5.0', url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
            text = (r.stdout or b'').decode('utf-8', 'replace')
            if r.returncode == 0 and text.startswith('#') and '### #' in text:
                return date_s, text
        except Exception:
            pass
    return None, None

def _valid_refined(text, min_len=28):
    """校验 LLM 精炼结果是否可用（防止推理残片/自述行混入）。"""
    if not text or len(text) < min_len:
        return False
    # 中文量要够（英文项目名会拉低占比，用绝对字数 + 放宽比例双重判断）
    cjk = len(re.findall(r"[\u4e00-\u9fa5]", text))
    if cjk < 22 or cjk / max(1, len(text)) < 0.4:
        return False
    # 过滤典型的模型自述/计数痕迹
    BAD = ("Good", "Count", "markdown", "Under", "字数", "字符", "Oneline", "output", "需要", "可以：")
    if any(b in text for b in BAD):
        return False
    # 排除连续英文/数字混排的残片（如 .66incl?27+39）
    if re.search(r"[A-Za-z]{2,}\d|\d+[A-Za-z]{2,}", text):
        return False
    # 必须有「解决/适用/上手」类语义之一，确保是结构化一句话
    if not any(k in text for k in ("解决", "适用", "上手", "用于", "适合", "即可", "安装")):
        return False
    return True


def parse_trending_report(md, max_items=5, max_desc=78, use_llm=True):
    """解析日报：分类 + 一句话（D1: LLM 精炼「解决X/适用Y/上手Z」，失败降级规则提取）。"""
    items = []
    blocks = re.split(r'\n###\s+#\d+\s+', md)
    for block in blocks[1:]:
        head = block.split('\n', 1)[0].strip()
        repo = head.replace('⭐', '').strip()
        # stars
        m = re.search(r'⭐\s*Stars\s*\|\s*([\d,]+)\s*(\(\+[\d,]+\))?', block)
        stars = f"⭐{m.group(1)}" + (f"({m.group(2).strip('()')})" if m and m.group(2) else "") if m else ""
        # 分类
        mcat = re.search(r'📦\s*分类\s*\|\s*([^|]+)\|', block)
        category = mcat.group(1).strip() if mcat else ""
        # 语言
        mlang = re.search(r'💻\s*语言\s*\|\s*([^|]+)\|', block)
        lang = mlang.group(1).strip() if mlang else ""
        # 项目介绍 = 解决什么问题（整段，直到下一个 emoji 小节）
        mintro = re.search(r'项目是干什么的\s*\n+(.*?)(?=\n\s*(?:💡|🌟|📥|📊|###|---)|\Z)', block, re.DOTALL)
        intro_text = re.sub(r'<[^>]+>', '', mintro.group(1)).strip() if mintro else ""
        intro_text = re.sub(r'\s+', '', intro_text)
        # 亮点 = 价值点
        mhigh = re.search(r'(?:特别亮眼的地方|为什么受欢迎|核心优势)\s*\n+(.*?)(?=\n\s*(?:📥|📊|###|---)|\Z)', block, re.DOTALL)
        high_text = re.sub(r'<[^>]+>', '', mhigh.group(1)).strip() if mhigh else ""
        high_text = re.sub(r'\s+', '', high_text)

        # ① LLM 精炼（三要素：问题/场景/用法 + 分类），失败重试 1 次
        desc = ""
        if use_llm and intro_text and category:
            for _attempt in range(2):
                llm_desc = refine_trending_desc(category, intro_text, high_text, max_len=max_desc)
                if _valid_refined(llm_desc):
                    desc = llm_desc
                    break
        # ② 降级：规则提取（首句 + 亮点句），并把三要素拼成【分类】句式
        if not desc:
            # py3.6 不支持零宽断言 split（2026-10-29 改为逐字符切句）
            def _split_sents(t):
                parts, buf = [], []
                for ch in t:
                    buf.append(ch)
                    if ch in "。！？":
                        parts.append("".join(buf))
                        buf = []
                if buf:
                    parts.append("".join(buf))
                return parts
            sents = [s for s in _split_sents(intro_text) if s.strip()]
            body = ""
            if sents:
                body = sents[0]
                if len(sents) > 1 and len(body) + len(sents[1]) <= max_desc - 16:
                    body += sents[1]
            if high_text and len(body) < max_desc - 30:
                hs = [h.strip() for h in re.split(r'(?<=[。！？])', high_text)
                      if h.strip() and not h.strip().startswith(('-', '•', '*')) and 6 <= len(h.strip()) <= 30]
                if hs:
                    body += "；" + hs[0]
            body = body.strip()
            if len(body) > max_desc:
                # 截断到最近的句读，避免半句
                cut = max(body.rfind("，", 0, max_desc), body.rfind("；", 0, max_desc),
                          body.rfind("。", 0, max_desc), body.rfind("：", 0, max_desc))
                body = (body[:cut] if cut >= max_desc * 0.6 else body[:max_desc - 1]) + "…"
            desc = (f"【{category}】{body}" if category else body)[:max_desc + 1]
        # 卡片已单独展示分类，这里去掉描述里重复的【分类】前缀
        desc = re.sub(r"^【[^】]{1,30}】\s*", "", desc).strip()[:max_desc]
        if repo:
            items.append({"repo": repo, "url": f"https://github.com/{repo}",
                          "stars": stars, "lang": lang, "category": category, "desc": desc})
        if len(items) >= max_items:
            break
    return items

def generate_briefing():
    """生成早间简报（2026-10-28 A案重构：4板块12条，聚焦一屏）"""
    now = datetime.now()
    time_str = now.strftime('%m月%d日')
    weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][now.weekday()]

    elements = []

    # ① 今日关注：天气 + 邮件TOP3
    print("获取天气...")
    weather = get_weather()
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"**🌤️ 深圳天气** {weather['text']}\n💡 {weather['advice']}"}
    })

    print("获取邮件...")
    mail_results, mail_count = get_new_emails()
    if mail_count == 0:
        mail_content = "**📭 邮件** 无新邮件"
    else:
        mail_content = f"**📧 邮件** 新增 {mail_count} 封"
        top_mails = [e for acc in mail_results for e in acc['new']][:3]
        for e in top_mails:
            mail_content += f"\n• {e['from']} - {e['subject'][:30]}"
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": mail_content}})

    # ② AI 要闻：3维度×3条 = 9条（D3焦点聚合 + D5维度配额；2026-10-29 海外取消）
    print("获取AI要闻...")
    elements.append({"tag": "hr"})
    headlines = get_top_headlines(9)
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"**🗞️ AI 要闻** {len(headlines)} 条精选（AI趋势/创业/产品）"}
    })
    DIM_EMOJI = {"AI趋势": "🤖", "创业": "💼", "产品经理": "📱", "其他": "📌"}
    for h in headlines:
        dim = h.get("_dim", "其他")
        emoji = DIM_EMOJI.get(dim, "📌")
        focus = h.get("_focus", 1)
        ftag = f" 🔥{focus}源报道" if focus > 1 else ""
        line = f"• {emoji} [{h['title']}]({h['url']}){ftag}"
        if h.get('summary'):
            line += f"\n  {h['summary']}"
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})

    # ③ GitHub 双仓库更新（openclaw + hermes-agent，2026-10-29 独立板块）
    print("获取GitHub双仓库更新...")
    elements.append({"tag": "hr"})
    gh_news = get_github_dual_updates()
    if not gh_news:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**🦞🚀 双仓库更新** 暂无"}
        })
    else:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**🦞🚀 双仓库更新** {len(gh_news)} 条（openclaw + hermes-agent）"}
        })
        for g in gh_news:
            line = f"• [{g['title']}]({g['url']})"
            if g.get("summary"):
                line += f"\n  {g['summary']}"
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})

    # ④ GitHub 热榜（2026-10-28 集成：TTlook111/github-trending-daily）
    print("获取GitHub热榜...")
    elements.append({"tag": "hr"})
    t_date, t_md = fetch_trending_report()
    t_items = parse_trending_report(t_md) if t_md else []
    if not t_items:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**🔥 GitHub 热榜** 今日暂无"}
        })
    else:
        label = t_date[5:] if t_date else ""
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**🔥 GitHub 热榜** Top5（{label}）"}
        })
        for it in t_items:
            meta = " ".join(x for x in (it["stars"], it["lang"]) if x)
            line = f"• [{it['repo']}]({it['url']}) {meta}"
            if it.get("category"):
                line += f"\n  【{it['category']}】"
            if it["desc"]:
                line += f"\n  {it['desc']}"
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})

    # ④ B站精选（2条）
    print("获取B站AI资讯...")
    elements.append({"tag": "hr"})
    bili_items = reach_bilibili("AI 大模型", 2)
    if bili_items:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**📺 B站精选** {len(bili_items)} 条"}
        })
        for item in bili_items:
            line = f"• [{item['title']}]({item['url']})"
            if item.get("author"):
                line += f"（{item['author']}）"
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})

    # ⑤ 页脚
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
