#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量提取多个页面的结构信息
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from extract_structure_selenium import FrontendStructureExtractor
import json
from datetime import datetime

def batch_extract(urls, output_dir):
    """
    批量提取多个页面

    Args:
        urls: URL 列表
        output_dir: 输出目录
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    extractor = FrontendStructureExtractor(headless=True)

    results = []

    for i, url in enumerate(urls, 1):
        print(f"\n{'='*60}")
        print(f"进度: {i}/{len(urls)}")
        print(f"{'='*60}")

        # 生成输出文件名
        if url.startswith('http'):
            filename = url.split('/')[-1] or 'index'
        else:
            filename = f"page_{i}"

        output_file = os.path.join(output_dir, f"{filename}.json")

        # 提取页面
        result = extractor.extract_page(url, output_file)
        if result:
            results.append(result)

    # 生成汇总报告
    summary_file = os.path.join(output_dir, "summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_pages': len(results),
            'pages': [
                {
                    'url': r['url'],
                    'title': r['title'],
                    'nav_tabs': len(r['navigation']['tabs']),
                    'filters': len(r['filters']['fields']),
                    'metric_cards': len(r['metric_cards']),
                    'table_rows': r['table']['row_count']
                }
                for r in results
            ]
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ 批量提取完成！")
    print(f"📁 输出目录: {output_dir}")
    print(f"📊 提取页面数: {len(results)}")
    print(f"📋 汇总报告: {summary_file}")
    print(f"{'='*60}")

    return results

def main():
    # 定义要提取的页面列表
    # 注意：这些 URL 需要在实际网络环境中可访问
    urls = [
        'http://10.65.134.124:8080/metrics',
        'http://10.65.134.124:8080/metrics/token-usage',
        'http://10.65.134.124:8080/metrics/silicon'
    ]

    # 本地测试模式（使用 mock 文件）
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        base_path = '/root/.openclaw/workspace/knowledge/tech/AI-Native/prototype-mock.html'
        urls = [
            f'file://{base_path}?page=overview',
            f'file://{base_path}?page=token-usage',
            f'file://{base_path}?page=silicon'
        ]
        output_dir = '/tmp/prototype-extract-test'
    else:
        output_dir = '/root/.openclaw/workspace/knowledge/tech/AI-Native/prototype-structure'

    # 执行批量提取
    batch_extract(urls, output_dir)

if __name__ == '__main__':
    main()
