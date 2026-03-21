#!/usr/bin/env python3
"""
邮件汇总脚本 - 读取多个邮箱的最新邮件并生成汇总报告
支持 163/QQ/企业邮箱，发送报告到飞书
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

# ============ 飞书配置 ============
FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
# 你的飞书用户 ID (从配置中获取)
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"

# ============ 邮箱配置 ============
EMAIL_ACCOUNTS = [
    {
        "name": "163邮箱",
        "email": "yanguoxian122@163.com",
        "password": "TXwt8fxsuKTcrQbK",
        "imap_server": "imap.163.com",
        "imap_port": 993,
    },
    {
        "name": "QQ邮箱",
        "email": "635752474@qq.com",
        "password": "ardxgeqhzylcbefd",
        "imap_server": "imap.qq.com",
        "imap_port": 993,
    },
    {
        "name": "163企业邮箱",
        "email": "ygx@sundray.com",
        "password": "2hh2dPEMmGEx#m8d",
        "imap_server": "imap.qiye.163.com",
        "imap_port": 993,
    },
]

def get_feishu_token():
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("tenant_access_token")
    except Exception as e:
        print(f"获取飞书token失败: {e}")
        return None

def send_feishu_message(token, user_id, content):
    """发送飞书消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    
    # 构建消息内容 - 正确的格式
    message = {
        "receive_id": user_id,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    
    # 使用 open_id 发送
    params = {"receive_id_type": "open_id"}
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = json.dumps(message).encode()
    
    req = urllib.request.Request(full_url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if result.get("code") == 0:
                return True
            else:
                print(f"飞书API错误: {result}")
                return False
    except urllib.error.HTTPError as e:
        print(f"HTTP错误 {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"发送飞书消息失败: {e}")
        return False

def decode_str(s):
    """解码邮件头"""
    if s is None:
        return ""
    value, charset = decode_header(s)[0]
    if isinstance(value, bytes):
        try:
            return value.decode(charset or 'utf-8')
        except:
            return value.decode('utf-8', errors='ignore')
    return value

def get_email_content(msg):
    """获取邮件正文"""
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    pass
            elif content_type == "text/html" and not content:
                try:
                    content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
    else:
        try:
            content = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            pass
    return content[:500]

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

def fetch_emails_163(account, limit=5):
    """获取 163 邮箱邮件"""
    emails = []
    try:
        mail = connect_163(
            account["email"],
            account["password"],
            account["imap_server"],
            account["imap_port"]
        )
        
        date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        mail.sock.send(f'4 SEARCH SINCE "{date}"\r\n'.encode())
        response = mail.sock.recv(4096).decode()
        
        if 'SEARCH' in response:
            import re
            msg_ids = re.findall(r'\d+', response)
            msg_ids = msg_ids[-limit:] if len(msg_ids) > limit else msg_ids
            
            for msg_id in reversed(msg_ids):
                try:
                    mail.sock.send(f'5 FETCH {msg_id} RFC822\r\n'.encode())
                    response = b''
                    while True:
                        chunk = mail.sock.recv(4096)
                        response += chunk
                        if b'5 OK' in chunk or b'5 NO' in chunk:
                            break
                    
                    raw_email = response.split(b'\r\n', 1)[1].rsplit(b')\r\n', 1)[0]
                    msg = email.message_from_bytes(raw_email)
                    
                    subject = decode_str(msg["Subject"])
                    from_addr = decode_str(msg["From"])
                    date_str = msg["Date"]
                    content = get_email_content(msg)
                    
                    emails.append({
                        "subject": subject,
                        "from": from_addr,
                        "date": date_str,
                        "content": content[:200] + "..." if len(content) > 200 else content,
                    })
                except:
                    continue
        
        mail.sock.send(b'6 LOGOUT\r\n')
        mail.sock.close()
        return emails
    except Exception as e:
        return [{"error": str(e)}]

def fetch_emails(account, limit=5):
    """从邮箱获取最新邮件"""
    if "163.com" in account["imap_server"] and "qiye" not in account["imap_server"]:
        return fetch_emails_163(account, limit)
    
    emails = []
    try:
        mail = imaplib.IMAP4_SSL(account["imap_server"], account["imap_port"])
        mail.login(account["email"], account["password"])
        
        status, _ = mail.select("INBOX")
        if status != 'OK':
            raise Exception("无法选择收件箱")
        
        date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        _, messages = mail.search(None, f'(SINCE "{date}")')
        
        if messages[0]:
            msg_ids = messages[0].split()[-limit:]
            
            for msg_id in reversed(msg_ids):
                try:
                    _, msg_data = mail.fetch(msg_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    subject = decode_str(msg["Subject"])
                    from_addr = decode_str(msg["From"])
                    date_str = msg["Date"]
                    content = get_email_content(msg)
                    
                    emails.append({
                        "subject": subject,
                        "from": from_addr,
                        "date": date_str,
                        "content": content[:200] + "..." if len(content) > 200 else content,
                    })
                except:
                    continue
        
        mail.logout()
        return emails
    except Exception as e:
        return [{"error": str(e)}]

# 重要邮件关键词过滤
IMPORTANT_KEYWORDS = [
    # 银行/金融
    "账单", "对账单", "还款", "逾期", "扣款", "转账", "支付", "消费",
    "银行", "信用卡", "贷款", "招商银行", "农业银行", "工商银行",
    # 工作相关
    "会议", "日程", "待办", "任务", "项目", "审批", "请假", "加班",
    "工作", "办公", "OA", "钉钉", "企业微信", "飞书",
    # 安全/账号
    "安全提醒", "登录", "密码", "验证", "验证码", "异常", "冻结",
    "账号", "账户", "Auth", "Security", "Login",
    # 云服务
    "阿里云", "腾讯云", "AWS", "服务器", "实例", "告警", "过期", "续费",
    # 重要通知
    "重要", "紧急", "通知", "公告", "系统", "升级", "维护",
]

# 垃圾邮件过滤关键词
SPAM_KEYWORDS = [
    "广告", "推广", "优惠", "促销", "活动", "抽奖", "免费", "赠送",
    "点击", "立即", "限时", "特价", "折扣", "优惠券", "红包",
    "贷款助力", "闪电贷", "周年庆", "好礼", "APP推广",
]

def is_important_email(subject, from_addr, content):
    """判断邮件是否重要"""
    text = f"{subject} {from_addr} {content}".lower()
    
    # 检查是否包含重要关键词
    has_important = any(kw.lower() in text for kw in IMPORTANT_KEYWORDS)
    
    # 检查是否明显的垃圾邮件
    has_spam = any(kw.lower() in text for kw in SPAM_KEYWORDS)
    
    # 重要且不是垃圾邮件
    return has_important and not has_spam

def generate_summary():
    """生成邮件汇总（只显示重要邮件）"""
    summary = []
    summary.append("📧 重要邮件汇总")
    summary.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    summary.append("(已过滤广告/推广邮件)")
    summary.append("")
    
    total_important = 0
    total_all = 0
    
    for account in EMAIL_ACCOUNTS:
        summary.append(f"【{account['name']}】")
        
        emails = fetch_emails(account, limit=10)  # 获取更多以便过滤
        
        if emails and "error" in emails[0]:
            summary.append(f"❌ 获取失败: {emails[0]['error']}")
        elif not emails:
            summary.append("📭 最近24小时无新邮件")
        else:
            total_all += len(emails)
            
            # 过滤重要邮件
            important_emails = [
                msg for msg in emails 
                if is_important_email(msg.get('subject', ''), msg.get('from', ''), msg.get('content', ''))
            ]
            
            total_important += len(important_emails)
            
            if important_emails:
                for i, msg in enumerate(important_emails[:5], 1):  # 最多显示5封
                    summary.append(f"{i}. {msg['subject']}")
                    summary.append(f"   发件人: {msg['from']}")
                    if msg.get('content'):
                        content = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
                        summary.append(f"   预览: {content}")
            else:
                summary.append("📭 无重要邮件（已过滤广告/推广）")
        
        summary.append("")
    
    summary.append(f"总计: {total_important} 封重要邮件 / {total_all} 封全部邮件")
    return "\n".join(summary)

if __name__ == "__main__":
    report = generate_summary()
    print(report)
    
    # 保存到文件
    output_dir = "/root/mail-reports"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/mail-summary-{datetime.now().strftime('%Y%m%d')}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n✅ 报告已保存: {output_file}")
    
    # 发送到飞书
    print("\n📤 正在发送到飞书...")
    token = get_feishu_token()
    if token:
        if send_feishu_message(token, FEISHU_USER_ID, report):
            print("✅ 飞书发送成功")
        else:
            print("❌ 飞书发送失败")
    else:
        print("❌ 获取飞书token失败")
