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

---

## 🔒 安全事件处理（2026-08-25 完成）

### SSL 证书续期（vw.ygxpro.online）
- **状态**: ✅ 已修复。证书续至 2026-11-22（Let's Encrypt，ZeroSSL 当时 502 已切换）
- **双根因**: ① crontab 缺 acme.sh 续期任务 ② 旧 AccessKey（LTAI5t…GBJV）被阿里云风控封禁
- **修复**: 换新 AccessKey（LTAI5t…DjDT）+ 签发新证书 + cron 每天 22:06 自动续期 + acme.sh v3.1.4 自动升级
- **待办**: 旧被封 AccessKey 需在阿里云 RAM 删除；NAS 侧 Hermes 需手动 load_secrets.sh + 重启 gateway（用户操作）；建议加证书到期监控（<14 天告警）

### SSH 暴力破解防护加固（方案 A）
- **状态**: ✅ 已完成。7天133万次攻击尝试后加固：fail2ban maxretry 3→2、findtime 600→3600、递增封禁最长7天、SSH MaxAuthTries 6→3
- **备份**: /etc/fail2ban/jail.local.bak-20260825, /etc/ssh/sshd_config.bak-20260825

---

## 🤖 模型体系大更新（2026-09-02 ~ 09-03 完成）

- **状态**: ✅ 完成。模型列表 22 个（zai 7 / volcengine 12 / deepseek 3），全部实测可用
- **默认模型**: main → `zai/glm-5.3`（旗舰，1M ctx），fallback deepseek-v4-pro → doubao-seed-2-1-turbo；scheduler → glm-4.7-flash；coding → glm-5.3
- **移除（不可用）**: glm-5v-turbo（套餐未开放）、glm-4.7-flashx（需单独计费）、doubao-seed-2-1-pro（不支持 coding plan）
- **火山引擎"欠费"破案**: 系误判——标准端点 `/api/v3` 确实欠费，但配置走 Coding Plan 端点 `/api/coding/v3` 完全正常（130 模型可用）。MEMORY.md 误判已修正

## 🔧 Hermes 部署（9-05 建成，2026-09-22 升级 v0.21.4）

- **ECS 当前版本**: v0.21.4 (v2026.9.21)，HEAD d337b736，detached at tag；2026-09-22 从 v0.21.1 升级，CLI/模型链路冒烟通过
- **升级流程（下次参考）**: `cd /usr/lib/node_modules/hermes-agent/runtime/hermes-agent && git fetch origin --tags && git checkout <tag>` → `sed -i 's|https://pypi.org/simple|https://pypi.tuna.tsinghua.edu.cn/simple|g; s|https://files.pythonhosted.org/packages|https://pypi.tuna.tsinghua.edu.cn/packages|g' uv.lock`（tuna 镜像必做：pypi CDN 本机仅 28KB/s，tuna ~12.7MB/s）→ `venv/bin/pip install -q uv` → `UV_PROJECT_ENVIRONMENT=$PWD/venv venv/bin/uv sync --frozen --no-dev --all-extras` → `hermes --version` 验证
- **git 通道**: origin=**git@github.com**（SSH）；ECS HTTPS git 协议被卡（ls-remote 25s 超时）、api.github.com 正常；ghproxy.net 缓存滞后 11 天已弃用
- **ECS gateway 决策（9-22 Boss 定）**: hermes-gateway.service 保持 disabled，NAS 为主力
- **hermes-config 同步**: NAS(hub) 03:00 push → ECS 05:00 pull；9-05~9-22 曾断 17 天（ECS 本地 19 分叉提交 vs 远端 39，ff-only 失败无告警），9-22 已 bundle 备份后强制对齐 deb655d 并恢复（传播 63 新技能）；pull.sh 已加飞书告警（alert_fail 函数）
- **升级备份**: /root/openclaw-backups/hermes-preupgrade-20260922/（397M：.hermes tar 30M + 双 bundle），稳定 1-2 周后可删
- **待验证**: Boss 9-20 提的思考流不实时刷新问题，新版含大量 TUI 修复，待实际使用确认
- **范围注记**: 本次仅 ECS；NAS 侧 hermes-studio 如需同步升级另议
- **基建**: nginx `/etc/nginx/conf.d/hermes-studio.conf`（泛域名证书，WebSocket/SSE/3600s）→ frps:8648 → NAS

