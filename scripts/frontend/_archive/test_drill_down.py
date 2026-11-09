#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试页面的下钻交互逻辑
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

class DrillDownTester:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None

    def init_driver(self):
        """初始化浏览器"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.binary_location = '/usr/lib64/chromium-browser/headless_shell'

        self.driver = webdriver.Chrome(
            executable_path='/usr/local/bin/chromedriver',
            options=chrome_options
        )

    def test_drill_down(self, url, team_name, output_file):
        """
        测试下钻交互

        Args:
            url: 页面 URL
            team_name: 要点击的团队名称
            output_file: 输出文件
        """
        print(f"🌐 访问: {url}")
        self.driver.get(url)
        time.sleep(2)

        results = {
            'url': url,
            'drill_down_path': []
        }

        # 第一步：体系级页面
        print("\n📊 提取体系级数据...")
        results['level_1'] = self.extract_current_state()
        results['drill_down_path'].append('体系整体')

        # 第二步：点击某一行下钻到团队级
        print(f"\n👆 点击团队: {team_name}")
        try:
            # 查找包含团队名称的表格行
            row = self.driver.find_element(By.XPATH, f"//tbody/tr[td[text()='{team_name}']]")
            row.click()
            time.sleep(2)

            # 提取团队级数据
            print("📊 提取团队级数据...")
            results['level_2'] = self.extract_current_state()
            results['drill_down_path'].append(team_name)

            # 第三步：再下钻到个人级（如果有）
            try:
                print("\n👆 尝试继续下钻到个人级...")
                first_person_row = self.driver.find_element(By.CSS_SELECTOR, 'tbody tr:first-child')
                first_person_row.click()
                time.sleep(2)

                print("📊 提取个人级数据...")
                results['level_3'] = self.extract_current_state()
                results['drill_down_path'].append('个人级')
            except:
                print("⚠️ 无法继续下钻（可能已到最底层）")

        except Exception as e:
            print(f"❌ 下钻失败: {str(e)}")

        # 测试面包屑导航返回
        print("\n🔙 测试面包屑导航返回...")
        try:
            breadcrumb_items = self.driver.find_elements(By.CSS_SELECTOR, '.breadcrumb-item, .breadcrumb li')
            if breadcrumb_items:
                # 点击第一个面包屑（返回最上层）
                breadcrumb_items[0].click()
                time.sleep(2)

                print("📊 提取返回后的数据...")
                results['back_to_top'] = self.extract_current_state()

        except Exception as e:
            print(f"⚠️ 面包屑导航测试失败: {str(e)}")

        # 保存结果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 下钻测试完成！结果已保存到: {output_file}")
        return results

    def extract_current_state(self):
        """提取当前页面的状态"""
        try:
            # 提取面包屑
            breadcrumb = []
            try:
                breadcrumb_items = self.driver.find_elements(By.CSS_SELECTOR, '.breadcrumb-item, .breadcrumb li')
                breadcrumb = [item.text.strip() for item in breadcrumb_items if item.text.strip()]
            except:
                pass

            # 提取表格
            table_data = {'headers': [], 'rows': [], 'row_count': 0}
            try:
                table = self.driver.find_element(By.TAG_NAME, 'table')
                headers = table.find_elements(By.TAG_NAME, 'th')
                table_data['headers'] = [h.text.strip() for h in headers]

                rows = table.find_elements(By.CSS_SELECTOR, 'tbody tr')
                table_data['row_count'] = len(rows)

                for row in rows[:5]:  # 只取前 5 行
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    table_data['rows'].append([cell.text.strip() for cell in cells])
            except:
                pass

            return {
                'breadcrumb': breadcrumb,
                'table': table_data,
                'url': self.driver.current_url
            }
        except Exception as e:
            print(f"⚠️ 提取状态失败: {str(e)}")
            return {}

def main():
    if len(sys.argv) < 2:
        print("用法: python3 test_drill_down.py <URL> [团队名称] [输出文件]")
        print("示例: python3 test_drill_down.py http://10.65.134.124:8080/metrics '终端安全产品研发部' drill-down-result.json")
        sys.exit(1)

    url = sys.argv[1]
    team_name = sys.argv[2] if len(sys.argv) > 2 else '终端安全产品研发部'
    output_file = sys.argv[3] if len(sys.argv) > 3 else '/tmp/drill-down-result.json'

    tester = DrillDownTester(headless=True)
    tester.init_driver()

    try:
        result = tester.test_drill_down(url, team_name, output_file)

        # 打印摘要
        print(f"\n{'='*60}")
        print("📋 下钻路径:")
        for i, level in enumerate(result['drill_down_path'], 1):
            print(f"  {i}. {level}")
        print(f"{'='*60}")
    finally:
        tester.driver.quit()

import sys

if __name__ == '__main__':
    main()
