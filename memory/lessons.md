# 经验教训

## 📊 系统配置管理

### 定时任务配置检查机制缺失
**问题**: 日报脚本配置错误（只扫描scheduler目录）运行多天未发现
**根因**: 缺少配置验证和监控告警
**Fix**: 建立配置检查清单，增加任务失败告警机制
**级别**: 🟡 中

### 多用户环境路径规划不足
**问题**: OpenClauw迁移中，/root vs /home/openclaw路径混乱
**根因**: 迁移前未充分规划路径映射
**Fix**: 迁移前明确所有脚本/配置的路径依赖，建立路径对照表
**级别**: 🟡 中

---

## 🔧 技术架构

### 系统升级依赖兼容性
**问题**: skillhub CLI因Python 3.6兼容性问题无法运行
**根因**: 升级时未检查运行环境依赖版本
**Fix**: 升级前检查Python版本，升级后验证CLI可用性
**级别**: 🟢 低

### 归档任务sessionTarget配置错误
**问题**: 归档任务配置为"main"导致400错误，改为"isolated"解决
**根因**: 不理解sessionTarget作用机制
**Fix**: 记录：systemEvent+main=可能有400错误，使用isolated隔离执行
**级别**: 🟢 低

---

## 📈 流程改进

### 日报与反思任务时间错位
**问题**: 反思任务4:00执行，但记忆文件8:30才生成
**根因**: 任务依赖关系未梳理清楚
**Fix**: 调整反思到9:00，确保依赖数据就绪
**级别**: 🟡 中

### 日报生成到archive但memory文件为空
**问题**: 归档任务连续2天失败，记忆文件未更新
**根因**: 依赖23:00归档任务，但任务失败无告警
**Fix**: 日报生成时直接更新memory文件，不依赖归档任务
**级别**: 🟡 中

---

## 🔒 安全与权限

### OpenClaw用户迁移PAM限制
**问题**: openclaw用户无crontab权限，迁移卡住
**根因**: 未预检查openclaw用户的crontab权限
**Fix**: 迁移前检查目标用户权限，或使用root执行crontab任务
**级别**: 🟢 低

### 百炼API月配额耗尽导致failover雪崩
**问题**: NAS备份cron看似"重复触发"（18-36个error日志），实际是bailian provider配额耗尽后failover链路全部429
**根因**: 百炼provider下所有模型共享月配额，配额耗尽后整个provider不可用
**Fix**: (1) cron任务model直接设为非bailian模型 (2) 月初检查配额 (3) provider级429应跳过该provider下所有模型
**级别**: 🟡 中

### cron任务重复触发的误判
**问题**: 多个error日志 ≠ 多次触发，需要区分failover重试和真正的重复调度
**根因**: 对gateway failover机制理解不足
**Fix**: 排查时先查cron runs确认触发次数，再分析单次run内部的error链路
**级别**: 🟢 低

### skillhub配置残留导致持续告警
**问题**: `plugins.entries.skillhub` 已卸载但配置残留，每次CLI操作都产生warning
**根因**: 卸载插件时未清理openclaw.json配置
**Fix**: 从openclaw.json的plugins.entries中删除skillhub条目
**级别**: 🟢 低

---

## 📝 最佳实践

### 配置变更流程
1. 修改配置/脚本
2. 本地测试验证
3. 部署到生产
4. 监控首次执行
5. 确认无异常后关闭监控

### 问题排查流程
1. 检查脚本路径和权限
2. 查看cron运行日志
3. 检查环境变量
4. 手动执行脚本验证
5. 对比系统crontab和OpenClaw cron配置

### 多目录扫描模式
```python
SESSIONS_DIRS = [
    "/root/.openclaw/agents/scheduler/sessions",
    "/root/.openclaw/agents/main/sessions"
]
```
适用于需要整合多个agent会话数据的场景。
