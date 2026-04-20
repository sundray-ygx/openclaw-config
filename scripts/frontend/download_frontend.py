#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案 B：下载原平台完整前端资源
下载所有 HTML/CSS/JS/图片/字体，然后替换 API 地址指向自己的后端

用法:
  pip install playwright && python -m playwright install chromium
  python download_frontend.py <URL> [-o 输出目录]

示例:
  python download_frontend.py http://10.65.134.124:8080/metrics -o original-frontend
"""

import sys, os, json, time, re, hashlib, argparse
from urllib.parse import urljoin, urlparse
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("请先安装: pip install playwright && python -m playwright install chromium")
    sys.exit(1)


class FrontendDownloader:
    def __init__(self, base_url, output_dir):
        self.base_url = base_url.rstrip('/')
        # 解析出 origin（如 http://10.65.134.124:8080）
        parsed = urlparse(base_url)
        self.origin = f"{parsed.scheme}://{parsed.netloc}"
        self.output_dir = output_dir
        self.downloaded = {}  # url -> local_path
        self.api_patterns = []  # 发现的 API 路径
        self.report = {
            'base_url': base_url,
            'timestamp': datetime.now().isoformat(),
            'resources': {},
            'api_endpoints': [],
            'api_base_config': [],
            'steps': [],
        }

    def _url_to_path(self, url):
        """将 URL 转为本地文件路径"""
        parsed = urlparse(url)
        path = parsed.path
        if path.startswith('/'):
            path = path[1:]
        if not path or path.endswith('/'):
            path += 'index.html'
        # 处理 query string
        if parsed.query:
            base, ext = os.path.splitext(path)
            path = f"{base}_{hashlib.md5(parsed.query.encode()).hexdigest()[:8]}{ext}"
        return os.path.join(self.output_dir, 'static', path)

    def _download_binary(self, url, local_path):
        """下载二进制文件"""
        if url in self.downloaded:
            return self.downloaded[url]
        try:
            resp = self.page.request.get(url)
            if resp.ok:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(resp.body())
                self.downloaded[url] = local_path
                rel = os.path.relpath(local_path, self.output_dir)
                print(f"  [OK] {rel} ({len(resp.body())} bytes)")
                return local_path
            else:
                print(f"  [SKIP] {url} (HTTP {resp.status})")
        except Exception as e:
            print(f"  [ERR] {url}: {e}")
        return None

    def _download_text(self, url, local_path):
        """下载文本文件"""
        if url in self.downloaded:
            return self.downloaded[url]
        try:
            resp = self.page.request.get(url)
            if resp.ok:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                text = resp.text()
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.downloaded[url] = local_path
                rel = os.path.relpath(local_path, self.output_dir)
                print(f"  [OK] {rel} ({len(text)} chars)")
                return text
        except Exception as e:
            print(f"  [ERR] {url}: {e}")
        return None

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)

        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=True, args=['--no-sandbox'])
        self.context = self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = self.context.new_page()

        # 拦截所有请求，记录资源 URL
        all_resources = {
            'document': [], 'stylesheet': [], 'script': [],
            'image': [], 'font': [], 'other': []
        }

        def on_request(req):
            rtype = req.resource_type
            if rtype in all_resources:
                all_resources[rtype].append(req.url)
            else:
                all_resources['other'].append(req.url)
            # 检测 API 调用
            if '/api/' in req.url:
                self.api_patterns.append({
                    'url': req.url,
                    'method': req.method,
                    'type': rtype,
                })

        self.page.on('request', on_request)

        # Step 1: 访问页面
        print(f"\n{'='*60}")
        print(f"Step 1: 访问页面 {self.base_url}")
        print(f"{'='*60}")
        self.page.goto(self.base_url, wait_until='networkidle', timeout=30000)
        time.sleep(5)  # 等待所有资源加载

        # 截图
        ss_path = os.path.join(self.output_dir, 'screenshot-original.png')
        self.page.screenshot(path=ss_path, full_page=True)
        print(f"  [OK] screenshot-original.png")

        self.report['steps'].append('1. 访问页面并等待加载完成')

        # Step 2: 获取渲染后 HTML
        print(f"\n{'='*60}")
        print(f"Step 2: 保存渲染后 HTML")
        print(f"{'='*60}")

        html = self.page.content()
        html_path = os.path.join(self.output_dir, 'index.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  [OK] index.html ({len(html)} chars)")
        self.report['steps'].append('2. 保存渲染后 HTML')

        # Step 3: 下载所有 CSS
        print(f"\n{'='*60}")
        print(f"Step 3: 下载 CSS 文件")
        print(f"{'='*60}")
        css_urls = list(dict.fromkeys(all_resources['stylesheet']))  # 去重保序
        for url in css_urls:
            if url.startswith('data:') or url.startswith('blob:'):
                continue
            local = self._url_to_path(url)
            self._download_text(url, local)
        self.report['resources']['css_count'] = len(css_urls)
        self.report['steps'].append(f'3. 下载 {len(css_urls)} 个 CSS 文件')

        # Step 4: 下载所有 JS
        print(f"\n{'='*60}")
        print(f"Step 4: 下载 JS 文件")
        print(f"{'='*60}")
        js_urls = list(dict.fromkeys(all_resources['script']))
        js_contents = {}
        for url in js_urls:
            if url.startswith('data:') or url.startswith('blob:'):
                continue
            local = self._url_to_path(url)
            content = self._download_text(url, local)
            if content:
                js_contents[url] = (local, content)
        self.report['resources']['js_count'] = len(js_urls)
        self.report['steps'].append(f'4. 下载 {len(js_urls)} 个 JS 文件')

        # Step 5: 分析 JS 中的 API 配置
        print(f"\n{'='*60}")
        print(f"Step 5: 分析 JS 中的 API 路径")
        print(f"{'='*60}")

        api_paths_found = set()
        api_base_found = set()

        for url, (local, content) in js_contents.items():
            # 查找 API 路径字符串
            # 匹配 /api/xxx 格式
            api_matches = re.findall(r'["\'](/api/[a-zA-Z0-9_\-/]+)["\']', content)
            for m in api_matches:
                api_paths_found.add(m)

            # 查找 API base URL 配置
            # 常见模式: baseURL, apiBase, API_URL, VUE_APP_API 等
            base_patterns = [
                r'baseURL\s*[:=]\s*["\']([^"\']+)["\']',
                r'apiBase\s*[:=]\s*["\']([^"\']+)["\']',
                r'API_URL\s*[:=]\s*["\']([^"\']+)["\']',
                r'VUE_APP_API\s*[:=]\s*["\']([^"\']+)["\']',
                r'VITE_API\s*[:=]\s*["\']([^"\']+)["\']',
                r'apiPrefix\s*[:=]\s*["\']([^"\']+)["\']',
                r'["\']((?:http)?://[^"\']*api[^"\']*)["\']',
            ]
            for pat in base_patterns:
                matches = re.findall(pat, content)
                for m in matches:
                    if len(m) < 200 and m not in ('http://localhost', 'http://127.0.0.1'):
                        api_base_found.add(m)

            # 查找 axios/fetch 配置
            if 'axios' in content or 'fetch(' in content:
                rel = os.path.relpath(local, self.output_dir)
                # 找到包含 axios/fetch 配置的行
                for i, line in enumerate(content.split('\n')):
                    if any(k in line for k in ['baseURL', 'axios.create', '/api/', 'apiBase']):
                        api_base_found.add(f"{rel}:{i+1}: {line.strip()[:200]}")

        api_paths_found = sorted(api_paths_found)
        self.report['api_endpoints'] = api_paths_found
        self.report['api_base_config'] = sorted(api_base_found)
        print(f"  发现 {len(api_paths_found)} 个 API 路径:")
        for p in api_paths_found:
            print(f"    {p}")
        print(f"  发现 {len(api_base_found)} 个 API 配置:")
        for c in sorted(api_base_found):
            print(f"    {c[:150]}")
        self.report['steps'].append(f'5. 分析 JS 文件，发现 {len(api_paths_found)} 个 API 路径')

        # Step 6: 下载图片
        print(f"\n{'='*60}")
        print(f"Step 6: 下载图片和字体")
        print(f"{'='*60}")
        img_urls = list(dict.fromkeys(all_resources['image']))
        for url in img_urls:
            if url.startswith('data:') or url.startswith('blob:'):
                continue
            local = self._url_to_path(url)
            self._download_binary(url, local)
        self.report['resources']['image_count'] = len(img_urls)

        # Step 7: 下载字体
        font_urls = list(dict.fromkeys(all_resources['font']))
        for url in font_urls:
            if url.startswith('data:') or url.startswith('blob:'):
                continue
            local = self._url_to_path(url)
            self._download_binary(url, local)
        self.report['resources']['font_count'] = len(font_urls)
        self.report['steps'].append(f'6. 下载 {len(img_urls)} 个图片, {len(font_urls)} 个字体')

        # Step 8: 生成 API 替换脚本
        print(f"\n{'='*60}")
        print(f"Step 7: 生成 API 替换脚本")
        print(f"{'='*60}")

        self._generate_replace_script(api_paths_found, api_base_found)
        self.report['steps'].append('7. 生成 API 替换脚本')

        # 保存报告
        report_path = os.path.join(self.output_dir, 'download-report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)
        print(f"\n  [OK] download-report.json")

        self.browser.close()
        self.pw.stop()

        # 输出最终摘要
        print(f"\n{'='*60}")
        print(f"下载完成！")
        print(f"{'='*60}")
        print(f"输出目录: {self.output_dir}")
        print(f"  index.html              - 渲染后 HTML")
        print(f"  screenshot-original.png - 原平台截图")
        print(f"  static/                 - 所有静态资源")
        print(f"  replace-api.sh          - API 替换脚本（将原平台 API 改为自己的）")
        print(f"  download-report.json    - 下载报告")
        print(f"\n下一步:")
        print(f"  1. 查看 download-report.json 中的 api_base_config")
        print(f"  2. 确认 API 地址替换方式")
        print(f"  3. 执行 replace-api.sh 或手动替换")
        print(f"  4. 用 nginx 托管 static/ 目录，测试页面是否正常")

    def _generate_replace_script(self, api_paths, api_base):
        """生成 API 地址替换脚本"""
        script_path = os.path.join(self.output_dir, 'replace-api.sh')

        # 获取原平台的 host:port
        parsed = urlparse(self.base_url)
        old_origin = self.origin  # e.g. http://10.65.134.124:8080
        new_origin = 'http://localhost:8080'  # 默认替换目标

        script = f"""#!/bin/bash
