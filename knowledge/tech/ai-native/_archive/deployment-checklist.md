# 前端自动化提取工具 - 快速部署清单

> 在公司内网环境中快速部署前端页面结构自动化提取工具

---

## 📋 部署前检查

### 1. 系统要求

| 项目 | 最低要求 | 推荐配置 | 检查命令 |
|------|---------|---------|----------|
| 操作系统 | CentOS 7+ / Ubuntu 18.04+ | CentOS 8 / Ubuntu 20.04 | `cat /etc/os-release` |
| Python | 3.6+ | 3.8+ | `python3 --version` |
| 内存 | 2GB | 4GB+ | `free -h` |
| 磁盘 | 5GB | 10GB+ | `df -h` |
| 网络 | 可访问目标 URL | - | `curl -I http://10.65.134.124:8080/metrics` |

### 2. 运行环境检查

```bash
# 一键检查脚本
cat > check_env.sh << 'EOF'
#!/bin/bash
echo "🔍 检查环境..."

check_item() {
    local name=$1
    local cmd=$2
    local expected=$3

    echo -n "$name: "
    result=$($cmd 2>&1)
    if echo "$result" | grep -q "$expected"; then
        echo "✅ $result"
        return 0
    else
        echo "❌ $result"
        return 1
    fi
}

# 检查项
check_item "Python" "python3 --version" "Python 3"
check_item "Selenium" "python3 -c 'import selenium; print(selenium.__version__)'" "3.141.0"
check_item "Chromium" "ls -la /usr/lib64/chromium-browser/headless_shell" "headless_shell"
check_item "ChromeDriver" "chromedriver --version" "ChromeDriver"
check_item "网络连通性" "curl -I -s http://10.65.134.124:8080/metrics > /dev/null 2>&1 && echo OK" "OK"

echo ""
echo "✅ 检查完成"
EOF

chmod +x check_env.sh
./check_env.sh
```

---

## 🚀 一键部署

### 方式 1: 使用一键安装脚本（推荐）

```bash
# 1. 下载脚本
cp /root/.openclaw/workspace/knowledge/tech/AI-Native/install_selenium_env.sh .
chmod +x install_selenium_env.sh

# 2. 运行安装
./install_selenium_env.sh

# 3. 验证环境
python3 test_selenium.py
```

### 方式 2: 手动安装

#### 步骤 1: 安装 Python

**CentOS/RHEL**:
```bash
sudo yum install -y python38 python38-pip
sudo ln -sf /usr/bin/python3.8 /usr/bin/python3
sudo ln -sf /usr/bin/pip3.8 /usr/bin/pip3
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install -y python3.8 python3-pip
```

#### 步骤 2: 安装 Chromium

**CentOS/RHEL**:
```bash
sudo yum install -y epel-release
sudo yum install -y chromium-headless
```

**Ubuntu/Debian**:
```bash
sudo apt install -y chromium-browser
```

#### 步骤 3: 安装 ChromeDriver

```bash
# 获取 Chromium 版本
CHROMIUM_VERSION=$(chromium-headless --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
echo "Chromium 版本: $CHROMIUM_VERSION"

# 下载匹配的 ChromeDriver
cd /tmp
wget https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.98/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
chromedriver --version
```

#### 步骤 4: 安装 Selenium

```bash
pip3 install selenium==3.141.0
```

#### 步骤 5: 安装依赖库

**CentOS/RHEL**:
```bash
sudo yum install -y atk cups-libs gtk3 libXcomposite libXcursor libXdamage \
    libXext libXi libXrandr libXScrnSaver libXtst pango xorg-x11-fonts-100dpi \
    xorg-x11-fonts-75dpi xorg-x11-fonts-cyrillic xorg-x11-fonts-misc \
    xorg-x11-fonts-Type1 xorg-x11-utils
```

**Ubuntu/Debian**:
```bash
sudo apt install -y libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 \
    libgtk-3-0 libnspr4 libnss3 libwayland-client0 libxcomposite1 \
    libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 libxshmfence1 \
    libxss1 libxtst6
```

---

## 🌐 网络配置

### 测试连通性

```bash
# 测试 HTTP 访问
curl -I http://10.65.134.124:8080/metrics

# 测试端口
telnet 10.65.134.124 8080
# 或
nc -zv 10.65.134.124 8080
```

### 配置代理（如需要）

```bash
# 临时配置
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="10.65.134.124,10.65.0.0/16,localhost,127.0.0.1"

# 永久配置
echo 'export HTTP_PROXY="http://proxy.company.com:8080"' >> ~/.bashrc
echo 'export HTTPS_PROXY="http://proxy.company.com:8080"' >> ~/.bashrc
echo 'export NO_PROXY="10.65.134.124,10.65.0.0/16,localhost,127.0.0.1"' >> ~/.bashrc
source ~/.bashrc
```

### 配置 DNS（如需要）

```bash
# 添加内网 DNS
sudo echo "nameserver 10.0.0.1" >> /etc/resolv.conf

# 配置 /etc/hosts
sudo echo "10.65.134.124  metrics.internal" >> /etc/hosts
```

