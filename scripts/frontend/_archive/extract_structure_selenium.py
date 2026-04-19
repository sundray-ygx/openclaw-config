#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端页面结构自动提取工具
使用 Selenium + Chromium 提取页面 DOM 结构、组件信息、交互逻辑

输出格式: JSON
适用场景: 1:1 复刻前端页面
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import sys
from datetime import datetime

class FrontendStructureExtractor:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None

    def init_driver(self):
        """初始化 Selenium WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.binary_location = '/usr/lib64/chromium-browser/headless_shell'

        try:
            self.driver = webdriver.Chrome(
                executable_path='/usr/local/bin/chromedriver',
                options=chrome_options
            )
            return True
        except Exception as e:
            print(f"❌ 初始化浏览器失败: {str(e)}")
            return False

    def extract_navigation(self):
        """提取导航栏信息"""
        try:
            # 尝试多种常见的导航选择器
            nav_selectors = [
                'nav',
                '[role="navigation"]',
                '.navbar',
                '.nav-tabs',
                '[role="tablist"]',
                '.navigation'
            ]

            nav_data = {'tabs': []}

            for selector in nav_selectors:
                try:
                    nav = self.driver.find_element(By.CSS_SELECTOR, selector)
                    tabs = nav.find_elements(By.CSS_SELECTOR, 'a, [role="tab"], .nav-item')

                    for tab in tabs:
                        tab_info = {
                            'text': tab.text.strip(),
                            'href': tab.get_attribute('href'),
                            'active': 'active' in tab.get_attribute('class') or tab.get_attribute('aria-selected') == 'true'
                        }
                        if tab_info['text']:  # 只记录有文字的标签
                            nav_data['tabs'].append(tab_info)

                    if nav_data['tabs']:
                        break
                except:
                    continue

            return nav_data
        except Exception as e:
            print(f"⚠️ 提取导航失败: {str(e)}")
            return {'tabs': []}

    def extract_filters(self):
        """提取筛选区域信息"""
        try:
            filter_selectors = [
                '.filter-bar',
                '.filter-section',
                '[class*="filter"]',
                '.search-bar'
            ]

            filters_data = {'fields': []}

            for selector in filter_selectors:
                try:
                    filter_bar = self.driver.find_element(By.CSS_SELECTOR, selector)
                    inputs = filter_bar.find_elements(By.CSS_SELECTOR, 'input, select, button')

                    for input_elem in inputs:
                        field_info = {
                            'type': input_elem.get_attribute('type') or input_elem.tag_name,
                            'name': input_elem.get_attribute('name') or '',
                            'id': input_elem.get_attribute('id') or '',
                            'placeholder': input_elem.get_attribute('placeholder') or '',
                            'class': input_elem.get_attribute('class') or '',
                            'text': input_elem.text.strip() if input_elem.tag_name == 'button' else ''
                        }
                        filters_data['fields'].append(field_info)

                    if filters_data['fields']:
                        break
                except:
                    continue

            return filters_data
        except Exception as e:
            print(f"⚠️ 提取筛选栏失败: {str(e)}")
            return {'fields': []}

    def extract_metric_cards(self):
        """提取指标卡片信息"""
        try:
            card_selectors = [
                '.metric-card',
                '.card',
                '.stat-card',
                '[class*="card"][class*="metric"]'
            ]

            cards_data = []

            for selector in card_selectors:
                try:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for card in cards:
                        # 提取标题
                        title_elem = card.find_element(By.CSS_SELECTOR, '.title, .card-title, h3, h4, .label')
                        title = title_elem.text.strip() if title_elem else ''

                        # 提取主值
                        value_elem = card.find_element(By.CSS_SELECTOR, '.value, .card-value, .number, .stat-value')
                        value = value_elem.text.strip() if value_elem else ''

                        # 提取副值
                        subvalue_elem = card.find_elements(By.CSS_SELECTOR, '.subvalue, .card-subvalue, .subtitle')
                        subvalue = subvalue_elem[0].text.strip() if subvalue_elem else ''

                        if title or value:
                            cards_data.append({
                                'title': title,
                                'value': value,
                                'subvalue': subvalue
                            })

                    if cards_data:
                        break
                except:
                    continue

            return cards_data
        except Exception as e:
            print(f"⚠️ 提取指标卡片失败: {str(e)}")
            return []

    def extract_table(self):
        """提取表格信息"""
        try:
            table = self.driver.find_element(By.TAG_NAME, 'table')
            table_data = {
                'headers': [],
                'rows': [],
                'row_count': 0
            }

            # 提取表头
            try:
                headers = table.find_elements(By.TAG_NAME, 'th')
                table_data['headers'] = [h.text.strip() for h in headers]
            except:
                pass

            # 提取表格行（最多 5 行作为示例）
            try:
                rows = table.find_elements(By.CSS_SELECTOR, 'tbody tr')
                table_data['row_count'] = len(rows)

                for i, row in enumerate(rows[:5]):  # 只取前 5 行
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    row_data = [cell.text.strip() for cell in cells]
                    table_data['rows'].append(row_data)
            except:
                pass

            return table_data
        except Exception as e:
            print(f"⚠️ 提取表格失败: {str(e)}")
            return {'headers': [], 'rows': [], 'row_count': 0}

    def extract_breadcrumb(self):
        """提取面包屑导航"""
        try:
            breadcrumb_selectors = [
                '.breadcrumb',
                '[aria-label="breadcrumb"]',
                '.nav-breadcrumb'
            ]

            breadcrumb_data = {'items': []}

            for selector in breadcrumb_selectors:
                try:
                    breadcrumb = self.driver.find_element(By.CSS_SELECTOR, selector)
                    items = breadcrumb.find_elements(By.CSS_SELECTOR, 'li, a, .breadcrumb-item')

                    breadcrumb_data['items'] = [item.text.strip() for item in items if item.text.strip()]

                    if breadcrumb_data['items']:
                        break
                except:
                    continue

            return breadcrumb_data
        except Exception as e:
            print(f"⚠️ 提取面包屑失败: {str(e)}")
            return {'items': []}

    def extract_api_requests(self):
        """提取 Network 面板中的 API 请求（通过执行 JS）"""
        try:
            # 注入 JS 监听网络请求
            script = """
            (function() {
                const requests = [];
                const originalFetch = window.fetch;
                window.fetch = function(...args) {
                    requests.push({
                        url: args[0],
                        method: args[1]?.method || 'GET',
                        body: args[1]?.body || null
                    });
                    return originalFetch.apply(this, args);
                };
                window.capturedRequests = requests;
                return requests.length;
            })();
            """
            self.driver.execute_script(script)

            # 等待一段时间收集请求
            time.sleep(2)

            # 获取捕获的请求
            requests = self.driver.execute_script("return window.capturedRequests || [];")

            return requests
        except Exception as e:
            print(f"⚠️ 提取 API 请求失败: {str(e)}")
            return []

    def extract_page(self, url, output_file=None):
        """提取页面完整结构"""
        if not self.init_driver():
            return None

        try:
            print(f"🌐 访问: {url}")
            self.driver.get(url)

            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            time.sleep(2)  # 额外等待动态内容加载

            print("📊 提取页面结构...")

            # 提取各个组件
            result = {
                'url': url,
                'title': self.driver.title,
                'timestamp': datetime.now().isoformat(),
                'navigation': self.extract_navigation(),
                'filters': self.extract_filters(),
                'metric_cards': self.extract_metric_cards(),
                'table': self.extract_table(),
                'breadcrumb': self.extract_breadcrumb(),
                'api_requests': self.extract_api_requests()
            }

            # 输出结果
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"✅ 结果已保存到: {output_file}")
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))

            return result

        except Exception as e:
            print(f"❌ 提取失败: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

def main():
    if len(sys.argv) < 2:
        print("用法: python3 extract_structure_selenium.py <URL> [输出文件]")
        print("示例: python3 extract_structure_selenium.py http://10.65.134.124:8080/metrics output.json")
        sys.exit(1)

    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    extractor = FrontendStructureExtractor(headless=True)
    result = extractor.extract_page(url, output_file)

    if result:
        print("\n✅ 提取完成！")
        print(f"📋 导航 Tab 数量: {len(result['navigation']['tabs'])}")
        print(f"🔍 筛选字段数量: {len(result['filters']['fields'])}")
        print(f"📈 指标卡片数量: {len(result['metric_cards'])}")
        print(f"📊 表格行数: {result['table']['row_count']}")
        print(f"🍞 面包屑层级: {len(result['breadcrumb']['items'])}")
        sys.exit(0)
    else:
        print("❌ 提取失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
