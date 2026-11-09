#!/bin/bash
# sing-box 状态查询脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================================"
echo -e "                         sing-box 代理状态查询"
echo -e "================================================================================${NC}\n"

# 1. 容器状态
echo -e "${GREEN}【1. 容器状态】${NC}"
docker ps --filter name=sing-box --format "  状态: {{.Status}}\n  端口: {{.Ports}}" 2>/dev/null || echo "  容器未运行"
echo ""

# 2. 当前代理节点
echo -e "${GREEN}【2. 当前代理节点】${NC}"
python3 << 'PYTHON'
import json
try:
    with open('/etc/sing-box/config.json', 'r') as f:
        config = json.load(f)

    selector = next((o for o in config['outbounds'] if o.get('type') == 'selector'), None)
    if selector:
        default = selector.get('default')
        print(f"  默认节点: {default}")

        # 获取节点类型
        us_node = next((o for o in config['outbounds'] if o.get('tag') == default), None)
        if us_node:
            node_type = us_node.get('type', 'unknown').upper()
            print(f"  节点类型: {node_type}")
        else:
            print(f"  节点类型: TROJAN (旧配置)")
except:
    print("  无法读取配置")
PYTHON
echo ""

# 3. 出口 IP 测试
echo -e "${GREEN}【3. 出口 IP 测试】${NC}"
current_ip=$(curl -s --max-time 10 --proxy socks5://127.0.0.1:1080 https://api.ipify.org?format=json 2>/dev/null | grep -o '"ip":"[^"]*"' | cut -d'"' -f4)

if [ -n "$current_ip" ]; then
    echo -e "  当前 IP: ${BLUE}${current_ip}${NC}"

    # 查询 IP 地理位置
    geo_info=$(curl -s --max-time 10 --proxy socks5://127.0.0.1:1080 "http://ip-api.com/json/${current_ip}" 2>/dev/null)

    if [ -n "$geo_info" ]; then
        country=$(echo "$geo_info" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('country','N/A'))" 2>/dev/null)
        city=$(echo "$geo_info" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('city','N/A'))" 2>/dev/null)
        isp=$(echo "$geo_info" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('isp','N/A'))" 2>/dev/null)

        echo "  地理位置: $country - $city"
        echo "  ISP: $isp"
    fi
else
    echo -e "  ${RED}无法获取出口 IP${NC}"
fi
echo ""

# 4. 节点统计
echo -e "${GREEN}【4. 节点统计】${NC}"
python3 << 'PYTHON'
import json
try:
    with open('/etc/sing-box/config.json', 'r') as f:
        config = json.load(f)

    vless_count = len([o for o in config['outbounds'] if o.get('type') == 'vless'])
    trojan_count = len([o for o in config['outbounds'] if o.get('type') == 'trojan'])
    total = vless_count + trojan_count

    print(f"  总节点数: {total}")
    print(f"    VLESS: {vless_count} 个")
    print(f"    TROJAN: {trojan_count} 个")
except:
    print("  无法读取配置")
PYTHON
echo ""

# 5. 连接测试
echo -e "${GREEN}【5. 连接测试】${NC}"
echo "  测试 Google..."
time_google=$(curl -s --max-time 10 --proxy socks5://127.0.0.1:1080 -o /dev/null -w "%{time_total}" https://www.google.com 2>/dev/null)

if [ -n "$time_google" ] && [ "$time_google" != "0.000" ]; then
    echo -e "  响应时间: ${GREEN}${time_google}${NC} 秒"
else
    echo -e "  ${RED}连接失败${NC}"
fi
echo ""

# 6. 近期日志
echo -e "${GREEN}【6. 近期日志】${NC}"
docker logs --tail 3 sing-box 2>&1 | grep -v '^+' | while read line; do
    echo "  $line"
done
echo ""

echo -e "${BLUE}================================================================================"
echo -e "查询完成 - 时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "================================================================================${NC}"
