#!/usr/bin/env python3
"""
Cron 健康检查 - 检查 openclaw cron 任务是否正常运行
集成 cron_registry 的连续性检查，异常时通过飞书告警
"""

import json
import os
import sys
from datetime import datetime, timedelta

# 添加 utils 路径
sys.path.insert(0, '/root/.openclaw/workspace/scripts/utils')
try:
    from cron_registry import record_execution, check_continuity, generate_report
except ImportError:
    print("⚠️ cron_registry 不可用，使用基础检查")
    check_continuity = None
    record_execution = None

MEMORY_DIR = "/root/.openclaw/workspace/memory"
HEALTH_FILE = os.path.join(MEMORY_DIR, "cron-health.json")


def check_openclaw_crons(max_gap_hours=48):
    """通过 openclaw status 检查 cron 健康状态"""
    import subprocess
    
    result = subprocess.run(
        ['openclaw', 'cron', 'list', '--json'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60
    )
    
    if result.returncode != 0:
        return {'error': f'openclaw cron list 失败: {result.stderr[:200]}'}
    
    try:
        parsed = json.loads(result.stdout)
        crons = parsed.get('jobs', parsed) if isinstance(parsed, dict) else parsed
    except json.JSONDecodeError:
        # 解析表格格式
        lines = result.stdout.strip().split('\n')
        crons = []
        for line in lines:
            if line.strip() and not line.startswith('ID') and not line.startswith('-'):
                parts = line.split()
                if len(parts) >= 6:
                    crons.append({
                        'id': parts[0],
                        'name': parts[1],
                        'status': parts[5] if len(parts) > 5 else 'unknown',
                        'last': parts[4] if len(parts) > 4 else 'unknown'
                    })
    
    if not crons:
        return {'total': 0, 'issues': []}
    
    issues = []
    healthy = 0
    now_ms = datetime.now().timestamp() * 1000
    # 调度过期容忍窗口：nextRunAtMs 已过期超过该值才报警（避免轮询间隙误报）
    overdue_ms = max_gap_hours * 3600 * 1000
    for c in crons:
        if not isinstance(c, dict):
            continue
        name = c.get('name', c.get('displayName', c.get('id', '?')))
        enabled = c.get('enabled', True)
        if not enabled:
            continue  # skip disabled jobs
        run_status = (c.get('lastRunStatus') or c.get('lastStatus') or c.get('status') or '').lower()
        # 1) 运行失败告警
        if 'error' in run_status:
            issues.append(f"⚠️ {name}: 上次运行失败 (status={run_status})")
            continue
        # 2) 调度过期告警：one-shot 或周期任务的 nextRunAtMs 已过期超窗
        next_ms = c.get('nextRunAtMs') or 0
        if next_ms and (now_ms - next_ms) > overdue_ms:
            next_time = datetime.fromtimestamp(next_ms / 1000).strftime('%Y-%m-%d %H:%M')
            issues.append(f"⚠️ {name}: 调度过期 next={next_time} 未触发")
            continue
        healthy += 1
    
    return {
        'total': len(crons),
        'healthy': healthy,
        'issues': issues,
        'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }


def load_health_history():
    """加载历史健康记录"""
    if os.path.exists(HEALTH_FILE):
        with open(HEALTH_FILE) as f:
            return json.load(f)
    return {'checks': []}


def save_health_check(result):
    """保存健康检查结果"""
    history = load_health_history()
    history['checks'].append({
        'time': result['checked_at'],
        'total': result.get('total', 0),
        'healthy': result.get('healthy', 0),
        'issues': result.get('issues', [])
    })
    # 只保留最近 30 条
    history['checks'] = history['checks'][-30:]
    with open(HEALTH_FILE, 'w') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    print("🔍 Cron 健康检查")
    
    # 1. 检查 openclaw cron 状态
    result = check_openclaw_crons(max_gap_hours=48)
    
    if 'error' in result:
        print(f"❌ {result['error']}")
        return
    
    print(f"📊 总任务: {result['total']}, 健康: {result['healthy']}")
    
    if result['issues']:
        print(f"\n⚠️ 发现 {len(result['issues'])} 个问题:")
        for issue in result['issues']:
            print(f"  {issue}")
    else:
        print("✅ 所有任务运行正常")
    
    # 2. 保存结果
    save_health_check(result)
    
    # 3. 记录到 cron_registry（如果可用）
    if record_execution:
        try:
            record_execution('cron-health-check', 'ok', 0)
        except Exception:
            pass
    
    # 4. 如果有问题，输出告警信息（供飞书推送使用）
    if result['issues']:
        print(f"\n🔔 需要关注: {len(result['issues'])} 个 cron 任务异常")


if __name__ == '__main__':
    main()
