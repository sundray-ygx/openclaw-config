# NAS Shell 环境（dotfiles）恢复方案 — S9

日期：2026-11-02 · 状态：**待 Boss 决策** · 前置：S8 已完成（node 移植成功，profile.d 踩空）

## 一、事故定位（推理链）

1. DSM 升级清空 rootfs 用户层：`/root`（dotfiles 全灭）+ `/etc/profile` 个性化段被重置为出厂
2. 证据链：S8 实测 `/etc/profile.d` 目录不存在；`ash-4.4#` 提示符证明 root 登录 shell 是 **BusyBox ash**（非 bash）
3. 关键推论：ECS 的 `.bashrc` **直接拷过去不会生效**——ash 登录 shell 只读 `/etc/profile` + `~/.profile`，两者 DSM 还会在下次升级再清一次
4. vim 情况未知：DSM 出厂仅 busybox vi；NAS 是否装过 vim 套件待探测（决定 .vimrc 是否有用武之地）

## 二、ECS 侧盘点（供体资产）

| 文件 | 内容 | 可移植性 |
|------|------|----------|
| `.bashrc` | rm/cp/mv -i 别名 + 密钥导出段 + ECS 专属段（nvm/pnpm/acme/singbox） | 别名✅；密钥段❌（见 D1）；ECS 专属段❌ |
| `.vimrc` (167行) | 行号/语法高亮/darkblue 配色/cscope 映射/F5-F7/增量搜索/回跳上次位置 | ✅ 忠实拷（见 D3） |
| `.gitconfig` | OpenClaw Bot 身份 + ghproxy insteadOf | ⚠️ 身份是 ECS 机器人（见 D2） |
| `.inputrc` `.tmux.conf` `.profile` `.bash_aliases` | 不存在 | — |
| `/etc/profile` `/etc/bashrc` | 无个性化（PS1 是发行版默认） | 仅参考 |

密钥段明细（**不入库不外传**）：OPENAI_API_KEY/BASE_URL、FEISHU_APP_ID/SECRET/USER_ID、NOTION_API_KEY/两个 DB ID——NAS 的 `/root/.hermes/.env` 已在 S2 恢复这些值，无需经 shell 导出。

## 三、架构：volume1 主副本 + rootfs 薄指针（抗下次升级）

```
/volume1/hermes-data/dotfiles/          ← 主副本，DSM 升级不碰 volume1
├── profile-master.sh   # POSIX 兼容（ash+bash 双读）：别名/PATH/EDITOR/HISTSIZE/PS1
├── vimrc               # ECS .vimrc 忠实拷贝
└── gitconfig           # 见 D2

/etc/profile   += 一行: . /volume1/hermes-data/dotfiles/profile-master.sh   # 薄指针
/root/.profile  = 同样 source master + 仅交互 shell 生效段                  # ash 真正读的文件
/root/.vimrc    -> 软链 -> /volume1/hermes-data/dotfiles/vimrc
/usr/local/bin/{node,npm,npx} -> 软链 -> node-runtime（S8b 收尾一并做，见 D4）
```

下次 DSM 升级后的恢复 = 重跑一个自愈脚本（写好放 dotfiles/restore.sh，重做 4 个软链/薄指针即全量还原）。

## 四、S9 脚本设计（单脚本三段式，NAS 上跑一次）

- **A 段 探测（只读）**：`$SHELL`、bash/vim 是否存在、busybox ls/grep 是否支持 --color、TERM/tput colors、现存 /etc/profile 尾部
- **B 段 落地（按探测结果自适应）**：建主副本→写薄指针→node 软链（D4 批准则做）
- **C 段 验证**：`env -i PATH=/usr/bin:/bin sh -lc 'alias ls; echo $PS1'` 模拟全新登录；vim 存在则 `vim -Nu /volume1/hermes-data/dotfiles/vimrc -c q` 冒烟；输出回传 WebDAV
- 主机守卫（enjoysynology）、变更面仅限上述路径、ECS 上验证器全套照旧

已知边界（如实声明）：若 busybox ls 不支持 --color，ls 变色在纯 ash 下无法实现（DSM 无 GNU coreutils），届时给出 Entware/opkg 装核心工具的选项，不强做。

## 五、决策点

- **D1 密钥段**：不带（推荐，.hermes/.env 已有全部值）/ 带进 profile-master
- **D2 .gitconfig**：NAS 身份用什么？A=ECS 原样(OpenClaw Bot) B=最小化仅 [core]+常用alias，name/email 留空由你后续填 C=你给指定值
- **D3 .vimrc**：忠实全拷（推荐，失效插件行静默无害）/ 裁剪成 30 行核心
- **D4 S8b node 软链**：一并做（推荐，同属 shell 环境，S8 遗留收尾）/ 不做

## 六、回滚

所有变更均可逆：删 4 个软链/薄指针 + master 目录即回到当前状态；/etc/profile 追加段独立成块可整段摘除。不触碰 DSM 系统文件本体。
