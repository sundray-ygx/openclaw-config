# openclaw 网关回切 + hermes 降级 v0.19.0 评估方案

> **⚠️ 方向调整（2026-10-29 11:0x，Boss 定版）**：不再实际切换到 openclaw 网关。
> 保持 hermes gateway 运行；0.19.0 独立安装后用**软链脚本**切换版本；
> openclaw 网关仅保留"随时可切"的能力（unit/插件已就绪，双向切换脚本见下）。
> 原 Phase 1/2 文本保留作能力文档。

- 日期：2026-10-29　评估人：小群（ECS hermes TUI）　状态：**待 Boss 决策，未执行任何变更**
- 关联：`ecs-openclaw-upgrade-assessment-20261029.md`（今晨 openclaw 已升 2026.10.8，CLI 验证通过）

## 一、只读核实结果

| # | 项目 | 核实值 | 影响 |
|---|------|--------|------|
| 1 | openclaw 飞书通道配置 | channels.feishu enabled，websocket，双账号：main=cli_a93b96…（小群）、scheduler=cli_a93c6b…（日程管家） | 配置完整保留 |
| 2 | feishu 插件状态 | ⚠️ `plugins doctor` 实测：**register 失败**——插件 built with 2026.9.5，运行核 2026.10.8，`json-store` 导出名不匹配。官方报错自带解法：`openclaw plugins update feishu` | Phase 1 必修步骤，风险低（官方插件更新，非手补丁） |
| 3 | 旧 lark 补丁插件 | openclaw-lark entry enabled:false，不加载 | 无影响（已被官方 feishu 插件替代） |
| 4 | systemd unit | 正式 unit 已删，但 **bak-env-20260923 完整保留**（含 MemoryMax=520M、NODE_OPTIONS、ExecStopPost 端口清理全套）；daily-restart timer 存在但 inactive | 重建 unit 有现成模板，仅路径需改 |
| 5 | 端口 18789 | 空闲 | 无冲突 |
| 6 | **飞书 app 归属** | ⚠️ **双网关完全重叠**：hermes default profile=cli_a93b96…（=openclaw main）、hermes scheduler profile=cli_a93c6b…（=openclaw scheduler） | openclaw 起网关前**必须先停 hermes-gateway**，否则同 app 两条 ws 抢消息 |
| 7 | hermes-gateway | systemd 服务 enabled+active，RSS ~600M（python 524M+UI） | 停止后内存净改善（openclaw 网关预计 400M+） |
| 8 | hermes 版本 | **0.21.0**，npm 全局装于 /usr/lib/node_modules/hermes-agent（4.1G，其中 runtime 4.0G） | 降级目标 0.19.0 存在（npm 已确认） |
| 9 | hermes-agent 包结构 | npm 包为**瘦客户端**（21KB）+ postinstall 下载 runtime | npm 安装内存压力小（非 openclaw 那种重构建），但网络下载 GB 级、磁盘 4G 级 |
| 10 | hermes 自动升级 | config/crontab 无自动升级项 | 降级后不会被自动翻回 |
| 11 | openclaw agents | main/scheduler/coding 三 agent，模型链完整（glm-5.3/glm-5.3-flash） | scheduler agent 原生承接日程管家收信 |
| 12 | 巡检脚本 | heartbeat_syscheck.sh 现盯 hermes-gateway（10-08 改的） | 回切当天必须改回盯 openclaw-gateway，否则每小时误告警 |
| 13 | state DB | 10-29 备份新鲜（68M） | doctor 前进迁移有回滚底 |

## 二、可行性结论

**Phase 1（openclaw 网关回切）：可行，风险中等偏低。**
- 阻塞项只有 feishu 插件版本匹配，且官方给了明确修复命令；
- unit 模板、config、state、备份全部就位；
- 最大风险延续既往教训：channels running ≠ 消息能收发，必须 Boss 实测飞书闭环；
- 内存面：停 hermes-gateway（-600M）再起 openclaw（+400M+），净改善；MemoryMax=520M 沿用，10.x 内存胃口若变大按 skill 健康诊断流程调。