## new-api 模型网关（2026-09-08 上线 → 9-17 迁 NAS → 9-27 迁回 ECS 主）
- **状态**: 🟢 运行中，**ECS 为主网关**（9-27 切换）；入口 ECS nginx(443 TLS)→127.0.0.1:3000(ECS 容器)；NAS:3000 为热备（经 frp ECS:3100 可达）；ECS 桥接 `/etc/nginx/conf.d/newapi-upstream.conf`（172.17.0.1:8081，必须保留，渠道 1/2 走它）；版本 rc.35；每日 08:20 巡检 + 每 5 分钟 failover 探测
- **9-27 切换要点**: 容器重建（300M→1G + json-file 20m×3）；种子数据用宿主机 Python 导入（SQLite 保留字 `group` + 容器无 sqlite3）；⚠️ 文档步骤 2 的“base_url 改上游直连”是错的，必须走 bridge（否则 404），已回写修正 ecs-newapi-deploy.md/ecs_seed.sql
- **9-27 failover**: `/root/scripts/utils/ecs-failover-probe.sh`（crontab */5），连续 2 次探活失败→sed 3000→3100 + reload + 飞书红卡；恢复→绿卡提示人工切回（`bash <脚本> switchback`，不自动切回）；飞书告警复用 nas_backup.sh 同套应用凭证；演练已通过
- **入口**: api.ygxpro.online；渠道 GLM-Coding(主)→Volc-Coding(备)→DeepSeek-Paygo(兜底)；三渠道数据在 NAS /volume1/docker/newapi/data
- **迁移记录**: 2026-09-17 完成；评估与双侧 runbook 见 knowledge/tech/infrastructure/newapi-nas-migration-*.md；首次编排切流因 hermes 模型配置问题超时自动回滚，hermes 修复后改零停机直接切流成功；ECS 旧容器/数据保留热备待观察期后清理
- **9-11/12 变更**: fallback 链按 Boss 预期修正（glm→火山→deepseek）；scheduler 主模型 glm-4.7-flash→glm-5.3-flash（4.7-flash 在网关无渠道致 503+重试8次，每条消息慢 86s）；定价/费用重算/渠道事故恢复见 2026-09-08.md
- **双向 failover（9-18）**: scripts/utils/failover-to-ecs.sh（故障切热备 ~5s）/ failover-back-to-nas.sh（切回，3100 不可达自动拒绝）；手册 knowledge/tech/infrastructure/newapi-gateway-failover.md；⚠️ 切回 ECS 后数据=09-17 23:15 快照；skill 提案 pending 待 Boss 激活
- **监控（9-13）**: 渠道检查已改 command 型零 LLM（原 agentTurn 单次 70k tokens）+ 静默模式（成功无推送，失败 failureAlert after=1 推飞书）
- **待办**: [ ] glm-4.7-flash 渠道在 new-api 后台补配（Boss 手动，NAS 侧同样缺失）；[ ] 观察期 1-2 周后 Phase4 收尾（ECS 清理、备份脚本 08-new-api 段改造、3100 连通性入巡检）；[ ] Hermes fallback 缺失评估；[ ] failover skill 提案激活确认

## OpenClaw 2026.9.3 升级攻坚（2026-09-11，已闭环）
- **状态**: ✅ 完成。三起连锁故障全部修复：①飞书插件不兼容 9.3 新插件 API（runtime.config 变纯对象），3 处兼容补丁；②doctor/tui ownership——user 级迁移在本机不可行（busctl --json 需 systemd≥243，Al8 只有 239），最终方案=保留系统级 unit + OPENCLAW_SERVICE_REPAIR_POLICY=external + systemd-run 自愈脚本跑 doctor --fix；③fallback 链与 scheduler 模型修正（上条）
- **配置备份**: openclaw.json.bak-fallback-20260911、/etc/systemd/system/openclaw-gateway.service.bak-userscope-migration-20260911
- **教训**: 见 lessons.md「OpenClaw 升级与 systemd」节

