# ECS OpenClaw 升级评估方案（2026.9.5 → 2026.10.8）

- 日期：2026-10-29　评估人：小群（ECS hermes）　状态：**待 Boss 决策，未执行任何变更**
- 依据：openclaw-maintenance skill（2026-09-11 升级实战）+ 本日全只读核实

## 一、只读核实结果（现状 vs 记忆/交接差异表）

| # | 项目 | 核实值 | 与记忆/预期差异 |
|---|------|--------|----------------|
| 1 | 当前版本 | **2026.9.5** (ec9c1a1) | 记忆记为 2026.9.3，实际已到 9.5（wrapper 同步指向 9.5，正常） |
| 2 | 最新稳定版 | **2026.10.8**（2026-10-27 发布，昨天） | 9.x 维护线末版 = 2026.9.35（10-27 同日发布） |
| 3 | **gateway 服务** | **systemd unit 文件已不存在，无任何 openclaw 进程** | ⚠️ 重大：ECS openclaw 网关已退役（2026-10-08 切换至 hermes-gateway），当前 openclaw 只是"安装态"，无运行态业务 |
| 4 | cron 承接 | openclaw state 库剩 10 个 cron 定义，最后执行记录停在 **2026-10-08**；业务 cron（GitHub同步 23:30 / GLM检查 09:30）已按方案A迁入 root crontab 并正常运行 | 无孤儿 cron；库内条目为死数据，不随升级复活 |
| 5 | lark 插件 | /root/.openclaw/plugins/ 已空（仅 migrated 标记），插件残留仅在 workspace/extensions | ✅ 好消息：上次升级最痛的 lark 补丁问题**本次不存在**（无 gateway 加载它） |
| 6 | 内存 | total 1870M，used 1345M，available 525M + swap 3852M 空闲 | 无 gateway 进程（省 ~400M RSS），比上次升级时更宽裕 |
| 7 | 磁盘 | / 69%，可用 12G | 新包 250M + Node ~120M，充裕 |
| 8 | **Node 版本卡点** | 本机 v24.21.0；**2026.9.35 与 2026.10.8 均要求 node >=24.22.1 <25 或 >=26.12.1** | ⚠️ 硬卡点：无论升到哪个新版，**必须先升 Node 到 v24.22.2**（24.x 线最新，满足 <25） |

## 二、可行性结论

**可行，且风险显著低于 2026-09-11 那次**。理由：
1. 网关已退役 → 无停机窗口、无消息中断、无 lark 插件运行时断裂问题；
2. pnpm 路线已验证（npm 在本机必 OOM 的教训），且现在无 gateway 抢内存，安装期内存压力更小；
3. 磁盘余量充足。

剩余风险（均为可控）：
- **R1 Node 升级**（新增步骤）：nvm 装 v24.22.2 ≈ 二进制解压，内存/磁盘影响极小；风险点是 wrapper 与其它引用 v24.21.0 路径的地方需同步（本机仅 /usr/bin/openclaw wrapper 引用）。
- **R2 Config Guard**：新版 CLI/gateway 若读 openclaw.json 报 invalid（Unrecognized key），按 skill 迁移模式处理（env→.env、删过时 key）。当前仅 CLI 使用，触发面小。
- **R3 State DB 前进迁移**：若升级后启动 gateway/doctor，schema 迁移**不可逆**——升级前必须备份 state/，否则无法回滚到 2026.9.5。
- **R4 回滚路径**：pnpm 旧版本目录保留（2026.9.5 现占 246M 不删）+ wrapper 指回 + Node 24.21.0 目录保留，三层都可退。

## 三、升级方案（分步，全程 hermes 会话内执行，符合"不在 openclaw 自身会话升级"规矩）

**阶段 0：备份（5 分钟）**
```bash
mkdir -p /root/.openclaw/backup-pre-upgrade-20261029
cd /root/.openclaw && tar czf backup-pre-upgrade-20261029/state-cron-agents.tgz \
  openclaw.json agents/ cron/ state/ credentials/ identity/ devices/
```

**阶段 1：升 Node 24.21.0 → 24.22.2（nvm，~2 分钟）**
```bash
export NVM_DIR=/root/.nvm && . $NVM_DIR/nvm.sh
nvm install 24.22.2 && nvm alias default 24.22.2
/root/.nvm/versions/node/v24.22.2/bin/node --version
```

**阶段 2：pnpm 安装新版 openclaw（沿用既定路线，~1 分钟）**
```bash
export PNPM_HOME=/root/.local/share/pnpm; export PATH=$PNPM_HOME:$PATH
export PATH=/root/.nvm/versions/node/v24.22.2/bin:$PATH   # 新 node 下跑 pnpm
corepack enable pnpm
pnpm add -g openclaw@2026.10.8 --dangerously-allow-all-builds
```
验证：`timeout 15 openclaw --version`（务必 timeout 包裹）+ 前台干跑 `node <新包路径>/openclaw.mjs --help`。