**Phase 2（hermes 降级 0.21.0→0.19.0）：技术上可行，但有三个必须知悉的风险。**
- **R1 自噬风险**：本次评估会话本身跑在 hermes 0.21.0 上。降级替换 /usr/lib/node_modules/hermes-agent 时，本 TUI 会话的运行时文件被抽走，会话可能中途失联。缓解：postinstall 用 nohup 后台跑 + 由 Boss 在 openclaw TUI 或 SSH 收尾验证。
- **R2 格式回读风险**：0.20/0.21 可能对 config/skills/memories 做过前进迁移，0.19 读新格式有兼容风险（降级比升级危险，schema 只进不退是常态）。缓解：降级前备份 /root/.hermes（排除 cache/audio）；出问题回滚 0.21.0。
- **R3 磁盘**：10G 可用；旧 4.1G 用同盘 mv 保留（零额外空间），新 runtime 下载约 4G → 剩 ~6G。若紧张，可在 0.19 验证稳定后删旧包（但失去秒级回滚）。
- 顺带确认：hermes-gateway unit 的 ExecStop 路径硬编码 runtime venv python，降级后 unit 兼容性需复核（若 0.19 runtime 结构不同需微调 unit）。

## 三、执行方案

### Phase 1：openclaw 网关回切（完整验证链 + doctor，约 20-30 分钟）

```
1. plugins update feishu     # 修 register 失败，然后 plugins doctor 复检至 0 error
2. 重建 systemd unit         # 以 bak-env-20260923 为模板，改三处：
                             #   ExecStart → Node 24.22.2 + global/v11/c45a5-.../openclaw.mjs
                             #   PATH → /root/.local/share/pnpm/bin:$PNPM_HOME:Node24.22.2:...
                             #   其余（MemoryMax=520M/Restart/NODE_OPTIONS=384M）沿用
3. systemctl stop hermes-gateway && systemctl disable hermes-gateway
                             # 先断飞书 ws 再起 openclaw，避免同 app 抢消息
                             # 注意：本 hermes TUI 会话是独立进程，不受影响继续可用
4. systemctl start openclaw-gateway
5. 轮询 http://127.0.0.1:18789/health 到 200（10.x 冷启动 30s~数分钟，端口在听≠能应答）
6. OPENCLAW_SERVICE_REPAIR_POLICY=external openclaw doctor --fix   # state DB 前进迁移
7. openclaw channels status  # 期待 feishu: enabled/configured/running（唯一真值）
8. Boss 实测：飞书给小群 bot 发一条消息，收到回复才算闭环
9. heartbeat_syscheck.sh 改回盯 openclaw-gateway（PATH 注意绝对路径 /usr/sbin/ss）
10. 观察内存 10 分钟（diagnostics/memory 日志 + RSS），MemoryMax 需要则调 drop-in
```

Phase 1 回滚：`systemctl stop openclaw-gateway && systemctl start hermes-gateway`，5 分钟内可回。

### Phase 2（修订 v2，2026-10-29 Boss 定版）：双版本并存 + 软链切换（参照 NAS Strategy B）

**设计**（适配 ECS npm 形态）：
```
/usr/lib/node_modules/
├── hermes-agent-0.21.0/     # 现役 4.1G 真身（mv 改名，同盘零成本，包内含独立 runtime）
├── hermes-agent-0.19.0/     # 新装旁路版本（staging 安装后 mv 进来，含独立 runtime ~4G）
└── hermes-agent -> hermes-agent-0.21.0   # 软链（相对路径）；切换=改指向，秒级
/usr/bin/hermes -> ../lib/node_modules/hermes-agent/bin/hermes.js  # 不动，穿软链解析
```
- 优势1：hermes-gateway systemd unit 的路径全部是无版本的 `/usr/lib/node_modules/hermes-agent/...`，穿软链解析——**切换版本无需改 unit**（NAS 教训里 unit 四处路径要同步的坑天然规避）；
- 优势2：回滚 = `ln -sfn hermes-agent-0.21.0 …`，10 秒级；
- 优势3：后续想试 0.21.7（registry 有 0.21.1-0.21.7，若含 TUI 乱码修复）再加一个旁路目录即可。

