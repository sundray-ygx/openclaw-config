#!/bin/bash
# ECS 侧每日同步 hermes-config：git pull + 技能增量传播
# cron: 0 5 * * * /root/scripts/hermes-sync/pull.sh >> /var/log/hermes-config-pull.log 2>&1
# 规则：
#   - 新技能（本机无）→ 自动装入
#   - NAS 自有技能有更新 → 自动覆盖（本机对该技能的手动改动会被还原，hub 是 NAS）
#   - protected-skills.txt 中的技能（官方版本漂移）→ 永不覆盖本机版本
#   - NAS 删除技能不联动删除本机
set -u
REPO=/root/hermes-config
LOCAL_SKILLS=/root/.hermes/skills
PROTECTED=/root/scripts/hermes-sync/protected-skills.txt
LOCK=/var/lock/hermes-config-pull.lock

exec 9>"$LOCK"
flock -n 9 || { echo "[$(date '+%F %T')] 上一次同步仍在运行，跳过"; exit 0; }

cd "$REPO" || { echo "[$(date '+%F %T')] 🔴 仓库目录不存在: $REPO"; exit 1; }
echo "===== $(date '+%F %T') 同步开始 ====="

if ! git fetch origin main 2>&1; then
  echo "🔴 git fetch 失败（网络/SSH）"; exit 1
fi
if ! git pull --ff-only origin main 2>&1; then
  echo "🔴 git pull 失败（本地与远端分叉？ECS 侧不应有本地提交）"; exit 1
fi

added=0; updated=0; skipped=0
while IFS= read -r skill; do
  [ -n "$skill" ] || continue
  if [ -d "$LOCAL_SKILLS/$skill" ]; then
    if grep -qxF "$skill" "$PROTECTED" 2>/dev/null; then
      skipped=$((skipped+1)); continue
    fi
    if ! diff -rq "$REPO/skills/$skill" "$LOCAL_SKILLS/$skill" >/dev/null 2>&1; then
      rsync -a --delete "$REPO/skills/$skill/" "$LOCAL_SKILLS/$skill/"
      echo "  更新: $skill"
      updated=$((updated+1))
    fi
  else
    mkdir -p "$LOCAL_SKILLS/$(dirname "$skill")"
    rsync -a "$REPO/skills/$skill" "$LOCAL_SKILLS/$(dirname "$skill")/"
    echo "  新增: $skill"
    added=$((added+1))
  fi
done < <(cd "$REPO/skills" && find . -name SKILL.md -printf '%h\n' | sed 's|^\./||' | sort)

echo "✅ 完成: $(git log -1 --format='%h %s') | 技能 新增 $added / 更新 $updated / 官方保护跳过 $skipped"
