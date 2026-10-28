#!/usr/bin/env python3
"""sing-box 订阅更新器（2026-10-28 重建，复刻 2026-04-10 openclaw 版逻辑）

用法: python3 update_singbox_subscription.py <订阅URL>
流程: 拉订阅(base64节点列表) -> 解析 vless:///trojan:// -> 重建 outbounds
      -> 校验 -> 备份旧配置 -> 写入 -> docker restart sing-box -> 自检
红线: 只动 outbounds/规则组；inbounds/dns/route/experimental 原样保留。
"""
import base64, json, sys, urllib.parse, subprocess, shutil, time
from pathlib import Path

CONFIG = Path("/etc/sing-box/config.json")
CONTAINER = "sing-box"


def fetch_subscription(url: str) -> list[str]:
    import urllib.request
    req = urllib.request.Request(url, headers={
        "User-Agent": "sing-box/1.11.3",  # 机场按 UA 返回节点列表
        "Accept": "*/*",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", "replace").strip()
    if raw.startswith("ss://") or raw.startswith("vless://") or raw.startswith("trojan://"):
        return [l.strip() for l in raw.splitlines() if l.strip()]
    decoded = base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "replace")
    return [l.strip() for l in decoded.splitlines() if l.strip() and not l.startswith("#")]


def parse_vless(url: str) -> dict | None:
    u = url[8:]
    if "@" not in u:
        return None
    body, frag = (u.split("#", 1) + [""])[:2]
    name = urllib.parse.unquote(frag)
    userinfo, hostport = body.rsplit("@", 1)
    uuid = urllib.parse.unquote(userinfo)
    q: dict = {}
    if "?" in hostport:
        hostport, qs = hostport.split("?", 1)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(qs).items()}
    server, _, port = hostport.rpartition(":")
    port = int(port or 443)
    if not uuid or not server:
        return None
    ob: dict = {"tag": name or f"{server}:{port}", "type": "vless", "server": server,
                "server_port": port, "uuid": uuid, "tcp_fast_open": False}
    security = q.get("security", "")
    if security == "reality":
        tls = {"enabled": True, "server_name": q.get("sni", ""), "utls": {"enabled": True, "fingerprint": q.get("fp", "chrome")},
               "reality": {"enabled": True, "public_key": q.get("pbk", ""), "short_id": q.get("sid", "")}}
        if tls["server_name"]:
            ob["tls"] = tls
    elif security == "tls":
        tls = {"enabled": True, "server_name": q.get("sni", "")}
        if q.get("fp"):
            tls["utls"] = {"enabled": True, "fingerprint": q["fp"]}
        if q.get("alpn"):
            tls["alpn"] = q["alpn"].split(",")
        ob["tls"] = tls
    net = q.get("type", "tcp")
    if net == "ws":
        transport: dict = {"type": "ws", "path": q.get("path", "/")}
        if q.get("host"):
            transport["headers"] = {"Host": q["host"]}
        ob["transport"] = transport
    elif net == "grpc":
        ob["transport"] = {"type": "grpc", "service_name": q.get("serviceName", "")}
    if q.get("flow"):
        ob["flow"] = q["flow"]
    return ob


def parse_trojan(url: str) -> dict | None:
    u = url[9:]
    body, frag = (u.split("#", 1) + [""])[:2]
    name = urllib.parse.unquote(frag)
    userinfo, hostport = body.rsplit("@", 1)
    password = urllib.parse.unquote(userinfo)
    if "?" in hostport:
        hostport, qs = hostport.split("?", 1)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(qs).items()}
    else:
        q = {}
    server, _, port = hostport.rpartition(":")
    if not password or not server:
        return None
    ob: dict = {"tag": name or f"{server}:{port}", "type": "trojan", "server": server,
                "server_port": int(port or 443), "password": password}
    sni = q.get("sni") or q.get("peer", "")
    if sni:
        ob["tls"] = {"enabled": True, "server_name": sni}
    if q.get("allowInsecure") in ("1", "true"):
        ob["tls"]["insecure"] = True
    return ob


def build_config(old: dict, nodes: list[dict]) -> dict:
    info_tags = [n["tag"] for n in nodes if any(k in n["tag"] for k in ("剩余", "到期", "套餐", "重置", "官网", "流量"))]
    real_nodes = [n for n in nodes if n["tag"] not in info_tags]
    groups = [
        {"tag": "proxy", "type": "selector", "outbounds": ["us-auto", "subscription-auto", "direct"] + [n["tag"] for n in real_nodes], "default": "us-auto"},
        {"tag": "us-auto", "type": "urltest", "outbounds": [n["tag"] for n in real_nodes if "US" in n["tag"] or "美国" in n["tag"]] or [n["tag"] for n in real_nodes[:5]],
         "url": "https://www.gstatic.com/generate_204", "interval": "5m"},
        {"tag": "subscription-auto", "type": "urltest",
         "outbounds": [n["tag"] for n in real_nodes if n["tag"] not in ("us-auto",)] or ["direct"],
         "url": "https://www.gstatic.com/generate_204", "interval": "5m"},
    ]
    outbounds = groups + info_tags_placeholder(info_tags) + real_nodes + [o for o in old["outbounds"] if o.get("type") in ("direct", "block")]
    old["outbounds"] = outbounds
    return old


def info_tags_placeholder(tags: list[str]) -> list[dict]:
    # 机场信息节点用 direct 占位，保持 tag 可引用
    return [{"tag": t, "type": "direct"} for t in tags]


def main():
    if len(sys.argv) != 2:
        print("用法: update_singbox_subscription.py <订阅URL>"); sys.exit(2)
    url = sys.argv[1]
    links = fetch_subscription(url)
    nodes = []
    for l in links:
        if l.startswith("vless://"):
            p = parse_vless(l)
        elif l.startswith("trojan://"):
            p = parse_trojan(l)
        else:
            p = None
        if p:
            nodes.append(p)
    if len(nodes) < 3:
        print(f"✗ 解析到的节点过少({len(nodes)}),订阅内容异常,中止"); sys.exit(1)
    old = json.loads(CONFIG.read_text())
    new = build_config(old, nodes)
    # sing-box check 校验
    CONFIG.with_suffix(".json.new").write_text(json.dumps(new, ensure_ascii=False, indent=2))
    chk = subprocess.run(["docker", "run", "--rm", "-v", "/etc/sing-box/config.json.new:/etc/sing-box/config.json:ro",
                          "ghcr.io/sagernet/sing-box:v1.11.3", "check", "-c", "/etc/sing-box/config.json"],
                         capture_output=True, text=True)
    if chk.returncode != 0:
        print("✗ 新配置校验失败:\n" + chk.stdout + chk.stderr); sys.exit(1)
    shutil.copy2(CONFIG, CONFIG.with_suffix(f".json.bak.{int(time.time())}"))
    shutil.move(str(CONFIG.with_suffix(".json.new")), CONFIG)
    subprocess.run(["docker", "restart", CONTAINER], check=True)
    time.sleep(8)
    test = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                           "--proxy", "socks5h://127.0.0.1:1080", "-m", "25",
                           "https://www.google.com/generate_204"], capture_output=True, text=True)
    code = test.stdout.strip()
    print(f"节点数: {len(nodes)} | 代理自检: HTTP {code} {'✅' if code == '204' else '❌'}")
    sys.exit(0 if code == "204" else 1)


if __name__ == "__main__":
    main()
