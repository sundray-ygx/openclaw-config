# OpenClaw 用户迁移诊断报告

**诊断时间**: 2026-03-24 17:45  
**诊断人**: 小助  
**迁移脚本**: `/root/.openclaw/workspace/scripts/migration/openclaw-user-migration.sh`

---

## 1. 核心问题确认

### 1.1 根本设计缺陷

**迁移方案的根本假设错误**:

迁移脚本假设 OpenClaw 的数据目录可以从 `/root/.openclaw` 迁移到 `/home/openclaw/.openclaw`，但实际上 OpenClaw 的架构设计决定了：

1. **Gateway 服务使用 systemd 管理**，配置中指定了 `User=openclaw` 和 `WorkingDirectory=/home/openclaw`
2. **OpenClaw CLI 默认读取的是 `$HOME/.openclaw`**，即运行命令的用户的 home 目录
3. **当 root 用户运行 `openclaw` 命令时，读取的是 `/root/.openclaw`**
4. **当 openclaw 用户运行命令时，读取的是 `/home/openclaw/.openclaw`**

**问题本质**: 两个目录同时存在且各自独立，不是一个"迁移"关系，而是"双轨并行"关系。

---

## 2. 当前状态对比

### 2.1 目录结构对比

| 目录 | /root/.openclaw (属主: root) | /home/openclaw/.openclaw (属主: openclaw) |
|------|------------------------------|-------------------------------------------|
| agents/main | ❌ root 属主 | ✅ openclaw 属主 |
| agents/scheduler | ❌ root 属主 | ✅ openclaw 属主 |
| cron | ❌ root 属主 | ✅ openclaw 属主 |
| credentials | ❌ root 属主 | ✅ openclaw 属主 |
| devices | ❌ root 属主 | ✅ openclaw 属主 |
| extensions | ❌ root 属主 | ✅ openclaw 属主 |
| feishu | ❌ root 属主 | ✅ openclaw 属主 |
| identity | ❌ root 属主 | ✅ openclaw 属主 |
| logs | ❌ root 属主 | ✅ openclaw 属主 |
| media | ❌ root 属主 | ✅ openclaw 属主 |
| memory | ❌ root 属主 | ✅ openclaw 属主 |
| delivery-queue | ❌ root 属主 | ✅ openclaw 属主 |

### 2.2 关键发现

**问题 1: /root/.openclaw 仍在被使用**
- 当 root 用户运行 `openclaw` 命令时（如当前 TUI 会话），实际使用的是 `/root/.openclaw`
- 这导致两个目录的数据不同步
- 例如：`devices/paired.json` 在两个目录中内容不同

**问题 2: /root/scripts 权限未完全修复**
- `/home/openclaw/scripts/` 目录存在但为空
- `/root/scripts/` 仍为 root 属主
- openclaw 用户的 crontab 中引用的脚本路径已改为 `/home/openclaw/.openclaw/workspace/scripts/`，但原 `/root/scripts/` 下的部分脚本未被复制

**问题 3: 进程运行状态混乱**
```
当前进程状态:
root     1961198  openclaw (TUI)
root     1961205  openclaw-gateway  ← 仍以 root 运行！
root     1961217  openclaw (TUI)
root     1961224  openclaw-tui
```

Gateway 服务虽然 systemd 配置改为 `User=openclaw`，但实际进程仍以 root 运行。

---

## 3. 具体问题清单

### 🔴 严重问题 (需立即修复)

| # | 问题 | 影响 | 位置 |
|---|------|------|------|
| 1 | Gateway 仍以 root 运行 | 安全违规，迁移未生效 | systemd 服务 |
| 2 | /root/.openclaw 和 /home/openclaw/.openclaw 数据分叉 | 配置不一致，设备配对信息可能丢失 | 双目录 |
| 3 | root crontab 仍存在 OpenClaw 任务 | 任务重复执行，路径混乱 | root crontab |

### 🟡 中等问题 (建议修复)

| # | 问题 | 影响 | 位置 |
|---|------|------|------|
| 4 | /root/scripts 仍为 root 属主 | openclaw 用户可能无法访问 | /root/scripts |
| 5 | 部分脚本路径在 crontab 中指向旧位置 | 定时任务可能失败 | openclaw crontab |
| 6 | memory 目录中 SQLite 数据库不同步 | 会话历史可能不一致 | memory/*.sqlite |

### 🟢 低优先级问题

| # | 问题 | 影响 | 位置 |
|---|------|------|------|
| 7 | /root/.openclaw 旧数据未清理 | 磁盘空间占用 | /root/.openclaw |
| 8 | 日志文件分散在两个目录 | 排查问题困难 | logs/ |

---

## 4. 根因分析

### 4.1 迁移脚本缺陷

1. **阶段二未完全执行**: 从日志看，阶段二（服务切换）可能未完整执行或执行失败
2. **systemd 服务未重启**: 修改 systemd 配置后未执行 `systemctl daemon-reload` 和 restart
3. **数据同步不完整**: `/root/.openclaw` 中的最新数据未同步到 `/home/openclaw/.openclaw`

### 4.2 架构理解偏差

迁移脚本的设计假设是"数据迁移"，但实际情况是：
- OpenClaw 支持多用户运行
- 每个用户有自己的 `$HOME/.openclaw` 目录
- Gateway 服务只能绑定到一个数据目录
- 当前配置中，systemd 服务已指向 `/home/openclaw`，但进程未重启

---

## 5. 修复建议

### 方案 A: 完成迁移 (推荐)

1. **停止所有 OpenClaw 进程**
   ```bash
   openclaw gateway stop
   pkill -f openclaw
   ```

2. **最终数据同步**
   ```bash
   rsync -av --delete /root/.openclaw/ /home/openclaw/.openclaw/
   chown -R openclaw:openclaw /home/openclaw/.openclaw/
   ```

3. **重启 systemd 服务**
   ```bash
   systemctl daemon-reload
   systemctl restart openclaw-gateway
   ```

4. **清理 root crontab**
   ```bash
   crontab -r  # 或手动删除 OpenClaw 相关任务
   ```

5. **验证**
   ```bash
   ps aux | grep openclaw-gateway  # 确认用户是 openclaw
   ls -la /home/openclaw/.openclaw/agents/main/sessions/  # 确认权限
   ```

### 方案 B: 回滚到 root 运行

如果迁移问题太多，可以回滚：
1. 修改 systemd 服务 `User=root`
2. 删除 openclaw 用户 crontab
3. 恢复 root crontab
4. 重启服务

---

## 6. 当前临时修复

已执行:
- ✅ `/root/.openclaw/agents/main/` 权限已修复为 openclaw:openclaw

这解决了 immediate 的权限报错，但未解决根本问题。

---

## 7. 建议下一步行动

1. **决定**: 是否继续完成迁移，还是回滚到 root 运行？
2. **备份**: 执行最终数据同步前，备份当前两个目录
3. **切换**: 按方案 A 完成迁移，或按方案 B 回滚

---

**报告生成时间**: 2026-03-24 17:45 CST  
**数据版本**: OpenClaw 2026.3.11
