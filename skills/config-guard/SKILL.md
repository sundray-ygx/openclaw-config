---
name: config-guard
description: 核心配置防护 Skill - 防篡改与自动恢复。监控 OpenClaw 核心配置文件（openclaw.json、devices/paired.json）的完整性，检测到篡改时自动恢复并告警。
---

# Config Guard - 核心配置防护

## 防护目标

| 文件 | 重要性 | 防护方式 |
|------|--------|----------|
| `~/.openclaw/openclaw.json` | 🔴 核心配置 | 权限锁死 + 哈希校验 + 自动恢复 |
| `~/.openclaw/devices/paired.json` | 🔴 设备配对 | 权限锁死 + 备份保护 |
| `~/.openclaw/devices/pending.json` | 🟡 待处理配对 | 权限锁死 |

## 防护机制

### 1. 权限加固 (600)

所有核心配置文件设为仅所有者可读写：
```bash
chmod 600 ~/.openclaw/openclaw.json
chmod 600 ~/.openclaw/devices/paired.json
chmod 600 ~/.openclaw/openclaw.json.backup
```

### 2. 哈希基线校验

生成配置指纹，定期校验完整性：
```bash
# 生成基线
sha256sum ~/.openclaw/openclaw.json > ~/.openclaw/.config-baseline.sha256

# 校验
sha256sum -c ~/.openclaw/.config-baseline.sha256
```

### 3. 自动恢复

检测到篡改时自动从备份恢复：
```bash
if ! sha256sum -c ~/.openclaw/.config-baseline.sha256; then
    cp ~/.openclaw/openclaw.json.backup ~/.openclaw/openclaw.json
    # 重新生成基线
    sha256sum ~/.openclaw/openclaw.json > ~/.openclaw/.config-baseline.sha256
fi
```

### 4. 双任务冗余

同时配置系统 crontab 和 OpenClaw 内置定时任务：

**系统 crontab** (防止 OpenClaw 被禁用):
```cron
*/5 * * * * /root/.openclaw/scripts/check_config.sh
```

**OpenClaw cron** (防止系统 crontab 被清除):
```
openclaw cron add --name "config-guard" --schedule "*/5 * * * *" --payload "systemEvent:执行配置校验"
```

## 使用方式

### 初始化防护

```bash
# 1. 权限加固
chmod 600 ~/.openclaw/openclaw.json
chmod 600 ~/.openclaw/devices/paired.json

# 2. 创建备份
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup
chmod 600 ~/.openclaw/openclaw.json.backup

# 3. 生成哈希基线
sha256sum ~/.openclaw/openclaw.json > ~/.openclaw/.config-baseline.sha256

# 4. 配置系统 crontab
echo "*/5 * * * * /root/.openclaw/scripts/check_config.sh" | crontab -
```

### 手动校验

```bash
# 校验配置完整性
sha256sum -c ~/.openclaw/.config-baseline.sha256

# 或执行防护脚本
bash /root/.openclaw/scripts/check_config.sh
```

### 更新基线（授权修改后）

```bash
# 修改配置后重新生成基线
sha256sum ~/.openclaw/openclaw.json > ~/.openclaw/.config-baseline.sha256

# 同步更新备份
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup
```

## 告警通知

检测到篡改时：
1. 自动恢复配置
2. 记录安全事件到 `memory/security-alerts-config.md`
3. 创建待发送告警标记 `.config-tamper-alert-pending`
4. 通过飞书插件推送给管理员

## 日志位置

- 防护日志: `/var/log/openclaw-config-guard.log`
- 安全事件: `~/.openclaw/memory/security-alerts-config.md`
- 告警队列: `~/.openclaw/memory/.config-tamper-alert-pending`

## 安全原则

- **任何配置修改必须通过授权流程**
- **修改后必须更新基线和备份**
- **告警信息必须推送给管理员**
- **双任务冗余确保防护不被绕过**