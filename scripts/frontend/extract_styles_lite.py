#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright 样式提取工具（精简版）
输出精简的文本摘要，适配 minimax 2.7 的 196K token 上下文限制

用法:
  pip install playwright && python -m playwright install chromium
  python extract_styles_lite.py <URL> [-o 输出文件]
"""

import sys, os, json, time, argparse
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("请先安装: pip install playwright && python -m playwright install chromium")
    sys.exit(1)


def extract(url, output_file):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_context(viewport={'width': 1920, 'height': 1080}).new_page()

    # 拦截 API
    api_logs = []
    def on_resp(resp):
        if '/api/' in resp.url:
            try:
                body = resp.text()
            except:
                body = None
            api_logs.append({
                'url': resp.url,
                'method': resp.request.method,
                'status': resp.status,
                'request_body': resp.request.post_data,
                'response_preview': body[:3000] if body else None,
            })
    page.on('response', on_resp)

    print(f"访问: {url}")
    page.goto(url, wait_until='networkidle', timeout=30000)
    time.sleep(3)

    # 截图保存（供人眼对比，不喂给模型）
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    page.screenshot(path=output_file.replace('.json', '.png'), full_page=True)
    print(f"截图: {output_file.replace('.json', '.png')}")

    # 提取精简样式摘要
    summary = page.evaluate(r"""() => {
        const S = {};
        function gs(el) {
            const c = getComputedStyle(el);
            return {
                display: c.display, flexDir: c.flexDirection, justifyContent: c.justifyContent, alignItems: c.alignItems, gap: c.gap,
                w: c.width, h: c.height, pad: c.padding, mar: c.margin,
                ff: c.fontFamily, fs: c.fontSize, fw: c.fontWeight, lh: c.lineHeight,
                color: c.color, bg: c.backgroundColor, border: c.border, radius: c.borderRadius,
                shadow: c.boxShadow, textAlign: c.textAlign,
            };
        }
        function clean(sel, label) {
            const el = document.querySelector(sel);
            return el ? { label, cls: el.className?.toString().split(' ').filter(c => c && !c.startsWith('data-v')).slice(0,3), s: gs(el) } : null;
        }

        // 1. 页面根信息
        const root = document.documentElement;
        const rc = getComputedStyle(root);
        S.page = {
            title: document.title,
            framework: document.querySelector('[data-v-]') ? 'Vue' : (document.querySelector('[data-reactroot]') ? 'React' : 'unknown'),
            body_bg: rc.backgroundColor,
            body_ff: rc.fontFamily,
            body_fs: rc.fontSize,
            body_color: rc.color,
        };

        // CSS 变量
        const vars = {};
        try {
            for (const sheet of document.styleSheets) {
                for (const rule of sheet.cssRules) {
                    if (rule.selectorText === ':root') {
                        for (const m of rule.cssText.matchAll(/--([\w-]+)\s*:\s*([^;]+)/g)) {
                            vars[m[1]] = m[2].trim();
                        }
                    }
                }
            }
        } catch(e) {}
        if (Object.keys(vars).length) S.css_vars = vars;

        // 2. 主要区域
        S.areas = {};
        const app = document.querySelector('#app') || document.body;
        if (app) S.areas.app = gs(app);

        // Header/标题栏
        const hdr = document.querySelector('header,.header,.navbar,[class*="header"],[class*="navbar"]');
        if (hdr) {
            S.areas.header = gs(hdr);
            const title = hdr.querySelector('h1,h2,.title,[class*="title"]');
            if (title) S.areas.header_title = { text: title.textContent.trim(), s: gs(title) };
        }

        // 3. 筛选栏
        const filter = document.querySelector('[class*="filter"],[class*="toolbar"],[class*="query"],.filter-bar');
        if (filter) {
            S.areas.filter_bar = gs(filter);
            S.filter_items = [];
            filter.querySelectorAll('button,input,select').forEach((el, i) => {
                S.filter_items.push({
                    idx: i, tag: el.tagName.toLowerCase(), type: el.type,
                    text: el.textContent?.trim().substring(0, 30),
                    value: el.value, placeholder: el.placeholder,
                    cls: el.className?.toString().split(' ').filter(c => c && !c.startsWith('data-v')).slice(0,2),
                    s: gs(el),
                });
            });
        }

        // 4. 表格
        const tbl = document.querySelector('table,[class*="table"]');
        if (tbl) {
            S.areas.table = gs(tbl);
            const thead = tbl.querySelector('thead');
            if (thead) {
                S.areas.thead = gs(thead);
                S.table_headers = [];
                thead.querySelectorAll('th').forEach((th, i) => {
                    S.table_headers.push({ idx: i, text: th.textContent.trim().replace(/\n/g,' '), s: gs(th) });
                });
            }
            const tbody = tbl.querySelector('tbody');
            if (tbody) S.areas.tbody = gs(tbody);
            // 第一行
            const row1 = tbl.querySelector('tbody tr');
            if (row1) {
                S.areas.row1 = gs(row1);
                S.row1_cells = [];
                row1.querySelectorAll('td').forEach((td, i) => {
                    S.row1_cells.push({ idx: i, text: td.textContent.trim().replace(/\n/g,' ').substring(0, 50), s: gs(td) });
                });
            }
            // 操作列按钮
            const actionBtn = tbl.querySelector('tbody td button,tbody td a');
            if (actionBtn) {
                S.areas.action_btn = { text: actionBtn.textContent.trim(), s: gs(actionBtn) };
            }
        }

        // 5. 图标/SVG
        S.icons = [];
        document.querySelectorAll('svg,img[class*="icon"],i[class*="icon"],[class*="logo"]').forEach((el, i) => {
            if (i >= 10) return;
            S.icons.push({
                tag: el.tagName.toLowerCase(),
                cls: el.className?.toString().split(' ').filter(c => c && !c.startsWith('data-v')).slice(0,2),
                html: el.outerHTML.substring(0, 500),
            });
        });

        // 6. 分页
        const pager = document.querySelector('[class*="pagination"],[class*="pager"]');
        if (pager) S.areas.pagination = gs(pager);

        // 7. 面包屑
        const bc = document.querySelector('[class*="breadcrumb"]');
        if (bc) S.areas.breadcrumb = gs(bc);

        return S;
    }""")

    # 保存精简 JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"样式摘要: {output_file} ({os.path.getsize(output_file)} bytes)")

    # API 日志（精简）
    api_file = output_file.replace('.json', '-api.json')
    with open(api_file, 'w', encoding='utf-8') as f:
        json.dump(api_logs, f, ensure_ascii=False, indent=2)
    print(f"API日志: {api_file}")

    browser.close()
    pw.stop()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('url')
    p.add_argument('-o', default='style-summary.json')
    args = p.parse_args()
    extract(args.url, args.output if hasattr(args, 'output') else args.o)

if __name__ == '__main__':
    main()
