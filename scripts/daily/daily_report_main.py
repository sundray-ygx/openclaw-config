#!/usr/bin/env python3
"""
工作日报生成脚本 V8 - AI 驱动版
合并：系统运行状况 + 工作总结
"""

import os
import json
import re
import subprocess
from datetime import datetime, timedelta
import urllib.request
import urllib.parse

FEISHU_APP_ID = "cli_a93b96047e7a5bc3"
FEISHU_APP_SECRET = "ir6uAf1L7O52AFgXrepgabIrYG1oOcbD"
FEISHU_USER_ID = "ou_c2cde251e01a87fc09ba7561f76d8606"
SESSIONS_DIR = "/home/openclaw/.openclaw/agents/main/sessions"
MEMORY_DIR = "/root/.openclaw/workspace/memory"

AI_MODEL = "glm-5"
ZAI_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"


def _load_zai_key():
    try:
        with open('/root/.openclaw/agents/main/agent/auth-profiles.json', 'r') as f:
            profiles = json.load(f)
        return profiles['profiles']['zai:default']['key']
    except Exception:
        return ""

ZAI_API_KEY = _load_zai_key()


# ── 飞书 ──

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode()).get("tenant_access_token")
    except Exception:
        return None


def send_feishu_text(token, user_id, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    message = {"receive_id": user_id, "msg_type": "text", "content": json.dumps({"text": text}, ensure_ascii=False)}
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full_url, data=json.dumps(message, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode()).get("code") == 0
    except Exception:
        return False


# ── AI 调用 ──

def get_ai_response(system_prompt, user_prompt, max_tokens=2000):
    data = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"{ZAI_BASE_URL}/chat/completions",
             "-H", f"Authorization: Bearer {ZAI_API_KEY}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(data)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=180
        )
        if result.returncode == 0:
            response = json.loads(result.stdout)
            message = response.get('choices', [{}])[0].get('message', {})
            content = message.get('content', '') or message.get('reasoning_content', '')
            return content.strip() if content else None
        else:
            print(f"  AI 调用失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"  AI 调用异常: {e}")
        return None


# ── 数据收集 ──

def collect_system_status(date_str):
    """收集系统运行数据"""
    status = {"cron_tasks": [], "errors": [], "disk": "", "memory": ""}

    # 读取当日日志
    log_file = os.path.join(MEMORY_DIR, f"{date_str}.md")
    log_content = ""
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()

    # 提取 cron 任务执行记录
    cron_patterns = [
        (r'早间简报.*?(?:成功|失败|完成)', '早间简报'),
        (r'工作日报.*?(?:成功|失败|完成)', '工作日报'),
        (r'每日反思.*?(?:成功|失败|完成|生成)', '每日反思'),
        (r'NAS.*?(?:备份|成功|失败)', 'NAS备份'),
        (r'GitHub.*?(?:同步|成功|失败|push)', 'GitHub同步'),
        (r'周复盘.*?(?:成功|失败|完成)', '周复盘'),
        (r'安全.*?(?:巡检|检查|成功|失败)', '安全巡检'),
    ]
    for pattern, label in cron_patterns:
        matches = re.findall(pattern, log_content, re.IGNORECASE)
        if matches:
            status["cron_tasks"].append(f"{label}: {matches[-1][:60]}")

    # 提取错误
    error_lines = []
    for line in log_content.split('\n'):
        if any(kw in line.lower() for kw in ['error', '失败', '异常', '错误', 'failed', 'timeout']):
            clean = line.strip().lstrip('- ')
            if clean and len(clean) > 10 and len(clean) < 200:
                if 'Traceback' not in clean and 'import ' not in clean:
                    error_lines.append(clean)
    status["errors"] = error_lines[:5]

    # 磁盘和内存（实时快照）
    try:
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        for line in disk.stdout.split('\n'):
            if '/' in line and 'tmpfs' not in line:
                parts = line.split()
                if len(parts) >= 5:
                    status["disk"] = f"{parts[2]}/{parts[1]} ({parts[4]})"
    except Exception:
        pass

    try:
        mem = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        for line in mem.stdout.split('\n'):
            if 'Mem:' in line:
                parts = line.split()
                if len(parts) >= 3:
                    status["memory"] = f"{parts[2]}/{parts[1]}"
    except Exception:
        pass

    return status, log_content


def collect_session_interactions(start_time, end_time):
    """从会话文件提取用户交互"""
    interactions = []
    cron_tasks = []

    if not os.path.exists(SESSIONS_DIR):
        return cron_tasks, interactions

    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)

    for filename in os.listdir(SESSIONS_DIR):
        if not filename.endswith('.jsonl'):
            continue
        filepath = os.path.join(SESSIONS_DIR, filename)
        try:
            mtime_ms = int(os.stat(filepath).st_mtime * 1000)
            if not (start_ts <= mtime_ms <= end_ts):
                continue
        except Exception:
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue

                    msg_type = data.get('type', '')
                    msg = data.get('message', {})
                    role = msg.get('role', '')
                    content = msg.get('content', [])

                    text_parts = [p.get('text', '') for p in content if p.get('type') == 'text']
                    full_text = ' '.join(text_parts)

                    if not full_text or len(full_text) < 5:
                        continue

                    # 跳过系统噪音
                    if any(x in full_text for x in [
                        'Skills store policy', 'A scheduled reminder', 'operator configured',
                        'HEARTBEAT_OK', 'System: [', 'openclaw.inbound_meta'
                    ]):
                        continue

                    if role == 'user' and msg_type == 'message':
                        # 检查是否是 cron 触发
                        if 'scheduled reminder' in full_text.lower() or '定时' in full_text:
                            task_match = re.search(r'The reminder content is:\s*\n\s*(.+?)(?:\n\s*Please relay|$)', full_text, re.DOTALL)
                            if task_match:
                                cron_tasks.append(task_match.group(1).strip()[:80])
                            continue
                        interactions.append(full_text[:150])
        except Exception:
            continue

    return cron_tasks, interactions


