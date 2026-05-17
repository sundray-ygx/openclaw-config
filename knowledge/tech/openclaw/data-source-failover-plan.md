# 数据源故障应急预案

## 1. 故障检测机制

### Notion API 故障检测
- 每5分钟执行一次 `data_integrity_check.py` 脚本
- 检测指标：API 响应时间 > 10s 或 HTTP 状态码 != 200
- 连续3次失败触发告警

### 飞书 API 故障检测  
- 每10分钟执行一次基础消息发送测试
- 检测指标：消息发送失败或响应超时
- 连续2次失败触发告警

## 2. 自动切换流程

### Notion 故障切换
1. **立即降级**：停止所有 Notion 相关操作
2. **启用本地缓存**：使用最近24小时的本地快照数据
3. **通知用户**：通过飞书发送故障通知
4. **重试机制**：每15分钟尝试恢复连接
5. **恢复验证**：连续3次成功后恢复正常操作

### 飞书故障切换
1. **立即降级**：暂停飞书消息推送
2. **启用备用通道**：切换到邮件通知（如果配置）
3. **本地记录**：将待发送消息暂存到 `/root/.openclaw/workspace/memory/fallback-messages/`
4. **重试机制**：每10分钟尝试恢复连接
5. **批量重发**：恢复后按时间顺序重发积压消息

## 3. 手动干预点

### 需要人工确认的场景
- 故障持续超过2小时
- 本地缓存数据超过48小时未更新
- 备用通道也出现故障

### 人工操作清单
- [ ] 检查故障原因（网络/认证/配额）
- [ ] 评估数据一致性风险
- [ ] 决定是否手动强制切换或等待自动恢复
- [ ] 记录故障处理过程到 `memory/YYYY-MM-DD.md`

## 4. 监控和告警

### 告警级别
- **INFO**: 单次失败，自动重试中
- **WARNING**: 连续失败，已降级处理  
- **ERROR**: 故障持续30分钟以上，需要人工介入

### 监控面板
- 使用 `config_health_check.py` 定期生成健康报告
- 在每日反思中包含数据源状态摘要

## 5. 测试计划

### 定期测试
- 每月第一个周日执行故障切换演练
- 模拟 Notion API 不可用，验证本地缓存切换
- 模拟飞书 API 不可用，验证消息队列和重发

### 测试脚本
```bash
# Notion 故障模拟测试
python3 /root/.openclaw/workspace/scripts/utils/data_integrity_check.py --simulate-notion-failure

# 飞书故障模拟测试  
python3 /root/.openclaw/workspace/scripts/utils/config_health_check.py --simulate-feishu-failure
```