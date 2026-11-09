#!/usr/bin/env python3
"""解析 sing-box 订阅并更新配置"""

import urllib.parse
import json
import sys
import os

def parse_vless_url(url):
    """解析 VLESS URL"""
    # 移除 vless:// 前缀
    url = url[8:]
    # 分离地址部分和参数部分
    if '?' not in url:
        return None

    addr_part, params_part = url.split('?', 1)
    # 解析地址
    if '@' not in addr_part:
        return None

    uuid, server_port = addr_part.split('@', 1)
    if ':' not in server_port:
        return None

    server, port = server_port.split(':', 1)
    # 解析参数
    params = urllib.parse.parse_qs(params_part)

    # 获取标签（#后面的部分）
    name = ""
    if '#' in params_part:
        _, fragment = params_part.split('#', 1)
        name = urllib.parse.unquote(fragment)

    # 构建配置
    config = {
        "type": "vless",
        "tag": name or f"{server}:{port}",
        "server": server,
        "server_port": int(port),
        "uuid": uuid,
        "network": params.get('type', ['tcp'])[0],
        "tls": {
            "enabled": True,
            "server_name": params.get('sni', [server])[0],
        }
    }

    # Reality 配置
    if params.get('security', [''])[0] == 'reality':
        config["tls"]["reality"] = {
            "enabled": True,
            "public_key": params.get('pbk', [''])[0],
            "short_id": params.get('sid', [''])[0]
        }
        # flow 参数
        if 'flow' in params:
            config["flow"] = params['flow'][0]

    return config

def main():
    subscription_url = "https://316.sub987.top/weibo/ipx/client/dy?token=8adf1b9ba567c1292f8ef5ba2fec247b"
    config_file = "/etc/sing-box/config.json"

    # 下载订阅
    import subprocess
    print("正在下载订阅...")
    result = subprocess.run(
        ['curl', '-s', subscription_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if result.returncode != 0:
        print(f"下载失败: {result.stderr}")
        sys.exit(1)

    # 解码 base64
    import base64
    try:
        decoded = base64.b64decode(result.stdout).decode('utf-8')
    except Exception as e:
        print(f"解码失败: {e}")
        sys.exit(1)

    # 解析所有 VLESS 节点
    vless_urls = [line.strip() for line in decoded.split('\n') if line.strip().startswith('vless://')]
    print(f"找到 {len(vless_urls)} 个 VLESS 节点")

    if not vless_urls:
        print("没有找到 VLESS 节点")
        sys.exit(1)

    # 生成 outbound 配置
    outbounds = []
    for vless_url in vless_urls:
        config = parse_vless_url(vless_url)
        if config:
            outbounds.append(config)

    print(f"成功解析 {len(outbounds)} 个节点")

    # 读取现有配置
    print("读取现有配置...")
    with open(config_file, 'r') as f:
        config = json.load(f)

    # 获取所有 outbounds 标签
    existing_tags = {outbound['tag'] for outbound in config['outbounds'] if outbound.get('tag')}

    # 过滤掉已存在的节点
    new_outbounds = [ob for ob in outbounds if ob['tag'] not in existing_tags]
    print(f"新增 {len(new_outbounds)} 个节点")

    if not new_outbounds:
        print("没有新节点需要添加")
        return

    # 创建一个 urltest selector 作为新组的出口
    if new_outbounds:
        new_tags = [ob['tag'] for ob in new_outbounds]
        urltest_config = {
            "type": "urltest",
            "tag": "subscription-auto",
            "outbounds": new_tags,
            "url": "https://www.gstatic.com/generate_204",
            "interval": "10m",
            "tolerance": 50
        }
        new_outbounds.insert(0, urltest_config)

    # 更新 selector 添加新组
    for outbound in config['outbounds']:
        if outbound['type'] == 'selector' and outbound.get('tag') == 'proxy':
            if 'subscription-auto' not in outbound['outbounds']:
                outbound['outbounds'].insert(0, 'subscription-auto')
            break

    # 添加新的 outbounds
    config['outbounds'].extend(new_outbounds)

    # 备份原配置
    backup_file = config_file + '.bak.' + str(int(__import__('time').time()))
    print(f"备份原配置到: {backup_file}")
    with open(backup_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 写入新配置
    print("写入新配置...")
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 重启 sing-box
    print("重启 sing-box 服务...")
    subprocess.run(['systemctl', 'restart', 'sing-box'], check=True)

    print("完成！新增节点:")
    for ob in new_outbounds:
        if ob.get('tag') != 'subscription-auto':
            print(f"  - {ob['tag']}")

if __name__ == '__main__':
    main()