**步骤**：
```
1. 备份共享状态（0.19 读 0.21 写过的 config/memories 有格式回读风险）：
   tar czf /root/hermes-state-backup-pre-downgrade-20261029.tgz -C /root \
     .hermes/config.yaml .hermes/.env .hermes/profiles .hermes/memories .hermes/cron
2. 旁路安装（不碰现役软链，对运行中系统零影响，可由我在本会话安全执行）：
   mkdir -p /root/hermes-staging && cd /root/hermes-staging
   npm install --prefix /root/hermes-staging hermes-agent@0.19.0
   # 瘦包 21KB；postinstall 会 git sparse-clone 上游 v0.19.0 源码 + uv venv + 装依赖
   # 全程落在 staging/node_modules/hermes-agent/ 内（postinstall 有包内路径护栏）
   # 耗时预估 5-15 分钟（网络下载 ~GB 级）
3. 验证 staging 版本真身（NAS 教训：hermes --version 会说谎，直接问 venv）：
   /root/hermes-staging/node_modules/hermes-agent/runtime/hermes-agent/venv/bin/python \
     -c "from hermes_cli import __version__; print(__version__)"   # 期待 0.19.0
4. 就位 + 建软链结构（此刻起才影响系统，按 Boss 定版在 openclaw TUI/SSH 执行）：
   mv /root/hermes-staging/node_modules/hermes-agent /usr/lib/node_modules/hermes-agent-0.19.0
   mv /usr/lib/node_modules/hermes-agent /usr/lib/node_modules/hermes-agent-0.21.0
   ln -s hermes-agent-0.21.0 /usr/lib/node_modules/hermes-agent    # 先指旧版，确认链路无损
   hermes --version   # 仍应 0.21.0，TUI 正常
5. 切换到 0.19：
   ln -sfn hermes-agent-0.19.0 /usr/lib/node_modules/hermes-agent
   /usr/lib/node_modules/hermes-agent/runtime/hermes-agent/venv/bin/python \
     -c "from hermes_cli import __version__; print(__version__)"   # 0.19.0
   hermes --version   # 新进程生效；正在跑的旧 TUI 会话（含本会话）不受影响直到重启
6. Boss 重开 hermes TUI 验证乱码是否消失（这是降级动机的最终验收标准）
```
**回滚**：`ln -sfn hermes-agent-0.21.0 /usr/lib/node_modules/hermes-agent` + 必要时恢复状态备份 tar。hermes-gateway 保持 stop+disable（Boss 已确认 ⑤），unit 无需改动即可兼容两版本。

**磁盘账**：+~3.5-4G（0.19.0 旁路包），操作后 / 预计 ~82%（剩 ~6G）。/root/.hermes/tools 内工具按版本命名（node-26.7.0/python-3.14.7 等），两版本 pin 相同则复用不重复占盘。staging 目录（/root/hermes-staging）用完即删。

**遗留注意**：日后若跑 `npm install -g hermes-agent@x` 会无视软链结构直接写穿/覆盖——升级一律走"旁路安装+改指向"流程（写入本方案与 skill）。

## 六、执行记录（2026-10-29 进行中）

| # | 步骤 | 结果 |
|---|------|------|
| 1 | feishu 插件修复 | ✅ `plugins update feishu` 2026.9.5→2026.10.8，doctor 插件层全过 |
| 2 | systemd unit 重建 | ✅ /etc/systemd/system/openclaw-gateway.service（Node 24.22.2 + global/v11 路径） |
| 3 | 巡检脚本改造 | ✅ heartbeat_syscheck.sh：双网关任一 active 即健康 + openclaw RSS 段（阈值500M） |
| 4 | hermes 状态备份 | ✅ 主 tar 11M + profiles 二次快照（网关运行中写入，二次快照 exit 0） |
| 5 | 0.19.0 旁路安装 | 🔄 重跑中 |

**执行中发现（重要）：**
1. **hermes TUI 会话 = hermes-gateway 的客户端**：停网关会杀死本会话的工具执行；且 Boss 向本会话发消息时 TUI 会自动经 systemd 拉起网关（10:42:56 实测）。⇒ 切换脚本必须 systemd-run 脱离进程树派发，且派发后本会话下线，收尾由 Boss 走 SSH/openclaw。
2. **现役 hermes 实际版本是 0.22.4**（npm 壳 0.21.0，runtime venv 被 PyPI 侧自动升级过）——降级实际跨度 0.22.4→0.19.0，比方案评估时更大；也证实存在 runtime 自动升级机制（找到后需评估是否关闭，否则 0.19 会被再升回去）。
3. **npm postinstall 会继承会话的 HERMES_\* 环境变量**：第一次安装把 0.19.0 pip 定向到在跑的运行环境（`/root/.hermes/installs/...`），幸好目标 venv 无 pip 未写成。⇒ 旁路安装必须 `env -i` 干净环境跑（教训记入 skill）。
4. 切换脚本：`/root/scripts/utils/cutover-start-openclaw.sh`（停 hermes → 起 openclaw → 轮询 health → doctor --fix → channels status，失败自动回滚 hermes），日志 `/var/log/openclaw-cutover-20261029.log`。

