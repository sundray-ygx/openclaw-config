# ECS ⇄ NAS hermes 配置/数据同步机制审计报告

- 审计时间：2026-11-24 10:00–10:30（只读巡检，零变更）
- 审计人：小群（ECS 侧）
- 触发：Boss 要求核实"NAS 同步到 ECS 的 hermes 配置/数据是否真正合并进 ECS 运行实例，两台 hermes 是否共享 knowledge/skills/memory"
- 方法：crontab/cron.d 盘点 + 同步脚本逐行读解 + git 仓实证 + 软链可达性 + 资产差异量化 + WebDAV 只读列举

---

## 一、结论（一句话）

当前机制本质是 **"NAS hub 单向外发 skills + 多通道冷备"，不是双向合并**：

- **真正实现"两台 hermes 都有"的资产只有 skills，且为 NAS→ECS 单向、只到 default profile**；
- **knowledge 是两台完全独立的两套库，互不可见、互不流动**；
- **memory（hermes 内置记忆）两台各自独立，不跨机**；
- config/.env/SOUL/cron 等刻意不合并（机器特定，设计正确）。

---

## 二、四条同步/备份链路现状（全部今日实证）

### 链路 1：NAS → GitHub 私仓 → ECS（hermes-config，每日）

| 环节 | 时间 | 实证 |
|---|---|---|
| NAS push（hub） | 03:00 | 最新提交 `09a3f82f sync: 2026-11-24 03:00 (+6 ~21 -0)` |
| ECS A2 冷备 pull | 03:40 | → `/opt/backups/hermes-config`（686M 全量含 .git），日志"副本新鲜度 OK（0 天前）" |
| ECS 主同步 pull | 05:00 | → `/root/hermes-config`，`git reset --hard origin/main`；今晨技能"新增 0 / 更新 7 / 保护跳过 14"，飞书绿卡已发 |

- 仓：`git@github.com:sundray-ygx/hermes-config.git`
- 主同步脚本 `/root/scripts/hermes-sync/pull.sh`（97 行，已逐行读）：**全脚本唯一的"合并进运行实例"动作是 skills 传播**——
  - repo 有、本机无 → rsync 装入 `/root/.hermes/skills/`
  - 同名技能有差异 → `rsync -a --delete` 覆盖（hub 为准，ECS 本地改动被还原是设计行为）
  - `protected-skills.txt` 14 个官方技能 → 永不覆盖
  - NAS 删除技能不联动删 ECS
- **除此之外不传播任何其他资产**（没有 knowledge/memory/config 的 install 动作）

### 链路 2：ECS → GitHub（openclaw-config 仓，每日 23:30）

- `/root/.openclaw/workspace` 整仓 `git add -A` → commit → push master
- 最新提交 `d461fe7 Auto sync: 2026-11-23 23:30:01`
- 覆盖 ECS 侧 knowledge（11M / 230 个 md）+ scripts
- **未发现 NAS 侧 pull 此仓的任何链路** → ECS knowledge 不流向 NAS（仅有异地 GitHub 副本，NAS hermes 运行实例读不到）

### 链路 3：ECS → NAS WebDAV（每日 02:00，tar 冷备，v5.1）

- `nas_backup.sh` 打 11 项 tar（含 09-hermes-config、10-hermes-profile、11b /etc/cron.d+acme+ssh 等）→ `http://127.0.0.1:5005/aliyun_backup/server-backup/YYYYMMDD/`
- 今日实证：`server-backup/20261124/` 目录已存在（连续 20261113→20261124 无断日）
- 纯冷备，NAS 侧无任何自动解包/合并动作

### 链路 4：NAS → ECS WebDAV（周备）—— ⚠️ 发现缺口

- git-config-sync 技能记载（pitfall #11，2026-11-10 Boss 批方案 B）：NAS 每周日 04:00 `weekly-hermes-data-backup.py` 将六棵不可再生树（knowledge/projects/memory/scripts/cron-live/secrets，约 566MB gz）PUT 到 `/aliyun_backup/hermes-data-weekly/`，8 周滚动
- **今日实测该目录在 WebDAV 上不存在**。`/aliyun_backup/` 下仅有：`#recycle/`、`server-backup/`、`nas-recovery/`、`openclaw-security-hardening-guide.md`
- 可能性：①周备脚本 rootfs 灾后未重新挂载/未部署；②上传路径变更；③周日任务失败无告警
- ECS 无 SSH 到 NAS，无法直接核实 NAS cron 状态 → **列为决策点 D4，需 Boss 在 NAS 侧查证或授权写 exec 脚本经 nas-recovery/ 回传**

---

## 三、核心问题逐项回答：NAS 同步内容是否进入 ECS 运行实例？

ECS 运行实例根：`/root/.hermes/`；档案库根：`/root/hermes-config/`（NAS 仓工作树）。

