# OpenClaw 升级执行计划

> **计划版本**: 1.0  
> **制定日期**: 2026-03-24  
> **当前版本**: OpenClaw 2026.3.11  
> **目标版本**: 待确认（latest）  
> **执行人**: 小助  
> **审批人**: Boss

---

## 执行摘要

<callout emoji="📋" background-color="light-blue">
本计划基于《OpenClaw升级指导文档》(v1.0)制定，针对内存不足(OOM)问题提供专项处理方案，确保升级过程安全可控。
</callout>

---

## 一、升级前检查清单

### 1.1 系统资源检查

```bash
# 执行以下命令检查当前环境

# 1. 检查内存和 Swap
free -h

# 2. 检查磁盘空间
df -h ~

# 3. 检查当前 OpenClaw 版本
openclaw --version

# 4. 检查 Gateway 服务状态
systemctl status openclaw-gateway

# 5. 检查 Node.js 版本
node --version
```

**预期输出示例**:
```
$ free -h
              total        used        free      shared  buff/cache   available
Mem:           15Gi       2.1Gi       9.8Gi       1.0Mi       3.5Gi        12Gi
Swap:         4.0Gi       512Mi       3.5Gi

$ openclaw --version
2026.3.11
```

### 1.2 检查项确认表

| 检查项 | 最低要求 | 当前状态 | 是否满足 |
|--------|----------|----------|----------|
| 物理内存 | ≥ 2GB | 待检查 | ⬜ |
| Swap | ≥ 4GB | 待检查 | ⬜ |
| 磁盘空间 | ≥ 1GB | 待检查 | ⬜ |
| Node.js | ≥ 18.x | 待检查 | ⬜ |

---

## 二、升级执行步骤

### 阶段一：升级前准备（预计 5 分钟）

#### 步骤 1.1：停止 Gateway 服务

```bash
# 停止服务释放内存（关键步骤！）
systemctl stop openclaw-gateway

# 确认服务已停止
systemctl status openclaw-gateway
# 应显示 "inactive (dead)"
```

**预期结果**: Gateway 服务停止，释放约 600MB 内存

---

#### 步骤 1.2：备份当前配置

```bash
# 创建备份目录
mkdir -p /root/openclaw-backups/$(date +%Y%m%d)

# 备份配置文件
cp /root/.openclaw/openclaw.json /root/openclaw-backups/$(date +%Y%m%d)/openclaw.json.backup

# 备份整个 .openclaw 目录
tar -czf /root/openclaw-backups/$(date +%Y%m%d)/openclaw-full-backup-$(date +%Y%m%d_%H%M%S).tar.gz -C /root .openclaw

# 验证备份
ls -lh /root/openclaw-backups/$(date +%Y%m%d)/
```

**预期结果**: 备份文件创建成功，大小约 50-200MB

---

#### 步骤 1.3：清理 npm 缓存

```bash
# 清理缓存释放空间
npm cache clean --force

# 验证缓存大小
npm cache verify
```

**预期结果**: 缓存清理完成，释放磁盘空间

---

### 阶段二：执行升级（预计 10-15 分钟）

#### 步骤 2.1：选择升级方式

根据系统内存情况选择升级方式：

<grid cols="2">
<column>

**方式 A：标准升级**
适用：内存 ≥ 2GB 且 Swap ≥ 4GB

```bash
npm install -g openclaw@latest
```

</column>
<column>

**方式 B：内存受限升级**
适用：内存 < 2GB 或 Swap < 4GB

```bash
NODE_OPTIONS="--max-old-space-size=1024" npm install -g openclaw@latest
```

</column>
</grid>

---

#### 步骤 2.2：监控升级过程

```bash
# 在另一个终端监控内存使用
watch -n 5 'free -h && echo "---" && ps aux --sort=-%mem | head -10'
```

**关键观察点**:
- 内存使用率不超过 90%
- Swap 使用率不超过 80%
- npm 进程正常运行，无 "Killed" 或 "ENOMEM" 错误

---

#### 步骤 2.3：处理升级中断（如发生 OOM）

如果升级过程中出现 OOM，执行以下应急方案：

```bash
# 1. 确认是 OOM 导致
dmesg | tail -20 | grep -i "killed process"

# 2. 检查当前内存
free -h

# 3. 如果 Swap 不足，增加 Swap
sudo dd if=/dev/zero of=/swapfile2 bs=1M count=4096
sudo chmod 600 /swapfile2
sudo mkswap /swapfile2
sudo swapon /swapfile2

# 4. 重新执行升级（使用内存限制）
NODE_OPTIONS="--max-old-space-size=512" npm install -g openclaw@latest
```

---

### 阶段三：升级后验证（预计 5 分钟）

#### 步骤 3.1：验证安装

```bash
# 检查新版本
openclaw --version

# 查看更新日志
head -100 /usr/lib/node_modules/openclaw/CHANGELOG.md
```

**预期结果**: 版本号更新，无报错信息

