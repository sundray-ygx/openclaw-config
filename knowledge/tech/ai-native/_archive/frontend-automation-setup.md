# 前端自动化提取工具 - 安装与使用说明

## 工具概述

本工具集使用 **Selenium + Chromium** 自动化提取前端页面结构，无需截图，适用于 minimax 2.7 等上下文受限的模型。

---

## 一、工具依赖（已安装）

| 工具 | 版本 | 状态 | 安装路径 |
|------|------|------|----------|
| Python | 3.6.8 | ✅ 已安装 | /usr/bin/python3 |
| Selenium | 3.141.0 | ✅ 已安装 | /usr/lib/python3.6/site-packages/selenium |
| Chromium | 133.0.6943.141 | ✅ 已安装 | /usr/lib64/chromium-browser/headless_shell |
| ChromeDriver | 133.0.6943.98 | ✅ 已安装 | /usr/local/bin/chromedriver |

### 验证安装

```bash
# 检查 Python 版本
python3 --version

# 检查 Selenium
python3 -c "import selenium; print(selenium.__version__)"

# 检查 Chromium
ls -la /usr/lib64/chromium-browser/headless_shell

# 检查 ChromeDriver
chromedriver --version
```

---

## 二、在其他环境中部署（公司内网）

### 2.1 系统要求

| 要求 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| 操作系统 | Linux (CentOS 7+, Ubuntu 18.04+) | CentOS 8 / Ubuntu 20.04 | 需要 GUI 支持（即使无头运行） |
| Python | 3.6+ | 3.8+ | 必须安装 pip |
| 内存 | 2GB | 4GB+ | Chromium 运行需要较多内存 |
| 磁盘 | 5GB | 10GB+ | Chromium 二进制文件较大 |
| 网络 | 需要访问目标 URL | - | 确保能访问 `http://10.65.134.124:8080/metrics` |

### 2.2 安装步骤

#### 步骤 1: 安装 Python 和 pip

**CentOS / RHEL**:
```bash
# 安装 Python 3.8
sudo yum install -y python38 python38-pip

# 创建软链接
sudo ln -sf /usr/bin/python3.8 /usr/bin/python3
sudo ln -sf /usr/bin/pip3.8 /usr/bin/pip3
```

**Ubuntu / Debian**:
```bash
# 安装 Python 3.8
sudo apt update
sudo apt install -y python3.8 python3-pip

# 创建软链接
sudo ln -sf /usr/bin/python3.8 /usr/bin/python3
sudo ln -sf /usr/bin/pip3 /usr/bin/pip3
```

#### 步骤 2: 安装 Chromium

**CentOS / RHEL**:
```bash
# 启用 EPEL 仓库
sudo yum install -y epel-release

# 安装 Chromium（无头版本）
sudo yum install -y chromium-headless

# 验证安装
ls -la /usr/lib64/chromium-browser/headless_shell
```

**Ubuntu / Debian**:
```bash
# 安装 Chromium
sudo apt update
sudo apt install -y chromium-browser

# 验证安装
which chromium-browser
```

**手动安装（如果包管理器不可用）**:
```bash
# 下载 Chromium 133
cd /tmp
wget https://commondatastorage.googleapis.com/chromium-browser-snapshots/Linux_x64/133.0.6943.141/chrome-linux.zip

# 解压
unzip chrome-linux.zip -d /opt/chromium

# 创建软链接
sudo ln -sf /opt/chromium/chrome-linux/chrome /usr/local/bin/chromium-headless
sudo chmod +x /usr/local/bin/chromium-headless
```

#### 步骤 3: 安装 ChromeDriver

**重要**: ChromeDriver 版本必须与 Chromium 版本匹配！

```bash
# 获取 Chromium 版本
chromium-headless --version
# 输出示例: Chromium 133.0.6943.141

# 下载匹配版本的 ChromeDriver
# 访问: https://googlechromelabs.github.io/chrome-for-testing/
# 或使用以下命令（针对 Chromium 133）:

cd /tmp
wget https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.98/linux64/chromedriver-linux64.zip

# 解压
unzip chromedriver-linux64.zip

# 安装
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver

# 验证
chromedriver --version
# 输出示例: ChromeDriver 133.0.6943.98
```