| 资产 | repo（NAS 仓工作树）里的形态 | 是否合并进 ECS 运行实例 | 说明 |
|---|---|---|---|
| **skills** | `skills/` 实体目录，251 个 SKILL.md | ✅ **是，且是唯一真正合并项** | 05:00 传播到 `/root/.hermes/skills/`（345 个）。NAS 新增 ECS 当天可得；今晨实证更新 7 个。仅覆盖 default profile |
| **knowledge** | **死软链** `knowledge → /volume1/hermes-data/knowledge`（ECS 无 /volume1）；git 中自 2026-11-05 起只存软链 blob（120000），最后实体快照停在 `f2610b7e`（11-05） | ❌ **不合并且不可读** | ECS 运行实例 knowledge 软链 → 自有 `/root/.openclaw/workspace/knowledge`（11M/230md）。**两台是完全独立的两套知识库，零交集** |
| **memory（内置记忆 memories/）** | `memories/MEMORY.md` 5,574B（NAS 运行记忆，实体文件在 git 中） | ❌ **不合并** | pull.sh 无传播逻辑。ECS 运行实例 MEMORY.md 9,481B 独立演进；档案库副本只是躺着 |
| **memory/ 日志目录**（183+ 日期文件、projects.md、lessons.md） | 死软链 → `/volume1/hermes-data/memory` | ❌ 不可达 | NAS 11-10 软链硬化后，该目录内容仅存于 NAS 卷 + 周备 tar（而周备目录当前缺失，见链路 4） |
| **config.yaml** | 实体文件 17KB（NAS 运行配置，含明文密钥） | ❌ 不合并 | **设计正确**：机器特定配置，ECS 自用 904B 精简版（模型链经 api.ygxpro.online） |
| **.env** | 实体文件 1.5KB（在仓内，含密钥） | ❌ 不合并 | 设计正确 |
| **SOUL.md** | NAS 版 2.9KB | ❌ 不合并 | ECS 自用 ECS 版 1.8KB |
| **cron/** | 死软链 → `/volume1/hermes-data/cron-live` | ❌ | ECS hermes cron 独立（jobs.json） |
| **scripts/**、**projects/**、**tools/** | 均死软链 | ❌ | ECS 脚本走 openclaw workspace 体系（独立仓） |
| **sessions/state.db 等会话数据** | repo 有 sessions 实体目录 | ❌ | 从不传播，会话历史天然单机 |

### 反向（ECS → NAS）缺口量化

- skills：ECS 345 个 vs repo 251 个，路径级差异 94 个；**按技能名校准并扣除官方包后，ECS 自研技能孤岛 = 0**（94 个差异全部是同名技能的分类目录不同，如 `apple/*`、`creative/*` 官方包技能在 ECS 的摆放路径与 repo 不同）。即 skills 反向无真实内容缺口。
- knowledge：ECS 独有 230 个 md（openclaw-config 仓有 GitHub 异地副本，NAS hermes 不可见）。
- memory：ECS 独有记忆（本报告对话上下文依赖的 9.5KB MEMORY.md 等），NAS 无副本。

### profile 维度（额外发现）

| profile | 技能数 | 是否吃 05:00 传播 | memory |
|---|---|---|---|
| default（TUI/本会话） | 345 | ✅ 是（pull.sh 硬编码 `/root/.hermes/skills`） | 独立 9.5KB |
| scheduler（日程管家/推送） | **60（独立实体目录，非软链）** | ❌ **完全不吃传播** | 独立 2.9KB |

scheduler profile 自 10-22 后技能集冻结在捆绑清单（.bundled_manifest），NAS hub 后续新增/更新的技能它一个都收不到。这是已存在的配置漂移点。

---

## 四、数据流向示意

```
NAS hermes (hub)                         ECS hermes
/root/.hermes/                           /root/.hermes/
  skills/ ──03:00 push──► GitHub ──05:00──► skills/ (default) ✅ 单向合并
  knowledge(/volume1) ──push► [仅软链blob] ──✗ 死链，ECS读不到
  memories/MEMORY.md ──push► 实体躺档案库 ──✗ 不传播
  config/.env/SOUL ──push► 档案库 ──────── ✗ 刻意不合并（正确）
                                          knowledge ─► openclaw workspace
                                                          │23:30 push
                                                          ▼
                                                   GitHub openclaw-config（NAS不拉）
  NAS卷六棵树 ──周备tar──► WebDAV hermes-data-weekly/ ⚠️目录实测不存在
  WebDAV ◄──02:00 tar 冷备 11项──────── /root/.hermes + 系统配置（server-backup/今日健康）
```

---

## 五、风险点汇总

1. **knowledge 双机孤岛**：任一机器卷损坏，另一台的知识库完全不能顶替。ECS 侧有 GitHub 副本保底；NAS 侧当前只剩本机卷（周备缺失下）。
2. **NAS memory 日志目录（183+ 文件）异地副本疑似消失**：git 只存软链 blob，周备目录缺失 → 这些文件目前疑似只有 NAS 卷一份。
3. **scheduler profile 技能漂移**：60 个冻结技能，不接收任何同步。
4. 密钥仍随 hermes-config 私仓保存（config.yaml 17KB 含明文、.env 1.5KB 在仓）——私仓+SSH 钥控制，现状可接受但值得知晓。

---

## 六、决策点（等待 Boss 拍板，批准前不执行任何变更）

- **D1 knowledge 是否双机共享？**
  - A. 维持双库独立（现状）：零风险，但两台 hermes 知识不互通
  - B. 单 hub 化（推荐若要共享）：指定一边为 hub（建议 NAS，沿用现有 hub 模式），修复"软链不入 git"问题（staging 工作树或恢复实体目录入仓），ECS 侧 knowledge 改为拉取合并；需处理 ECS openclaw workspace 的仓冲突与归属
  - C. 仅冷备互通：两边都能只读访问对方的 tar/仓快照，不做运行时合并
- **D2 hermes memory 是否跨机？** 建议不做运行时合并（字符预算+机器特定）；可选"每周精选蒸馏"半自动对齐
- **D3 scheduler profile 是否接入技能传播？** 可让 05:00 脚本增加第二目标或改软链共享（注意 curator 写权限差异）
- **D4 NAS 周备缺口是否立即追查？** 需 Boss 在 NAS 侧查证 weekly cron，或授权 ECS 写 exec 诊断脚本经 `/aliyun_backup/nas-recovery/` 回传结果