## ECS SSH 安全加固（2026-09-12 诊断，待 Boss 决策）
- **状态**: ⏳ 确认未入侵（2129 次失败爆破全为互联网背景噪音，攻击 IP 零成功），但 PasswordAuthentication=yes 攻击面全开
- **待办**: [ ] Boss 先完成密钥登录验证 → 再改 sshd 关闭密码认证（PasswordAuthentication no + PermitRootLogin prohibit-password）；备选 Tailscale/安全组白名单

---

## cc.ygxpro.online 公网部署（2026-09-20，完成）
- **状态**: ✅ 完成。hermes-mobile + hermes-studio 公网入口，同域无 CORS
- **架构**: ECS nginx(443/TLS) → frps → frpc → NAS；`/`→3346(hermes-mobile)，`/api/`+`/socket.io/`→8648(hermes-studio)
- **文件**: `/etc/nginx/conf.d/cc.conf`
- **验证**: 移动页 200、socket.io 握手拿 sid、API 401 鉴权生效、80→301
- **教训**: 上游协议别信文档，直连实测（cc-manager 是 HTTPS 自签，文档写 http 导致 502）

---

## ECS Hermes 升级 + hermes-config 同步修复（2026-09-22，完成）
- **状态**: ✅ 完成。v0.21.1 → v0.21.4 (v2026.9.21)，tag d337b736
- **同步修复**: 断同步 17 天（ECS 本地 19 分叉 vs 远端 39）→ bundle 备份后强制对齐 deb655d，传播 63 新技能；pull.sh 加飞书告警
- **git 通道**: origin 切 SSH（HTTPS git 被卡但 SSH/api 正常）；ghproxy.net 缓存可滞后 11 天
- **升级流程**: checkout tag → uv.lock sed tuna 镜像（pypi CDN 本机仅 28KB/s，tuna ~12.7MB/s）→ uv sync → 验证
- **ECS gateway 决策**: hermes-gateway.service 保持 disabled，NAS 为主力

---

## OpenClaw 2026.9.5 升级（2026-09-22，完成）
- **状态**: ✅ 完成。首跑因 PNPM_HOME 缺失失败→自动回滚兜底，修复后二跑成功
- **飞书插件修复（2 处 9.5 兼容）**: ① `openclaw/plugin-sdk` 裸入口被移除→package.json 补 exports；② pnpm realpath 嵌套 symlink 失效→lark store 补 openclaw symlink
- **巡检发现**: ① TimeoutStopSec=30 < 网关退出预算 55s → 每次重启必 SIGKILL，连带杀 GitHub 同步 ② 冷启动 62s vs 正常 9-16s（6700 dist 文件+内存压力） ③ TUI 常驻 242M + hermes-tui 265M

---

## 磁盘暴涨处置（2026-09-23，完成）
- **状态**: ✅ 完成。磁盘 80% → **69%**（回收 ~4.4G）
- **清理项**: /root/.cache/uv 1.5G + /tmp plugin staging 174 个目录 3.5G + node-compile-cache 238M + npm/pnpm 缓存
- **根因**: plugins update/install 每次产生 /tmp/openclaw-plugin-build-* staging 目录，升级中断+重启竞态累积
- **验证**: 23:30 GitHub 同步复跑成功（c9d4542），TimeoutStopSec 修复经真实负载验证

---

## 网关 4 连崩排障 + heap 调优（2026-09-24，完成）
- **状态**: ✅ 完成。08:02/10:00/11:41/12:18 四次 V8 堆 OOM 全部修复
- **根因**: V8 堆上限 384M 打满（`FATAL ERROR: Reached heap limit`），驱动=主会话大上下文+心跳任务
- **修复**: ① NODE_OPTIONS 384→512M ② MemoryMax 对齐 880M（主 unit 死配置被 system.control drop-in 覆盖）③ 重启验证
- **教训**: `systemctl show` 的 MemoryMax 才是真值，unit 文本可能被 drop-in 静默覆盖

---

