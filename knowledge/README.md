# Knowledge 知识库

按 MECE 原则分类，确保每个文件都有明确归属。

## 一级目录（共 11 个，禁止新建）

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

## 文件归档决策树

新文件产生时，按以下规则直接归位（禁止放 inbox 暂存）：

```
新文件产生
│
├─ 不确定放哪？→ 按下方规则判断后直接归位
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

## 维护红线

1. **禁止创建新的一级目录**（当前 11 个已 MECE）
2. **禁止 inbox 暂存模式**（新文件按决策树直接归位）
3. **新二级/三级目录需审批**（防止目录膨胀）
4. 定期检查过期文件归档
5. 保持命名规范一致

## 命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 日期类文档 | `YYYY-MM-DD-title.md` | `2026-05-09-ssh-hardening.md` |
| 人物文档 | `person-name.md` | `zhang-san.md` |
| 项目文档 | `README.md` 或 `YYYY-MM-DD-title.md` | `README.md` |
| 说明文档 | `topic-name.md` | `frp-config.md` |
| Office 文档 | 保持原名 | `信锐研发体系ORK.docx` |