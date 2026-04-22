# 项目追踪

## 日报机制优化
**状态**: ✅ 完成
**时间**: 2026-03-24 ~ 2026-03-25
**描述**: 修复日报生成脚本，支持多目录扫描、飞书IM集成、记忆文件直接写入

**关键改进**:
- 数据源：从单一scheduler目录扩展到scheduler+main多目录扫描
- 飞书集成：通过chat_id缓存获取飞书IM单聊消息
- 输出模式：同时输出到archive/daily/（详细版）和memory/（摘要版）

**相关文件**:
- `/root/.openclaw/workspace/scripts/daily/daily_report.py`
- `/root/.openclaw/workspace/memory/reflections.md`

---

## OpenClaw用户迁移
**状态**: ⏸️ 暂停（权限问题）
**时间**: 2026-03-24
**描述**: 将OpenClaw从root用户迁移到openclaw用户运行，提高安全性

**进展**:
- ✅ 阶段一：准备完成（创建用户、复制数据）
- ❌ 阶段二：切换失败（PAM限制crontab访问）
- ⏸️ 阶段三：启动未执行

**阻塞问题**:
- openclaw用户无crontab权限（PAM限制）
- 需要root权限或修改PAM配置

---

## OKR优化项目
**状态**: ✅ 完成
**时间**: 2026-03-25 ~ 2026-03-26
**描述**: 综合管理部OKR文档优化，生成V2版本

**交付物**:
- `knowledge/work/2026-03-25-okr-smart-v2.md`
- 调整O1（去掉KR2和KR5，修改KR1）
- 弱化O2构建设计描述，聚焦业务价值

**待跟进**: Boss审阅后是否进一步调整

---

## 校招新员工 AI-Coding 培训
**状态**: ✅ 完成
**时间**: 2026-04-09 ~ 2026-04-11
**描述**: 为校招新员工（软件开发、软件测试、前端开发、硬件研发）制定 AI-Coding 培训课题方案

**交付物**:
- `docs/plans/2026-04-10-campus-hiring-ai-coding-training-final.md`
- 归档至 `knowledge/work/AI-Native/campus-hiring-ai-coding-training.md`
- 课题设计：通用类为主，不涉及公司产品业务，纯软件可完成
- 覆盖 4 个岗位：软件开发、软件测试、前端开发、硬件研发

**关键决策**:
- 课题难度需适合校招新人
- 不需要额外硬件器件
- 重点体验 AI-Coding 实践过程

---

## 综合管理部 AI-Native 落地计划更新
**状态**: ✅ 完成
**时间**: 2026-04-10 ~ 2026-04-13
**描述**: 更新综合管理部及各团队 AI-Native 落地计划，生成对齐报告

**关键更新**:
- 补充测试中心职责：测试自动化平台、DFX 平台等中台能力
- 更新会议主机团队落地计划（第四版）
- 生成综合管理部 AI-Native 落地计划-对齐报告-V1.2.md
- 更新各团队 AI-Native OKR 汇总文档

**交付物**:
- `knowledge/work/AI-Native/综合管理部AI-Native落地计划-对齐报告-V1.2.md`
- `knowledge/work/AI-Native/各团队AI-Native-OKR-汇总.md`

---

## 技术问题修复
**状态**: ✅ 完成
**时间**: 2026-03-26
**描述**: 修复skillhub CLI Python 3.6兼容性问题

**问题**: `required=True`参数在Python 3.6中不支持
**修复**: 修改为兼容Python 3.6的写法

**相关文件**:
- `/root/.skillhub/skills_store_cli.py`

---

## 定时任务优化
**状态**: ✅ 完成
**时间**: 2026-03-25 ~ 2026-04-05（持续优化）
**描述**: 优化定时任务的稳定性与资源使用

**调整记录**:
- 3/25: 反思从4:00调到9:00，日报8:30生成，归档改isolated模式
- 4/1: 禁用daily-runtime-monitor（连续8次超时），反思超时60→180s，月反思120→300s
- 4/3: 清理6个废弃cron任务（重复/路径错误/已停用）
- 4/5: 排查NAS备份cron"重复触发"问题 → 确认为百炼API配额耗尽

**待决策**:
- NAS备份cron model是否切换到zai/glm-5
- 百炼账户是否需要充值

---

## 记忆维护
**状态**: ✅ 完成
**时间**: 2026-04-08
**描述**: 执行记忆维护，更新 heartbeat-state.json

