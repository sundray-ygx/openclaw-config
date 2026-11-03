#!/bin/bash
# ============================================================
# NAS 恢复 S2 — hermes 骨架重建（从幸存 git 仓库）+ 启动链诊断
# 变更动作（Boss 已批准）：
#   1. 重建 /root/.hermes/{knowledge,memory,skills,logs}（rsync 自 /volume1/hermes-config）
#   2. 恢复 config.yaml / AGENTS.md / SOUL.md / MEMORY.md
#   3. state.db 软链回接 /volume1/hermes-data/state.db
#   4. 生成 .env 模板（600 权限，占位符，不传真实密钥）
# 不做：启动 gateway（等 S3 密钥就位）
# 用法：SSH 到 NAS root 执行：bash <本脚本路径>
# ============================================================

OUT="/tmp/nas-s2-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS 恢复 S2 — hermes 骨架重建  $(date '+%F %T')"
echo "=================================================="
sec() { echo; echo "########## $1 ##########"; }

SRC=/volume1/hermes-config
DST=/root/.hermes

sec "A. 前置校验"
[ -d "$SRC" ] && echo "✅ 源仓库存在: $SRC" || { echo "❌ 源仓库缺失"; exit 1; }
for d in knowledge memory skills config; do
    [ -d "$SRC/$d" ] && echo "✅ $SRC/$d" || echo "⚠️ 缺 $SRC/$d"
done
ls -la /volume1/hermes-data/state.db || { echo "❌ state.db 实体缺失"; exit 1; }

sec "B. 恢复前 .hermes 现状"
ls -la "$DST" 2>/dev/null || echo "[尚未创建]"

sec "C. 恢复（已批准的变更）"
mkdir -p "$DST/logs"
echo "--- knowledge ---"
rsync -a "$SRC/knowledge/" "$DST/knowledge/" && echo OK
echo "--- memory ---"
rsync -a --exclude='*.log' --exclude='state.db*' "$SRC/memory/" "$DST/memory/" && echo OK
echo "--- skills ---"
rsync -a --exclude='__pycache__/' --exclude='*.pyc' --exclude='.curator_backups/' --exclude='*.tar.gz' "$SRC/skills/" "$DST/skills/" && echo OK
echo "--- 顶层配置四件 ---"
for f in config.yaml AGENTS.md SOUL.md MEMORY.md; do
    if [ -f "$SRC/config/$f" ]; then cp "$SRC/config/$f" "$DST/$f" && echo "OK $f"; else echo "⚠️ $f 不在仓库"; fi
done

sec "D. state.db 软链回接"
if [ -e "$DST/state.db" ] || [ -L "$DST/state.db" ]; then
    echo "已存在，先看内容: $(ls -la "$DST/state.db")"
    echo "跳过（人工确认后处理）"
else
    ln -s /volume1/hermes-data/state.db "$DST/state.db" && echo "✅ 软链已建"
fi
ls -la "$DST/state.db" 2>/dev/null
echo "--- 只读完整性 ---"
REAL=$(readlink -f "$DST/state.db" 2>/dev/null)
[ -n "$REAL" ] && timeout 90 sqlite3 "file:${REAL}?mode=ro" "PRAGMA integrity_check;" 2>&1 | head -3
[ -n "$REAL" ] && timeout 90 sqlite3 "file:${REAL}?mode=ro" "SELECT count(*) FROM sessions;" 2>&1 | head -2

sec "E. .env 模板生成（不含密钥值）"
if [ -f "$DST/.env" ]; then
    echo "⚠️ .env 已存在，不覆盖"
else
cat > "$DST/.env" << 'ENVEOF'
# ============================================================
# NAS Hermes .env — 2026-10-31 重建模板
# 密钥值待手工填入（通道安全原因不经 WebDAV 传输）：
#   - ZAI_API_KEY / VOLCENGINE_API_KEY / DEEPSEEK_API_KEY / NEWAPI_API_KEY / ANTHROPIC_AUTH_TOKEN
#     → Boss 从 ECS 查看: ssh ECS 后 cat /root/.hermes/.env（仅复制需要的）
#   - FEISHU_APP_SECRET → 从 vaultwarden「飞书」条目取（App ID: cli_a9700b52b1621cd2）
#   - NOTION_API_KEY → vaultwarden 或 Notion 开发者后台重置
# 填完后: chmod 600 保持，勿入 git
# ============================================================
ZAI_API_KEY=
VOLCENGINE_API_KEY=
DEEPSEEK_API_KEY=
NEWAPI_API_KEY=
ANTHROPIC_AUTH_TOKEN=
FEISHU_APP_ID=cli_a9700b52b1621cd2
FEISHU_APP_SECRET=
FEISHU_DOMAIN=https://open.feishu.cn
FEISHU_ALLOWED_USERS=
FEISHU_HOME_CHANNEL=
NOTION_API_KEY=
ENVEOF
    chmod 600 "$DST/.env" && echo "✅ 模板已生成（600）"
fi

sec "F. hermes 启动链诊断（只读）"
echo "--- /usr/local/bin/hermes 内容 ---"
cat /usr/local/bin/hermes
echo "--- 各版本 venv 检查 ---"
for d in /usr/local/lib/hermes-agent /usr/local/lib/hermes-agent-v*; do
    [ -d "$d" ] || continue
    VENV="$d/venv"
    if [ -x "$VENV/bin/python3" ]; then
        VER=$("$VENV/bin/python3" --version 2>&1)
        echo "$d -> venv OK ($VER)"
    else
        echo "$d -> ❌ venv 缺失/损坏 (找: $VENV)"
        ls "$d" | head -6
    fi
done
echo "--- hermes --version 完整报错 ---"
hermes --version 2>&1 | head -10 || true
echo "--- /opt 幸存检查（bill-to-notion 等） ---"
ls -la /opt/ 2>/dev/null || echo "[/opt 不存在]"
ls /opt/bill-to-notion/ 2>/dev/null | head -5 || echo "[bill-to-notion 缺失——加入丢失清单]"

sec "G. 恢复后规模核验"
du -sh "$DST"/knowledge "$DST"/memory "$DST"/skills 2>/dev/null
find "$DST/skills" -name SKILL.md | wc -l | xargs echo "skills 数:"
ls "$DST/memory" | wc -l | xargs echo "memory 条目:"
ls "$DST" | head -20

sec "S2 完成"
date '+结束: %F %T'
echo "输出文件: $OUT"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cp "$OUT" "$SCRIPT_DIR/" 2>/dev/null && echo "已回传: $SCRIPT_DIR/$(basename "$OUT")" || echo "[回传失败，请手动取 $OUT]"
