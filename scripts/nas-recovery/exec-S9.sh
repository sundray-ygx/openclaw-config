#!/bin/bash
# ============================================================
# NAS 恢复 S9 — Shell 环境(dotfiles)恢复
# 批复: D1=不带密钥 D2=gitconfig最小化 D3=vimrc忠实拷 D4=跳过(Boss已手动)
# 架构: /volume1/hermes-data/dotfiles/ 主副本 + rootfs 薄指针
# 变更面: /volume1/hermes-data/dotfiles/ (新建)
#         /etc/profile (追加标记块, 幂等)
#         /root/.profile /root/.vimrc /root/.gitconfig (薄指针/软链)
# 不动: DSM 系统文件本体, node 软链(D4已手动, 仅只读复核)
# 用法: SSH 到 NAS root: bash <本脚本路径>  (物料需同目录)
# ============================================================

OUT="/tmp/nas-s9-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================="
echo " NAS 恢复 S9 — Shell 环境恢复  $(date '+%F %T')"
echo "=================================================="
sec() { echo; echo "########## $1 ##########"; }

HN=$(hostname)
if [ "$HN" != "enjoysynology" ]; then
    echo "❌ 主机守卫: hostname=$HN ≠ enjoysynology, 终止"
    exit 1
fi
echo "✅ 主机守卫通过: $HN"

SRC="$(cd "$(dirname "$0")" && pwd)"
DF=/volume1/hermes-data/dotfiles

sec "A. 探测 (只读)"
echo "登录 shell: $SHELL  (当前: $(ps -p $$ -o comm= 2>/dev/null))"
echo "bash: $(command -v bash || echo 无)"
echo "vim:  $(command -v vim || echo 无)  vi: $(command -v vi || echo 无)"
echo "TERM=$TERM  tput colors: $(tput colors 2>/dev/null || echo 无tput)"
if ls --color=auto / >/dev/null 2>&1; then echo "busybox ls --color: ✅支持"; else echo "busybox ls --color: ❌不支持(颜色别名不会生效)"; fi
if echo x | grep --color=auto x >/dev/null 2>&1; then echo "grep --color: ✅"; else echo "grep --color: ❌"; fi
echo "--- D4 手动软链复核 (只读) ---"
for b in node npm npx; do
    P=$(command -v $b 2>/dev/null)
    [ -n "$P" ] && echo "$b -> $P ($($b --version 2>/dev/null | head -1))" || echo "$b ❌ 不在 PATH"
done
echo "--- 现存 /etc/profile 尾部 3 行 ---"
tail -3 /etc/profile 2>/dev/null
echo "--- 现存 /root/.profile ---"
cat /root/.profile 2>/dev/null || echo "(不存在)"

sec "B. 落地主副本 (已批准变更)"
mkdir -p "$DF"
cp "$SRC/dotfiles-profile-master.sh" "$DF/profile-master.sh" && echo "✅ profile-master.sh"
cp "$SRC/dotfiles-vimrc" "$DF/vimrc" && echo "✅ vimrc ($(wc -l < "$DF/vimrc") 行, 忠实拷贝)"

cat > "$DF/gitconfig" << 'GITEOF'
# NAS 最小化 gitconfig (D2=B: 身份留空, Boss 后续填 name/email)
[core]
	autocrlf = input
	editor = vim
[color]
	ui = auto
[alias]
	st = status
	co = checkout
	br = branch
	ci = commit
	lg = log --oneline --graph --decorate --all
	undo = reset --soft HEAD~1
GITEOF
echo "✅ gitconfig (最小化)"

sec "C. 薄指针落地 (已批准变更, 全部幂等)"
MARK='profile-master.sh'
if grep -q "$MARK" /etc/profile 2>/dev/null; then
    echo "/etc/profile: 标记块已存在, 跳过"
else
    printf '\n# --- hermes dotfiles master (restore: /volume1/hermes-data/dotfiles/restore.sh) ---\n[ -r /volume1/hermes-data/dotfiles/profile-master.sh ] && . /volume1/hermes-data/dotfiles/profile-master.sh\n' >> /etc/profile
    echo "/etc/profile: ✅ 追加薄指针"
fi

printf '# thin pointer (ash login shell) — master on volume1\n[ -r /volume1/hermes-data/dotfiles/profile-master.sh ] && . /volume1/hermes-data/dotfiles/profile-master.sh\n' > /root/.profile
echo "/root/.profile: ✅ 写入"

ln -sf "$DF/vimrc" /root/.vimrc      && echo "/root/.vimrc -> master: ✅"
ln -sf "$DF/gitconfig" /root/.gitconfig && echo "/root/.gitconfig -> master: ✅"

cat > "$DF/restore.sh" << 'RSTEOF'
#!/bin/sh
# DSM 升级后一键自愈: 重建 rootfs 薄指针 (主副本在 volume1 不会丢)
D=/volume1/hermes-data/dotfiles
grep -q 'profile-master.sh' /etc/profile 2>/dev/null || \
  printf '\n# --- hermes dotfiles master (restore: /volume1/hermes-data/dotfiles/restore.sh) ---\n[ -r %s/profile-master.sh ] && . %s/profile-master.sh\n' "$D" "$D" >> /etc/profile
printf '# thin pointer (ash login shell) — master on volume1\n[ -r %s/profile-master.sh ] && . %s/profile-master.sh\n' "$D" "$D" > /root/.profile
ln -sf "$D/vimrc" /root/.vimrc
ln -sf "$D/gitconfig" /root/.gitconfig
NRB=/volume1/hermes-data/node-runtime/v24.22.2/bin
for b in node npm npx; do [ -x "$NRB/$b" ] && ln -sf "$NRB/$b" "/usr/local/bin/$b"; done
echo "restore done — 新开 SSH 生效"
RSTEOF
chmod +x "$DF/restore.sh"
echo "✅ restore.sh (自愈脚本)"

sec "D. 验证"
echo "--- 模拟全新登录 (env -i, 无继承) ---"
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/root sh -l -c 'echo "PS1=$PS1"; echo "PATH=$PATH" | head -c 120; echo; alias' 2>&1 | head -12
echo "--- vimrc 冒烟 (vim 存在才跑) ---"
if command -v vim >/dev/null 2>&1; then
    timeout 30 vim -Nu "$DF/vimrc" -c 'echo "vimrc-ok" | quitall!' </dev/null >/dev/null 2>&1
    echo "vim 加载 vimrc 退出码: $? (0=干净)"
else
    echo "vim 不存在 — busybox vi 不读 .vimrc, 软链无害已就位 (装 vim 套件后自动生效)"
fi
echo "--- git 冒烟 ---"
git config --global --get alias.st 2>/dev/null && echo "gitconfig ✅" || echo "git 未装或配置未生效"

sec "S9 完成"
date '+结束: %F %T'
cp "$OUT" "$SRC/" 2>/dev/null && echo "已回传: $SRC/$(basename "$OUT")" || echo "[回传失败, 手动取 $OUT]"