### 配置路由（如需要）

```bash
# 添加内网路由
sudo route add -net 10.65.0.0/16 gw 10.0.0.254

# 验证路由
route -n | grep 10.65
```

---

## 📁 脚本文件准备

### 复制脚本文件

```bash
# 创建目录
mkdir -p scripts/frontend

# 从当前环境复制（示例，根据实际情况调整）
cp /root/.openclaw/workspace/scripts/frontend/*.py scripts/frontend/

# 验证文件
ls -la scripts/frontend/
```

**需要的脚本文件**:
- `extract_structure_selenium.py` - 提取单页面
- `batch_extract.py` - 批量提取
- `test_drill_down.py` - 下钻测试
- `test_selenium.py` - 环境测试

### 修改配置（如需要）

如果 Chromium 路径不同，修改脚本中的 `binary_location`:

```bash
# 查找 Chromium 实际路径
find /usr -name "chromium" -o -name "headless_shell" 2>/dev/null

# 编辑脚本
vim scripts/frontend/extract_structure_selenium.py

# 修改这一行（根据实际路径调整）:
# CentOS/RHEL:
chrome_options.binary_location = '/usr/lib64/chromium-browser/headless_shell'

# Ubuntu/Debian:
chrome_options.binary_location = '/usr/bin/chromium-browser'
```

---

## ✅ 部署验证

### 1. 环境验证

```bash
# 运行测试脚本
python3 scripts/frontend/test_selenium.py

# 期望输出:
# ✅ 页面标题: 百度一下，你就知道
```

### 2. 目标页面访问测试

```bash
# 测试访问目标页面
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

### 3. 批量提取测试

```bash
# 运行批量提取
python3 scripts/frontend/batch_extract.py

# 查看结果
cat prototype-structure/summary.json
```

---

## ❌ 常见问题快速排查

### 问题 1: Connection timed out

**检查**:
```bash
curl -I http://10.65.134.124:8080/metrics
ping 10.65.134.124
telnet 10.65.134.124 8080
```

**解决**:
- 检查网络连通性
- 配置代理
- 配置内网路由
- 检查防火墙

### 问题 2: no chrome binary

**检查**:
```bash
ls -la /usr/lib64/chromium-browser/headless_shell
```

**解决**:
```bash
# 修改脚本中的 binary_location
chrome_options.binary_location = '<实际 Chromium 路径>'
```

### 问题 3: ChromeDriver version mismatch

**检查**:
```bash
chromedriver --version
chromium-headless --version
```

**解决**:
```bash
# 下载匹配版本的 ChromeDriver
cd /tmp
wget https://storage.googleapis.com/chrome-for-testing-public/<匹配版本>/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
```

### 问题 4: 依赖库缺失

**解决**:

**CentOS/RHEL**:
```bash
sudo yum install -y atk cups-libs gtk3 libXcomposite libXcursor libXdamage \
    libXext libXi libXrandr libXScrnSaver libXtst pango xorg-x11-fonts-100dpi \
    xorg-x11-fonts-75dpi xorg-x11-fonts-cyrillic xorg-x11-fonts-misc \
    xorg-x11-fonts-Type1 xorg-x11-utils
```

**Ubuntu/Debian**:
```bash
sudo apt install -y libatk-bridge2.0-0 libatk1.0-0 libcups2 libdrm2 \
    libgtk-3-0 libnspr4 libnss3 libwayland-client0 libxcomposite1 \
    libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 libxshmfence1 \
    libxss1 libxtst6
```

### 问题 5: 内网无法下载 ChromeDriver

**解决**:

**方案 1**: 使用内部镜像
```bash
wget http://internal-mirror.company.com/chromedriver/chromedriver-133.0.6943.98.zip
unzip chromedriver-133.0.6943.98.zip
sudo mv chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
```

**方案 2**: 手动复制
```bash
# 在有网络的机器上下载，通过 U 盘/共享复制到目标机器
sudo mv /tmp/chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
```

---

## 📞 需要帮助？

### 提供以下信息以便快速定位问题:

1. **环境信息**:
   ```bash
   cat /etc/os-release
   python3 --version
   python3 -c "import selenium; print(selenium.__version__)"
   chromedriver --version
   ```

2. **错误信息**: 脚本运行的完整错误输出

3. **网络配置**:
   ```bash
   echo $HTTP_PROXY
   echo $HTTPS_PROXY
   echo $NO_PROXY
   curl -I http://10.65.134.124:8080/metrics
   ```

4. **日志文件**: 如有日志文件，提供相关部分

---

## 📚 相关文档

- **详细安装指南**: [frontend-automation-setup.md](./frontend-automation-setup.md)
- **复刻开发指南**: [frontend-replication-guide.md](./frontend-replication-guide.md)
- **方案对比**: [frontend-replication-alternatives.md](./frontend-replication-alternatives.md)

---

*文档版本: v1.0*
*更新时间: 2026-04-19*
