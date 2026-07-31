# 知识库同步规则与 ECS 侧对齐指南

> **目的**：确保阿里云 ECS（OpenClaw）与 NAS（Hermes）的知识库目录结构一致，为重新开放 `knowledge/` 增量同步做准备。
> **生成时间**：2026-06-03
> **适用对象**：ECS 上的 OpenClaw 执行整理 + NAS 侧 Hermes 参照校验

---

## 一、背景

### 1.1 问题根因

2026-06-02 重建阿里云同步脚本后，首次运行从旧备份恢复了 **86 个已删除的 knowledge 文件**（包括 CLASSIFICATION-GUIDE.md、work/ai-native/、work/okr/ 等旧目录），导致 NAS 侧 Hermes 知识库被污染。

**临时措施**：已从 `sync-aliyun-backup.sh` 中排除 `knowledge/` 同步（只保留 `memory/`）。

**最终目标**：ECS 侧按 NAS 最新规则整理后，重新开放 `knowledge/` 增量同步。

### 1.2 历史整理动作摘要

| 时间 | 动作 | 结果 |
|------|------|------|
| 2026-05-17 ~ 05-20 | 知识库 MECE 全面重构（P0-P2） | 542→284 文件，目录结构重定义 |
| 2026-06-01 | P3 审核完成 + Hermes 根目录清理 | 28→21 目录，scripts 65→15 文件 |
| 2026-06-02 | 同步脚本恢复问题诊断 + 修复 | 去掉 knowledge 同步，清理恢复的 86 个文件 |

---

## 二、知识库标准目录结构（NAS 侧当前状态）

### 2.1 一级目录定义（共 11 个，MECE，禁止新建）

