#!/usr/bin/env python3
"""飞书文本消息通知（直连 API，零网关依赖）
用法: notify_feishu.py <标题> <内容>
凭据与 morning_briefing.py 同源（2026-10-08 实测有效）
"""
import json
import sys
import urllib.request

FEISHU_APP_ID = "cli_a93c6b1e1ff89bd4"
FEISHU_APP_SECRET = "gK0tXRdPTOHq3kZVKsP2PgZrUBoGSAsl"
FEISHU_USER_ID = "ou_d8ae71cd421f8954a9c97e973d4f03d1"


def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode()).get("tenant_access_token")


def send_text(token, title, body):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    msg = {
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({"text": f"{title}\n{body}"}, ensure_ascii=False),
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(msg).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode()).get("code") == 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: notify_feishu.py <title> <body>", file=sys.stderr)
        sys.exit(1)
    try:
        ok = send_text(get_token(), sys.argv[1], sys.argv[2])
        print("sent" if ok else "send failed")
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"notify error: {e}", file=sys.stderr)
        sys.exit(1)