#### 步骤 4: 安装 Selenium

```bash
# 安装 Selenium
pip3 install selenium==3.141.0

# 验证
python3 -c "import selenium; print(selenium.__version__)"
```

#### 步骤 5: 配置无头运行环境

**CentOS / RHEL**:
```bash
# 安装依赖库
sudo yum install -y \
  atk \
  cups-libs \
  gtk3 \
  libXcomposite \
  libXcursor \
  libXdamage \
  libXext \
  libXi \
  libXrandr \
  libXScrnSaver \
  libXtst \
  pango \
  xorg-x11-fonts-100dpi \
  xorg-x11-fonts-75dpi \
  xorg-x11-fonts-cyrillic \
  xorg-x11-fonts-misc \
  xorg-x11-fonts-Type1 \
  xorg-x11-utils
```

**Ubuntu / Debian**:
```bash
# 安装依赖库
sudo apt install -y \
  libatk-bridge2.0-0 \
  libatk1.0-0 \
  libcups2 \
  libdrm2 \
  libgtk-3-0 \
  libnspr4 \
  libnss3 \
  libwayland-client0 \
  libxcomposite1 \
  libxdamage1 \
  libxfixes3 \
  libxkbcommon0 \
  libxrandr2 \
  libxshmfence1 \
  libxss1 \
  libxtst6
```

#### 步骤 6: 测试环境

```bash
# 创建测试脚本
cat > test_selenium.py << 'EOF'
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 配置 Chrome 选项
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')

# 设置 Chromium 路径（根据实际安装路径调整）
# CentOS/RHEL:
chrome_options.binary_location = '/usr/lib64/chromium-browser/headless_shell'
# Ubuntu/Debian:
# chrome_options.binary_location = '/usr/bin/chromium-browser'

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
EOF

# 运行测试
python3 test_selenium.py
```

### 2.3 部署脚本（一键安装）

创建一键安装脚本 `install_selenium_env.sh`:

```bash
#!/bin/bash

# 一键安装 Selenium + Chromium 环境
# 支持 CentOS/RHEL 和 Ubuntu/Debian

set -e

echo "🚀 开始安装 Selenium + Chromium 环境..."

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
if [ "$OS" = "centos" ]; then
    echo "📦 安装 Python..."
    sudo yum install -y python38 python38-pip
    sudo ln -sf /usr/bin/python3.8 /usr/bin/python3
    sudo ln -sf /usr/bin/pip3.8 /usr/bin/pip3
else
    echo "📦 安装 Python..."
    sudo apt update
    sudo apt install -y python3.8 python3-pip
fi

# 安装 Chromium
if [ "$OS" = "centos" ]; then
    echo "📦 安装 Chromium..."
    sudo yum install -y epel-release
    sudo yum install -y chromium-headless
    CHROMIUM_PATH="/usr/lib64/chromium-browser/headless_shell"
else
    echo "📦 安装 Chromium..."
    sudo apt install -y chromium-browser
    CHROMIUM_PATH="/usr/bin/chromium-browser"
fi

# 获取 Chromium 版本
CHROMIUM_VERSION=$($CHROMIUM_PATH --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
echo "✅ Chromium 版本: $CHROMIUM_VERSION"

# 安装 ChromeDriver（根据 Chromium 版本下载）
echo "📦 安装 ChromeDriver..."
cd /tmp

# 根据 Chromium 版本选择对应的 ChromeDriver
if [[ "$CHROMIUM_VERSION" == 133* ]]; then
    CHROMEDRIVER_VERSION="133.0.6943.98"
elif [[ "$CHROMIUM_VERSION" == 114* ]]; then
    CHROMEDRIVER_VERSION="114.0.5735.90"
else
    echo "⚠️  未找到匹配的 ChromeDriver 版本，使用默认版本"
    CHROMEDRIVER_VERSION="133.0.6943.98"
fi

wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip"
unzip -o chromedriver-linux64.zip
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
echo "✅ ChromeDriver 版本: $(chromedriver --version)"

# 安装依赖库
if [ "$OS" = "centos" ]; then
    echo "📦 安装依赖库..."
    sudo yum install -y atk cups-libs gtk3 libXcomposite libXcursor libXdamage \
        libXext libXi libXrandr libXScrnSaver libXtst pango xorg-x11-fonts-100dpi \
        xorg-x11-fonts-75dpi xorg-x11-fonts-cyrillic xorg-x11-fonts-misc \
        xorg-x11-fonts-Type1 xorg-x11-utils
else
    echo "📦 安装依赖库..."
    sudo apt install -y libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 \
        libgtk-3-0 libnspr4 libnss3 libwayland-client0 libxcomposite1 libxdamage1 \
        libxfixes3 libxkbcommon0 libxrandr2 libxshmfence1 libxss1 libxtst6
fi

# 安装 Selenium
echo "📦 安装 Selenium..."
pip3 install selenium==3.141.0

echo ""
echo "✅ 安装完成！"
echo ""
echo "📋 环境信息:"
echo "  - Python 版本: $(python3 --version)"
echo "  - Selenium 版本: $(python3 -c 'import selenium; print(selenium.__version__)')"
echo "  - Chromium 路径: $CHROMIUM_PATH"
echo "  - ChromeDriver 版本: $(chromedriver --version)"
echo ""
echo "🧪 运行测试:"
echo "  python3 test_selenium.py"
echo ""
```