## 七、方向调整后的最终架构（2026-10-29 定版，v2 机制定稿）

**主网关 = hermes-gateway（全程运行未重启，现役 v0.22.4+54）。三套能力就位：**

| 能力 | 入口 | 说明 |
|------|------|------|
| hermes 版本切换 | `/root/scripts/utils/hermes-version-switch.sh [0.19.0\|0.22.4]` | 切换点 = `/usr/bin/hermes` 软链 + gateway unit 的 venv 路径 sed（NAS 原版做法）；只影响新进程，gateway/TUI 重启后生效；venv python 直读真身版本 |
| 切到 openclaw 网关（应急） | `systemd-run --unit=oc-cutover /root/scripts/utils/cutover-start-openclaw.sh` | 必须 systemd-run 脱离会话进程树（hermes TUI 是网关客户端，会连坐）；失败自动回滚 hermes |
| 切回 hermes 网关 | `systemd-run --unit=oc-back /root/scripts/utils/cutover-back-to-hermes.sh` | 与上互逆 |

**最终目录布局（教训修正版——不动现役目录！）**：
```
/usr/lib/node_modules/
├── hermes-agent/            # 现役 0.22.4+54（git/npm 形态，保持原名不动）
│                            #   ⚠️ pm 按 install 路径哈希登记依赖环境(/root/.hermes/installs/<hash>/facts.json)
│                            #   改名/软链化此目录会触发 NoCommittedEnvironment→repair 死循环，禁止
└── hermes-agent-0.19.0/     # NAS 形态独立版：runtime/hermes-agent/venv(uv venv py3.11 + PyPI hermes-agent[feishu]==0.19.0)
                             #   + bin/hermes.js(sh shim → venv python -m hermes_cli.main)
切换态 A(0.22.4 现状): /usr/bin/hermes → ../lib/node_modules/hermes-agent/bin/hermes.js；unit → …/hermes-agent/runtime/…/venv
切换态 B(0.19.0):     /usr/bin/hermes → …/hermes-agent-0.19.0/bin/hermes.js；unit 三处 venv 路径 sed 为 0.19 目录
```

**路线试错记录（重要教训，均已回滚归零）**：
1. npm wrapper 装 0.19.0：薄壳形态（要求系统 Python≥3.11 + pip），失败×2；且第一次继承了会话 HERMES_* 环境变量险些把 0.19 pip 进在跑环境。→ 旁路安装必须 `env -i`。
2. 现役目录改名+软链化（v1 机制）：pm 环境登记按路径哈希失效 → CLI 全部陷入 `hermes pm repair` 循环；repair 用 `uv sync --frozen` 直连 PyPI 极慢，20 分钟未完成；期间误写的 facts.json（指向旧 key 环境）触发"outside this install"硬错误，**一度卡死本会话全部进程派生型工具**（terminal/execute_code 均挂，靠进程内 write_file 写空登记自救）。→ 教训：pm 的 facts.json 千万别手写；现役目录改名前必须先评估 pm 登记。
3. 最终方案：现役目录原地不动；0.19 走独立 venv；切换点外移到 /usr/bin/hermes + unit（NAS 原版）。

**磁盘账**：0.19.0 目录 ~430M（uv 硬链共享缓存）；半成品 install 已清（回收 482M）；/ 76%（可用 9G）。

---

## 八、最终执行情况与待办（2026-10-29 收口，v3 全量盘点）

### A. 已完成且实测验证 ✅
| 项 | 验证深度 |
|---|---|
| openclaw 2026.10.8 升级（Node 24.22.2 + pnpm 12 + wrapper + PATH） | CLI 三项验证过（version/config validate/agents list）；wrapper 与登录 shell PATH 实测 |
| hermes 0.19.0 独立安装（uv venv py3.11 + hermes-agent[feishu] 0.19.0） | venv 真身版本 + shim CLI 冒烟（--version 完整输出）均过 |
| hermes 现役 0.22.4+54 | 全程未动未重启；CLI/网关/facts 登记复核健康（含迟到 repair 进程清理核查，无残留） |
| 版本切换脚本 hermes-version-switch.sh | 语法过、状态读取逻辑手工等价验证过；**但未执行过一次真实切换**（真切换是首个待校验项） |
| 巡检脚本 heartbeat_syscheck.sh | 双网关兼容逻辑 + openclaw RSS 段就位（bash -n 过；效果要到下次整点巡检才见） |
| 备份 | openclaw state 68M（10-29）+ hermes 状态 11M×2 |
| 归档 | 本文档 + memory + agent-gateway-cutover skill 教训同步完成 |

