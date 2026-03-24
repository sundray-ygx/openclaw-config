# OpenClaw 升级指导文档

> **版本**: 1.0  
> **日期**: 2026-03-23  
> **适用版本**: OpenClaw ≥ 2026.3.8  
> **编写依据**: 基于实际升级过程中遇到的内存不足（OOM）问题及解决方案整理

---

## 目录

1. [升级前必读](#升级前必读)
2. [标准升级流程](#标准升级流程)
3. [内存不足专项处理](#内存不足专项处理)
4. [故障排查指南](#故障排查指南)
5. [预防措施](#预防措施)
6. [附录](#附录)

---

## 升级前必读

### 系统要求

| 资源 | 最低要求 | 推荐配置 | 说明 |
|------|----------|----------|------|
| **内存** | 2GB | 4GB+ | 低于 2GB 极易触发 OOM |
| **Swap** | 2GB | 4GB+ | 小内存系统必须配置 |
| **磁盘** | 1GB 空闲 | 2GB+ | npm 缓存和安装包占用 |
| **Node.js** | 18.x | 20.x LTS | OpenClaw 运行依赖 |

### 当前环境检查

执行以下命令检查当前环境：

```bash
# 检查内存和 Swap
free -h

# 检查 OpenClaw 版本
openclaw --version

# 检查 Gateway 服务状态
systemctl --user status openclaw-gateway

# 检查 Node.js 版本
node --version
```

### 升级风险等级

| 升级类型 | 风险等级 | 说明 |
|----------|----------|------|
| 小版本升级（如 2026.3.8 → 2026.3.11） | 🟡 中 | 通常安全，但仍需备份 |
| 大版本升级（如 2026.3.x → 2026.4.x） | 🔴 高 | 可能有破坏性变更 |
| 跨年度版本（如 2025.x → 2026.x） | 🔴 高 | 需仔细阅读 Changelog |

---

## 标准升级流程

### 步骤 1：备份当前配置

```bash
# 备份配置文件
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup.$(date +%Y%m%d_%H%M%S)

# 备份整个 .openclaw 目录（可选但推荐）
tar -czf ~/openclaw-backup-$(date +%Y%m%d_%H%M%S).tar.gz -C ~ .openclaw
```

### 步骤 2：停止 Gateway 服务

**⚠️ 关键步骤**：释放内存，避免升级过程中 OOM

```bash
# 停止服务
systemctl --user stop openclaw-gateway

# 确认服务已停止
systemctl --user status openclaw-gateway
# 应显示 "inactive (dead)"
```

### 步骤 3：清理 npm 缓存

```bash
# 清理缓存释放空间
npm cache clean --force

# 验证缓存大小
npm cache verify
```

### 步骤 4：执行升级

#### 方式 A：标准升级（内存 ≥ 2GB）

```bash
npm install -g openclaw@latest
```

#### 方式 B：内存受限升级（内存 < 2GB 或 Swap < 4GB）

```bash
# 设置 Node 内存限制后执行安装
NODE_OPTIONS="--max-old-space-size=1024" npm install -g openclaw@latest
```

**参数说明**：
- `--max-old-space-size=1024`：限制 Node.js 堆内存为 1024MB
- 可根据实际情况调整数值（512/1024/1536/2048）

### 步骤 5：验证安装

```bash
# 检查新版本
openclaw --version

# 查看更新日志（前 50 行）
head -50 /usr/lib/node_modules/openclaw/CHANGELOG.md
```

### 步骤 6：启动 Gateway 服务

```bash
# 启动服务
systemctl --user start openclaw-gateway

# 等待 5 秒后检查状态
sleep 5
systemctl --user status openclaw-gateway
```

### 步骤 7：功能验证

```bash
# 测试基本命令
openclaw status

# 测试 TUI 连接
openclaw tui --version
```

---

## 内存不足专项处理

### 问题现象

升级过程中出现以下错误：

```
Killed
# 或
npm ERR! code ENOMEM
npm ERR! errno 12
```

系统日志（`dmesg`）中出现：

```
Out of memory: Killed process xxxxx (npm install ope)
```

### 根本原因

1. **物理内存不足**：npm install 过程中需要解压大量文件、解析依赖树，内存占用可达 800MB+
2. **Gateway 服务占用**：运行中的 OpenClaw Gateway 常驻内存约 600MB+
3. **系统其他进程**：SSH、系统服务等占用剩余内存

### 解决方案

#### 方案 1：停止 Gateway 服务后升级（推荐）

```bash
# 1. 停止服务释放内存
systemctl --user stop openclaw-gateway

# 2. 执行升级
npm install -g openclaw@latest

# 3. 启动服务
systemctl --user start openclaw-gateway
```

**效果**：释放 600MB+ 内存，成功率 > 95%

#### 方案 2：增加 Swap 空间

如果当前 Swap < 4GB，建议扩容：

```bash
# 1. 创建 4GB Swap 文件
sudo dd if=/dev/zero of=/swapfile bs=1M count=4096

# 2. 设置权限
sudo chmod 600 /swapfile

# 3. 初始化 Swap
sudo mkswap /swapfile

# 4. 启用 Swap
sudo swapon /swapfile

# 5. 验证
free -h
```

**持久化配置**（重启后仍有效）：

```bash
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### 方案 3：限制 Node.js 内存使用

```bash
# 限制堆内存为 1024MB
NODE_OPTIONS="--max-old-space-size=1024" npm install -g openclaw@latest

# 或限制为 512MB（极端情况）
NODE_OPTIONS="--max-old-space-size=512" npm install -g openclaw@latest
```

**注意**：数值过小可能导致安装失败，建议从 1024 开始尝试。

#### 方案 4：组合方案（内存 < 1GB 时使用）

```bash
# 1. 停止服务
systemctl --user stop openclaw-gateway

# 2. 清理缓存
npm cache clean --force

# 3. 限制内存 + 执行升级
NODE_OPTIONS="--max-old-space-size=512" npm install -g openclaw@latest

# 4. 启动服务
systemctl --user start openclaw-gateway
```

---

## 故障排查指南

### 问题 1：升级后 Gateway 无法启动

**排查步骤**：

```bash
# 1. 查看详细错误
systemctl --user status openclaw-gateway --no-pager

# 2. 查看日志
journalctl --user -u openclaw-gateway -n 50

# 3. 手动运行查看错误
/usr/bin/node /usr/lib/node_modules/openclaw/dist/index.js gateway --port 18789
```

**常见原因**：
- 配置文件损坏 → 恢复备份：`cp ~/.openclaw/openclaw.json.bak ~/.openclaw/openclaw.json`
- 端口被占用 → 修改端口：`openclaw config set gateway.port 18790`
- 权限问题 → 检查：`ls -la ~/.openclaw/openclaw.json`

### 问题 2：升级过程中被 Kill

**排查步骤**：

```bash
# 1. 确认是 OOM 导致
dmesg | grep -i "killed process.*npm\|killed process.*openclaw"

# 2. 检查内存使用
free -h

# 3. 检查 Swap 使用
cat /proc/swaps
```

**解决方案**：参见 [内存不足专项处理](#内存不足专项处理)

### 问题 3：版本未更新

```bash
# 1. 确认全局安装路径
which openclaw

# 2. 检查 npm 全局路径
npm root -g

# 3. 如果路径不一致，使用完整路径
/usr/bin/npm install -g openclaw@latest
```

### 问题 4：插件丢失或失效

```bash
# 1. 查看已安装插件
openclaw plugins list

# 2. 重新安装插件
openclaw plugins install @larksuite/openclaw-lark

# 3. 检查插件配置
cat ~/.openclaw/openclaw.json | grep -A 5 "plugins"
```

---

## 预防措施

### 1. 定期备份

```bash
# 创建备份脚本
cat > ~/backup-openclaw.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="~/openclaw-backups"
mkdir -p $BACKUP_DIR
tar -czf "$BACKUP_DIR/openclaw-$(date +%Y%m%d_%H%M).tar.gz" -C ~ .openclaw
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
EOF

chmod +x ~/backup-openclaw.sh
```

### 2. 监控内存使用

```bash
# 添加到 crontab，每日检查
echo "0 3 * * * free -h > /var/log/memory-check.log 2>&1" | crontab -
```

### 3. 保持 Swap 充足

```bash
# 监控脚本
cat > ~/check-swap.sh << 'EOF'
#!/bin/bash
SWAP_TOTAL=$(free -m | awk '/Swap:/ {print $2}')
if [ "$SWAP_TOTAL" -lt 4096 ]; then
    echo "Warning: Swap 不足 4GB，当前 ${SWAP_TOTAL}MB"
fi
EOF
```

### 4. 升级前检查清单

- [ ] 已备份配置文件
- [ ] 已停止 Gateway 服务
- [ ] Swap ≥ 4GB 或物理内存 ≥ 2GB
- [ ] 磁盘空间 ≥ 1GB
- [ ] 已清理 npm 缓存

---

## 附录

### A. 相关命令速查

| 命令 | 说明 |
|------|------|
| `openclaw --version` | 查看版本 |
| `openclaw status` | 查看状态 |
| `openclaw doctor` | 诊断问题 |
| `openclaw doctor --fix` | 自动修复 |
| `systemctl --user stop openclaw-gateway` | 停止服务 |
| `systemctl --user start openclaw-gateway` | 启动服务 |
| `systemctl --user restart openclaw-gateway` | 重启服务 |

### B. 配置文件位置

| 文件 | 路径 |
|------|------|
| 主配置 | `~/.openclaw/openclaw.json` |
| 日志 | `~/.openclaw/logs/` |
| 备份 | `~/.openclaw/*.bak*` |
| 插件 | `~/.openclaw/extensions/` |

### C. 参考资源

- OpenClaw 官方文档: `/usr/lib/node_modules/openclaw/docs/`
- Changelog: `/usr/lib/node_modules/openclaw/CHANGELOG.md`
- 系统日志: `dmesg`, `journalctl --user -u openclaw-gateway`

### D. 历史问题记录

**2026-03-11 至 2026-03-16 升级事件**

- **问题**: 从 2026.3.8 升级至 2026.3.11 过程中多次 OOM
- **原因**: 系统内存 1.8GB，npm install 时内存不足
- **解决**: 
  1. 增加 4GB Swap
  2. 升级前停止 Gateway 服务
  3. 使用 `NODE_OPTIONS="--max-old-space-size=1024"` 限制内存
- **结果**: 升级成功，服务稳定运行

---

**文档维护**: 如遇新问题或解决方案更新，请同步修改本文档。
