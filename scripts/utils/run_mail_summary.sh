#!/bin/bash
# 邮件汇总定时任务脚本

cd /root
export PYTHONIOENCODING=utf8
python3 /root/scripts/mail_summary.py >> /root/mail-reports/cron.log 2>&1
