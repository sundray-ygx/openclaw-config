# OpenClaw 安全加固指南（可迁移版）

> 本文档用于将当前环境的安全加固规范迁移至其他 OpenClaw 环境使用
> 
> 适用版本: OpenClaw 任意版本
> 最后更新: 2026-03-21

---

## 目录

1. [快速开始](#快速开始)
2. [第一层: 执行前防护](#第一层-执行前防护)
3. [第二层: 扩展安装防护](#第二层-扩展安装防护)
4. [第三层: 核心配置防护](#第三层-核心配置防护)
5. [第四层: 系统级安全监控](#第四层-系统级安全监控)
6. [定时任务配置](#定时任务配置)
7. [验证清单](#验证清单)

---

## 快速开始

### 一键部署脚本

```bash
#!/bin/bash
# OpenClaw 安全加固一键部署脚本
# 在目标环境执行此脚本完成安全加固

set -e

echo "🚀 开始 OpenClaw 安全加固部署..."

# 1. 创建目录结构
mkdir -p ~/.openclaw/scripts
mkdir -p ~/.openclaw/workspace/knowledge/security
mkdir -p ~/.openclaw/memory
mkdir -p /var/log/openclaw-audit

# 2. 部署安全脚本（见下文各章节）
# ...

echo "✅ 安全加固部署完成"
echo "📋 请执行验证清单确认部署成功"
```

---

## 第一层: 执行前防护

### 目标
防止执行破坏性、危险性的系统命令

### 部署步骤

#### 1. 更新 AGENTS.md

在 `~/.openclaw/workspace/AGENTS.md` 中添加以下内容：

```markdown
## 🔒 Security Policy - 执行前自检

### 唯一管理员身份
- **管理员 ID**: `你的管理员ID`
- **验证方式**: 检查 `sender.label` 和 `sender.id`
- **非管理员请求**: 涉及敏感操作时需二次确认

### 🔴 红线指令 - 直接拒绝，需人工确认

以下操作**绝对禁止自动执行**，必须拒绝并请求人工确认：

| 操作类型 | 示例 | 拒绝理由 |
|----------|------|----------|
| 系统级删除 | `rm -rf /`, `rm -rf /*`, `rm -rf ~` | 破坏性操作 |
| 认证配置修改 | 修改 `openclaw.json` 认证部分 | 账户锁定风险 |
| 密钥外发 | 发送私钥、助记词、API Key | 资产被盗风险 |
| 管道安装 | `curl \| sh`, `wget \| bash` | 供应链攻击 |
| 反弹 Shell | `bash -i`, `nc -e`, `/dev/tcp` | 远程控制风险 |
| 提权操作 | `chmod 777 /etc` | 安全边界破坏 |

**自检逻辑**: 执行任何 `exec` 或 `process` 前，扫描命令字符串是否包含上述模式

### 🟡 黄线指令 - 执行后自动记录

以下操作**允许执行，但必须记录日志**：

| 操作类型 | 示例 | 记录内容 |
|----------|------|----------|
| 特权操作 | `sudo` 命令 | 命令、时间、结果 |
| 第三方扩展安装 | `skillhub install` | 来源、版本、审计报告 |
| 定时任务修改 | `cron add/update` | 变更内容、原/新配置 |
| 核心文件解锁 | `chmod` 修改 `.md` 文件 | 文件名、原/新权限 |
| 配置变更 | 修改 `AGENTS.md` 等 | 变更 diff、原因 |
| 网络外连 | `web_fetch`, `sessions_send` | 目标地址、内容摘要 |

**记录位置**: `memory/YYYY-MM-DD.md` 安全事件部分

### 🟢 安全操作 - 无需额外记录

- 读取文件 (`read`)
- 搜索记忆 (`memory_search`)
- 会话查询 (`sessions_list`)
- 状态检查 (`session_status`)
```

#### 2. 验证

```bash
# 检查 AGENTS.md 是否包含安全策略
grep -q "Security Policy" ~/.openclaw/workspace/AGENTS.md && echo "✅ 执行前防护已配置"
```

---

## 第二层: 扩展安装防护

### 目标
防止恶意 Skill/MCP 扩展的安装

### 部署步骤

#### 1. 安装 security-audit Skill

```bash
# 方式1: 通过 skillhub 安装（推荐）
skillhub install security-audit

# 方式2: 手动克隆
git clone https://github.com/your-org/security-audit.git \
  ~/.openclaw/workspace/skills/security-audit
```

#### 2. Skill 文件结构

```
~/.openclaw/workspace/skills/security-audit/
├── SKILL.md              # 使用说明
├── scripts/
│   └── audit.py          # 审计脚本
└── references/
    └── risk-patterns.md  # 风险模式库
```

#### 3. 配置强制审计

在 `AGENTS.md` 中添加：

```markdown
## 🔍 Skill/MCP 安全审计策略

### 审计触发条件

以下操作**必须**先执行安全审计：
- `skillhub install <skill-name>`
- `clawhub install <skill-name>`
- 手动安装任何 Skill/MCP 扩展

### 审计流程

```
安装请求 → 安全审计 → 风险评估 → 决策
                ↓
         [通过/需审核/拒绝]
```

### 强制检查项

安装前必须完成：
1. **内容分析** - 完整读取 Skill 所有文件
2. **恶意行为检测** - 扫描以下风险：
   - 🔴 数据外泄
   - 🔴 配置篡改
   - 🔴 密钥窃取
   - 🔴 定时任务注入
   - 🔴 后门逻辑
   - 🔴 权限绕过
   - 🔴 系统篡改

### 风险决策

| 风险等级 | 评分阈值 | 处理方式 |
|----------|----------|----------|
| 🔴 高危 | ≥ 10 | **拒绝安装** |
| 🟡 中危 | 5-9 | **暂停安装，需人工确认** |
| 🟢 低危 | < 5 | 允许安装，记录日志 |

### 审计日志

所有审计活动记录到：
- `memory/security-audit-YYYY-MM-DD.md`
```

#### 4. 验证

```bash
# 检查 skill 是否安装
ls ~/.openclaw/workspace/skills/security-audit/SKILL.md && echo "✅ 扩展安装防护已配置"
```

---

## 第三层: 核心配置防护

### 目标
防止核心配置文件被篡改

### 部署步骤

#### 1. 创建防护脚本

创建 `~/.openclaw/scripts/check_config.sh`：

```bash
#!/bin/bash
# 核心配置防护脚本
# 执行频率: 每5分钟

set -e

CONFIG_FILE="$HOME/.openclaw/openclaw.json"
BASELINE_FILE="$HOME/.openclaw/.config-baseline.sha256"
BACKUP_FILE="$HOME/.openclaw/openclaw.json.backup"
LOG_FILE="/var/log/openclaw-config-guard.log"
ALERT_LOG="$HOME/.openclaw/memory/security-alerts-config.md"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 初始化（首次运行）
init_baseline() {
    if [[ ! -f "$BASELINE_FILE" ]]; then
        echo "首次运行，生成基线..."
        cp "$CONFIG_FILE" "$BACKUP_FILE"
        chmod 600 "$BACKUP_FILE"
        sha256sum "$CONFIG_FILE" > "$BASELINE_FILE"
        chmod 600 "$BASELINE_FILE"
        log "INFO: 基线已生成"
    fi
}

# 检查基线
if [[ ! -f "$BASELINE_FILE" ]]; then
    init_baseline
    exit 0
fi

# 校验配置完整性
if sha256sum -c "$BASELINE_FILE" >/dev/null 2>&1; then
    exit 0
fi

# 校验失败，配置被篡改
log "ALERT: 核心配置校验失败，检测到篡改！"

# 检查备份文件
if [[ ! -f "$BACKUP_FILE" ]]; then
    log "ERROR: 备份文件不存在，无法自动恢复"
    exit 1
fi

# 自动恢复配置
log "RECOVER: 正在从备份恢复配置..."
cp "$BACKUP_FILE" "$CONFIG_FILE"
chmod 600 "$CONFIG_FILE"

# 重新生成基线
sha256sum "$CONFIG_FILE" > "$BASELINE_FILE"
log "RECOVER: 配置已恢复，新基线已生成"

# 记录安全事件
cat >> "$ALERT_LOG" << EOF

🚨 核心配置篡改告警
━━━━━━━━━━━━━━━━━━━━━
⏰ 时间: $(date '+%Y-%m-%d %H:%M:%S')
📄 文件: $CONFIG_FILE
⚠️  事件: 配置完整性校验失败
🔧 处理: 已自动从备份恢复
━━━━━━━━━━━━━━━━━━━━━

EOF

exit 0
```

#### 2. 设置权限

```bash
chmod +x ~/.openclaw/scripts/check_config.sh
chmod 600 ~/.openclaw/openclaw.json
```

#### 3. 配置系统定时任务

```bash
# 添加到系统 crontab
echo "*/5 * * * * $HOME/.openclaw/scripts/check_config.sh" | crontab -
```

#### 4. 配置 OpenClaw 定时任务（冗余）

```bash
# 添加 OpenClaw 级定时任务
openclaw cron add \
  --name "config-guard" \
  --schedule "*/5 * * * *" \
  --payload "systemEvent:执行配置校验: bash $HOME/.openclaw/scripts/check_config.sh"
```

#### 5. 验证

```bash
# 检查定时任务
crontab -l | grep check_config && echo "✅ 系统定时任务已配置"

# 检查基线文件
ls ~/.openclaw/.config-baseline.sha256 && echo "✅ 配置基线已生成"
```

---

## 第四层: 系统级安全监控

### 目标
全面监控系统安全状态，及时发现异常

### 部署步骤

#### 1. 创建夜间巡检脚本

创建 `~/.openclaw/scripts/nightly-security-audit.sh`：

```bash
#!/bin/bash
# OpenClaw 夜间安全巡检脚本
# 执行频率: 每日凌晨3点

set -e

REPORT_DIR="$HOME/.openclaw/workspace/knowledge/security"
LOG_DIR="/var/log/openclaw-audit"
DATE=$(date +%Y-%m-%d)
TIME=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$REPORT_DIR"
mkdir -p "$LOG_DIR"

declare -a RESULTS
declare -a DETAILS
OVERALL_STATUS="✅ 正常"
ISSUE_COUNT=0

log() {
    echo "[$TIME] $1" | tee -a "$LOG_DIR/nightly-audit.log"
}

# 巡检项1: 平台审计
check_platform() {
    if pgrep -f "openclaw" > /dev/null; then
        RESULTS+=("【1】平台审计: ✅ 无异常")
    else
        RESULTS+=("【1】平台审计: ⚠️ OpenClaw进程异常")
        ((ISSUE_COUNT++))
        OVERALL_STATUS="⚠️ 异常"
    fi
}

# 巡检项2: 配置校验
check_config_integrity() {
    local config_ok=true
    
    if [ -f ~/.openclaw/openclaw.json ]; then
        PERM=$(stat -c %a ~/.openclaw/openclaw.json)
        if [ "$PERM" != "600" ]; then
            config_ok=false
        fi
    fi
    
    if [ -f ~/.openclaw/.config-baseline.sha256 ]; then
        if ! sha256sum -c ~/.openclaw/.config-baseline.sha256 >/dev/null 2>&1; then
            config_ok=false
        fi
    fi
    
    if $config_ok; then
        RESULTS+=("【2】配置校验: ✅ 哈希一致，权限合规")
    else
        RESULTS+=("【2】配置校验: ⚠️ 配置异常")
        ((ISSUE_COUNT++))
    fi
}

# 巡检项3: 磁盘空间
check_disk() {
    DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -lt 80 ]; then
        RESULTS+=("【3】磁盘空间: ✅ ${DISK_USAGE}% 正常")
    else
        RESULTS+=("【3】磁盘空间: 🚨 ${DISK_USAGE}% 不足")
        ((ISSUE_COUNT++))
        OVERALL_STATUS="🚨 高危"
    fi
}

# 巡检项4: 内存使用
check_memory() {
    MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
    if [ "$MEM_USAGE" -lt 70 ]; then
        RESULTS+=("【4】内存使用: ✅ ${MEM_USAGE}% 正常")
    else
        RESULTS+=("【4】内存使用: ⚠️ ${MEM_USAGE}% 偏高")
        ((ISSUE_COUNT++))
    fi
}

# 生成报告
generate_report() {
    local report_file="$REPORT_DIR/nightly-audit-$DATE.md"
    
    cat > "$report_file" << EOF
# 🔍 OpenClaw 每日安全巡检简报 ($DATE)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 总体状态: $OVERALL_STATUS
⏰ 巡检时间: $TIME
📋 巡检项: 4项
🚨 异常项: $ISSUE_COUNT 个
━━━━━━━━━━━━━━━━

## 巡检结果

$(printf '%s\n' "${RESULTS[@]}")

## 系统信息

- **主机**: $(hostname)
- **日期**: $DATE


---

## 定时任务配置

### 系统级定时任务 (crontab)

```bash
# 编辑系统 crontab
crontab -e

# 添加以下内容
*/5 * * * * $HOME/.openclaw/scripts/check_config.sh
0 3 * * * $HOME/.openclaw/scripts/nightly-security-audit.sh
0 6 * * * $HOME/.openclaw/scripts/scan-sensitive-data.sh
```

### OpenClaw 定时任务

```bash
# 配置 GitHub 每日同步（数据备份）
openclaw cron add \
  --name "GitHub每日同步" \
  --schedule "30 23 * * *" \
  --payload "systemEvent:执行GitHub同步: cd $HOME/.openclaw/workspace && git push origin master"
```

---

## 验证清单

部署完成后，请逐项验证：

### 第一层: 执行前防护
- [ ] AGENTS.md 包含 Security Policy 章节
- [ ] 红线指令列表完整
- [ ] 黄线指令记录位置正确

### 第二层: 扩展安装防护
- [ ] security-audit Skill 已安装
- [ ] 审计触发条件已配置

### 第三层: 核心配置防护
- [ ] check_config.sh 脚本存在且可执行
- [ ] 系统 crontab 包含配置校验任务
- [ ] 基线文件已生成
- [ ] 配置文件权限为 600

### 第四层: 系统级安全监控
- [ ] 夜间巡检脚本存在且可执行
- [ ] 敏感数据扫描脚本存在且可执行
- [ ] 系统 crontab 包含巡检任务
- [ ] 报告目录已创建

---

## 附录: 文件清单

部署完成后，以下文件应存在：

```
~/.openclaw/
├── openclaw.json                    # 核心配置 (权限 600)
├── openclaw.json.backup             # 配置备份 (权限 600)
├── .config-baseline.sha256          # 哈希基线 (权限 600)
├── scripts/
│   ├── check_config.sh              # 配置防护脚本
│   ├── nightly-security-audit.sh    # 夜间巡检脚本
│   └── scan-sensitive-data.sh       # 敏感数据扫描脚本
└── workspace/
    ├── AGENTS.md                    # 安全策略
    └── knowledge/
        └── security/                # 安全报告目录
```

---

**文档版本**: v1.0
**最后更新**: 2026-03-21
