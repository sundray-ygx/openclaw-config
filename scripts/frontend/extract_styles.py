#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright 页面样式提取工具
获取原平台完整样式信息（CSS、布局、截图、组件树），用于 1:1 复刻

用法:
  pip install playwright
  python -m playwright install chromium
  python extract_styles.py <URL> [-o 输出目录]

示例:
  python extract_styles.py http://10.65.134.124:8080/metrics -o metrics-output
  python extract_styles.py http://10.65.134.124:8080/metrics -o metrics-output --drill-down "溯源研发部"
"""

import sys
import os
import json
import time
import base64
import argparse
from datetime import datetime

# Windows GBK 控制台兼容
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("Playwright 未安装，请执行:")
    print("  pip install playwright")
    print("  python -m playwright install chromium")
    sys.exit(1)


class StyleExtractor:
    def __init__(self, output_dir="style-output"):
        self.output_dir = output_dir
        self.browser = None
        self.page = None

    def init_browser(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
        )
        self.page = self.context.new_page()
        print("[OK] 浏览器启动成功")

    def close(self):
        if self.browser:
            self.browser.close()
        if hasattr(self, 'pw'):
            self.pw.stop()

    def _save_json(self, data, filename):
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] 已保存: {path}")
        return path

    def _screenshot(self, name, element=None, full_page=True):
        path = os.path.join(self.output_dir, f"{name}.png")
        if element:
            element.screenshot(path=path)
        else:
            self.page.screenshot(path=path, full_page=full_page)
        print(f"[OK] 截图: {path}")
        return path

    # ==================== 主要提取方法 ====================

    def extract_all(self, url, drill_down_team=None):
        """完整提取流程"""
        os.makedirs(self.output_dir, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"目标: {url}")
        print(f"{'='*60}\n")

        self.init_browser()

        # 拦截 API 请求
        api_logs = []
        def handle_response(response):
            if any(k in response.url for k in ['/api/', '/graphql', '/query', '/data']):
                try:
                    body = response.text()
                except:
                    body = None
                api_logs.append({
                    'url': response.url,
                    'method': response.request.method,
                    'status': response.status,
                    'request_body': response.request.post_data,
                    'response_body': body[:50000] if body else None,
                    'headers': dict(response.headers),
                })
        self.page.on('response', handle_response)

        # 访问页面
        print("[1/8] 访问页面...")
        self.page.goto(url, wait_until='networkidle', timeout=30000)
        time.sleep(3)

        # 2. 全页截图
        print("\n[2/8] 全页截图...")
        self._screenshot("01-full-page")

        # 3. 获取页面 HTML 和所有 CSS
        print("\n[3/8] 提取 HTML + CSS...")
        page_assets = self._extract_page_assets()
        self._save_json(page_assets['meta'], "02-page-meta.json")

        # 保存完整 HTML
        html_path = os.path.join(self.output_dir, "03-full-page.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(page_assets['html'])
        print(f"[OK] HTML: {html_path}")

        # 保存合并后的 CSS
        css_path = os.path.join(self.output_dir, "04-all-styles.css")
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(page_assets['css'])
        print(f"[OK] CSS: {css_path}")

        # 4. 组件级样式快照
        print("\n[4/8] 提取组件级样式...")
        component_styles = self._extract_component_styles()
        self._save_json(component_styles, "05-component-styles.json")

        # 5. 布局信息
        print("\n[5/8] 提取布局信息...")
        layout_info = self._extract_layout()
        self._save_json(layout_info, "06-layout.json")

        # 6. 图标/Logo 资源
        print("\n[6/8] 提取图标和 Logo...")
        icons = self._extract_icons()
        self._save_json(icons, "07-icons.json")

        # 7. 下钻测试
        if drill_down_team:
            print(f"\n[7/8] 测试下钻: {drill_down_team}...")
            self._test_drill_down(drill_down_team)
        else:
            print("\n[7/8] 跳过下钻测试（未指定团队名）")

        # 8. 汇总 API 日志
        print(f"\n[8/8] 汇总 API 请求（共 {len(api_logs)} 个）...")
        self._save_json(api_logs, "08-api-calls.json")

        # 输出摘要
        print(f"\n{'='*60}")
        print(f"提取完成！输出目录: {self.output_dir}")
        print(f"{'='*60}")
        print(f"文件清单:")
        print(f"  01-full-page.png       - 全页截图")
        print(f"  02-page-meta.json      - 页面元信息（标题、框架、字体、颜色变量）")
        print(f"  03-full-page.html      - 完整 HTML（含内联样式）")
        print(f"  04-all-styles.css      - 所有 CSS（合并、去重）")
        print(f"  05-component-styles.json - 各组件的计算样式")
        print(f"  06-layout.json         - 布局信息（位置、尺寸）")
        print(f"  07-icons.json          - 图标、Logo 资源")
        print(f"  08-api-calls.json      - API 请求日志")

        self.close()

    # ==================== 具体提取方法 ====================

    def _extract_page_assets(self):
        """提取完整 HTML + 所有 CSS"""
        # 获取渲染后的 HTML
        html = self.page.content()

        # 获取所有 CSS（包括 <style> 和 <link> 引用的）
        css_data = self.page.evaluate("""() => {
            let allCss = '';
            // 内联 <style> 标签
            document.querySelectorAll('style').forEach(s => {
                allCss += '/* === inline style === */\\n' + s.textContent + '\\n';
            });
            // CSS 变量（:root）
            const rootStyles = getComputedStyle(document.documentElement);
            const cssVars = {};
            for (const sheet of document.styleSheets) {
                try {
                    for (const rule of sheet.cssRules) {
                        if (rule.selectorText === ':root' || rule.selectorText === 'html') {
                            allCss += '/* === CSS variables === */\\n' + rule.cssText + '\\n';
                        }
                    }
                } catch(e) {} // 跨域样式表会报错
            }
            // Meta 信息
            const meta = {
                title: document.title,
                charset: document.characterSet,
                lang: document.documentElement.lang,
                viewport: document.querySelector('meta[name=viewport]')?.content,
                favicon: document.querySelector('link[rel*=icon]')?.href,
                framework: 'unknown',
                ui_library: 'unknown',
            };
            // 框架检测
            if (document.querySelector('[data-v-]') || document.querySelector('[data-server-rendered]')) meta.framework = 'Vue';
            else if (document.querySelector('[data-reactroot]') || document.querySelector('[data-reactid]')) meta.framework = 'React';
            // UI 库检测
            const html = document.documentElement.outerHTML;
            if (html.includes('ant-design') || html.includes('anticon') || html.includes('ant-')) meta.ui_library = 'Ant Design';
            else if (html.includes('el-') || html.includes('element-ui')) meta.ui_library = 'Element UI';
            else if (html.includes('van-')) meta.ui_library = 'Vant';
            else if (html.includes('a-') && html.includes('ant-')) meta.ui_library = 'Ant Design Vue';
            // 全局字体
            meta.font_family = rootStyles.fontFamily;
            meta.font_size = rootStyles.fontSize;
            meta.bg_color = rootStyles.backgroundColor;
            meta.text_color = rootStyles.color;
            // 获取 CSS 变量
            const vars = {};
            for (const sheet of document.styleSheets) {
                try {
                    for (const rule of sheet.cssRules) {
                        if (rule.selectorText === ':root') {
                            const matches = rule.cssText.matchAll(/--([\\w-]+)\\s*:\\s*([^;]+)/g);
                            for (const m of matches) {
                                vars[m[1]] = m[2].trim();
                            }
                        }
                    }
                } catch(e) {}
            }
            meta.css_variables = vars;
            // 获取所有外部 CSS 链接
            const cssLinks = [];
            document.querySelectorAll('link[rel=stylesheet]').forEach(l => {
                cssLinks.push(l.href);
            });
            meta.external_css_links = cssLinks;
            // 获取所有 JS 链接
            const jsLinks = [];
            document.querySelectorAll('script[src]').forEach(s => {
                jsLinks.push(s.src);
            });
            meta.external_js_links = jsLinks;
            return { allCss, meta };
        }""")

        # 下载外部 CSS 内容
        external_css = ""
        for link in css_data['meta'].get('external_css_links', []):
            try:
                resp = self.page.request.get(link)
                if resp.ok:
                    external_css += f"/* === {link} === */\n{resp.text()}\n\n"
            except:
                pass

        return {
            'html': html,
            'css': css_data['allCss'] + "\n\n" + external_css,
            'meta': css_data['meta'],
        }

    def _extract_component_styles(self):
        """提取各组件的计算样式"""
        return self.page.evaluate("""() => {
            const result = {};

            // 通用：提取元素关键样式
            function getStyles(el, label) {
                if (!el) return null;
                const cs = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return {
                    tag: label || el.tagName.toLowerCase(),
                    text: el.textContent?.trim().substring(0, 100),
                    classes: el.className?.toString().split(' ').filter(Boolean),
                    styles: {
                        display: cs.display,
                        position: cs.position,
                        width: cs.width,
                        height: cs.height,
                        padding: cs.padding,
                        margin: cs.margin,
                        'font-family': cs.fontFamily,
                        'font-size': cs.fontSize,
                        'font-weight': cs.fontWeight,
                        'line-height': cs.lineHeight,
                        'color': cs.color,
                        'background-color': cs.backgroundColor,
                        'border': cs.border,
                        'border-radius': cs.borderRadius,
                        'box-shadow': cs.boxShadow,
                        'text-align': cs.textAlign,
                        'flex-direction': cs.flexDirection,
                        'justify-content': cs.justifyContent,
                        'align-items': cs.alignItems,
                        'gap': cs.gap,
                        overflow: cs.overflow,
                    },
                    box: {
                        x: rect.x, y: rect.y,
                        width: rect.width, height: rect.height,
                    },
                    attributes: Object.fromEntries(
                        [...el.attributes].map(a => [a.name, a.value]).filter(([k,v]) => !k.startsWith('data-v'))
                    ),
                };
            }

            // 1. 整体页面容器
            const app = document.querySelector('#app') || document.querySelector('[id]');
            if (app) result.page_container = getStyles(app, 'page-root');

            // 2. 顶部导航/标题栏
            const header = document.querySelector('header, .header, .navbar, .nav-bar, [class*="header"], [class*="navbar"]');
            if (header) result.header = getStyles(header, 'header');
            // 标题
            const h1 = document.querySelector('h1, .title, [class*="title"]');
            if (h1) result.page_title = getStyles(h1, 'title');

            // 3. 筛选栏/工具栏
            const filterBar = document.querySelector(
                '.filter-bar, .filter-section, .toolbar, [class*="filter"], [class*="toolbar"], [class*="query"]'
            );
            if (filterBar) {
                result.filter_bar = getStyles(filterBar, 'filter-bar');
                // 筛选栏内每个控件
                result.filter_items = [];
                const items = filterBar.querySelectorAll('button, input, select, .select, .dropdown');
                items.forEach((item, i) => {
                    result.filter_items.push(getStyles(item, `filter-item-${i}`));
                });
            }

            // 4. 指标卡片区域
            const cards = document.querySelectorAll(
                '.card, .metric-card, .stat-card, .summary-card, [class*="card"], [class*="stat"], [class*="summary"]'
            );
            if (cards.length > 0) {
                result.metric_cards = [];
                cards.forEach((card, i) => {
                    result.metric_cards.push(getStyles(card, `card-${i}`));
                });
                // 卡片容器
                const cardContainer = cards[0].parentElement;
                if (cardContainer) {
                    result.card_container = getStyles(cardContainer, 'card-container');
                }
            }

            // 5. 表格
            const table = document.querySelector('table, .table, [class*="table"], .el-table, .ant-table');
            if (table) {
                result.table = getStyles(table, 'table');
                // 表头
                const thead = table.querySelector('thead, .thead, [class*="header"]');
                if (thead) result.table_header = getStyles(thead, 'table-header');
                // 表头单元格
                const ths = table.querySelectorAll('th');
                if (ths.length) {
                    result.table_header_cells = [];
                    ths.forEach((th, i) => {
                        result.table_header_cells.push(getStyles(th, `th-${i}`));
                    });
                }
                // 表体
                const tbody = table.querySelector('tbody, .tbody');
                if (tbody) result.table_body = getStyles(tbody, 'table-body');
                // 第一行数据
                const firstRow = table.querySelector('tbody tr, .tbody .tr');
                if (firstRow) {
                    result.table_first_row = getStyles(firstRow, 'first-row');
                    const tds = firstRow.querySelectorAll('td');
                    result.table_first_row_cells = [];
                    tds.forEach((td, i) => {
                        result.table_first_row_cells.push(getStyles(td, `td-${i}`));
                    });
                }
            }

            // 6. 分页
            const pagination = document.querySelector(
                '.pagination, .ant-pagination, .el-pagination, [class*="pagination"], [class*="pager"]'
            );
            if (pagination) result.pagination = getStyles(pagination, 'pagination');

            // 7. 面包屑
            const breadcrumb = document.querySelector(
                '.breadcrumb, [class*="breadcrumb"]'
            );
            if (breadcrumb) result.breadcrumb = getStyles(breadcrumb, 'breadcrumb');

            // 8. Tab 导航
            const tabs = document.querySelector(
                '.tabs, .ant-tabs, .el-tabs, [class*="tab"]'
            );
            if (tabs) {
                result.tabs = getStyles(tabs, 'tabs');
                const tabItems = tabs.querySelectorAll('.tab, .tab-item, [class*="tab-item"], [role="tab"]');
                result.tab_items = [];
                tabItems.forEach((t, i) => {
                    result.tab_items.push(getStyles(t, `tab-${i}`));
                });
            }

            // 9. 侧边栏/菜单
            const sidebar = document.querySelector(
                '.sidebar, .side-bar, .menu, [class*="sidebar"], [class*="side-menu"]'
            );
            if (sidebar) result.sidebar = getStyles(sidebar, 'sidebar');

            return result;
        }""")

    def _extract_layout(self):
        """提取页面布局结构（带位置信息）"""
        layout = self.page.evaluate("""() => {
            const result = { viewport: { width: window.innerWidth, height: window.innerHeight }, elements: [] };

            function scan(el, depth = 0) {
                if (depth > 8 || !el) return;
                const cs = getComputedStyle(el);
                const rect = el.getBoundingClientRect();

                // 只记录有意义的元素（可见且有面积）
                if (rect.width < 1 || rect.height < 1 || cs.display === 'none' || cs.visibility === 'hidden') return;

                const info = {
                    tag: el.tagName?.toLowerCase(),
                    id: el.id || undefined,
                    classes: (el.className?.toString() || '').split(' ').filter(c => c && !c.startsWith('data-v')).slice(0, 5),
                    text: (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3) ? el.textContent.trim().substring(0, 50) : undefined,
                    box: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
                    display: cs.display,
                    position: cs.position,
                    bg: cs.backgroundColor !== 'rgba(0, 0, 0, 0)' ? cs.backgroundColor : undefined,
                    children_count: el.children.length,
                };

                result.elements.push(info);
                for (const child of el.children) {
                    scan(child, depth + 1);
                }
            }

            const root = document.querySelector('#app') || document.body;
            scan(root, 0);
            return result;
        }""")
        return layout

    def _extract_icons(self):
        """提取图标、Logo 等图片资源"""
        return self.page.evaluate("""() => {
            const result = { favicons: [], images: [], svgs: [], icon_fonts: [], logos: [] };

            // 1. Favicon
            document.querySelectorAll('link[rel*=icon]').forEach(l => {
                result.favicons.push(l.href);
            });

            // 2. <img> 标签
            document.querySelectorAll('img').forEach(img => {
                result.images.push({
                    src: img.src,
                    alt: img.alt,
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                    classes: img.className,
                });
            });

            // 3. SVG 内联图标
            document.querySelectorAll('svg').forEach(svg => {
                result.svgs.push({
                    html: svg.outerHTML.substring(0, 2000),
                    viewBox: svg.getAttribute('viewBox'),
                    width: svg.getAttribute('width'),
                    height: svg.getAttribute('height'),
                    classes: svg.className?.baseVal || svg.className,
                });
            });

            // 4. 图标字体（如 element-ui icon、anticon 等）
            document.querySelectorAll('[class*="icon"], i').forEach(el => {
                const cs = getComputedStyle(el);
                const before = cs.getPropertyValue('content');
                if (before && before !== 'normal' && before !== 'none') {
                    result.icon_fonts.push({
                        classes: el.className?.toString(),
                        pseudo_content: before,
                        font_family: cs.fontFamily,
                        font_size: cs.fontSize,
                        color: cs.color,
                    });
                }
            });

            // 5. Logo（通常在 header 左上角）
            const header = document.querySelector('header, .header, .navbar, [class*="header"]');
            if (header) {
                const logoImg = header.querySelector('img, svg');
                if (logoImg) {
                    result.logos.push({
                        tag: logoImg.tagName.toLowerCase(),
                        src: logoImg.src || undefined,
                        html: logoImg.outerHTML.substring(0, 2000),
                    });
                }
                // Logo 文字
                const logoText = header.querySelector('.logo, [class*="logo"]');
                if (logoText) {
                    result.logos.push({
                        tag: 'text-logo',
                        text: logoText.textContent.trim(),
                        classes: logoText.className,
                    });
                }
            }

            return result;
        }""")

    def _test_drill_down(self, team_name):
        """测试下钻：点击团队行 -> 截图 -> 再点击子行 -> 截图"""
        # 先截图当前状态
        self._screenshot("09-drill-level1")

        # 查找并点击团队行
        clicked = self.page.evaluate(f"""(teamName) => {{
            const rows = document.querySelectorAll('tbody tr');
            for (const row of rows) {{
                const text = row.textContent;
                if (text.includes(teamName) || text.includes(teamName.substring(0, 4))) {{
                    row.click();
                    return {{ success: true, text: text.substring(0, 100) }};
                }}
            }}
            // 列出可用行
            const available = [];
            rows.forEach((r, i) => {{
                const cells = r.querySelectorAll('td');
                if (cells.length > 1) available.push(cells[1]?.textContent?.trim() || cells[0]?.textContent?.trim());
            }});
            return {{ success: false, available: available.slice(0, 10) }};
        }}""", team_name)

        print(f"  点击结果: {json.dumps(clicked, ensure_ascii=False)}")

        if clicked.get('success'):
            time.sleep(3)
            self._screenshot("10-drill-level2")

            # 尝试继续下钻到个人级
            try:
                first_row = self.page.query_selector('tbody tr')
                if first_row:
                    first_row.click()
                    time.sleep(3)
                    self._screenshot("11-drill-level3")
            except:
                print("  无法继续下钻到个人级")
        else:
            avail = clicked.get('available', [])
            if avail:
                print(f"  可用团队: {avail}")


def main():
    parser = argparse.ArgumentParser(description='Playwright 页面样式提取工具')
    parser.add_argument('url', help='目标 URL')
    parser.add_argument('-o', '--output', default='style-output', help='输出目录')
    parser.add_argument('--drill-down', metavar='TEAM', help='测试下钻交互，指定团队名称')
    args = parser.parse_args()

    extractor = StyleExtractor(output_dir=args.output)
    try:
        extractor.extract_all(args.url, drill_down_team=args.drill_down)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        extractor.close()
        sys.exit(1)


if __name__ == '__main__':
    main()