**执行内容**:
- 更新 lastMemoryMaintenance 为 2026-04-08
- 更新 projects.md 添加 4/8 定时任务调整记录
- 更新 lessons.md 添加记忆维护过期教训

---

## 项目管理端到端流程优化
**状态**: ⏳ 进行中
**时间**: 2026-04-13 ~
**描述**: 采用AI方式推进项目管理端到端流程优化，梳理完整流程框架

**任务目标**:
1. 梳理决策链、权责定义
2. 定义各阶段准入准出规则（含交付物、交付标准）
3. 以当前项目为试点串联流程（按试点项目当前阶段）
4. 确保决策链、权责定义及准入准出标准清晰，流程可落地执行
5. 不断迭代优化流程
6. 考虑产品质量运营在端到端流程优化中的闭环
7. 提供基础信息和试点项目信息

**关键提醒**:
- 明天 9:00 需要提供基础信息和试点项目信息

**待跟进**: Boss提供基础信息和试点项目信息后，开始执行流程梳理

---

## 定时任务优化方案 C（第二阶段）
**状态**: ✅ 完成
**时间**: 2026-04-14
**描述**: 执行方案 C 折中优化，精简定时任务数量

**删除任务（6 个）**:
1. NAS 备份通知-main（合并到备份任务）
2. 周计划制定提醒-OpenClaw（周复盘已覆盖）
3. 日计划生成（delivery:none，不交付）
4. claude-budget-reminder（连续 3 次失败）
5. 月反思报告（连续 4 次失败，超时问题）
6. 月度 inbox 整理提醒（改为手动触发）

**清理文件（11 个）**:
- scripts/daily/daily_report.py.backup
- scripts/daily/daily_report_v9.py
- scripts/daily/daily_reflection_v2.py
- scripts/briefing/morning_briefing_*.py (4 个)
- 其他冗余脚本 (4 个)

**效果**:
- 任务数量：16 个 → 10 个（减少 37.5%）
- 预期 token 节省：35-45%
- 失败任务清零

**备份文件**: `archive/cron-backup-20260414-092400.json`

**待跟进**:
- [ ] 观察 3 天运行效果
- [ ] 记录实际 token 节省情况

---

## OpenSpec 插件安装
**状态**: ✅ 完成
**时间**: 2026-04-19
**描述**: 安装 OpenSpec 插件，用于 Spec-Driven Development

**关键内容**:
- 安全审计通过，风险评分 0/100（无风险）
- 文件类型：纯文档（SKILL.md）
- 位置：`~/.openclaw/workspace/skills/openspec/`

---

## AI Native 平台度量实战考试
**状态**: 🔄 进行中
**时间**: 2026-04-19 ~
**描述**: 8小时内完成 AI Native 度量平台 1:1 全流程复刻（需求分析→架构设计→编码实现→测试验证→发布）

**核心要求**:
- 功能、UI布局与交互逻辑需与原平台一致（无需在意配色）
- 采用 Spec-Driven Development + Claude Code 分阶段提示词驱动
- 架构：前后端分离，后端 Python/FastAPI + ES，前端 React/Vue

**已完成工作**:
1. **环境配置**（4/19-4/20）
   - Python 3.6.8 + Selenium 3.141.0 + Chromium
   - 创建前端页面结构自动提取工具（extract_structure.py）
   - 解决 Win10 内网环境部署问题（代理、Chromium 安装、ChromeDriver 版本匹配）

2. **页面结构提取**（4/20）
   - 主页面（/metrics）提取成功：20行数据，5个筛选字段
   - 识别技术栈：Vue + Element Plus
   - 识别为单页应用（SPA），Tab切换非标准路由
   - 提取 API 调用信息（通过 CDP Network 拦截）

3. **文档创建**（4/19-4/20）
   - development-plan.md：SDD 开发方案
   - frontend-replication-guide.md：前端页面 1:1 复刻完全指南
   - frontend-automation-setup.md：前端自动化提取工具部署指南
   - frontend-replication-alternatives.md：6 种复刻方案对比

**遇到的问题**:
- Unicode编码错误：脚本包含emoji字符，Win10 PowerShell执行失败
- Selenium环境复杂性：ChromeDriver版本不匹配、网络超时、CDP Network 域启用失败
- 跨域问题：前端页面打不开数据，后端API通（待排查）
- 考试方技术限制：评估是否可能限制F12抓包和API拦截

**待跟进**:
- [ ] 解决前端跨域问题
- [ ] 完成后端 API 开发
- [ ] 完成前端页面开发
- [ ] 测试验证
