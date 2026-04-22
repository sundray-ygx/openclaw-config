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

## 🤖 AI 辅助工作

### 培训课题设计难度控制
**问题**: 校招新员工 AI-Coding 培训课题最初过于专业，涉及公司业务
**根因**: 未充分考虑校招新生的技术背景和学习曲线
**Fix**: 采用通用类课题，纯软件可完成，聚焦 AI-Coding 实践过程而非业务知识
**级别**: 🟢 低

### 定时任务重复执行未及时发现
**问题**: 每日反思任务在 4/8 一天执行了 8 次才被发现
**根因**: 缺少定时任务执行频率监控和异常告警
**Fix**: 为高频任务添加执行计数器，超过阈值时触发告警
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

### 记忆维护过期导致信息堆积
**问题**: heartbeat-state.json 的 lastMemoryMaintenance 为 2026-01-01，过期 90+ 天
**根因**: 记忆维护脚本未定期执行，缺少提醒机制
**Fix**: 将记忆维护加入 HEARTBEAT.md，每周自动检查并执行
**级别**: 🟡 中

---

## 🛠️ 前端开发

### Unicode编码导致脚本执行失败
**问题**: Python脚本包含emoji字符，在Win10 PowerShell中执行时报 "There's a Unicode encoding error with emoji characters in the script"
**根因**: PowerShell默认编码不支持emoji，脚本文件保存时未指定UTF-8编码
**Fix**: (1) 在Python脚本顶部添加 `# -*- coding: utf-8 -*-` (2) 确保文件保存为UTF-8格式 (3) PowerShell执行前设置 `$OutputEncoding = [console]::InputEncoding = [console]::OutputEncoding = [System.Text.Encoding]::UTF8`
**级别**: 🟢 低

### Selenium环境配置复杂性
**问题**: (1) ChromeDriver版本与Chrome版本不匹配 (2) 网络超时（ERR_CONNECTION_TIMED_OUT） (3) CDP Network 域启用失败
**根因**: (1) Chrome自动更新后驱动版本未同步 (2) 内网环境网络配置复杂（代理、防火墙） (3) Chromium headless模式CDP支持有限
**Fix**: (1) 使用 webdriver-manager 自动管理驱动版本 (2) 配置代理设置（$env:HTTPS_PROXY） (3) 增加重试机制和超时配置 (4) CDP失败不影响主要功能，仅降级处理
**级别**: 🟡 中

### 前端页面数据加载问题（CORS）
**问题**: 后端API可通，但前端页面看不到数据
**根因**: 跨域（CORS）问题 - 前端端口与后端端口不一致
**Fix**: (1) 检查后端CORS配置（FastAPI添加CORSMiddleware） (2) 检查前端JS中API路径是否硬编码了原平台地址 (3) 确保前端代理配置正确
**级别**: 🟡 中

---

## 🎯 考试与技术评估

### 考试平台技术限制评估
**问题**: 担心考试方通过技术限制阻止自动化提取（如禁用F12、限制API拦截）
**评估结果**: 浏览器必须接收HTML才能渲染，因此无法阻止 `driver.page_source` 获取；CDP网络拦截无法阻止（浏览器内置功能）；但可能限制截图、阻止devtools协议
**建议**: 以JSON提取为主，截图为辅；假设最坏情况（部分功能受限），提前准备替代方案
**级别**: 🟢 低