**使用一键安装脚本**:
```bash
# 下载脚本（如果在当前环境有脚本文件）
cp /root/.openclaw/workspace/knowledge/tech/AI-Native/install_selenium_env.sh .

# 赋予执行权限
chmod +x install_selenium_env.sh

# 运行安装
./install_selenium_env.sh
```

### 2.4 网络配置

#### 2.4.1 检查网络连通性

```bash
# 测试是否能访问目标页面
curl -I http://10.65.134.124:8080/metrics

# 测试 DNS 解析
nslookup 10.65.134.124

# 测试端口连通性
telnet 10.65.134.124 8080
# 或
nc -zv 10.65.134.124 8080
```

#### 2.4.2 防火墙配置

**CentOS / RHEL (firewalld)**:
```bash
# 检查防火墙状态
sudo firewall-cmd --state

# 如果防火墙开启，允许出站连接（默认通常已允许）
sudo firewall-cmd --zone=public --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

**Ubuntu (ufw)**:
```bash
# 检查防火墙状态
sudo ufw status

# 允许出站连接（默认通常已允许）
sudo ufw allow out 8080/tcp
```

#### 2.4.3 代理配置（如需要）

如果公司内网需要通过代理访问外网，配置代理环境变量：

```bash
# 临时设置（当前会话有效）
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="10.65.134.124,localhost,127.0.0.1"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export HTTP_PROXY="http://proxy.company.com:8080"' >> ~/.bashrc
echo 'export HTTPS_PROXY="http://proxy.company.com:8080"' >> ~/.bashrc
echo 'export NO_PROXY="10.65.134.124,localhost,127.0.0.1"' >> ~/.bashrc
source ~/.bashrc
```

#### 2.4.4 内网环境特殊配置

如果目标 URL 在公司内网，但需要特殊 DNS 或路由配置：

```bash
# 添加内网 DNS
sudo echo "nameserver 10.0.0.1" >> /etc/resolv.conf

# 添加内网路由（如需要）
sudo route add -net 10.65.0.0/16 gw 10.0.0.254

# 配置 /etc/hosts（如果域名解析有问题）
sudo echo "10.65.134.124  metrics.internal" >> /etc/hosts
```

### 2.5 部署后验证

```bash
# 1. 验证所有工具版本
python3 --version
python3 -c "import selenium; print('Selenium:', selenium.__version__)"
chromedriver --version
ls -la /usr/lib64/chromium-browser/headless_shell

# 2. 运行测试脚本
python3 test_selenium.py

