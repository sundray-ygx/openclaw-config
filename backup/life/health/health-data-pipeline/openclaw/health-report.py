#!/usr/bin/env python3
"""
OpenClaw 健康报告脚本
读取 GitHub 数据，生成可视化报告，发送到飞书
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# 配置
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_OWNER = os.getenv('GITHUB_OWNER')
GITHUB_REPO = os.getenv('GITHUB_REPO')
FEISHU_WEBHOOK = os.getenv('FEISHU_WEBHOOK')

class HealthReport:
    def __init__(self):
        self.data = {
            'sleep': [],
            'heartRate': [],
            'steps': [],
            'workouts': []
        }
    
    def fetch_from_github(self):
        """从 GitHub 获取健康数据"""
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # 获取 data 目录下的所有文件
        url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/trees/main?recursive=1'
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        tree = response.json()['tree']
        json_files = [f for f in tree if f['path'].startswith('data/') and f['path'].endswith('.json')]
        
        print(f"Found {len(json_files)} data files")
        
        for file in json_files:
            file_url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{file["path"]}'
            file_response = requests.get(file_url, headers=headers)
            
            if file_response.status_code == 200:
                content = file_response.json()
                import base64
                data = json.loads(base64.b64decode(content['content']).decode('utf-8'))
                
                # 根据路径分类
                if 'sleep' in file['path']:
                    self.data['sleep'].append(data)
                elif 'heart' in file['path']:
                    self.data['heartRate'].append(data)
                elif 'steps' in file['path']:
                    self.data['steps'].append(data)
                elif 'workout' in file['path']:
                    self.data['workouts'].append(data)
        
        # 按日期排序
        for key in self.data:
            self.data[key].sort(key=lambda x: x.get('date', ''))
    
    def calculate_stats(self):
        """计算统计数据"""
        stats = {}
        
        # 睡眠统计
        if self.data['sleep']:
            recent = self.data['sleep'][-7:]  # 最近7天
            durations = [d.get('duration', 0) for d in recent if 'duration' in d]
            qualities = [d.get('quality', 0) for d in recent if 'quality' in d]
            
            stats['sleep'] = {
                'avg_duration': sum(durations) / len(durations) / 60 if durations else 0,  # 小时
                'avg_quality': sum(qualities) / len(qualities) if qualities else 0,
                'days': len(recent)
            }
        
        # 心率统计
        if self.data['heartRate']:
            recent = self.data['heartRate'][-7:]
            rates = [d.get('avg', d.get('value', 0)) for d in recent]
            stats['heartRate'] = {
                'avg': sum(rates) / len(rates) if rates else 0,
                'days': len(recent)
            }
        
        # 步数统计
        if self.data['steps']:
            recent = self.data['steps'][-7:]
            steps = [d.get('steps', d.get('value', 0)) for d in recent]
            stats['steps'] = {
                'avg': sum(steps) / len(steps) if steps else 0,
                'total': sum(steps),
                'days': len(recent)
            }
        
        return stats
    
    def generate_feishu_card(self, stats):
        """生成飞书卡片消息"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        elements = []
        
        # 睡眠模块
        if 'sleep' in stats:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**💤 睡眠**\n平均时长: **{stats['sleep']['avg_duration']:.1f}** 小时\n睡眠质量: **{stats['sleep']['avg_quality']:.0f}%**"
                }
            })
            elements.append({"tag": "hr"})
        
        # 心率模块
        if 'heartRate' in stats:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**❤️ 心率**\n平均心率: **{stats['heartRate']['avg']:.0f}** bpm"
                }
            })
            elements.append({"tag": "hr"})
        
        # 步数模块
        if 'steps' in stats:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**🚶 步数**\n平均步数: **{stats['steps']['avg']:.0f}**\n本周总计: **{stats['steps']['total']/10000:.1f}万**"
                }
            })
        
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"📊 健康日报 - {today}"
                    },
                    "template": "blue"
                },
                "elements": elements
            }
        }
        
        return card
    
    def send_to_feishu(self, card):
        """发送到飞书"""
        if not FEISHU_WEBHOOK:
            print("Warning: FEISHU_WEBHOOK not set")
            return
        
        response = requests.post(FEISHU_WEBHOOK, json=card)
        response.raise_for_status()
        print("Report sent to Feishu successfully")
    
    def run(self):
        """主流程"""
        print("Fetching health data from GitHub...")
        self.fetch_from_github()
        
        print("Calculating statistics...")
        stats = self.calculate_stats()
        
        print("Generating Feishu card...")
        card = self.generate_feishu_card(stats)
        
        print("Sending to Feishu...")
        self.send_to_feishu(card)
        
        print("Done!")

if __name__ == '__main__':
    report = HealthReport()
    report.run()
