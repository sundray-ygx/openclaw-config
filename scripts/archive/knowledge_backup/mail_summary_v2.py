#!/usr/bin/env python3
"""
邮件汇总脚本 v2 - 优化排版，只显示新增邮件
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import json
import os
import socket
import ssl
import urllib.request
import urllib.parse
import re

# ============ 飞书配置 ============
FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"

# ============ 邮箱配置 ============
EMAIL_ACCOUNTS = [
    {"name": "163邮箱", "email": "yanguoxian122@163.com", "password": "TXwt8fxsuKTcrQbK", "imap_server": "imap.163.com", "imap_port": 993},
    {"name": "QQ邮箱", "email": "635752474@qq.com", "password": "ardxgeqhzylcbefd", "imap_server": "imap.qq.com", "imap_port": 993},
    {"name": "企业邮箱", "email": "ygx@sundray.com", "password": "2hh2dPEMmGEx#m8d", "imap_server": "imap.qiye.163.com", "imap_port": 993},
]

# 状态文件 - 记录上次检查的邮件ID
STATE_FILE = "/root/mail-reports/mail_state.json"

def load_state():
    """加载上次检查的邮件状态"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_state(state):
    """保存邮件状态"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

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
    
    # 构建卡片消息
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

def decode_str(s):
    """解码邮件头"""
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
    """清理主题，去除多余空格和换行"""
    return re.sub(r'\s+', ' ', subject).strip()[:50]

def clean_sender(sender):
    """清理发件人，只保留邮箱或名称"""
    # 提取 <email> 或 "name" <email> 中的名称
    match = re.search(r'<([^>]+)>', sender)
    if match:
        email_addr = match.group(1)
        name = sender[:match.start()].strip().strip('"')
        return name if name else email_addr.split('@')[0]
    return sender.split('@')[0] if '@' in sender else sender[:20]

def connect_163(email, password, server, port):
    """特殊处理 163 邮箱"""
    sock = socket.create_connection((server, port))
    sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1_2)
    sock.recv(1024)
    sock.send(b'1 ID ("name" "Python-IMAP" "version" "1.0")\r\n')
    sock.recv(1024)
    sock.send(f'2 LOGIN {email} {password}\r\n'.encode())
    response = sock.recv(1024).decode()
    if 'OK' not in response:
        sock.close()
        raise Exception("Login failed")
    sock.send(b'3 SELECT INBOX\r\n')
    sock.recv(1024)
    
    mail = imaplib.IMAP4_SSL(server, port)
    mail.sock = sock
    mail.file = sock.makefile('rb')
    mail.state = 'SELECTED'
    return mail

def fetch_emails_163(account, limit=20):
    """获取 163 邮箱邮件"""
    emails = []
    try:
        mail = connect_163(account["email"], account["password"], account["imap_server"], account["imap_port"])
        date = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        mail.sock.send(f'4 SEARCH SINCE "{date}"\r\n'.encode())
        response = mail.sock.recv(4096).decode()
        
        if 'SEARCH' in response:
            msg_ids = re.findall(r'\d+', response)
            msg_ids = msg_ids[-limit:] if len(msg_ids) > limit else msg_ids
            
            for msg_id in reversed(msg_ids):
                try:
                    mail.sock.send(f'5 FETCH {msg_id} (BODY.PEEK[HEADER.FIELDS (MESSAGE-ID SUBJECT FROM DATE)])\r\n'.encode())
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
                    date_match = re.search(r'Date:\s*(.+?)(?=\r?\n[A-Za-z-]+:|$)', raw, re.I | re.DOTALL)
                    
                    emails.append({
                        "id": msg_id_match.group(1) if msg_id_match else f"{account['email']}_{msg_id}",
                        "subject": clean_subject(decode_str(subject_match.group(1))) if subject_match else "无主题",
                        "from": clean_sender(decode_str(from_match.group(1))) if from_match else "未知",
                        "date": date_match.group(1)[:20] if date_match else "",
                    })
                except:
                    continue
        
        mail.sock.send(b'6 LOGOUT\r\n')
        mail.sock.close()
    except Exception as e:
        print(f"163 error: {e}")
    return emails

def fetch_emails(account, limit=20):
    """获取邮件（只取头部，不取正文）"""
    if "163.com" in account["imap_server"] and "qiye" not in account["imap_server"]:
        return fetch_emails_163(account, limit)
    
    emails = []
    try:
        mail = imaplib.IMAP4_SSL(account["imap_server"], account["imap_port"])
        mail.login(account["email"], account["password"])
        mail.select("INBOX")
        
        date = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        _, messages = mail.search(None, f'(SINCE "{date}")')
        
        if messages[0]:
            msg_ids = messages[0].split()[-limit:]
            
            for msg_id in reversed(msg_ids):
                try:
                    _, msg_data = mail.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID SUBJECT FROM DATE)])")
                    raw = msg_data[0][1].decode('utf-8', errors='ignore')
                    msg = email.message_from_string(raw)
                    
                    msg_id_hdr = msg.get("Message-ID", "")
                    msg_id = re.search(r'<([^>]+)>', msg_id_hdr).group(1) if '<' in msg_id_hdr else msg_id_hdr
                    
                    emails.append({
                        "id": msg_id or f"{account['email']}_{msg_id}",
                        "subject": clean_subject(decode_str(msg["Subject"])),
                        "from": clean_sender(decode_str(msg["From"])),
                        "date": msg["Date"][:20] if msg["Date"] else "",
                    })
                except:
                    continue
        
        mail.logout()
    except Exception as e:
        print(f"IMAP error: {e}")
    return emails

# 垃圾邮件过滤关键词
SPAM_KEYWORDS = ["广告", "推广", "优惠", "促销", "抽奖", "免费", "赠送", "点击", "限时", "特价", "折扣", "红包", "贷款助力", "闪电贷", "周年庆", "好礼", "APP推广"]

def is_spam(subject, sender):
    """判断是否为垃圾邮件"""
    text = f"{subject} {sender}".lower()
    return any(kw in text for kw in SPAM_KEYWORDS)

def generate_summary():
    """生成邮件汇总"""
    state = load_state()
    now = datetime.now()
    time_str = now.strftime('%m月%d日 %H:%M')
    
    all_new_emails = []
    all_emails_count = 0
    account_results = []
    
    for account in EMAIL_ACCOUNTS:
        emails = fetch_emails(account, limit=15)
        seen_ids = state.get(account['email'], [])
        
        new_emails = []
        for e in emails:
            all_emails_count += 1
            if is_spam(e['subject'], e['from']):
                continue
            if e['id'] not in seen_ids:
                new_emails.append(e)
        
        # 更新状态
        state[account['email']] = [e['id'] for e in emails]
        
        if new_emails:
            account_results.append({
                "name": account['name'],
                "new": new_emails[:5],  # 每邮箱最多5条新邮件
                "total_new": len(new_emails)
            })
            all_new_emails.extend(new_emails)
    
    save_state(state)
    
    # 构建卡片元素
    elements = []
    
    if not all_new_emails:
        elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": "**📭 暂无新邮件**"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"上次检查: {time_str}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": "所有邮箱已同步，没有新邮件。"}}
        ]
        title = f"📧 邮件简报 | {time_str}"
    else:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**📬 新增 {len(all_new_emails)} 封邮件**"}})
        
        for acc in account_results:
            elements.append({"tag": "hr"})
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**【{acc['name']}】** {acc['total_new']}封新邮件"}})
            
            # 构建邮件列表
            email_lines = []
            for e in acc['new']:
                email_lines.append(f"• **{e['from']}** - {e['subject']}")
            
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(email_lines)}})
        
        elements.append({"tag": "hr"})
        elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": f"共检查 {len(EMAIL_ACCOUNTS)} 个邮箱 | 过滤 {all_emails_count - len(all_new_emails)} 封"}]})
        title = f"📧 邮件简报 | {time_str}"
    
    return title, elements

if __name__ == "__main__":
    title, elements = generate_summary()
    print(title)
    
    # 发送到飞书
    print("\n📤 正在发送到飞书...")
    token = get_feishu_token()
    if token:
        if send_feishu_card(token, FEISHU_USER_ID, title, elements):
            print("✅ 飞书发送成功")
        else:
            print("❌ 飞书发送失败")
    else:
        print("❌ 获取token失败")
