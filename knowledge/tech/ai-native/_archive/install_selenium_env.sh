#!/bin/bash

# 一键安装 Selenium + Chromium 环境
# 支持 CentOS/RHEL 和 Ubuntu/Debian
# 适用环境: 公司内网开发环境

set -e

echo "🚀 开始安装 Selenium + Chromium 环境..."
echo ""

# 检测系统类型
if [ -f /etc/redhat-release ]; then
    OS="centos"
    echo "📦 检测到 CentOS/RHEL 系统"
elif [ -f /etc/debian_version ]; then
    OS="ubuntu"
    echo "📦 检测到 Ubuntu/Debian 系统"
else
    echo "❌ 不支持的操作系统"
    exit 1
fi

# 安装 Python
echo ""
echo "📦 安装 Python..."
if [ "$OS" = "centos" ]; then
    sudo yum install -y python38 python38-pip || {
        echo "⚠️  Python 3.8 安装失败，尝试安装 Python 3.6..."
        sudo yum install -y python36 python36-pip
        sudo ln -sf /usr/bin/python3.6 /usr/bin/python3
        sudo ln -sf /usr/bin/pip3.6 /usr/bin/pip3
    }
    if [ ! -L /usr/bin/python3 ]; then
        sudo ln -sf /usr/bin/python3.8 /usr/bin/python3
        sudo ln -sf /usr/bin/pip3.8 /usr/bin/pip3
    fi
else
    sudo apt update
    sudo apt install -y python3.8 python3-pip || {
        echo "⚠️  Python 3.8 安装失败，尝试安装默认 Python 3..."
        sudo apt install -y python3 python3-pip
    }
fi
echo "✅ Python 版本: $(python3 --version)"

# 安装 Chromium
echo ""
echo "📦 安装 Chromium..."
if [ "$OS" = "centos" ]; then
    sudo yum install -y epel-release
    sudo yum install -y chromium-headless
    CHROMIUM_PATH="/usr/lib64/chromium-browser/headless_shell"
else
    sudo apt install -y chromium-browser
    CHROMIUM_PATH="/usr/bin/chromium-browser"
fi

if [ ! -f "$CHROMIUM_PATH" ]; then
    echo "❌ Chromium 安装失败，请手动安装"
    exit 1
fi
echo "✅ Chromium 路径: $CHROMIUM_PATH"

