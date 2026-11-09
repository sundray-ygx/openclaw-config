#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Selenium + Chromium 是否能正常工作
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def test_selenium():
    try:
        # 配置 Chrome 选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.binary_location = '/usr/lib64/chromium-browser/headless_shell'

        # 启动浏览器
        driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)

        # 访问测试页面
        driver.get('http://10.65.134.124:8080/metrics')

        # 等待页面加载
        driver.implicitly_wait(10)

        # 获取页面标题
        title = driver.title
        print(f"✅ 页面标题: {title}")

        # 获取页面 URL
        url = driver.current_url
        print(f"✅ 当前 URL: {url}")

        # 测试元素提取
        tables = driver.find_elements_by_tag_name('table')
        print(f"✅ 找到 {len(tables)} 个表格")

        if tables:
            headers = [th.text for th in tables[0].find_elements_by_tag_name('th')]
            print(f"✅ 表格列名: {headers}")

        driver.quit()
        return True

    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_selenium()
    exit(0 if success else 1)
