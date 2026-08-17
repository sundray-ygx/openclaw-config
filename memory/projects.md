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
- ~~NAS备份cron model是否切换到zai/glm-5~~（已切换 zai/glm-5）
- ~~百炼账户是否需要充值~~ → 2026-08-13 确认：火山引擎账户欠费（AccountOverdueError 403），summarize 已加 deepseek 自动切换，无需充值

---

## 业务系统巡检与修复
**状态**: ✅ 修复完成（2 个 P0）
**时间**: 2026-08-13
**描述**: 深度巡检全部自动化业务，发现并修复 2 个静默故障

**发现的问题**:
- 🔴 GitHub 每日同步实际失效 12 天（8 月零提交），cron 显示 ok 但 systemEvent 只是投递、agent 未执行 → 改 isolated agentTurn + 失败告警
- 🔴 早间简报 AI 摘要失败 108 天（cron PATH 不含 /usr/local/bin + 火山引擎欠费）→ 绝对路径 + summarize 双 provider 切换
- 🟡 journald 日志 3.0G（磁盘 72%）→ 清理至 160M + SystemMaxUse=200M 限制 + logrotate
- 🟡 heartbeat 维护停滞 13 天（state 停在 7/31）→ 已补跑，需观察是否恢复

**文件变更**:
- `/usr/local/bin/summarize`、`/root/scripts/briefing/morning_briefing.py`
- `/root/.openclaw/workspace/scripts/sync-to-github.sh`
- `/etc/systemd/journald.conf`、`/etc/logrotate.d/openclaw-tasks`
- OpenClaw cron `5965cd2f`（isolated 模式）

**报告**: `archive/reports/2026-08-13-业务巡检报告.md`

**遗留**：
- [ ] 观察 GitHub 同步今晚 23:30 自动执行
- [ ] 观察 heartbeat 维护是否恢复
- [ ] 早间简报明日 08:00 验证 AI 摘要恢复

---

## OpenClaw 服务器迁移
**状态**: ✅ 完成
**时间**: 2026-04-22
**描述**: 将 OpenClaw 从源服务器迁移到 NAS 服务器（47.119.177.194）

**关键成果**:
- ✅ 合并 memory（57个文件）、skills（22个）、scripts、knowledge
- ✅ 更新 openclaw.json 配置（模型 zai/glm-4.7 + 13个fallback，heartbeat 60分钟）
- ✅ 创建 `/etc/cron.d/openclaw-tasks`（7条不重复任务）
- ✅ 保留 NAS 的「小群」身份
- ✅ 飞书配置独立，不迁移
- ✅ 备份和迁移包生成

**文件变更**:
- `/root/.openclaw/workspace/` - 已合并所有数据
- `/etc/cron.d/openclaw-tasks` - 新建

**相关文件**:
- `/tmp/openclaw-backup-20260422.tar.gz` - 目标备份
- `/tmp/openclaw-migration-20260422.tar.gz` - 迁移包

---

## 每日反思机制重构
**状态**: ✅ 完成
**时间**: 2026-04-24
**描述**: 从 V2 模板匹配升级到 V3 AI 深度反思

**V2 的三个致命问题**:
1. **输入源错误** - 从错误日志里提取「教训」，结果把文件路径、脚本内容都当反思素材
2. **根因分析是模板** - 关键词匹配返回固定文案，technical 类永远是「技术实现缺乏容错设计」
3. **解决方案也是模板** - 永远是「增加异常处理逻辑，加强监控告警」这类万金油

**V3 改进**:
- 将当日工作内容交给 AI 做真正的反思
- 提取具体场景、数据、影响
- 增加关联经验，提炼可复用的方法论
- 结构化呈现：数据概览、做得好的、需改进、关联经验

**文件变更**:
- `/root/.openclaw/workspace/scripts/daily/daily_reflection.py`

---

## 周复盘机制重构
**状态**: ✅ 完成
**时间**: 2026-04-24
**描述**: 从 V2 关键词匹配升级到 V3 AI 深度分析

**V2 的问题**:
1. **「成果」提取靠关键词匹配** - 包含「完成、跟进、整理」就是成果
2. **「优化建议」全是 fallback** - 「持续监控定时任务执行状态」这类万金油
3. **「下周重点」照搬上周计划** - 没有分析和判断
4. **不对比上周** - 每周都是独立的，看不出趋势

**V3 改进**:
- AI 深度分析，生成更深刻的见解
- 对比上周复盘，识别趋势
- 优化建议具体可执行
- 下周重点基于实际情况制定

**文件变更**:
- `/root/.openclaw/workspace/skills/weekly-review/weekly_review.py`

---

## 工作日报修复
**状态**: ✅ 完成
**时间**: 2026-04-25
**描述**: 修复工作日报重复推送问题

**问题**:
- `daily_report.py` 中 `get_feishu_messages` 函数定义了两次（第194行和第278行）
- `openclaw.json` 中 `memory-core.config` 配置不合规（嵌套了 `dreaming.enabled`）

**修复**:
- 删除重复的函数定义
- 修复配置文件警告

**文件变更**:
- `/root/.openclaw/workspace/scripts/daily/daily_report.py`

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

