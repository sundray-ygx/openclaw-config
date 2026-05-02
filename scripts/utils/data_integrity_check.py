#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据完整性检查工具
检查关键文件是否存在且非空，测试 API 连通性
"""

import os
import sys
import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# 关键文件列表
CRITICAL_FILES = [
    '/root/.openclaw/openclaw.json',
    '/root/.openclaw/workspace/MEMORY.md',
    '/root/.openclaw/workspace/AGENTS.md',
    '/root/.openclaw/workspace/SOUL.md',
]


def check_file_exists(filepath):
    """检查文件是否存在且非空"""
    if not os.path.exists(filepath):
        return {'exists': False, 'empty': None, 'error': '文件不存在'}
    if not os.path.isfile(filepath):
        return {'exists': False, 'empty': None, 'error': '不是常规文件'}
    if os.path.getsize(filepath) == 0:
        return {'exists': True, 'empty': True, 'error': '文件为空'}
    return {'exists': True, 'empty': False, 'error': None}


def test_notion_api():
    """测试 Notion API 连通性"""
    api_key = os.environ.get('NOTION_API_KEY')
    if not api_key:
        return {'connected': False, 'error': '未设置 NOTION_API_KEY 环境变量'}

    try:
        req = Request(
            'https://api.notion.com/v1/users/me',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Notion-Version': '2022-06-28',
            }
        )
        with urlopen(req, timeout=10) as response:
            if response.status == 200:
                return {'connected': True, 'error': None}
            else:
                return {'connected': False, 'error': f'HTTP {response.status}'}
    except HTTPError as e:
        return {'connected': False, 'error': f'HTTP 错误: {e.code}'}
    except URLError as e:
        return {'connected': False, 'error': f'连接错误: {str(e)}'}
    except Exception as e:
        return {'connected': False, 'error': f'未知错误: {str(e)}'}


def test_feishu_api():
    """测试飞书 API 连通性"""
    app_id = os.environ.get('FEISHU_APP_ID')
    app_secret = os.environ.get('FEISHU_APP_SECRET')

    if not app_id or not app_secret:
        return {'connected': False, 'error': '未设置 FEISHU_APP_ID 或 FEISHU_APP_SECRET 环境变量'}

    try:
        # 获取 tenant_access_token
        req = Request(
            'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
            data=json.dumps({
                'app_id': app_id,
                'app_secret': app_secret
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('code') == 0:
                return {'connected': True, 'error': None}
            else:
                return {'connected': False, 'error': data.get('msg', '未知错误')}
    except HTTPError as e:
        return {'connected': False, 'error': f'HTTP 错误: {e.code}'}
    except URLError as e:
        return {'connected': False, 'error': f'连接错误: {str(e)}'}
    except Exception as e:
        return {'connected': False, 'error': f'未知错误: {str(e)}'}


def main():
    """主函数"""
    report = {
        'timestamp': int(time.time()),
        'files': {},
        'apis': {},
        'summary': {
            'total_files': len(CRITICAL_FILES),
            'healthy_files': 0,
            'issues': []
        }
    }

    # 检查文件
    for filepath in CRITICAL_FILES:
        result = check_file_exists(filepath)
        report['files'][filepath] = result

        if result['exists'] and not result['empty']:
            report['summary']['healthy_files'] += 1
        else:
            report['summary']['issues'].append({
                'type': 'file',
                'path': filepath,
                'error': result['error']
            })

    # 测试 API
    notion_result = test_notion_api()
    report['apis']['notion'] = notion_result
    if not notion_result['connected']:
        report['summary']['issues'].append({
            'type': 'api',
            'service': 'notion',
            'error': notion_result['error']
        })

    feishu_result = test_feishu_api()
    report['apis']['feishu'] = feishu_result
    if not feishu_result['connected']:
        report['summary']['issues'].append({
            'type': 'api',
            'service': 'feishu',
            'error': feishu_result['error']
        })

    # 输出 JSON 报告
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # 返回退出码
    if report['summary']['issues']:
        sys.exit(1)
    return 0


if __name__ == '__main__':
    main()
