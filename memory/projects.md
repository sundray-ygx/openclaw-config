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