## 租房账单管理
**状态**: 🔄 进行中
**时间**: 2026-04-25 ~
**描述**: 管理 13B402 和 16A503 的租房账单和支出

**已完成工作**:
- ✅ 13B402 账单录入（水费¥48.06、电费¥104.07、燃气费¥88.66，合计¥240.79）
- ✅ 生成 13B402 2026年4月账单通知（按用户格式）
- ✅ 创建 16A503 租房支出提醒任务（每月27日14:00）
- ✅ 录入 5月房租及4月水电燃气费（总计6320.16元）

**待跟进**:
- [ ] 创建标准化账单模板配置文件
- [ ] 新增租房账单记录定时任务（待用户决策后执行）
- [ ] 定期统计周期账单

**文件变更**:
- `/root/.openclaw/workspace/knowledge/rent/13b402-2026-04.json`
- `/root/.openclaw/workspace/knowledge/finance/支出记录.md`

---

## AI-Native 落地推进研讨会准备
**状态**: ✅ 完成
**时间**: 2026-04-27
**描述**: 组织各产线 AI-Native 落地情况研讨会，对齐落地障碍，推动落地进展

**关键成果**:
- ✅ 生成完整方案文档（精简版+完整版）
- ✅ 创建 18 页 PPT（包含演讲者备注和会议引导提示）
- ✅ 准备会前填写模板和沟通话术
- ✅ 产线覆盖：无线、交换机、NMC、会议主机、IPSIP
- ✅ 采用 PGSAR 闭环框架

**会议信息**:
- 时间：2026-04-27 19:00 - 21:30
- 时长：2.5 小时
- 目标：对齐落地障碍，推动落地进展，更新里程碑计划

**文件变更**:
- `knowledge/work/AI-Native/AI-Native落地推进研讨会-方案V1.0.md`
- `knowledge/work/AI-Native/AI-Native落地推进研讨会-开场共识引导.pptx`

---

## 周复盘字段格式优化
**状态**: ✅ 完成
**时间**: 2026-04-28
**描述**: 优化 Notion 周复盘字段格式，提升可读性

**改动**:
- 将「周复盘」字段从长文本改为结构化摘要
- 关键成果限制 3 条（移除✅前缀，改为•）
- 教训合并技术+工作，限制3条，用🔴🟡🟢标识级别
- 下周重点限制 3 条
- 移除优化建议部分（在子页面中保留）
- 详细内容通过子页面链接展开

**文件变更**:
- `/root/.openclaw/workspace/skills/weekly-review/weekly_review.py`

---

## 周复盘数据提取修复
**状态**: ✅ 完成
**时间**: 2026-04-28
**描述**: 修复字段映射+优化提取逻辑，重新生成第17周复盘

**根因**:
- 脚本读取 `今日复盘`+`今日反思`，实际 Notion 字段是 `今日复盘&反思`（合并字段）

**改动**:
- 新增 `_split_review_reflection` 方法，兼容合并字段和独立字段
- `generate_summary` 改为只从复盘内容提取，避免与安排重复
- 教训提取改为严格匹配末尾未完成标记（`—未完成`、`—未完结`），避免误判
- 模糊去重（前15字符），减少重复条目

**验证**:
- ✅ 20项成果、2条工作教训
- ✅ Notion+飞书+归档全部成功

**文件变更**:
- `/root/.openclaw/workspace/skills/weekly-review/weekly_review.py`

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

---

## 🖥️ OpenClaw 环境维护（2026-08-13 ~ 08-14）

### GLM/智谱 provider 全链路切换（08-14 完成）
- **新 key**: c2078ce9***（旧 key 33838b1c*** 已 401 失效），key 存于 main agent sqlite auth_profile_store（zai:default）
- **主配置**: openclaw.json → models.providers.zai，**coding 套餐端点** `https://open.bigmodel.cn/api/coding/paas/v4`，精简为 4 模型：glm-5.2（旗舰）/ glm-4.7（主力）/ glm-4.7-flash（轻量）/ glm-4.6v（视觉），别名 GLM-5.2 等
- **scheduler**: models.json zai provider 同 key 同端点
- **脚本**: morning_briefing_v2.py / news_summary_v2.py 已删除 ANTHROPIC 死代码（summarize 不读这些变量，实际走 volcengine/deepseek）
- **验证**: coding 端点 4 模型调用正常；GitHub 同步 cron 投递修复后连续正常
- **备份**: /root/.openclaw/backup-key-switch-20260814_151824/、openclaw.json.bak-20260814_152817-pre-slim

### 关键事实
- 智谱三端点：`coding/paas/v4`（套餐✅）/ `paas/v4`（按量，余额不足 1113）/ `anthropic`（可用但无 coding 变体）
- /root/scripts 与 workspace/scripts 部分文件为硬链接（inode 同），改一处即同步
- gateway restart 会 drain 当前会话（SIGTERM 中断属正常，systemd 自动拉起）
- 8-13 完成升级 2026.5.28→2026.7.1-2 + systemd 单一管理 + memorySearch 已禁用
- 待处理：volcengine 欠费（有 deepseek fallback）、daily/weekly 反思脚本废弃（读不存在的 auth-profiles.json）
