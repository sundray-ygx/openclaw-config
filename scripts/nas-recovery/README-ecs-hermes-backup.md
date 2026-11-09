# ECS 侧 hermes-config 备份部署指引（A2 · 2026-11-05 定版）

## 背景
NAS 每日 03:00 自动 push `/volume1/hermes-config` → GitHub 私仓 `sundray-ygx/hermes-config`（含 secret 扫描闸门）。
A2 目标：ECS 增加**只读拉取副本**，形成「NAS rootfs → NAS /volume1 快照 → GitHub → ECS」四层备份。

## ECS 一次性部署（3 步）

### ① 配置 GitHub 只读 deploy key
```bash
ssh-keygen -t ed25519 -f ~/.ssh/gh_deploy_nas -N "" -C "ecs-pull-hermes-config"
cat ~/.ssh/gh_deploy_nas.pub
# → GitHub 私仓 Settings → Deploy keys → Add（勾选 Read-only）
cat >> ~/.ssh/config <<'EOF'
Host github.com-nasrepo
    HostName github.com
    User git
    IdentityFile ~/.ssh/gh_deploy_nas
    IdentitiesOnly yes
EOF
```

### ② 取脚本并执行
本目录（阿里云盘同步）下：
```bash
bash /path/to/aliyun_backup/nas-recovery/ecs-setup-hermes-backup.sh
```
脚本幂等：克隆仓库到 `/opt/backups/hermes-config`、注册 `/etc/cron.d/hermes-config-pull`（每日 03:40）。

### ③ 验证
```bash
tail /var/log/hermes-config-pull.log
ls /opt/backups/hermes-config/config/   # 应见 config.yaml SOUL.md 等
```

## 注意事项
- deploy key 若用 SSH 直连格式（`git@github.com:...`），脚本默认地址可用；若走 config 别名，把脚本里 `REPO_SSH` 改为 `git@github.com-nasrepo:sundray-ygx/hermes-config.git`
- **只读 key**：ECS 端永远只 pull 不 push，零覆盖 NAS 风险
- 3 天无新提交脚本会 exit 2 打 🟡（NAS 侧推送断链预警）
- `state.db`（会话历史，649MB 二进制）**不在备份范围**——命脉是 config/skills/memory/knowledge，已在 git；state.db 由 NAS 本地 btrfs 只读快照（每 6 小时）兜底

## 灾难恢复总入口（NAS 全丢场景）
见同目录 `nas-restore-hermes.sh`（NAS 每日自动刷新，优先通道：GitHub clone → 本地冷备 clone）
