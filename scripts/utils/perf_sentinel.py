#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
perf_sentinel.py — ECS 性能哨兵（2026-10-22 建，配合 ecs-health-audit skill）

模式:
  --probe      每 30 分钟: 磁盘>=80% 或 load5>2 时自动只读诊断, 生成编号决策项
               报告, 推橙色卡片(同类 4h 去抖), 报告落 /var/log/perf-sentinel/
  --full       每周一 10:30: 完整只读巡检 + 分层风险清单, 推蓝色卡片
  --test       跑一次诊断, 报告打印 stdout, 不推送
  --test-push  推绿色测试卡验证链路

铁律: 自动化止于报告推送, 永不自动执行清理;
      执行由 Boss 在会话中批复("执行 perf 项 N")后按 ecs-health-audit skill 进行。

cron (root crontab):
  */30 * * * * python3 /root/.openclaw/workspace/scripts/utils/perf_sentinel.py --probe >> /var/log/perf-sentinel.log 2>&1
  30 10 * * 1 python3 /root/.openclaw/workspace/scripts/utils/perf_sentinel.py --full >> /var/log/perf-sentinel.log 2>&1
"""
import os
import sys
import json
import time
import hashlib
import subprocess

TH_DISK = 80    # 磁盘使用率触发自动诊断（heartbeat 告警线 85% 早一档）
TH_LOAD = 2.0   # load5 触发自动诊断
STATE_DIR = "/tmp/perf-sentinel"
REPORT_DIR = "/var/log/perf-sentinel"
DEDUP_S = 4 * 3600
NOTIFY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notify_feishu.py")


def sh(cmd, timeout=300):
    try:
        p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, universal_newlines=True,
                           timeout=timeout)
        return p.stdout.strip()
    except Exception:
        return ""


def human_mb(mb):
    return "%.1fG" % (mb / 1024.0) if mb >= 1024 else "%dM" % mb


def dir_mb(path):
    if not os.path.exists(path):
        return 0
    out = sh("du -sm %s 2>/dev/null | head -1 | awk '{print $1}'" % path, timeout=180)
    try:
        return int(out)
    except ValueError:
        return 0


def disk_info():
    line = sh("df -h / | sed -n 2p")
    parts = line.split()
    try:
        pct = int(parts[4].rstrip('%'))
    except (IndexError, ValueError):
        pct = 0
    return pct, line


def load5():
    try:
        return float(open("/proc/loadavg").read().split()[0])
    except Exception:
        return 0.0


def top_dirs():
    out = sh("for d in /*/; do d=${d%/}; case \"$d\" in /proc|/sys|/dev|/run|/tmp)"
             " continue;; esac; du -sm \"$d\" 2>/dev/null; done | sort -rn | head -6",
             timeout=600)
    rows = []
    for line in out.splitlines():
        p = line.split(None, 1)
        if len(p) == 2:
            try:
                rows.append((int(p[0]), p[1]))
            except ValueError:
                pass
    return rows


def top_mem_procs():
    return sh("ps aux --sort=-%mem | awk 'NR>=2&&NR<=5"
              "{printf \"%s%% %s\\n\", $4, substr($0, index($0,$11), 55)}'")


# 🟢 Tier1 playbook: 只收录 2026-10-22 实弹验证过的安全项, 新项须先经人工会话验证
# 结构: (路径, 卡片短名, 操作说明)  编号 = 序号+1, 跨报告稳定, 与 skill playbook 对齐
TIER1 = [
    ("/root/.hermes/cache/uv", "uv 缓存", "rm -rf 后重建空目录，自动重建"),
    ("/var/cache/dnf", "dnf 缓存", "dnf clean all"),
    ("/root/.npm/_npx", "npm _npx 缓存", "按需重下"),
    ("/root/.npm/_cacache", "npm _cacache 缓存", "按需重下"),
]

# 🟡 Tier2 线索: 只提示, 永不进自动执行清单
TIER2_HINTS = [
    "swap 总量/使用（1.8G 机保底 4G; 缩容五步法: swapoff→fstab 备份改→findmnt 校验→rm→swapon 复核）",
    "journal 用量（SystemMaxUse=100M 已设, 2026-10-22）",
    "/root/.openclaw/backup* 与各处 .bak 旧备份目录",
    "复涨规律: hermes 运行时升级每周期 ~1.3G; uv 缓存是第一大复涨项; pnpm store 585M 全被引用勿 prune",
    "npm 卸载坑: npm rm -g 对非本 prefix 安装无效, 须手动删 /usr/bin 符号链接 + /usr/lib/node_modules/x",
]


def build_report(trigger):
    pct, dfline = disk_info()
    rows = top_dirs()
    tier1 = []
    for i, (path, short, desc) in enumerate(TIER1, 1):
        mb = dir_mb(path)
        if mb >= 10:
            tier1.append((i, path, mb, short, desc))
    lines = []
    lines.append("# ECS 性能巡检报告 (%s)" % time.strftime("%F %T"))
    lines.append("")
    lines.append("触发: %s" % trigger)
    lines.append("磁盘: %s" % dfline)
    lines.append("load5: %.2f (阈值 %.1f)" % (load5(), TH_LOAD))
    lines.append("内存/swap (MB):")
    lines.append(sh("free -m | sed -n '2,3p'"))
    lines.append("")
    lines.append("## 顶层目录 TOP")
    for mb, d in rows:
        lines.append("- %s  %s" % (human_mb(mb), d))
    lines.append("")
    lines.append("## 🟢 Tier1 候选（已验证安全, 可批复执行）")
    for i, path, mb, short, desc in tier1:
        lines.append("%d. %s — %s 【%s】" % (i, path, human_mb(mb), desc))
    if not tier1:
        lines.append("(当前无可自动回收项)")
    lines.append("")
    lines.append("## 🟡 Tier2 线索（需会话人工评估, 勿自动执行）")
    for h in TIER2_HINTS:
        lines.append("- %s" % h)
    lines.append("")
    lines.append("## 内存 TOP 进程")
    lines.append(top_mem_procs() or "(无)")
    return "\n".join(lines), pct, tier1


def save_report(text):
    os.makedirs(REPORT_DIR, exist_ok=True)
    fn = os.path.join(REPORT_DIR, "report-%s.md" % time.strftime("%Y%m%d-%H%M"))
    with open(fn, "w") as f:
        f.write(text)
    with open(os.path.join(REPORT_DIR, "latest.md"), "w") as f:
        f.write(text)
    return fn


def mem_avail_m():
    try:
        return int(sh("free -m | awk '/Mem:/{print $7}'"))
    except ValueError:
        return 0


def swap_used_pct():
    try:
        return int(sh("free | awk '/Swap:/{if($2>0) printf \"%.0f\", $3/$2*100; else print 0}'"))
    except ValueError:
        return 0


def stat_col(label, value, sub=""):
    txt = "**%s**\n%s" % (label, value)
    if sub:
        txt += "\n%s" % sub
    return {"tag": "column", "width": "weighted", "weight": 1,
            "vertical_align": "top",
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": txt}}]}


def build_card(title, color, trigger, tier1, report_path):
    """富结构卡片: 三列统计位 → hr → Tier1 编号清单 → Tier2 压缩 → note 脚注"""
    pct, dfline = disk_info()
    avail = dfline.split()[3] if len(dfline.split()) >= 5 else ""
    elements = [
        {"tag": "column_set", "flex_mode": "trisect", "background_style": "grey",
         "columns": [
             stat_col("磁盘", "%d%%" % pct, "%s 可用" % avail),
             stat_col("load5", "%.2f" % load5(), "阈值 2.0"),
             stat_col("内存可用", "%dM" % mem_avail_m(), "swap %d%%" % swap_used_pct()),
         ]},
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md",
                                "content": "**🟢 Tier1 候选（已验证安全，可批复执行）**"}},
    ]
    if tier1:
        items = []
        for i, path, mb, short, desc in tier1:
            items.append("**%d. %s** — **%s**\n%s ｜ %s" % (i, short, human_mb(mb), path, desc))
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(items)}})
    else:
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                                                "content": "当前无可自动回收项，磁盘增长来自 Tier2 范畴，见报告明细"}})
    elements += [
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md",
                                "content": "**🟡 Tier2 线索**（需会话人工评估，勿自动执行）\nswap 容量 · journal · openclaw 旧备份 · 运行时/uv 复涨 · npm 卸载坑 → 明细见报告文件"}},
        {"tag": "note", "elements": [
            {"tag": "plain_text",
             "content": "触发: %s ｜ 批复: 会话回复「执行 perf 项 N」 ｜ 报告: %s" % (trigger, report_path)}]},
    ]
    return {"config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": title}, "template": color},
            "elements": elements}


def should_alert(key):
    os.makedirs(STATE_DIR, exist_ok=True)
    f = os.path.join(STATE_DIR, key + ".last")
    now = time.time()
    if os.path.exists(f):
        try:
            if now - float(open(f).read().strip() or 0) < DEDUP_S:
                return False
        except ValueError:
            pass
    with open(f, "w") as fh:
        fh.write(str(int(now)))
    return True


def push_card(card):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = os.path.join(STATE_DIR, "card.json")
    with open(tmp, "w") as f:
        json.dump(card, f, ensure_ascii=False)
    p = subprocess.run([sys.executable, NOTIFY, "--card-json", tmp],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    print("push rc=%d out=%s err=%s"
          % (p.returncode, p.stdout.strip()[:120], p.stderr.strip()[:120]))
    return p.returncode == 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--probe"

    if mode == "--test-push":
        push_card(build_card("🧪 perf-sentinel 排版验证", "green",
                             "链路测试（新排版）", [], "—"))
        return

    if mode == "--full":
        text, pct, tier1 = build_report("每周一定时全量巡检")
        rp = save_report(text)
        print(text)
        push_card(build_card("📋 ECS 每周性能巡检", "blue",
                             "每周一 10:30 定时", tier1, rp))
        return

    # --probe / --test
    pct, _ = disk_info()
    l5 = load5()
    print("%s probe disk=%d%% load5=%.2f" % (time.strftime("%F %T"), pct, l5))
    if pct < TH_DISK and l5 < TH_LOAD:
        if mode == "--test":
            print("未触发阈值(磁盘<%d%% 且 load5<%.1f), 诊断跳过" % (TH_DISK, TH_LOAD))
        return

    if pct >= TH_DISK:
        trigger = "磁盘 %d%% (阈值 %d%%)" % (pct, TH_DISK)
    else:
        trigger = ""
    if l5 >= TH_LOAD:
        trigger = (trigger + " " if trigger else "") + "load5 %.2f (阈值 %.1f)" % (l5, TH_LOAD)

    text, pct2, tier1 = build_report(trigger)
    rp = save_report(text)
    print(text)
    if mode == "--test":
        print("(test 模式不推送)")
        return
    key = "probe-" + hashlib.md5(trigger.encode()).hexdigest()[:8]
    if should_alert(key):
        push_card(build_card("⚠️ ECS 性能瓶颈触发", "orange",
                             trigger, tier1, rp))


if __name__ == "__main__":
    main()
