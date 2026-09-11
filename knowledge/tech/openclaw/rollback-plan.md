# OpenClaw 一键回滚预案

> 适用场景：升级后出现严重问题（服务不可用、核心功能异常、飞书集成失效等）
> 回滚目标：恢复到升级前的版本和状态，确保业务快速恢复
> 预计回滚时间：< 5 分钟

---

## 一、回滚触发条件

满足以下任一条件立即回滚：
- 🔴 Gateway 无法启动，端口未监听
- 🔴 飞书消息完全无法收发（且排除网络问题）
- 🔴 所有模型调用均失败
- 🔴 数据丢失或配置损坏
- 🟡 核心功能异常且 30 分钟内无法定位修复
- 🟡 内存/CPU 异常飙升影响其他业务

---

## 二、回滚核心原则（历史教训）

### ⚠️ 绝对不能只回滚配置！
**历史教训（2026-09-08）**：new-api 网关切换时，只回滚了 openclaw.json，没回滚 profile 数据，导致半态——配置是旧的，profile 是新的，两边不一致，问题更复杂。

### 回滚必须同时覆盖：
1. **二进制版本** — npm 重装旧版本
2. **配置文件** — openclaw.json
3. **Profile 数据** — agents/ 目录（SQLite，含 key、session 等）
4. **插件数据** — plugins/ 目录

---

## 三、回滚脚本

**脚本位置**：`scripts/utils/openclaw_rollback.sh`

**使用方法**：
```bash
# 回滚到指定备份目录
bash scripts/utils/openclaw_rollback.sh ~/.openclaw/backup-pre-upgrade-YYYYMMDD_HHMMSS

# 回滚到最近的备份（自动查找最新）
bash scripts/utils/openclaw_rollback.sh --latest
```

### 脚本执行流程
```
1. 验证备份目录存在且完整
2. 停止 Gateway 服务
3. 回滚二进制（npm install 旧版本）
4. 回滚配置文件（openclaw.json）
5. 回滚 Profile 数据（agents/）
6. 回滚插件数据（plugins/）
7. 启动 Gateway 服务
8. 验证服务恢复
9. 输出回滚报告
```

---

## 四、手动回滚步骤（脚本不可用时备用）

### 步骤 1：确认备份目录
```bash
# 列出所有备份
ls -lt ~/.openclaw/backup-pre-upgrade-*/

# 设置变量
BACKUP_DIR=~/.openclaw/backup-pre-upgrade-YYYYMMDD_HHMMSS
OLD_VERSION=$(cat $BACKUP_DIR/version.txt | awk '{print $2}')
```

### 步骤 2：停止 Gateway
```bash
systemctl --user stop openclaw-gateway
sleep 2
```

### 步骤 3：回滚二进制
```bash
npm install -g openclaw@$OLD_VERSION
openclaw --version
```

### 步骤 4：回滚配置
```bash
cp $BACKUP_DIR/openclaw.json ~/.openclaw/openclaw.json
```

### 步骤 5：回滚 Profile + 插件
```bash
# Profile（关键！不能漏）
rm -rf ~/.openclaw/agents
cp -r $BACKUP_DIR/agents ~/.openclaw/

# 插件
if [ -d "$BACKUP_DIR/plugins" ]; then
    rm -rf ~/.openclaw/plugins
    cp -r $BACKUP_DIR/plugins ~/.openclaw/
fi
```

### 步骤 6：启动并验证
```bash
systemctl --user start openclaw-gateway
sleep 5
systemctl --user status openclaw-gateway
ss -tlnp | grep 18789
```

### 步骤 7：功能验证
- 发一条测试消息确认模型调用正常
- 飞书消息测试
- 检查日志无报错

---

## 五、回滚后验证清单

- [ ] Gateway 运行中，状态 active
- [ ] 端口 18789 正常监听
- [ ] CLI 命令正常
- [ ] 模型调用成功
- [ ] 飞书消息收发正常
- [ ] 日志无 ERROR
- [ ] 定时任务配置完整

---

## 六、回滚后处理

1. **确认业务恢复** — 所有核心功能正常
2. **收集错误信息** — 升级失败的日志、报错信息，用于分析
3. **记录到记忆** — 当日 memory 文件记录升级失败及回滚
4. **保留现场** — 备份目录保留，便于后续分析
5. **评估是否重试** — 根据问题原因决定修复后重试还是延后升级

---

## 七、常见回滚坑及规避

| 坑 | 后果 | 规避方案 |
|----|------|----------|
| 只回滚配置，不回滚 profile | 半态，配置与数据不一致 | 脚本自动一起回，手动时严格按步骤 |
| 回滚后不重启 | 旧配置不生效 | 脚本自动重启，手动时必须 restart |
| 备份不完整 | 回滚后缺数据 | 升级前用脚本做完整备份 |
| 权限问题（root vs 用户） | 配置目录不对，回滚无效 | 确认当前用户，备份/回滚同一用户上下文 |
| npm 安装失败 | 二进制回滚失败 | 提前确认 npm 源可用，备用方案：用 nvm 或缓存 |