| 目录 | 定义 | 包含 | 不包含 |
|------|------|------|--------|
| **work/** | 工作业务 | OKR、周计划、AI-Native、IPD、质量运营、协同、敏捷 | 纯技术方案 |
| **life/** | 个人生活 | 财务管理、租金账单、个人项目 | 工作事务、技术文档 |
| **projects/** | 跨领域项目 | Console 数字中心、账单迁移 | 通用工作文档 |
| **tech/** | 纯技术知识 | 平台、基础设施、前端、数据管道、cospowers | 工作业务文档 |
| **security/** | 安全领域 | 审计、扫描、加固、配置检查 | 非安全类技术 |
| **productivity/** | 效率/个人 | 个人简历、周计划方法、个人财务 | 租房账单（→life/） |
| **reflection/** | 反思方法论 | 日复盘归档、改进方法论 | 具体技术/工作内容 |
| **lessons/** | 跨领域教训 | 提炼后的通用经验 | 某领域专属知识 |
| **people/** | 人物信息 | 联系人、关系网络 | 其他一切 |
| **inbox/** | 待分类缓冲区 | 应尽快清空（当前仅 .gitkeep） | 长期存放的文件 |
| **archive/** | 历史归档 | 不再活跃的知识、实验残留、旧配置 | 需要日常访问的内容 |

### 2.2 完整目录树（NAS 侧实际状态）

以下是 NAS 侧 `knowledge/` 的完整目录树，ECS 侧应对齐到此结构：

```
knowledge/
├── README.md                          # 唯一目录定义文档
│
├── work/                              💼 工作业务知识
│   ├── AI-Native/
│   │   ├── okr/                           AI-Native 专项 OKR/里程碑
│   │   ├── team-plans/                    各团队落地执行计划
│   │   ├── sxf-week-report/               双周报
│   │   ├── 研讨会/
│   │   │   ├── 第二次研讨会/
│   │   │   └── 落地推进研讨会/
│   │   │       └── 各产线预填模板内容/
│   │   └── 培训课件/                       独立培训 PPT（含 output/）
│   ├── OKR/
│   │   ├── design/                        OKR 方法论/设计迭代（v1-v6）
│   │   ├── data/                          各产线 OKR 原始数据（xlsx）
│   │   └── org/                           组织架构相关
│   ├── IPD/
│   │   ├── 全景表/                         IPD 全景表拆解（含 阶段/ 子目录）
│   │   ├── 项目管理/                       01_项目计划/ 02_风险管理/ 03_项目汇总/
│   │   ├── 模板/                           原始 xlsx/docx 模板
│   │   └── 参考资料/                       流程图等
│   ├── collaboration/                     跨团队协同问题汇总
│   ├── quality/                           质量运营会议纪要（含 April/）
│   ├── agile/                             敏捷实践/组织能力建设
│   ├── bp/                                BP 战略规划（各产线 OKR xlsx）
│   ├── plans/                             工作计划
│   ├── weekly-plans/                       周计划
│   ├── develop-resumes/                    校招候选人材料（pdf）
│   ├── training/                           新员工培训（含 output/）
│   ├── sxf-week-report/                    顶层双周报（与 AI-Native/sxf-week-report 部分重复）
│   ├── archive/                            过期工作文档（含 daily-reports/）
│   └── README.md
│
├── life/                              🏠 个人生活
│   ├── finance/
│   │   ├── rent/                           租金账单（13B402 收租 + 16A503 缴租）
│   │   │   ├── data/                           月度账单 JSON
│   │   │   └── reports/                        月度/季度/年度报告
│   │   └── libs/                           echarts.min.js 等前端库
│   └── projects/
│       └── sam-daigou/                     山姆代购项目（含 _archive/）
│
├── projects/                          📁 跨领域项目知识库
│   ├── console/
│   │   ├── 01-research/
│   │   ├── 02-requirements/
│   │   ├── 03-design/
│   │   └── 04-implementation/
│   └── bill-migration/
│
├── tech/                              🔧 技术知识
│   ├── hermes/
│   │   ├── migration/                      迁移/升级报告
│   │   ├── vaultwarden/                    Vaultwarden 部署全系列
│   │   ├── webui/                          Console/WebUI 设计报告
│   │   └── *.md                            平台零散技术文档
│   ├── infrastructure/
│   │   ├── backup/
│   │   ├── setup/
│   │   └── singbox/
│   ├── frontend/                           前端技术方案（含 _archive/, json/, png/）
│   ├── data-pipeline/
│   │   └── health/                         健康数据采集（含 ios-shortcut/, openclaw/, scripts/）
│   ├── cospowers/
│   │   ├── architecture/                      架构分析（11篇）
│   │   ├── getting-started/                    入门指南（8篇）
│   │   └── hermes-adaptation/                  Hermes 适配方案（5篇）
│   ├── openhuman/                          OpenHuman 部署文档
│   ├── industry-analysis/                  行业分析
│   ├── openclaw/                           OpenClaw 遗留技术文档
│   ├── product-requirement-management/     需求管理报告
│   └── README.md
│
├── security/                          🔒 安全知识
│   ├── audits/                             安全审计报告
│   ├── config-checks/                      配置安全检查
│   ├── hardening/                          安全加固指南
│   └── scans/                              敏感数据扫描
│
├── productivity/                      📈 效率提升/个人事务
│   ├── personal/
│   │   ├── finance/                            个人财务记录（含 libs/）
│   │   └── resume/                             个人简历（含 _archive/）
│   └── weekly-planning/                    周计划方法论（含 SKILL.md）
│
├── reflection/                        🟠 反思与方法论
│   ├── daily/                              每日反思归档（历史，已归档到 archive/）
│   └── methodology/                        反思方法论与改进指南
│
├── lessons/                           📝 经验教训（跨领域通用教训）
│   └── YYYY-MM-DD-title.md
│
├── people/                            👤 人物信息
│   └── README.md
│
├── inbox/                             📥 待分类缓冲区（应尽快清空）
│   └── .gitkeep
│
└── archive/                           📦 全局归档
    ├── inbox-history/                      OpenClaw 每日知识 dump + 日复盘归档
    ├── openclaw-config/                    OpenClaw 遗留配置文档（9个）
    ├── openclaw-multi-agents-experiment/   OpenClaw 多代理实验残留
    ├── security-old/                       旧安全巡检报告
    └── CLASSIFICATION-GUIDE-OLD.md        旧版分类指南（已废弃）
```

---

## 三、文件存放规则

### 3.1 决策树（新文件归位规则）

```
新文件产生
│
├─ 不确定放哪？→ 按下方规则判断后直接归位（禁止放 inbox 暂存）
│
├─ 跟公司/团队业务相关？
│  ├─ AI-Native 专项？
│  │  ├─ OKR/里程碑？→ work/AI-Native/okr/
│  │  ├─ 团队落地计划？→ work/AI-Native/team-plans/
│  │  ├─ 研讨会材料？→ work/AI-Native/研讨会/{研讨会名}/
│  │  ├─ 双周报？→ work/AI-Native/sxf-week-report/
│  │  └─ 培训课件？→ work/AI-Native/培训课件/
│  ├─ OKR 方法论/数据？
│  │  ├─ 设计迭代？→ work/OKR/design/
│  │  ├─ 原始 xlsx？→ work/OKR/data/
│  │  └─ 组织架构？→ work/OKR/org/
│  ├─ IPD 流程？→ work/IPD/（按子目录分）
│  ├─ 跨团队协同？→ work/collaboration/
│  ├─ 质量运营？→ work/quality/
│  ├─ 敏捷/组织能力？→ work/agile/
│  ├─ 周计划？→ work/weekly-plans/
│  ├─ 校招候选人？→ work/develop-resumes/
│  ├─ 新员工培训？→ work/training/
│  └─ 通用工作文档？→ work/ 或对应子目录
│
├─ 个人生活？
│  ├─ 租金账单？→ life/finance/rent/
│  └─ 个人副业项目？→ life/projects/{项目名}/
│
├─ 跨领域项目？→ projects/{项目名}/
│
├─ 纯技术知识？
│  ├─ 安全相关？→ security/（按类型选子目录）
│  ├─ Hermes 平台？
│  │  ├─ 迁移/升级？→ tech/hermes/migration/
│  │  ├─ Vaultwarden？→ tech/hermes/vaultwarden/
│  │  ├─ WebUI/Console？→ tech/hermes/webui/
│  │  └─ 其他平台文档？→ tech/hermes/
│  ├─ cospowers 相关？→ tech/cospowers/
│  ├─ 基础设施？→ tech/infrastructure/
│  ├─ 前端技术？→ tech/frontend/
│  ├─ 行业分析？→ tech/industry-analysis/
│  └─ 其他技术？→ tech/ 对应子目录
│
├─ 个人事务/效率方法论？→ productivity/
│  ├─ 个人简历？→ productivity/personal/resume/
│  ├─ 个人财务？→ productivity/personal/finance/
│  └─ 周计划方法？→ productivity/weekly-planning/
│
├─ 反思/方法论？→ reflection/methodology/
├─ 跨领域经验教训？→ lessons/
├─ 人物信息？→ people/
└─ 过期/历史？→ archive/
```

### 3.2 命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 日期类文档 | `YYYY-MM-DD-title.md` | `2026-05-09-ssh-hardening.md` |
| 人物文档 | `person-name.md` | `zhang-san.md` |
| 项目文档 | `README.md` 或 `YYYY-MM-DD-title.md` | `README.md` |
| 说明文档 | `topic-name.md` | `frp-config.md` |
| Office 文档 | 保持原名 | `信锐研发体系ORK.docx` |

### 3.3 维护红线

1. **禁止创建新的一级目录**（当前 11 个已 MECE）
2. **禁止 inbox 暂存模式**（新文件按决策树直接归位）
3. **新二级/三级目录需 Boss 审批**（防止目录膨胀）
4. **README.md 为唯一目录定义文档**（CLASSIFICATION-GUIDE.md 已废弃并删除）
5. 定期检查过期文件归档
6. 保持命名规范一致

---

## 四、ECS 侧执行指令

### 4.1 第一步：按规则整理 ECS 侧知识库

OpenClaw 应按照上述目录树和决策树，将 ECS 侧 `knowledge/` 目录重新整理：

1. 读取本文档中的标准目录树
2. 扫描 ECS 侧 `knowledge/` 当前所有文件和目录
3. 将每个文件按决策树规则归位到正确目录
4. 将不属于任何标准目录的文件归类或标记待处理
5. 删除根目录下的 `CLASSIFICATION-GUIDE.md`（已废弃，与 README.md 冲突）

### 4.2 第二步：生成差异清单

整理完成后，扫描 ECS 侧与 NAS 侧的差异，输出以下两类清单：

#### 清单 A：ECS 侧有但 NAS 侧没有的文件/目录

> 这些文件可能是 ECS 侧新增的，需要决策是否同步到 NAS。

格式：
```
| 序号 | 路径 | 类型（文件/目录） | 建议 |
|------|------|-------------------|------|
| 1 | work/new-feature-plan.md | 文件 | 新增，建议同步至 NAS |
```

#### 清单 B：NAS 侧有但 ECS 侧没有的文件/目录

> 这些文件 NAS 侧已整理好但 ECS 还没同步到，属于 ECS 侧缺失。

格式：
```
| 序号 | 路径 | 类型 | 说明 |
|------|------|------|------|
| 1 | work/agile/ | 目录 | NAS 新增目录，ECS 应创建 |
```

### 4.3 第三步：清理 ECS 侧冗余/已废弃内容

以下目录/文件在 NAS 侧已被删除，ECS 侧应**标记但先不删除**，等 Boss 决策：

```
# 已废弃，NAS 侧已删除的目录/文件
CLASSIFICATION-GUIDE.md              # 与 README.md 冲突
work/ai-native/                      # 已合并为 work/AI-Native/
work/okr/                            # 已合并为 work/OKR/
work/ipd/                            # 已合并为 work/IPD/
work/agile/others/                   # 已清理
tech/ai-native/                      # 已归入 work/AI-Native/
tech/industry/                       # 已合并为 tech/industry-analysis/
tech/dev-tools/                      # 已清理
security/audit-reports/              # 已合并为 security/audits/
security/optimization/               # 已清理
security/archive/                    # 已归入 archive/security-old/
inbox/ 中非 .gitkeep 的所有文件       # dreaming dump 已清理
```

### 4.4 第四步：验证对齐

执行以下检查确认对齐完成：

1. ECS 侧一级目录数量 = 11 个（与 NAS 侧一致）
2. 一级目录名称完全匹配
3. 无 `CLASSIFICATION-GUIDE.md` 散落文件
4. `inbox/` 目录中无超过 7 天的暂存文件
5. 所有文件都能在决策树中找到归属

---

## 五、同步策略

### 5.1 当前状态

- **NAS 侧同步脚本**：`/root/.hermes/scripts/backup/sync-aliyun-backup.sh`
- **当前策略**：仅同步 `memory/`，`knowledge/` 已排除
- **触发方式**：`/etc/cron.d/sync-aliyun-backup`，每天 03:00

### 5.2 重新开放同步的前提条件

1. ✅ ECS 侧知识库已按本文档规则整理完毕
2. ✅ 差异清单已输出，Boss 已决策哪些同步、哪些删除
3. ✅ ECS 侧冗余内容已清理（或标记忽略）
4. ⬜ 修改 `sync-aliyun-backup.sh`，恢复 `knowledge/` 增量同步
5. ⬜ 同步策略调整：**只增不覆盖**（保留 NAS 版本优先）

### 5.3 建议的同步策略

| 维度 | 策略 | 说明 |
|------|------|------|
| 新增文件 | ECS→NAS 单向同步 | ECS 侧新增的文件自动同步到 NAS |
| 已存在文件 | **不覆盖** | NAS 侧版本优先，避免旧文件覆盖新整理 |
| 已删除文件 | **不同步删除** | NAS 侧已删除的文件，ECS 侧不要同步回来 |
| 目录结构 | 以 NAS README.md 为准 | ECS 侧目录必须对齐 NAS 标准 |

---

## 六、附录

### A. NAS 侧完整文件清单（共 ~280 个文件）

> 以 `find /root/.hermes/knowledge/ -type f | sort` 输出为准。
> 完整清单见 NAS 侧实际文件系统，此处不逐一列出。

### B. 关键历史记录

| 日期 | 会话 | 关键动作 |
|------|------|----------|
| 2026-05-17~20 | 知识库 MECE 重构 | P0-P2 全面重构，定义 11 个一级目录 |
| 2026-06-01 | P3 审核完成 | IPD 合并、hermes/config 归档、清理 CLASSIFICATION-GUIDE |
| 2026-06-01 | Hermes 根目录清理 | 28→21 目录，scripts 65→15 文件 |
| 2026-06-02 | 同步脚本修复 | 重建 sync-aliyun-backup.sh，去掉 knowledge/ 同步 |
| 2026-06-02 | 恢复文件清理 | 删除阿里云同步恢复的 86 个已删文件 |

### C. 相关文件路径

| 文件 | 路径 | 说明 |
|------|------|------|
| 知识库 README | `/root/.hermes/knowledge/README.md` | 唯一目录定义文档 |
| 同步脚本 | `/root/.hermes/scripts/backup/sync-aliyun-backup.sh` | 阿里云增量同步 |
| 本文档 | `/root/.hermes/knowledge/tech/hermes/knowledge-sync-rules.md` | 即本文件 |

---

_本文档由 NAS 侧 Hermes（小群）生成，供 ECS 侧 OpenClaw 执行对齐操作。_
_整理完成后，需 Boss 审核差异清单并决策，方可重新开放 knowledge/ 增量同步。_