**阶段 3：更新 /usr/bin/openclaw wrapper（指向新 Node + 新包路径）**
```bash
mv /usr/bin/openclaw /usr/bin/openclaw.old-2026.9.5.bak
cat > /usr/bin/openclaw <<'EOF'
#!/bin/sh
exec /root/.nvm/versions/node/v24.22.2/bin/node /root/.local/share/pnpm/global/5/.pnpm/openclaw@2026.10.8/node_modules/openclaw/openclaw.mjs "$@"
EOF
chmod 755 /usr/bin/openclaw && openclaw --version
```

**阶段 4：验证（按当前用途裁剪）**
- CLI 层：`openclaw --version`、`timeout 30 openclaw config validate`（看 Config Guard 是否拦截）
- ⏸ gateway 层验证默认**跳过**（网关已退役）——见决策点 2

**回滚预案（任一步失败）**
```bash
mv /usr/bin/openclaw.old-2026.9.5.bak /usr/bin/openclaw
cd /root/.openclaw && tar xzf backup-pre-upgrade-20261029/state-cron-agents.tgz
# Node 不用退：24.22.2 对旧版 openclaw 亦兼容（engines 为 >= 下限型约束）
```

## 四、决策点（需 Boss 拍板）

1. **目标版本**：
   - A（建议）：**2026.10.8** —— 最新稳定版，跨大版本 9→10，变更面大但当前无运行态业务兜底风险，一次到位；
   - B：2026.9.35 —— 9.x 维护末版，变更最小，但一个月后还得再升。
2. **gateway 层验证**：网关已退役，升级后默认只验 CLI。若你计划恢复 openclaw 网关（双网关/回切），需追加完整验证链（unit 重建→启动→doctor --fix→channels status），周期 +30~60 分钟且触发 DB 不可逆迁移。
3. **执行时机**：随时可做（无运行态业务），全程约 15 分钟；建议避开 23:30 GitHub 同步 / 09:30 GLM 检查（虽然它们不依赖 openclaw，纯保守）。

## 五、执行影响面清单

（略，见上方）

---

## 六、执行记录（2026-10-29 10:00-10:20，Boss 已批准 A 方案）

**结果：✅ 升级成功，2026.9.5 → 2026.10.8 (dc2523e)，CLI 验证全通过，零业务影响。**

| 阶段 | 结果 | 备注 |
|------|------|------|
| 0 备份 | ✅ 68M/590条 | backup-pre-upgrade-20261029/state-cron-agents.tgz |
| 1 Node | ✅ v24.22.2（nvm，checksum 过） | default 别名已切，v24.21.0 保留 |
| 2 pnpm 安装 | ✅ 1m40s | corepack 拉了 **pnpm 12.16.1**（非旧版 10.x），见下方坑 |
| 3 wrapper | ✅ /usr/bin/openclaw 新脚本 | 指向 global/v11/c45a5-.../node_modules/openclaw/openclaw.mjs |
| 4 验证 | ✅ version/config validate/agents list 全过 | gateway 层按决策跳过 |

**执行中踩的新坑（pnpm 12 变化，均已解决）：**
1. `ERR_PNPM_GLOBAL_BIN_DIR_NOT_IN_PATH`：pnpm 12 全局 shim 移到 `$PNPM_HOME/bin`，PATH 需加该目录（.bashrc 已更新）。
2. 构建脚本默认忽略（"Ignored build scripts: koffi/esbuild/openclaw/..."）：`--dangerously-allow-all-builds` 在 pnpm 12 无效。解法：`pnpm approve-builds -g --all -y`（非交互批准）→ openclaw postinstall（bundled-plugins）执行成功。koffi 实为预编译 optional 依赖（@koromix/koffi-linux-x64 带 .node），不需要构建。
3. `$PNPM_HOME/openclaw` 旧 shim（指向 2026.9.5）残留，登录 shell PATH 优先命中旧版——已软链到新 `$PNPM_HOME/bin/openclaw`（pnpm 12 shim 自带符号链接解析，9.x 时代的 dirname 坑已修复）。

**磁盘增量**：+2.1G（pnpm store v11 全新内容寻址 1.2G + global v11 309M + Node 208M + corepack 63M），/ 74%（可用 10G）。旧 store v10/global 5 留作回滚，观察期后可清。

**回滚资产（全部就位）**：
- `/usr/bin/openclaw.old-2026.9.5.bak`（旧 wrapper）
- `/root/.local/share/pnpm/global/5/.pnpm/openclaw@2026.9.5`（旧包）
- `/root/.nvm/versions/node/v24.21.0`（旧 Node）
- `/root/.openclaw/backup-pre-upgrade-20261029/`（config+state+cron 备份）
