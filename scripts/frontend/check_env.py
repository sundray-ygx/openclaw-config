"""环境验证脚本 - Win10 + Selenium"""
import sys

# Windows GBK 控制台兼容
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def check_python():
    print(f"Python: {sys.version}")

def check_selenium():
    try:
        import selenium
        print(f"Selenium: {selenium.__version__}")
    except ImportError:
        print("Selenium: ❌ 未安装，运行 'pip install selenium'")

def check_chrome():
    import subprocess
    try:
        result = subprocess.run(
            ['reg', 'query', r'HKLM\SOFTWARE\Google\Chrome\BLBeacon', '/v', 'version'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip().split()[-1]
            print(f"Chrome: {version}")
            return version
        else:
            print("Chrome: ❌ 未安装")
            return None
    except Exception as e:
        print(f"Chrome: 检查失败 ({e})")
        return None

def check_chromedriver():
    import subprocess
    try:
        result = subprocess.run(['chromedriver', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"ChromeDriver: {result.stdout.strip()}")
        else:
            print("ChromeDriver: ❌ 未安装或不在 PATH 中")
    except FileNotFoundError:
        print("ChromeDriver: ❌ 未安装或不在 PATH 中")

def check_network():
    import urllib.request
    try:
        req = urllib.request.Request('http://10.65.134.124:8080/metrics', method='HEAD')
        urllib.request.urlopen(req, timeout=5)
        print("网络连通性: ✅ 可访问目标页面")
    except Exception as e:
        print(f"网络连通性: ❌ {e}")

def check_webdriver():
    """完整 Selenium 驱动测试"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=options)
        driver.get('https://www.baidu.com')
        print(f"Selenium 驱动测试: ✅ 页面标题: {driver.title}")
        driver.quit()
    except Exception as e:
        print(f"Selenium 驱动测试: ❌ {e}")

if __name__ == '__main__':
    print("🔍 环境检查\n" + "=" * 40)
    check_python()
    check_selenium()
    check_chrome()
    check_chromedriver()
    check_network()
    print()
    check_webdriver()
    print("\n✅ 检查完成")