# API 地址替换脚本
# 将原平台 API 地址替换为本地后端地址
#
# 用法:
#   bash replace-api.sh [新的 API 地址]
#   bash replace-api.sh http://localhost:8080
#   bash replace-api.sh http://10.65.134.124:8080

NEW_ORIGIN="${{1:-{new_origin}}}"
OLD_ORIGIN="{old_origin}"

echo "替换 API 地址: $OLD_ORIGIN -> $NEW_ORIGIN"
echo ""

# 替换所有 JS 文件中的 API 地址
find static/ -name '*.js' | while read f; do
    if grep -q "$OLD_ORIGIN" "$f" 2>/dev/null; then
        echo "替换: $f"
        sed -i "s|$OLD_ORIGIN|$NEW_ORIGIN|g" "$f"
    fi
done

# 也替换 HTML 中的引用（如果有内联的 API 地址）
if grep -q "$OLD_ORIGIN" index.html 2>/dev/null; then
    echo "替换: index.html"
    sed -i "s|$OLD_ORIGIN|$NEW_ORIGIN|g" index.html
fi

echo ""
echo "替换完成！"
echo ""
echo "测试方法:"
echo "  cd {self.output_dir}"
echo "  python -m http.server 3000"
echo "  浏览器访问 http://localhost:3000"
echo "  检查页面是否正常加载数据"
"""
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)
        print(f"  [OK] replace-api.sh")
        print(f"  用法: bash replace-api.sh http://你的后端地址:端口")


def main():
    p = argparse.ArgumentParser(description='下载原平台完整前端资源')
    p.add_argument('url', help='目标 URL (如 http://10.65.134.124:8080/metrics)')
    p.add_argument('-o', '--output', default='original-frontend', help='输出目录')
    args = p.parse_args()

    downloader = FrontendDownloader(args.url, args.output)
    downloader.run()


if __name__ == '__main__':
    main()
