#!/bin/bash
# ============================================================
# NAS 恢复 S7 — load_secrets 重建 + gateway 真启动
# 依据：vaultwarden-secrets-integration skill 规格（脚本本体丢失，按 spec 忠实重建）
# 变更动作（Boss 已批准「全部按推荐建议执行」的网关恢复范畴）：
#   1. 重建 /root/.hermes/scripts/load_secrets.{sh,py}
#      —— 过渡策略：bw session 文件缺失时回退用 .env 生成 .env.vaultwarden
#         （单元文件本就声明 .env 为 fallback 源，语义一致；WARN 落日志）
#   2. systemctl daemon-reload + restart hermes-gateway
# 其余只读（bw CLI 存在性、console-api 日志诊断、启动观察）
# 用法：SSH 到 NAS root 执行：bash <本脚本路径>
# ============================================================

OUT="/tmp/nas-s7-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS 恢复 S7 — gateway 真启动  $(date '+%F %T')"
echo "=================================================="
sec() { echo; echo "########## $1 ##########"; }

# ---- 主机守卫：本脚本只允许在 NAS 上执行（防 ECS 误跑重启自己的网关）----
HN=$(hostname)
if [ "$HN" != "enjoysynology" ]; then
    echo "❌ 主机守卫：hostname=$HN ≠ enjoysynology。本脚本仅限 NAS 执行（含 systemctl restart hermes-gateway，ECS 同名单元会被误伤）。终止。"
    exit 1
fi
echo "✅ 主机守卫通过: $HN"

sec "A. 前置盘点（只读）"
command -v bw && bw --version 2>/dev/null | head -1 || echo "[bw CLI 不在 PATH]"
ls -la /usr/local/bin/bw 2>/dev/null
for f in /root/.hermes/.bw_session /root/.hermes/.bw_password; do
    [ -f "$f" ] && echo "$f ✅在位" || echo "$f ❌缺失（rootfs 丢失，预期内）"
done

sec "B. 重建 load_secrets 脚本（已批准变更）"
mkdir -p /root/.hermes/scripts

