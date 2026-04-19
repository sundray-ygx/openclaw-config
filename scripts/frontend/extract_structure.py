#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端页面结构自动提取工具 (Win10 适配版)
使用 Selenium 自动提取页面 DOM 结构、组件信息、交互逻辑
输出 JSON 格式，适用于 minimax 2.7 等上下文受限模型

用法:
  python extract_structure.py <URL> [-o 输出文件] [--drill-down 团队名] [--chromedriver 路径]

示例:
  python extract_structure.py http://10.65.134.124:8080/metrics -o metrics.json
  python extract_structure.py http://10.65.134.124:8080/metrics --drill-down "终端安全产品研发部" -o drill.json
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import sys
import os
from datetime import datetime


class FrontendStructureExtractor:
    def __init__(self, headless=True, chromedriver_path=None):
        self.headless = headless
        self.chromedriver_path = chromedriver_path
        self.driver = None

    def init_driver(self):
        """初始化 Selenium WebDriver（含反检测措施）"""
        options = Options()
        if self.headless:
            options.add_argument('--headless')
            # headless 模式下伪装 User-Agent，避免被检测
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        # 反自动化检测：排除自动化开关
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        # 禁止图片加载（加速）
        prefs = {
            'profile.managed_default_content_settings.images': 2,
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
        }
        options.add_experimental_option('prefs', prefs)

        try:
            if self.chromedriver_path:
                service = Service(executable_path=self.chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)

            # 反检测：修改 navigator.webdriver 为 undefined
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })

            # 反检测：补充 Chrome 特征
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['zh-CN', 'zh', 'en'],
                    });
                '''
            })

            return True
        except Exception as e:
            print(f"❌ 初始化浏览器失败: {e}")
            print("  请确保:")
            print("  1. 已安装 Chrome 或 Chromium")
            print("  2. ChromeDriver 在 PATH 中且版本匹配")
            print("  3. 或使用 --chromedriver 参数指定路径")
            return False

    def _safe_find(self, by, selector, parent=None):
        """安全查找元素，返回 None 而不是抛异常"""
        ctx = parent or self.driver
        try:
            return ctx.find_element(by, selector)
        except:
            return None

    def _safe_find_all(self, by, selector, parent=None):
        """安全查找多个元素"""
        ctx = parent or self.driver
        try:
            return ctx.find_elements(by, selector)
        except:
            return []

    def extract_navigation(self):
        """提取导航栏信息"""
        nav_data = {'tabs': []}

        nav_selectors = [
            'nav', '[role="navigation"]', '.navbar', '.nav-tabs',
            '[role="tablist"]', '.navigation', 'header nav', '.header-nav',
        ]

        for selector in nav_selectors:
            nav = self._safe_find(By.CSS_SELECTOR, selector)
            if not nav:
                continue

            tabs = self._safe_find_all(By.CSS_SELECTOR, 'a, [role="tab"], .nav-item, .tab-item', nav)
            for tab in tabs:
                text = tab.text.strip()
                if text:
                    nav_data['tabs'].append({
                        'text': text,
                        'href': tab.get_attribute('href'),
                        'active': (
                            'active' in (tab.get_attribute('class') or '')
                            or tab.get_attribute('aria-selected') == 'true'
                        )
                    })
            if nav_data['tabs']:
                break

        return nav_data

    def extract_filters(self):
        """提取筛选区域信息"""
        filters_data = {'fields': []}

        filter_selectors = [
            '.filter-bar', '.filter-section', '.search-bar',
            '[class*="filter"]', '[class*="search"]',
            '.toolbar', '.query-bar',
        ]

        for selector in filter_selectors:
            filter_bar = self._safe_find(By.CSS_SELECTOR, selector)
            if not filter_bar:
                continue

            inputs = self._safe_find_all(By.CSS_SELECTOR, 'input, select, button', filter_bar)
            for elem in inputs:
                field = {
                    'tag': elem.tag_name,
                    'type': elem.get_attribute('type') or '',
                    'name': elem.get_attribute('name') or '',
                    'id': elem.get_attribute('id') or '',
                    'placeholder': elem.get_attribute('placeholder') or '',
                    'value': elem.get_attribute('value') or '',
                }
                if elem.tag_name == 'button':
                    field['text'] = elem.text.strip()
                if elem.tag_name == 'select':
                    options = self._safe_find_all(By.TAG_NAME, 'option', elem)
                    field['options'] = [opt.text.strip() for opt in options if opt.text.strip()]
                filters_data['fields'].append(field)

            if filters_data['fields']:
                break

        return filters_data

    def extract_metric_cards(self):
        """提取指标卡片信息"""
        cards_data = []

        card_selectors = [
            '.metric-card', '.card', '.stat-card', '.kpi-card',
            '[class*="card"][class*="metric"]', '[class*="card"][class*="stat"]',
            '.summary-card', '.overview-card',
        ]

        for selector in card_selectors:
            cards = self._safe_find_all(By.CSS_SELECTOR, selector)
            if not cards:
                continue

            for card in cards:
                title = ''
                for t_sel in ['.title', '.card-title', 'h3', 'h4', '.label', '.name', '.card-label']:
                    elem = self._safe_find(By.CSS_SELECTOR, t_sel, card)
                    if elem and elem.text.strip():
                        title = elem.text.strip()
                        break

                value = ''
                for v_sel in ['.value', '.card-value', '.number', '.stat-value', '.card-number']:
                    elem = self._safe_find(By.CSS_SELECTOR, v_sel, card)
                    if elem and elem.text.strip():
                        value = elem.text.strip()
                        break

                subvalue = ''
                for s_sel in ['.subvalue', '.subtitle', '.desc', '.card-desc']:
                    elem = self._safe_find(By.CSS_SELECTOR, s_sel, card)
                    if elem and elem.text.strip():
                        subvalue = elem.text.strip()
                        break

                if title or value:
                    cards_data.append({
                        'title': title,
                        'value': value,
                        'subvalue': subvalue,
                    })

            if cards_data:
                break

        return cards_data

    def extract_table(self):
        """提取表格信息"""
        table_data = {'headers': [], 'rows': [], 'row_count': 0}

        table = self._safe_find(By.TAG_NAME, 'table')
        if not table:
            return table_data

        headers = self._safe_find_all(By.TAG_NAME, 'th', table)
        table_data['headers'] = [h.text.strip() for h in headers if h.text.strip()]

        rows = self._safe_find_all(By.CSS_SELECTOR, 'tbody tr', table)
        table_data['row_count'] = len(rows)

        for row in rows[:5]:
            cells = self._safe_find_all(By.TAG_NAME, 'td', row)
            row_data = [cell.text.strip() for cell in cells]
            if row_data:
                table_data['rows'].append(row_data)

        return table_data

    def extract_breadcrumb(self):
        """提取面包屑导航"""
        breadcrumb_data = {'items': []}

        selectors = [
            '.breadcrumb', '[aria-label="breadcrumb"]',
            '.nav-breadcrumb', '[class*="breadcrumb"]',
        ]

        for selector in selectors:
            breadcrumb = self._safe_find(By.CSS_SELECTOR, selector)
            if not breadcrumb:
                continue

            items = self._safe_find_all(By.CSS_SELECTOR, 'li, a, .breadcrumb-item, span', breadcrumb)
            breadcrumb_data['items'] = [
                item.text.strip() for item in items
                if item.text.strip() and item.text.strip() != '>'
            ]
            if breadcrumb_data['items']:
                break

        return breadcrumb_data

    def extract_network_requests(self):
        """提取页面加载时的网络请求（通过 Performance API）"""
        try:
            requests = self.driver.execute_script("""
                var entries = performance.getEntriesByType('resource');
                return entries.filter(e => e.initiatorType === 'xmlhttprequest' || e.initiatorType === 'fetch')
                    .map(e => ({url: e.name, type: e.initiatorType, duration: Math.round(e.duration)}));
            """)
            return requests or []
        except:
            return []

    def extract_page_source_summary(self):
        """提取页面源码摘要（框架检测）"""
        try:
            page_source = self.driver.page_source
            framework = 'unknown'
            if 'data-reactroot' in page_source or '__REACT' in page_source:
                framework = 'React'
            elif '__vue__' in page_source or 'data-v-' in page_source:
                framework = 'Vue'
            elif 'ng-version' in page_source or 'ng-' in page_source:
                framework = 'Angular'

            ui_lib = 'unknown'
            if 'ant-design' in page_source or 'anticon' in page_source:
                ui_lib = 'Ant Design'
            elif 'element-ui' in page_source or 'el-' in page_source:
                ui_lib = 'Element UI'
            elif 'el-' in page_source:
                ui_lib = 'Element Plus'

            return {'framework': framework, 'ui_library': ui_lib}
        except:
            return {'framework': 'unknown', 'ui_library': 'unknown'}

    def extract_page(self, url, output_file=None, cookie_file=None, scroll_page=True):
        """提取页面完整结构
        
        Args:
            url: 目标 URL
            output_file: 输出 JSON 路径
            cookie_file: Cookie 文件路径（如果页面需要登录）
            scroll_page: 是否滚动页面触发懒加载
        """
        if not self.init_driver():
            return None

        try:
            print(f"🌐 访问: {url}")
            self.driver.get(url)

            # 如果有 Cookie 文件，加载 Cookie
            if cookie_file and os.path.exists(cookie_file):
                print(f"🍪 加载 Cookie: {cookie_file}")
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
                self.driver.refresh()

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            time.sleep(2)

            # 滚动页面触发懒加载
            if scroll_page:
                print("📜 滚动页面触发懒加载...")
                last_height = self.driver.execute_script('return document.body.scrollHeight')
                for _ in range(3):
                    self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(1)
                    new_height = self.driver.execute_script('return document.body.scrollHeight')
                    if new_height == last_height:
                        break
                    last_height = new_height
                self.driver.execute_script('window.scrollTo(0, 0)')
                time.sleep(1)

            print("📊 提取页面结构...")

            result = {
                'url': url,
                'title': self.driver.title,
                'timestamp': datetime.now().isoformat(),
                'tech_stack': self.extract_page_source_summary(),
                'navigation': self.extract_navigation(),
                'filters': self.extract_filters(),
                'metric_cards': self.extract_metric_cards(),
                'table': self.extract_table(),
                'breadcrumb': self.extract_breadcrumb(),
                'network_requests': self.extract_network_requests(),
            }

            json_str = json.dumps(result, ensure_ascii=False, indent=2)
            if output_file:
                os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                print(f"✅ 结果已保存: {output_file}")
            else:
                print(json_str)

            return result

        except Exception as e:
            print(f"❌ 提取失败: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

    def test_drill_down(self, url, team_name, output_file=None):
        """测试下钻交互逻辑"""
        if not self.init_driver():
            return None

        try:
            print(f"🌐 访问: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            time.sleep(3)

            results = {
                'url': url,
                'drill_down_path': [],
                'levels': {}
            }

            # Level 1: 体系级
            print("📊 提取体系级数据...")
            results['levels']['level_1_system'] = self._extract_current_state()
            results['drill_down_path'].append('体系整体')

            # Level 2: 点击团队行下钻
            print(f"👆 点击团队: {team_name}")
            try:
                row = self.driver.find_element(
                    By.XPATH, f"//tbody/tr[td[contains(text(),'{team_name}')]]"
                )
                row.click()
                time.sleep(3)

                print("📊 提取团队级数据...")
                results['levels']['level_2_team'] = self._extract_current_state()
                results['drill_down_path'].append(team_name)

                # Level 3: 继续下钻到个人级
                try:
                    print("👆 尝试继续下钻到个人级...")
                    first_row = self.driver.find_element(By.CSS_SELECTOR, 'tbody tr')
                    first_row.click()
                    time.sleep(3)

                    print("📊 提取个人级数据...")
                    results['levels']['level_3_person'] = self._extract_current_state()
                    results['drill_down_path'].append('个人级')
                except:
                    print("⚠️ 无法继续下钻（可能已到最底层）")

            except Exception as e:
                print(f"❌ 下钻失败: {e}")

            # 测试面包屑返回
            print("🔙 测试面包屑返回...")
            try:
                breadcrumb_items = self._safe_find_all(
                    By.CSS_SELECTOR, '.breadcrumb-item, .breadcrumb li, [class*="breadcrumb"] li'
                )
                if breadcrumb_items:
                    breadcrumb_items[0].click()
                    time.sleep(2)
                    results['back_to_top'] = self._extract_current_state()
                    print("✅ 面包屑返回成功")
            except:
                print("⚠️ 面包屑导航测试跳过")

            if output_file:
                os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"✅ 下钻测试结果已保存: {output_file}")

            return results

        except Exception as e:
            print(f"❌ 下钻测试失败: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

    def _extract_current_state(self):
        """提取当前页面状态"""
        return {
            'url': self.driver.current_url,
            'breadcrumb': self.extract_breadcrumb(),
            'table': self.extract_table(),
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='前端页面结构自动提取工具')
    parser.add_argument('url', help='目标页面 URL')
    parser.add_argument('-o', '--output', help='输出 JSON 文件路径')
    parser.add_argument('--drill-down', metavar='TEAM', help='测试下钻交互，指定团队名称')
    parser.add_argument('--chromedriver', help='ChromeDriver 路径')
    parser.add_argument('--cookie', help='Cookie 文件路径（用于需要登录的页面）')
    parser.add_argument('--no-scroll', action='store_true', help='禁用滚动触发懒加载')
    args = parser.parse_args()

    extractor = FrontendStructureExtractor(
        headless=True,
        chromedriver_path=args.chromedriver
    )

    if args.drill_down:
        result = extractor.test_drill_down(args.url, args.drill_down, args.output)
    else:
        result = extractor.extract_page(args.url, args.output, cookie_file=args.cookie, scroll_page=not args.no_scroll)

    if result:
        print("\n✅ 提取完成！")
        if 'drill_down_path' in result:
            print(f"📋 下钻路径: {' → '.join(result['drill_down_path'])}")
        else:
            print(f"📋 导航 Tab: {len(result.get('navigation', {}).get('tabs', []))} 个")
            print(f"🔍 筛选字段: {len(result.get('filters', {}).get('fields', []))} 个")
            print(f"📈 指标卡片: {len(result.get('metric_cards', []))} 个")
            print(f"📊 表格行数: {result.get('table', {}).get('row_count', 0)}")
            print(f"🍞 面包屑: {result.get('breadcrumb', {}).get('items', [])}")
            tech = result.get('tech_stack', {})
            print(f"🔧 技术栈: {tech.get('framework', '?')} + {tech.get('ui_library', '?')}")


if __name__ == '__main__':
    main()