# 3. 测试访问目标页面
curl -I http://10.65.134.124:8080/metrics

# 4. 测试脚本访问（替换 URL 为实际目标）
cat > test_target.py << 'EOF'
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.binary_location = '/usr/lib64/chromium-browser/headless_shell'

try:
    driver = webdriver.Chrome(
        executable_path='/usr/local/bin/chromedriver',
        options=chrome_options
    )
    
    driver.get('http://10.65.134.124:8080/metrics')
    print(f"✅ 成功访问目标页面！标题: {driver.title}")
    
    driver.quit()
except Exception as e:
    print(f"❌ 访问失败: {str(e)}")
EOF

python3 test_target.py
```

创建一键安装脚本 `install_selenium_env.sh`:

```bash
#!/bin/bash

# 一键安装 Selenium + Chromium 环境
# 支持 CentOS/RHEL 和 Ubuntu/Debian

set -e

echo "🚀 开始安装 Selenium + Chromium 环境..."

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
if [ "$OS" = "centos" ]; then
    echo "📦 安装 Python..."
    sudo yum install -y python38 python38-pip
    sudo ln -sf /usr/bin/python3.8 /usr/bin/python3
    sudo ln -sf /usr/bin/pip3.8 /usr/bin/pip3
else
    echo "📦 安装 Python..."
    sudo apt update
    sudo apt install -y python3.8 python3-pip
fi

# 安装 Chromium
if [ "$OS" = "centos" ]; then
    echo "📦 安装 Chromium..."
    sudo yum install -y epel-release
    sudo yum install -y chromium-headless
    CHROMIUM_PATH="/usr/lib64/chromium-browser/headless_shell"
else
    echo "📦 安装 Chromium..."
    sudo apt install -y chromium-browser
    CHROMIUM_PATH="/usr/bin/chromium-browser"
fi