cat > /root/.hermes/scripts/load_secrets.py << 'PYEOF'
#!/usr/bin/env python3
"""load_secrets.py — 从 Vaultwarden 集合生成 .env.vaultwarden
重建自 vaultwarden-secrets-integration skill 规格（2026-10-31 DSM 灾后）。
--check 模式：只列出密钥数量与名称，不写文件。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

BW = "/usr/local/bin/bw"
ENV_OUT = "/root/.hermes/.env.vaultwarden"
SESSION_FILE = "/root/.hermes/.bw_session"
PASS_FILE = "/root/.hermes/.bw_password"
FALLBACK_ENV = "/root/.hermes/.env"
ORG_COLLECTION = "hermes"  # skill 规格：组织内集合，条目 name=变量名 notes=值


def sh(cmd, env=None, timeout=120):
    e = os.environ.copy()
    if env:
        e.update(env)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=e, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def get_session():
    if not os.path.isfile(SESSION_FILE):
        return None
    return open(SESSION_FILE).read().strip()


def relogin():
    """session 过期时用 .bw_password 自动重登（skill 规格）"""
    if not os.path.isfile(PASS_FILE):
        return None
    email = os.environ.get("BW_EMAIL", "")
    if not email:
        return None
    pw = open(PASS_FILE).read().strip()
    rc, out, _ = sh(f'bw login {email} --passwordenv BW_PASSWORD --raw',
                    env={"BW_PASSWORD": pw})
    if rc == 0 and out:
        with open(SESSION_FILE, "w") as f:
            f.write(out)
        os.chmod(SESSION_FILE, 0o600)
        return out
    return None


def unlock_fallback():
    """过渡回退：无 session 时用 .env 直接生成 .env.vaultwarden（WARN）"""
    if not os.path.isfile(FALLBACK_ENV):
        print("[load_secrets] FATAL: 既无 bw session，.env 回退源也不存在", file=sys.stderr)
        return False
    with open(FALLBACK_ENV) as src, tempfile.NamedTemporaryFile("w", delete=False, dir="/root/.hermes") as t:
        for line in src:
            t.write(line)
        tmp = t.name
    os.chmod(tmp, 0o600)
    os.replace(tmp, ENV_OUT)
    print("[load_secrets] WARN: bw session 缺失，已用 .env 回退生成 .env.vaultwarden（过渡策略）")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(BW):
        print("[load_secrets] bw CLI 不存在", file=sys.stderr)
        ok = unlock_fallback()
        sys.exit(0 if ok else 1)

    sess = get_session()
    if sess is None:
        ok = unlock_fallback()
        sys.exit(0 if ok else 1)

    # status 检查 session 有效性
    rc, out, _ = sh("bw status", env={"BW_SESSION": sess})
    try:
        status = json.loads(out).get("status")
    except Exception:
        status = None
    if status not in ("unlocked",):
        sess = relogin()
        if sess is None:
            ok = unlock_fallback()
            sys.exit(0 if ok else 1)

    # 列集合内条目
    rc, out, err = sh(f"bw list items --collectionid $({BW} list collections --search {ORG_COLLECTION} | head -c 0; echo '') 2>/dev/null || bw list items",
                      env={"BW_SESSION": sess})
    # 上面的 collectionid 定位较脆，直接列全部条目再按组织过滤更稳：
    rc, out, err = sh("bw list items", env={"BW_SESSION": sess})
    if rc != 0 or not out:
        print(f"[load_secrets] bw list items 失败: {err}", file=sys.stderr)
        ok = unlock_fallback()
        sys.exit(0 if ok else 1)

    items = json.loads(out)
    kv = {}
    for it in items:
        name = it.get("name", "")
        notes = it.get("notes") or ""
        if it.get("type") == 2 and notes and "=" not in name:  # Secure Note: name=key notes=value
            first_line = notes.strip().splitlines()[0] if notes.strip() else ""
            if name and first_line:
                kv[name] = first_line

    if args.check:
        print(f"密钥数量: {len(kv)}")
        for k in sorted(kv):
            print(f"  {k}")
        sys.exit(0)

    if not kv:
        print("[load_secrets] 空集合，回退", file=sys.stderr)
        ok = unlock_fallback()
        sys.exit(0 if ok else 1)

    with tempfile.NamedTemporaryFile("w", delete=False, dir="/root/.hermes") as t:
        t.write("# generated by load_secrets.py from Vaultwarden\n")
        for k in sorted(kv):
            t.write(f"{k}={kv[k]}\n")
        tmp = t.name
    os.chmod(tmp, 0o600)
    os.replace(tmp, ENV_OUT)
    print(f"[load_secrets] ✅ 从 Vaultwarden 生成 {len(kv)} 个密钥 -> {ENV_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
PYEOF

cat > /root/.hermes/scripts/load_secrets.sh << 'SHEOF'
#!/bin/bash
# load_secrets.sh — hermes-gateway ExecStartPre（fail-closed）
# 重建自 vaultwarden-secrets-integration skill 规格（2026-10-31）
set -euo pipefail
PY=/usr/local/lib/hermes-agent/venv/bin/python
[ -x "$PY" ] || PY=python3
exec "$PY" /root/.hermes/scripts/load_secrets.py
SHEOF

chmod 700 /root/.hermes/scripts/load_secrets.sh
chmod 700 /root/.hermes/scripts/load_secrets.py
ls -la /root/.hermes/scripts/

sec "C. load_secrets 试跑（--check + 实跑）"
PY=/usr/local/lib/hermes-agent/venv/bin/python; [ -x "$PY" ] || PY=python3
"$PY" /root/.hermes/scripts/load_secrets.py --check 2>&1 | head -20
echo "--- 实跑 ---"
"$PY" /root/.hermes/scripts/load_secrets.py 2>&1 | head -5
echo "退出码: $?"
ls -la /root/.hermes/.env.vaultwarden
echo "键数: $(grep -cE '^[A-Z_]+=' /root/.hermes/.env.vaultwarden 2>/dev/null)"

sec "D. gateway 启动（已批准变更）"
systemctl daemon-reload
systemctl restart hermes-gateway 2>&1
sleep 10
systemctl is-active hermes-gateway
echo "--- journal 最近 25 行 ---"
journalctl -u hermes-gateway --no-pager -n 25 2>/dev/null | tail -25

sec "E. 启动后观察（90s）"
sleep 90
systemctl is-active hermes-gateway
echo "--- 飞书/模型连接迹象 ---"
journalctl -u hermes-gateway --no-pager --since '-3 min' 2>/dev/null | grep -iE 'lark|feishu|wss|websocket|provider|model|error|listen' | tail -15
echo "--- 进程 ---"
ps aux | grep -E 'hermes_cli|gateway run' | grep -v grep | head -3

sec "F. console-api 日志诊断（只读）"
docker logs --tail 20 projects-console-api-1 2>&1 | tail -20

sec "S7 完成"
date '+结束: %F %T'
echo "输出文件: $OUT"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cp "$OUT" "$SCRIPT_DIR/" 2>/dev/null && echo "已回传: $SCRIPT_DIR/$(basename "$OUT")" || echo "[回传失败，请手动取 $OUT]"
