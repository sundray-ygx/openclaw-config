# ============================================================
# NAS shell 环境主副本 — volume1 (抗 DSM 升级)  2026-11-02
# 消费者: /etc/profile 与 /root/.profile 双薄指针 source
# 兼容: BusyBox ash + bash (纯 POSIX, 无 bashism)
# ============================================================

# ---- PATH: node 运行时双保险 (软链丢了也能用) ----
_hm_nrb=/volume1/hermes-data/node-runtime/v24.22.2/bin
if [ -d "$_hm_nrb" ]; then
    case ":$PATH:" in
        *":$_hm_nrb:"*) ;;
        *) PATH="$_hm_nrb:$PATH"; export PATH ;;
    esac
fi
unset _hm_nrb

# ---- 交互 shell: 别名 + 提示符 ----
case "$-" in *i*)
    # 安全别名 (ECS 同款)
    alias rm='rm -i'
    alias cp='cp -i'
    alias mv='mv -i'

    # ls 颜色: 运行时探测 busybox 是否编译了 --color
    if ls --color=auto / >/dev/null 2>&1; then
        alias ls='ls --color=auto'
        alias ll='ls -l --color=auto'
        alias la='ls -la --color=auto'
    else
        alias ll='ls -l'
        alias la='ls -la'
    fi

    # grep 颜色: 同样探测
    if echo x | grep --color=auto x >/dev/null 2>&1; then
        alias grep='grep --color=auto'
    fi

    # 提示符: ash 安全版 (无 \[ \] 转义, 避免行宽计算 bug)
    PS1='\u@\h:\w\$ '
    export PS1
    ;;
esac

# ---- 环境 ----
export EDITOR=vim
export HISTSIZE=5000
export HISTFILESIZE=10000
export PAGER=less 2>/dev/null || true