---

#### 步骤 3.2：启动 Gateway 服务

```bash
# 启动服务
systemctl start openclaw-gateway

# 等待 5 秒
sleep 5

# 检查状态
systemctl status openclaw-gateway
```

**预期结果**: 服务状态为 "active (running)"

---

#### 步骤 3.3：功能验证

```bash
# 测试基本命令
openclaw status

# 测试 TUI 连接
openclaw tui --version

# 测试插件列表
openclaw plugins list
```

**预期结果**: 所有命令正常执行，无报错

---

#### 步骤 3.4：验证定时任务

```bash
# 检查 cron 任务
openclaw cron list | head -20

# 检查 cron 服务状态
openclaw cron status
```

**预期结果**: 所有定时任务正常显示，状态为 ok 或 idle

---

## 三、回滚方案

### 3.1 回滚触发条件

以下情况触发回滚：
- Gateway 服务无法启动
- 核心功能异常（如定时任务全部失败）
- 持续 30 分钟无法恢复正常

### 3.2 回滚步骤

```bash
# 1. 停止服务
systemctl stop openclaw-gateway

# 2. 降级到旧版本
npm install -g openclaw@2026.3.11

# 3. 恢复配置
cp /root/openclaw-backups/$(date +%Y%m%d)/openclaw.json.backup /root/.openclaw/openclaw.json

# 4. 启动服务
systemctl start openclaw-gateway

# 5. 验证
openclaw status
```

---

## 四、执行时间安排

### 建议执行时间窗口

| 时间窗口 | 建议 | 原因 |
|----------|------|------|
| 22:30 - 23:00 | ✅ 推荐 | 业务低峰期，定时任务未开始 |
| 00:00 - 06:00 | ✅ 可选 | 夜间维护窗口 |
| 08:00 - 20:00 | ❌ 不推荐 | 业务高峰期，定时任务密集 |

### 预计耗时

| 阶段 | 预计时间 | 备注 |
|------|----------|------|
| 阶段一：升级前准备 | 5 分钟 | 备份 + 停止服务 |
| 阶段二：执行升级 | 10-15 分钟 | 下载 + 安装 |
| 阶段三：升级后验证 | 5 分钟 | 验证 + 启动 |
| **总计** | **20-25 分钟** | 含缓冲时间 |

---

## 五、风险与应对

<lark-table column-widths="200,300,300" header-row="true">
<lark-tr>
<lark-td>

**风险**

</lark-td>
<lark-td>

**可能性**

</lark-td>
<lark-td>

**应对措施**

</lark-td>
</lark-tr>
<lark-tr>
<lark-td>

升级过程 OOM

</lark-td>
<lark-td>

中（内存 < 2GB 时高）

</lark-td>
<lark-td>

1. 停止 Gateway 服务
2. 增加 Swap
3. 使用 NODE_OPTIONS 限制内存

</lark-td>
</lark-tr>
<lark-tr>
<lark-td>

Gateway 无法启动

</lark-td>
<lark-td>

低

</lark-td>
<lark-td>

1. 检查日志定位问题
2. 恢复配置备份
3. 执行回滚

</lark-td>
</lark-tr>
<lark-tr>
<lark-td>

定时任务丢失

</lark-td>
<lark-td>

低

</lark-td>
<lark-td>

1. 从备份恢复 cron/jobs.json
2. 重新创建任务

</lark-td>
</lark-tr>
<lark-tr>
<lark-td>

插件失效

</lark-td>
<lark-td>

中

</lark-td>
<lark-td>

1. 重新安装插件
2. 检查插件配置

</lark-td>
</lark-tr>
</lark-table>

---

## 六、执行确认

### 执行前确认清单

- [ ] 已确认升级时间窗口（建议 22:30 后）
- [ ] 已检查系统资源（内存、Swap、磁盘）
- [ ] 已备份当前配置
- [ ] 已通知相关人员（如需要）
- [ ] 已准备回滚方案

### 执行后确认清单

- [ ] Gateway 服务正常启动
- [ ] openclaw status 命令正常
- [ ] 定时任务列表正常
- [ ] 飞书插件功能正常
- [ ] 备份文件已保存

---

## 七、参考文档

| 文档 | 路径 |
|------|------|
| OpenClaw 升级指导文档 | `/root/.openclaw/workspace/knowledge/tech/openclaw/openclaw-upgrade-guide.md` |
| 本执行计划 | `/root/.openclaw/workspace/knowledge/tech/openclaw/openclaw-upgrade-plan-2026-03-24.md` |

---

<callout emoji="✅" background-color="light-green" border-color="green">
**计划制定完成**

本计划基于历史升级经验制定，针对内存不足问题提供了专项处理方案。建议在 22:30 后的维护窗口执行，执行前请确认 Boss 审批。
</callout>

---

*计划制定时间: 2026-03-24 19:20 CST*  
*制定人: 小助*  
*状态: 待审批*
