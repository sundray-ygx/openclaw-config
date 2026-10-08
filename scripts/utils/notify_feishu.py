#!/usr/bin/env python3
"""飞书统一通知入口（直连 API，零网关依赖）
用法:
  notify_feishu.py <标题> <内容>              # 纯文本（向后兼容）
  notify_feishu.py --card <标题> <内容> [颜色]  # 卡片，颜色: red/green/blue/grey，默认 red
卡片结构复用 heartbeat_syscheck.sh 已验证格式（2026-10-08）
"""
import json
import sys
import urllib.parse
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


def _post_message(token, msg):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?" + urllib.parse.urlencode(
        {"receive_id_type": "open_id"}
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(msg, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode()).get("code") == 0


def send_text(token, title, body):
    msg = {
        "receive_id": FEISHU_USER_ID,
        "msg_type": "text",
        "content": json.dumps({"text": f"{title}\n{body}"}, ensure_ascii=False),
    }
    return _post_message(token, msg)


def send_card(token, title, body, color="red"):
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color,
        },
        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": body}}],
    }
    msg = {
        "receive_id": FEISHU_USER_ID,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    return _post_message(token, msg)


def main():
    args = sys.argv[1:]
    use_card = False
    color = "red"
    if args and args[0] == "--card":
        use_card = True
        args = args[1:]
        if args and args[-1] in ("red", "green", "blue", "grey"):
            color = args.pop()
    if len(args) < 2:
        print("Usage: notify_feishu.py [--card] <title> <body> [red|green|blue|grey]", file=sys.stderr)
        sys.exit(1)
    title, body = args[0], args[1]
    try:
        token = get_token()
        ok = send_card(token, title, body, color) if use_card else send_text(token, title, body)
        print("sent" if ok else "send failed")
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"notify error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