## jellyfin.ygxpro.online 反代上线（2026-09-24，完成）
- **状态**: ✅ 完成。方案 A：ECS nginx → frp → NAS Jellyfin
- **证书**: 复用泛域名证书（省去 certbot 单签），2026-11-22 到期
- **文件**: `/etc/nginx/conf.d/jellyfin.conf`
- **验证**: system/info 返回 Jellyfin-NAS 12.1.0，HTTP/2 200，80→443 正常

---

## ECS new-api 主网关部署 + failover（2026-09-27，完成）
- **状态**: ✅ 完成。ECS 为主网关，NAS(3100) 降热备
- **架构**: 公网 api.ygxpro.online → ECS nginx → 127.0.0.1:3000(new-api 容器)；bridge 172.17.0.1:8081 必保
- **容器配置**: 1G 内存 + json-file 日志 20m×3（NAS 僵死事故教训）
- **种子数据**: 宿主机 Python executescript 导入（SQLite `group` 保留字 + 容器无 sqlite3）
- **failover**: `/root/scripts/utils/ecs-failover-probe.sh`（crontab */5），连续 2 次失败→切 3100+飞书红卡；恢复需人工 switchback
- **教训**: 渠道 base_url 必须走 bridge 不能直连上游（见 lessons.md 高优条目）

---

## zai bridge IPv6 修复（2026-09-28，完成）
- **状态**: ✅ 完成。zai 渠道当日失败 12+ 次
- **根因**: nginx proxy_pass 写死域名=启动时静态解析，api.z.ai 优先 AAAA 记录，ECS 无 IPv6 出口 → Network is unreachable
- **修复**: `set $zai_target` + `resolver 100.100.2.136 ipv6=off valid=300s` + rewrite 拼路径
- **文件**: `/etc/nginx/conf.d/newapi-upstream.conf`

---

## ECS 系统巡检 + 三项优化（2026-09-28，完成）
- **状态**: ✅ 完成。Boss 批准三项
- **1. 每日自动重启**: `/etc/systemd/system/openclaw-gateway-daily-restart.{service,timer}`，04:30，已 enable
- **2. 停用 sing-box**: 5 个月总流量仅 70MB + 1080 无鉴权绑定 0.0.0.0 公网暴露风险；镜像配置保留
- **3. 磁盘清理**: npm/pnpm 缓存 + 旧备份 tar.gz，回收 ~1.5G，72%→68%
- **发现**: 09-22 23:15 曾全局 OOM 杀网关（内核 48 处 OOM 记录）；hermes ECS 已停用 23 天

---

## 心跳机制治理（2026-09-28，完成）
- **状态**: ✅ 完成。token 省 ~83%
- **措施**: ① heartbeat 60m→6h ② AGENTS.md 改静默优先（禁巡检/禁正常输出/仅 HEARTBEAT_OK）③ `scripts/utils/heartbeat_syscheck.sh` 零LLM巡检（磁盘85%/内存300M/swap50%/gateway/容器/僵尸），同类异常1h去抖，异常推飞书 ④ crontab 每小时执行
- **附带发现**: 9/26-9/27 心跳连续失败 20+ 小时（deepseek 超时），无失败告警

---

## 网关内存诊断 + 方案一执行（2026-10-06，观察中）
- **状态**: 🔄 观察期（72h 无重启验证，至 10-08 04:30）
- **诊断结论**: 无泄漏。心跳"94% 临界"是 cgroup 口径假警报（含 ~190M 可回收 page cache，真实 RSS ~600M）
- **真风险**: 每日 04:30 重启的启动潮 802M（离 880M 仅 9% 余量）——重启本身就是峰值制造者
- **方案一已执行**:
  1. syscheck 改 RSS≥750M 口径 + HEARTBEAT.md 硬规则
  2. 重启降频：每日 → Mon/Thu 04:30
  3. 止血三件套：notifyOnExit=false / timeout 300s / maxRetries 3（配置热生效）
  4. 会话清理：44 活跃全保留，回收 222 个无引用 artifacts ~3M
- **方案二（备选）**: heap 576M / MemoryMax 960M（拒绝 1G 建议，防 09-24 堆 OOM 重演）
- **教训**: 心跳告警必须区分 anon/file cache，cgroup current 不能直接当"内存临界"用