# 获取 Chromium 版本
CHROMIUM_VERSION=$($CHROMIUM_PATH --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
echo "✅ Chromium 版本: $CHROMIUM_VERSION"

# 安装 ChromeDriver（根据 Chromium 版本下载）
echo "📦 安装 ChromeDriver..."
cd /tmp

# 根据 Chromium 版本选择对应的 ChromeDriver
if [[ "$CHROMIUM_VERSION" == 133* ]]; then
    CHROMEDRIVER_VERSION="133.0.6943.98"
elif [[ "$CHROMIUM_VERSION" == 114* ]]; then
    CHROMEDRIVER_VERSION="114.0.5735.90"
else
    echo "⚠️  未找到匹配的 ChromeDriver 版本，使用默认版本"
    CHROMEDRIVER_VERSION="133.0.6943.98"
fi

wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip"
unzip -o chromedriver-linux64.zip
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
echo "✅ ChromeDriver 版本: $(chromedriver --version)"

# 安装依赖库
if [ "$OS" = "centos" ]; then
    echo "📦 安装依赖库..."
    sudo yum install -y atk cups-libs gtk3 libXcomposite libXcursor libXdamage \
        libXext libXi libXrandr libXScrnSaver libXtst pango xorg-x11-fonts-100dpi \
        xorg-x11-fonts-75dpi xorg-x11-fonts-cyrillic xorg-x11-fonts-misc \
        xorg-x11-fonts-Type1 xorg-x11-utils
else
    echo "📦 安装依赖库..."
    sudo apt install -y libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 \
        libgtk-3-0 libnspr4 libnss3 libwayland-client0 libxcomposite1 libxdamage1 \
        libxfixes3 libxkbcommon0 libxrandr2 libxshmfence1 libxss1 libxtst6
fi

# 安装 Selenium
echo "📦 安装 Selenium..."
pip3 install selenium==3.141.0

echo ""
echo "✅ 安装完成！"
echo ""
echo "📋 环境信息:"
echo "  - Python 版本: $(python3 --version)"
echo "  - Selenium 版本: $(python3 -c 'import selenium; print(selenium.__version__)')"
echo "  - Chromium 路径: $CHROMIUM_PATH"
echo "  - ChromeDriver 版本: $(chromedriver --version)"
echo ""
echo "🧪 运行测试:"
echo "  python3 test_selenium.py"
echo ""
```

---

## 二、脚本位置

| 脚本 | 路径 | 用途 |
|------|------|------|
| 提取单页面 | `/root/.openclaw/workspace/scripts/frontend/extract_structure_selenium.py` | 提取单个页面的结构信息 |
| 批量提取 | `/root/.openclaw/workspace/scripts/frontend/batch_extract.py` | 批量提取多个页面 |
| 下钻测试 | `/root/.openclaw/workspace/scripts/frontend/test_drill_down.py` | 测试页面的下钻交互 |
| 测试脚本 | `/root/.openclaw/workspace/scripts/frontend/test_selenium.py` | 验证环境是否正常 |

---

## 三、使用方法

### 1. 单页面提取

提取单个页面的结构信息，输出 JSON 文件。

```bash
# 语法
python3 scripts/frontend/extract_structure_selenium.py <URL> [输出文件]

# 示例
python3 scripts/frontend/extract_structure_selenium.py \
  http://10.65.134.124:8080/metrics \
  /root/.openclaw/workspace/knowledge/tech/AI-Native/prototype-structure/metrics.json
```

**输出内容**:
- 导航 Tab 列表
- 筛选字段列表
- 指标卡片列表
- 表格信息（表头、数据行）
- 面包屑层级
- API 请求列表

---

### 2. 批量提取

一次性提取多个页面的结构信息。

```bash
# 生产模式（提取实际原型页面）
python3 scripts/frontend/batch_extract.py

# 本地测试模式（使用 mock 文件）
python3 scripts/frontend/batch_extract.py --test
```

**输出目录**:
- 生产模式: `/root/.openclaw/workspace/knowledge/tech/AI-Native/prototype-structure/`
- 测试模式: `/tmp/prototype-extract-test/`

**输出文件**:
- `metrics.json` - 主页结构
- `token-usage.json` - Token 使用量页面结构
- `silicon.json` - 硅基含量页面结构
- `summary.json` - 汇总报告

---

### 3. 下钻测试

测试页面的下钻交互逻辑（体系 → 团队 → 个人）。

```bash
# 语法
python3 scripts/frontend/test_drill_down.py <URL> [团队名称] [输出文件]

# 示例
python3 scripts/frontend/test_drill_down.py \
  http://10.65.134.124:8080/metrics \
  "终端安全产品研发部" \
  /tmp/drill-down-result.json
```

**测试内容**:
- 点击团队行下钻到团队级
- 继续下钻到个人级
- 测试面包屑导航返回功能
- 记录每一层的数据结构

---

## 四、输出格式说明

### JSON 结构

```json
{
  "url": "http://10.65.134.124:8080/metrics",
  "title": "度量管理平台",
  "timestamp": "2026-04-19T09:45:24.845500",
  "navigation": {
    "tabs": [
      {
        "text": "度量管理",
        "href": null,
        "active": true
      },
      {
        "text": "Token使用量",
        "href": null,
        "active": false
      }
    ]
  },
  "filters": {
    "fields": [
      {
        "type": "select-one",
        "name": "team",
        "id": "team-select",
        "placeholder": "",
        "class": ""
      }
    ]
  },
  "metric_cards": [
    {
      "title": "AI-Native人数",
      "value": "28",
      "subvalue": "体系总人数: 120"
    }
  ],
  "table": {
    "headers": ["团队名称", "AI-Native人数", "Token消耗总量"],
    "rows": [
      ["终端安全产品研发部", "12", "5.2万"]
    ],
    "row_count": 4
  },
  "breadcrumb": {
    "items": ["体系整体"]
  },
  "api_requests": []
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `navigation.tabs` | 导航 Tab 列表，包含文字、href、active 状态 |
| `filters.fields` | 筛选字段列表，包含 type、name、id、placeholder |
| `metric_cards` | 指标卡片列表，包含 title、value、subvalue |
| `table.headers` | 表格列名 |
| `table.rows` | 表格数据行（前 5 行作为示例） |
| `table.row_count` | 表格总行数 |
| `breadcrumb.items` | 面包屑层级列表 |
| `api_requests` | 捕获的 API 请求列表（URL、Method、参数） |

---

## 五、上下文占用估算

| 内容 | 大小 | 说明 |
|------|------|------|
| 单个页面 JSON | 2-3 KB | 包含完整结构信息 |
| 3 个页面 JSON | 6-9 KB | 主页 + Token + 硅基 |
| 下钻测试结果 | 3-5 KB | 包含 3 层下钻数据 |

**结论**: 远低于 minimax 2.7 上下文限制 ✅

---

## 六、常见问题

### Q1: 提示 "Connection timed out"

**原因**: 目标 URL 在当前网络环境中不可访问

**解决**:
```bash
# 测试网络连通性
curl -I http://10.65.134.124:8080/metrics

# 检查防火墙/代理设置
```

### Q2: 提示 "no chrome binary"

**原因**: Chromium 路径配置错误

**解决**:
```bash
# 检查 Chromium 路径
ls -la /usr/lib64/chromium-browser/headless_shell

# 检查脚本中的 binary_location 配置
grep "binary_location" scripts/frontend/extract_structure_selenium.py
```

### Q3: 提示 "ChromeDriver only supports Chrome version XX"

**原因**: ChromeDriver 版本与 Chromium 版本不匹配

**解决**:
```bash
# 升级 ChromeDriver（匹配 Chromium 133）
cd /tmp
curl -sLO https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.98/linux64/chromedriver-linux64.zip
unzip -o chromedriver-linux64.zip
mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver
chromedriver --version
```

### Q4: 提取不到某些元素

**原因**: 页面选择器不匹配

**解决**:
1. 打开浏览器 F12 → Elements，检查实际的选择器
2. 修改脚本中的 CSS 选择器
3. 添加更多备选选择器（参考现有代码）

---

## 七、集成到前端复刻流程

### 完整流程

```bash
# 1. 批量提取原型页面结构
python3 scripts/frontend/batch_extract.py

# 2. 查看提取结果
cat /root/.openclaw/workspace/knowledge/tech/AI-Native/prototype-structure/summary.json

# 3. 测试下钻交互
python3 scripts/frontend/test_drill_down.py \
  http://10.65.134.124:8080/metrics \
  "终端安全产品研发部"

# 4. 将 JSON 内容复制给 Claude Code
cat /root/.openclaw/workspace/knowledge/tech/AI-Native/prototype-structure/metrics.json

# 5. Claude Code 根据 JSON 开始复刻开发
```

### Claude Code 提示词示例

```
我已提取了原型页面的结构信息，请根据以下 JSON 开始复刻开发：

[粘贴 metrics.json 的内容]

请实现：
1. 导航 Tab（3 个：度量管理、Token使用量、硅基含量）
2. 筛选栏（团队、职类、日期范围、阈值）
3. 4 个指标卡片
4. 数据表格（6 列）
5. 下钻交互（点击行 → 团队级 → 个人级）
6. 面包屑导航
```

---

## 八、维护与更新

### 检查工具状态

```bash
# 检查所有工具版本
python3 --version
python3 -c "import selenium; print('Selenium:', selenium.__version__)"
chromedriver --version
ls -la /usr/lib64/chromium-browser/headless_shell
```

### 更新 ChromeDriver

```bash
# 下载最新版本（根据 Chromium 版本调整）
VERSION=133.0.6943.98
cd /tmp
curl -sLO https://storage.googleapis.com/chrome-for-testing-public/${VERSION}/linux64/chromedriver-linux64.zip
unzip -o chromedriver-linux64.zip
mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
chmod +x /usr/local/bin/chromedriver
chromedriver --version
```

---

## 九、参考资料

- Selenium 官方文档: https://www.selenium.dev/documentation/
- Chromium 下载: https://www.chromium.org/getting-involved/download-chromium
- ChromeDriver 下载: https://googlechromelabs.github.io/chrome-for-testing/

---

*文档更新: 2026-04-19*
*工具版本: Selenium 3.141.0 + Chromium 133 + ChromeDriver 133*

---

## 十、内网环境常见问题

### Q1: 提示 "Connection timed out"

**可能原因**:
- 目标 URL 在当前网络不可达
- 防火墙阻止
- DNS 解析失败
- 内网路由配置问题

**排查步骤**:
```bash
# 1. 测试网络连通性
curl -I http://10.65.134.124:8080/metrics
ping 10.65.134.124

# 2. 测试端口
telnet 10.65.134.124 8080
# 或
nc -zv 10.65.134.124 8080

# 3. 检查路由
route -n

# 4. 检查 DNS
nslookup 10.65.134.124

# 5. 检查防火墙
sudo firewall-cmd --list-all  # CentOS
sudo ufw status                    # Ubuntu
```

**解决方案**:
```bash
# 添加内网路由（如需要）
sudo route add -net 10.65.0.0/16 gw <网关IP>

# 配置 /etc/hosts（如果 DNS 解析有问题）
sudo echo "10.65.134.124  metrics.internal" >> /etc/hosts

# 配置防火墙规则
sudo firewall-cmd --zone=public --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

### Q2: 内网无法下载 ChromeDriver

**原因**: 无法访问 Google 下载地址

**解决方案**:

**方案 1**: 使用公司内部镜像或文件服务器
```bash
# 从内部服务器下载
wget http://internal-mirror.company.com/chromedriver/chromedriver-133.0.6943.98.zip
unzip chromedriver-133.0.6943.98.zip
sudo mv chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
```

**方案 2**: 手动复制文件
```bash
# 在有网络的机器上下载，然后通过 U 盘或内网共享复制到目标机器
# 假设已复制到 /tmp/
sudo mv /tmp/chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
```

### Q3: 代理配置后仍无法访问

**原因**: 代理配置不完整或 NO_PROXY 设置错误

**解决方案**:
```bash
# 1. 验证代理设置
echo $HTTP_PROXY
echo $HTTPS_PROXY
echo $NO_PROXY

# 2. 确保 NO_PROXY 包含目标 IP 和网段
export NO_PROXY="10.65.134.124,10.65.0.0/16,localhost,127.0.0.1"

# 3. 测试代理连接
curl -I http://10.65.134.124:8080/metrics

# 4. 如果使用 Python requests，配置代理
# 在脚本中添加:
import os
os.environ['NO_PROXY'] = '10.65.134.124,10.65.0.0/16,localhost,127.0.0.1'
```

### Q4: DNS 解析失败

**原因**: 内网域名无法通过公网 DNS 解析

**解决方案**:
```bash
# 1. 配置内网 DNS
sudo echo "nameserver <内网DNS IP>" >> /etc/resolv.conf

# 2. 配置 /etc/hosts
sudo echo "10.65.134.124  metrics.internal" >> /etc/hosts
sudo echo "10.65.134.124  metrics-dev.internal" >> /etc/hosts

# 3. 验证解析
nslookup metrics.internal
ping metrics.internal
```

### Q5: SELinux 阻止

**原因**: CentOS 的 SELinux 安全策略阻止 Chromium 运行

**解决方案**:
```bash
# 临时禁用 SELinux（测试用）
sudo setenforce 0

# 永久禁用 SELinux（生产环境不建议）
sudo sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config

# 或配置 SELinux 允许 Chromium
sudo chcon -R -t httpd_sys_rw_content_t /usr/lib64/chromium-browser/
```

### Q6: 权限不足

**原因**: 非 root 用户无法运行 ChromeDriver

**解决方案**:
```bash
# 1. 确保用户有执行权限
chmod +x /usr/local/bin/chromedriver

# 2. 添加用户到必要组（如果需要）
sudo usermod -a -G audio,video <username>

# 3. 使用 --no-sandbox 参数（已在脚本中配置）
```

### Q7: 内存不足

**原因**: Chromium 运行需要较多内存

**解决方案**:
```bash
# 1. 添加内存限制参数
chrome_options.add_argument('--disable-dev-shm-usage')  # 已在脚本中
chrome_options.add_argument('--memory-pressure-off')

# 2. 减少 Chrome 实例并发数
# 批量提取时，一次只处理一个页面

# 3. 增加交换空间
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Q8: 中文乱码

**原因**: 系统缺少中文字体

**解决方案**:

**CentOS/RHEL**:
```bash
sudo yum install -y wqy-zenhei-fonts wqy-microhei-fonts
```

**Ubuntu/Debian**:
```bash
sudo apt install -y fonts-wqy-zenhei fonts-wqy-microhei
```

---

## 十一、快速部署清单

### 在公司内网环境快速部署

#### 步骤 1: 环境检查（5 分钟）

```bash
# 1. 检查操作系统
cat /etc/os-release

# 2. 检查 Python
python3 --version

# 3. 检查网络连通性
curl -I http://10.65.134.124:8080/metrics

# 4. 检查磁盘空间
df -h

# 5. 检查内存
free -h
```

#### 步骤 2: 安装依赖（10 分钟）

**使用一键安装脚本**:
```bash
# 下载脚本（从当前环境复制）
cp /root/.openclaw/workspace/knowledge/tech/AI-Native/install_selenium_env.sh .
chmod +x install_selenium_env.sh

# 运行安装
./install_selenium_env.sh
```

**或手动安装**（参考 2.1-2.2 节）

#### 步骤 3: 配置网络（5 分钟）

```bash
# 1. 测试连通性
curl -I http://10.65.134.124:8080/metrics

# 2. 配置代理（如需要）
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="10.65.134.124,10.65.0.0/16,localhost,127.0.0.1"

# 3. 配置 DNS（如需要）
sudo echo "nameserver <内网DNS>" >> /etc/resolv.conf

# 4. 配置路由（如需要）
sudo route add -net 10.65.0.0/16 gw <网关IP>
```

#### 步骤 4: 复制脚本文件（5 分钟）

```bash
# 从当前环境复制脚本文件到目标环境
# 方式 1: 通过 scp（如果网络连通）
scp -r /root/.openclaw/workspace/scripts/frontend/* <user>@<target-host>:/path/to/frontend/

# 方式 2: 通过 U 盘/共享文件夹
# 复制以下文件:
# - extract_structure_selenium.py
# - batch_extract.py
# - test_drill_down.py
# - test_selenium.py
```

#### 步骤 5: 验证环境（5 分钟）

```bash
# 1. 验证工具版本
python3 --version
python3 -c "import selenium; print('Selenium:', selenium.__version__)"
chromedriver --version

# 2. 运行环境测试
python3 test_selenium.py

# 3. 测试访问目标页面
cat > test_target.py << 'EOF'
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.binary_location = '/usr/lib64/chromium-browser/headless_shell'

try:
    driver = webdriver.Chrome(
        executable_path='/usr/local/bin/chromedriver',
        options=chrome_options
    )
    
    driver.get('http://10.65.134.124:8080/metrics')
    print(f"✅ 成功访问目标页面！标题: {driver.title}")
    
    driver.quit()
except Exception as e:
    print(f"❌ 访问失败: {str(e)}")
EOF

python3 test_target.py
```

#### 步骤 6: 开始使用

```bash
# 批量提取原型页面
python3 batch_extract.py

# 查看结果
cat prototype-structure/summary.json

# 测试下钻交互
python3 test_drill_down.py http://10.65.134.124:8080/metrics "终端安全产品研发部"
```

---

## 十二、联系与支持

### 遇到问题？

1. **查看本文档** - 大部分问题都有解决方案
2. **查看日志** - 脚本运行时的错误信息
3. **检查网络** - 内网环境最容易出问题
4. **版本匹配** - 确保 ChromeDriver 和 Chromium 版本一致

### 需要帮助？

- 提供错误信息截图
- 提供环境信息（OS、Python、Selenium、Chromium 版本）
- 提供网络配置信息（是否使用代理、DNS 设置）
