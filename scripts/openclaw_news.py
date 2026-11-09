#!/usr/bin/env python3
# 迁移后的OpenClaw资讯脚本入口
# 原路径: /root/scripts/news/openclaw_news.py
# 新路径: /root/scripts/openclaw_news.py

import sys
import os

# 调用实际脚本
os.chdir('/root/scripts/news')
sys.path.insert(0, '/root/scripts/news')

exec(open('/root/scripts/news/openclaw_news.py').read())
