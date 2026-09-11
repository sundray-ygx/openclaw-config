# OpenClaw 升级执行方案

> 版本：2026.7.1-2 → 2026.9.3
> 执行人：小助
> 前置条件：用户确认执行升级

---

## 一、前置检查（升级前 10 分钟）

### 1.1 环境检查
```bash
# 确认当前版本
openclaw --version
openclaw gateway status

# 确认 node 版本
node --version

# 确认 Python 版本（历史坑：skillhub 依赖 Python 3.7+）
python3 --version

# 确认磁盘空间（至少 500M 空余）
df -h /root
```

### 1.2 服务状态检查
```bash
# Gateway 状态
systemctl --user status openclaw-gateway

# 确认端口监听
ss -tlnp | grep 18789

# 最近错误日志
tail -50 /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log | grep -i error
```

### 1.3 配置完整性检查
- 确认 `~/.openclaw/openclaw.json` 存在且有效
- 确认飞书插件配置正常
- 确认所有 provider 配置完整

---

## 二、全量备份（升级前必做）

### 2.1 备份清单
| 类别 | 路径 | 说明 |
|------|------|------|
| 二进制 | `/usr/lib/node_modules/openclaw/` | npm 全局安装目录 |
| 配置 | `~/.openclaw/openclaw.json` | 主配置文件 |
| Profile 数据 | `~/.openclaw/agents/` | SQLite profile（含 key、session 等） |
| 插件数据 | `~/.openclaw/plugins/` | 插件配置和数据 |
| 工作区 | `~/.openclaw/workspace/` | 工作区文件（含 memory、skills） |
| 日志 | `/tmp/openclaw/` | 运行日志 |

### 2.2 备份命令（一键执行）
```bash
BACKUP_DIR=~/.openclaw/backup-pre-upgrade-$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 配置文件
cp ~/.openclaw/openclaw.json $BACKUP_DIR/

# 二进制版本记录（回滚时用 npm install 重装指定版本）
openclaw --version > $BACKUP_DIR/version.txt

# Profile + 插件 + 数据
cp -r ~/.openclaw/agents $BACKUP_DIR/
cp -r ~/.openclaw/plugins $BACKUP_DIR/ 2>/dev/null || true

# 工作区（memory 等关键数据）
cp -r ~/.openclaw/workspace/memory $BACKUP_DIR/workspace-memory/

echo "备份完成：$BACKUP_DIR"
ls -lh $BACKUP_DIR/
```

> **注意**：二进制不直接复制目录，而是记录版本号，回滚时用 `npm install -g openclaw@<version>` 重装。

---

## 三、执行升级

### 3.1 升级命令
```bash
# npm 全局升级
npm install -g openclaw@latest

# 确认新版本
openclaw --version
```

### 3.2 重启 Gateway
```bash
# 重启服务
systemctl --user restart openclaw-gateway

# 等待启动
sleep 5

# 确认状态
systemctl --user status openclaw-gateway
```

### 3.3 升级后自动迁移（如有）
- 启动后查看日志，确认是否有配置迁移
- 如有迁移，确认迁移成功无报错

---

## 四、验证清单（升级后逐项检查）

### 4.1 基础功能
- [ ] `openclaw --version` 显示目标版本
- [ ] Gateway 运行中，端口正常监听
- [ ] Dashboard 可访问（http://127.0.0.1:18789）
- [ ] CLI 命令正常（status、list 等）

### 4.2 核心功能
- [ ] 模型调用正常（发一条测试消息）
- [ ] 多 provider 均可调用（zai / deepseek / volcengine）
- [ ] 子代理功能正常
- [ ] Memory Dreaming 配置存在

### 4.3 飞书集成
- [ ] 飞书消息收发正常
- [ ] 飞书日历、文档、任务等工具可用
- [ ] 飞书定时任务不受影响

### 4.4 自动化任务
- [ ] crontab 任务列表完整（`crontab -l`）
- [ ] 下一个定时任务能正常触发（观察验证）
- [ ] 早间简报脚本不依赖 OpenClaw 版本（已确认）

### 4.5 日志检查
- [ ] 启动日志无 ERROR
- [ ] 运行 10 分钟无异常报错
- [ ] 内存/CPU 正常

---

## 五、观察期

### 5.1 立即观察（0-30 分钟）
- 实时监控日志
- 测试核心功能
- 确认无异常报错

### 5.2 短期观察（30 分钟 - 24 小时）
- 观察定时任务执行
- 观察飞书消息响应
- 定期检查日志错误

### 5.3 长期观察（24-72 小时）
- 确认每日定时任务全部正常
- 确认无隐性问题（内存泄漏、性能下降等）

---

## 六、异常处理

### 升级失败怎么办？
1. **不要慌**，先执行回滚脚本
2. 回滚后确认服务恢复正常
3. 收集错误日志，分析原因
4. 修复问题后再尝试

### 常见异常及处理
| 异常 | 可能原因 | 处理方式 |
|------|----------|----------|
| Gateway 启动失败 | 配置不兼容 / 插件冲突 | 回滚配置 + 二进制 |
| 飞书消息无响应 | 插件版本不兼容 | 回滚，检查插件更新 |
| 模型调用失败 | Provider 配置格式变更 | 检查配置，修复后重试 |
| 子代理异常 | 核心 API 变更 | 回滚，等后续版本 |

---

## 七、升级后确认

升级成功并验证完成后：
1. 更新 `MEMORY.md` 中的版本信息
2. 记录到当日 `memory/YYYY-MM-DD.md`
3. 保留备份至少 7 天，确认稳定后再清理