def generate_ai_report(date_str, log_content, sys_status, cron_tasks, interactions):
    """用 AI 生成有实质内容的日报"""

    has_content = log_content or interactions

    # 构建 AI 输入
    work_summary = log_content[:2000] if log_content else "当日无工作日志"

    cron_summary = "\n".join([f"- {t}" for t in cron_tasks[:10]]) if cron_tasks else "无记录"
    interaction_summary = "\n".join([f"- {i}" for i in interactions[:8]]) if interactions else "无交互"
    error_summary = "\n".join([f"- {e}" for e in sys_status['errors']]) if sys_status['errors'] else "无异常"

    system_prompt = """你是小助的日报生成器。根据当日数据生成简洁、有实质内容的工作日报。

要求：
1. 不要废话，不要客套话
2. 系统运行部分：有异常就报告，没异常简单说"系统运行正常"
3. 工作总结：提炼用户实际做了什么（不是流水账，是总结）
4. 如果当天内容很少（休息日/轻度使用），生成简短版即可
5. 如果有未解决的问题，列出来

输出格式：

📊 小助工作日报 - {date}

系统运行
- 定时任务：X 项执行（如有失败说明）
- 磁盘/内存：当前状态
- 异常：（有则列出，无则省略）

工作总结
（用 2-4 句话总结当天主要工作内容，基于交互记录和日志）

待处理
（如有未解决的异常或待办，列出；无则省略）"""

    user_prompt = f"""日期：{date_str}

当日日志：
{work_summary}

定时任务执行：
{cron_summary}

用户交互（{len(interactions)} 条）：
{interaction_summary}

异常记录：
{error_summary}

系统资源：磁盘 {sys_status['disk'] or '未知'}，内存 {sys_status['memory'] or '未知'}

请生成日报。"""

    return get_ai_response(system_prompt, user_prompt, max_tokens=1500)


def generate_fallback_report(date_str, sys_status, cron_tasks, interactions):
    """AI 不可用时的兜底模板"""
    lines = [f"📊 小助工作日报 - {date_str}", ""]

    lines.append("系统运行")
    lines.append(f"- 定时任务：{len(cron_tasks)} 项执行")
    if sys_status['disk']:
        lines.append(f"- 磁盘：{sys_status['disk']}")
    if sys_status['memory']:
        lines.append(f"- 内存：{sys_status['memory']}")
    if sys_status['errors']:
        lines.append("- 异常：")
        for e in sys_status['errors'][:3]:
            lines.append(f"  - {e[:60]}")
    else:
        lines.append("- 系统运行正常")
    lines.append("")

    lines.append("工作总结")
    if interactions:
        lines.append(f"- 处理用户请求 {len(interactions)} 次")
        for i in interactions[:3]:
            lines.append(f"  - {i[:50]}...")
    else:
        lines.append("- 当日无用户交互")
    lines.append("")

    return '\n'.join(lines)


def main():
    print("=" * 40)
    print("📊 工作日报 V8 - AI 驱动版")
    print("=" * 40)

    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    date_display = yesterday.strftime('%Y年%m月%d日')
    print(f"📅 日报日期: {date_display}")

    # 1. 收集数据
    print("📂 收集数据...")
    start_time = yesterday.replace(hour=0, minute=0, second=0)
    end_time = yesterday.replace(hour=23, minute=59, second=59)

    sys_status, log_content = collect_system_status(date_str)
    cron_tasks, interactions = collect_session_interactions(start_time, end_time)

    print(f"  定时任务: {len(cron_tasks)} 项")
    print(f"  用户交互: {len(interactions)} 条")
    print(f"  异常: {len(sys_status['errors'])} 条")
    print(f"  日志长度: {len(log_content)} 字符")

    # 2. AI 生成日报
    print("🤖 AI 生成日报...")
    report = generate_ai_report(date_str, log_content, sys_status, cron_tasks, interactions)

    if not report or len(report) < 50:
        print("⚠️ AI 生成失败或内容过短，使用兜底模板")
        report = generate_fallback_report(date_display, sys_status, cron_tasks, interactions)
    else:
        print(f"  ✅ AI 日报生成完成 ({len(report)} 字)")
        # 确保标题包含日期
        if date_display not in report:
            report = f"📊 小助工作日报 - {date_display}\n\n{report}"

    # 3. 质量守门：内容太少不发飞书（避免噪音）
    # 但系统状态至少要保留
    print(f"\n{report}")

    # 4. 发送飞书
    print("\n📤 发送到飞书...")
    token = get_feishu_token()
    if token:
        if send_feishu_text(token, FEISHU_USER_ID, report):
            print("✅ 发送成功")
        else:
            print("❌ 发送失败")
    else:
        print("❌ 获取 token 失败")


if __name__ == "__main__":
    main()