### B. 已就绪但"未实弹"⚠️（能力在，未真跑过）
| 项 | 未验证内容 | 实弹代价 |
|---|---|---|
| openclaw 网关应急切换 | doctor --fix（state DB 迁移）、channels status、飞书真实收发——全部未跑过 | 飞书收发中断 2-5 分钟；hermes TUI 会话（本会话）下线，Boss 需 SSH/openclaw 收尾 |
| hermes 0.19.0 TUI | 乱码是否消失（降级动机的最终验收标准） | 需切换 + 重开 TUI，随时可做、可秒回滚 |
| 0.19.0 完整功能 | 仅验证了 --version；TUI/工具链/cron 等在 0.22.4 数据（config/memories 格式回读）下是否正常未测 | 同上，切过去即测 |

### C. 待 Boss 校验/决策 ⏸
1. **【校验】0.19.0 TUI 乱码**：`/root/scripts/utils/hermes-version-switch.sh 0.19.0` → 退出本 TUI 重开 → 看乱码是否消失。不满意 `… 0.22.4` 秒回。
2. **【决策】gateway 是否也降到 0.19**：默认留 0.22.4（重启 gateway 才会吃到软链指向的版本）。若切 0.19 后重启 gateway，注意 0.19 读 0.22.4 写过的 config/memories 有格式回读风险（备份已备）。
3. **【决策】openclaw 应急切换是否实弹演练**：不演练=能力纸面就绪（真出事时第一次跑）；演练=一次真实切换+飞书实测闭环+切回。建议择低峰做一次。
4. **【决策】磁盘清理**：旧 pnpm store v10/global5（~1G）+ openclaw 2026.9.5 旧包（246M）——建议 0.19/2026.10.8 各自稳定 1-2 周后清。
5. **【观察】runtime 自动升级机制**：现役 0.21.0 壳→venv 0.22.4 说明有自动升级路径（未定位）。0.19 独立 venv 不归 pm 管、理论不会被自动升级，但 gateway 若长期跑 0.19 需留意。暂不处理，出问题再查。
6. **【观察】heartbeat_syscheck 下次整点巡检**确认无误报（尤其切换/重启后的过渡态）。

## 五、决策记录（2026-10-29 Boss 已定版）

1. ~~Phase 2 执行者~~ → **openclaw TUI/SSH 执行**（步骤 4-5 的系统级变更）；步骤 1-3（备份+旁路安装）零影响，由我在本会话执行。
2. ~~降级动机~~ → **TUI 交互乱码影响正常使用**。备注：registry 有 0.21.1-0.21.7，若 0.19 仍有问题或想回升，软链机制下随时加旁路版本。
3. ~~双版本处置~~ → **软链并存方案（NAS Strategy B 适配版）**，见 Phase 2 修订 v2。
4. ~~daily-restart timer~~ → 观察期保持 inactive。
5. ~~hermes-gateway~~ → stop + disable 确认。

**剩余待确认（执行前最后一问）**：Phase 1 全链（含飞书实测闭环）+ Phase 2 步骤 1-3 我现在就跑，跑到"0.19.0 就位待切换"为止；步骤 4-5 切换命令你在 openclaw TUI/SSH 执行（命令我会打印好）。是否按此开工？

## 五、影响面清单

| 影响对象 | 影响 |
|---------|------|
| 飞书收发（小群+日程管家） | 切换窗口内中断 ~2-5 分钟；切回 openclaw 后由其双账号承接 |
| 本 hermes TUI 会话 | Phase 1 不受影响；Phase 2 npm 替换期间可能失联（nohup 兜底） |
| root crontab 14 条业务 | 零影响（均不依赖两网关运行时） |
| 内存 | 净改善：hermes-gateway -600M，openclaw-gateway +400M 级 |
| 磁盘 | Phase 2 后 ~6G 可用（旧包 mv 保留期间） |
| ECS→NAS 同步链路（05:00 pull） | 不受影响（脚本独立于网关） |