# 获取 Chromium 版本
CHROMIUM_VERSION=$($CHROMIUM_PATH --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
echo "✅ Chromium 版本: $CHROMIUM_VERSION"

# 安装 ChromeDriver（根据 Chromium 版本下载）
echo ""
echo "📦 安装 ChromeDriver..."
cd /tmp

# 根据 Chromium 版本选择对应的 ChromeDriver
if [[ "$CHROMIUM_VERSION" == 133* ]]; then
    CHROMEDRIVER_VERSION="133.0.6943.98"
elif [[ "$CHROMIUM_VERSION" == 114* ]]; then
    CHROMEDRIVER_VERSION="114.0.5735.90"
elif [[ "$CHROMIUM_VERSION" == 120* ]]; then
    CHROMEDRIVER_VERSION="120.0.6099.109"
else
    echo "⚠️  未找到匹配的 ChromeDriver 版本，使用默认版本 133.0.6943.98"
    CHROMEDRIVER_VERSION="133.0.6943.98"
fi

echo "📥 下载 ChromeDriver $CHROMEDRIVER_VERSION..."

# 尝试下载，如果失败则提示手动下载
if wget -q --timeout=30 "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip"; then
    unzip -o chromedriver-linux64.zip
    sudo mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
    sudo chmod +x /usr/local/bin/chromedriver
    echo "✅ ChromeDriver 版本: $(chromedriver --version)"
else
    echo "⚠️  无法从 Google 下载 ChromeDriver，请手动下载"
    echo "   下载地址: https://googlechromelabs.github.io/chrome-for-testing/"
    echo "   版本: $CHROMEDRIVER_VERSION"
    echo ""
    echo "   下载后运行:"
    echo "   sudo mv chromedriver /usr/local/bin/chromedriver"
    echo "   sudo chmod +x /usr/local/bin/chromedriver"
    exit 1
fi

# 安装依赖库
echo ""
echo "📦 安装依赖库..."
if [ "$OS" = "centos" ]; then
    sudo yum install -y atk cups-libs gtk3 libXcomposite libXcursor libXdamage \
        libXext libXi libXrandr libXScrnSaver libXtst pango xorg-x11-fonts-100dpi \
        xorg-x11-fonts-75dpi xorg-x11-fonts-cyrillic xorg-x11-fonts-misc \
        xorg-x11-fonts-Type1 xorg-x11-utils
else
    sudo apt install -y libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 \
        libgtk-3-0 libnspr4 libnss3 libwayland-client0 libxcomposite1 \
        libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 libxshmfence1 \
        libxss1 libxtst6
fi
echo "✅ 依赖库安装完成"

# 安装 Selenium
echo ""
echo "📦 安装 Selenium..."
pip3 install selenium==3.141.0
echo "✅ Selenium 版本: $(python3 -c 'import selenium; print(selenium.__version__)')"

# 创建测试脚本
echo ""
echo "📝 创建测试脚本..."
cat > test_selenium.py << 'EOF'
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sys

# 配置 Chrome 选项
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')

# 设置 Chromium 路径
import os
if os.path.exists('/usr/lib64/chromium-browser/headless_shell'):
    chrome_options.binary_location = '/usr/lib64/chromium-browser/headless_shell'
elif os.path.exists('/usr/bin/chromium-browser'):
    chrome_options.binary_location = '/usr/bin/chromium-browser'
else:
    print("❌ 未找到 Chromium，请手动配置路径")
    sys.exit(1)

try:
    driver = webdriver.Chrome(
        executable_path='/usr/local/bin/chromedriver',
        options=chrome_options
    )

    # 访问测试页面
    driver.get('https://www.baidu.com')
    print(f"✅ 环境测试通过！页面标题: {driver.title}")

    driver.quit()
except Exception as e:
    print(f"❌ 环境测试失败: {str(e)}")
    sys.exit(1)
EOF

echo "✅ 测试脚本已创建: test_selenium.py"

# 运行测试
echo ""
echo "🧪 运行环境测试..."
if python3 test_selenium.py; then
    echo ""
    echo "========================================="
    echo "✅ 安装完成！"
    echo "========================================="
    echo ""
    echo "📋 环境信息:"
    echo "  - 操作系统: $OS"
    echo "  - Python 版本: $(python3 --version)"
    echo "  - Selenium 版本: $(python3 -c 'import selenium; print(selenium.__version__)')"
    echo "  - Chromium 路径: $CHROMIUM_PATH"
    echo "  - Chromium 版本: $CHROMIUM_VERSION"
    echo "  - ChromeDriver 版本: $(chromedriver --version)"
    echo ""
    echo "📝 下一步:"
    echo "  1. 测试网络连通性: curl -I http://10.65.134.124:8080/metrics"
    echo "  2. 配置代理（如需要）: export HTTP_PROXY=\"http://proxy.company.com:8080\""
    echo "  3. 复制脚本文件: cp /root/.openclaw/workspace/scripts/frontend/*.py ./scripts/frontend/"
    echo "  4. 批量提取: python3 scripts/frontend/batch_extract.py"
    echo ""
    echo "📚 详细文档: knowledge/tech/AI-Native/frontend-automation-setup.md"
    echo "========================================="
else
    echo ""
    echo "❌ 环境测试失败，请检查配置"
    echo ""
    echo "常见问题:"
    echo "  1. 网络问题: 检查是否能访问外网（测试需要访问百度）"
    echo "  2. 依赖缺失: 运行 'sudo yum install -y atk cups-libs gtk3 ...' (CentOS)"
    echo "  3. 权限问题: chmod +x /usr/local/bin/chromedriver"
    echo ""
    echo "📚 详细排查: knowledge/tech/AI-Native/deployment-checklist.md"
    exit 1
fi
