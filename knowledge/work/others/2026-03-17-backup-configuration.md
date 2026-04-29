# 备份与恢复指南

## 概述

本工作区使用自动化脚本将关键配置和数据备份到NAS。备份每天凌晨2:00自动执行。

## 备份内容

### 目录结构

```
server-backup-YYYYMMDD.tar.gz
├── 01-sing-box/        - sing-box代理配置
├── 02-frp/             - FRP内网穿透配置
├── 03-scripts/         - 自动化脚本
├── 04-workspace/       - OpenClaw工作区核心文档
├── 05-openclaw-config/ - OpenClaw完整工作区打包
├── backup-info.json    - 备份元数据
└── README.txt          - 恢复说明
```

### 详细说明

| 目录 | 内容 | 本地路径 |
|------|------|----------|
| 01-sing-box | 网络代理配置 | `/etc/sing-box/config.json` |
| 02-frp | FRP服务端/客户端配置 | `/root/frp_0.60.0_linux_amd64/` |
| 03-scripts | 自动化脚本 | `/root/scripts/` |
| 04-workspace | 工作区核心文档 | `/root/.openclaw/workspace/*.md` |
| 05-openclaw-config | 完整工作区打包 | `/root/.openclaw/workspace/` |

### 核心文档说明

- **AGENTS.md** - 代理配置和行为规范
- **SOUL.md** - AI助手身份和性格定义
- **USER.md** - 用户配置和偏好
- **TOOLS.md** - 工具和环境特定配置
- **HEARTBEAT.md** - 定时任务配置
- **IDENTITY.md** - 身份标识

## 恢复操作

### 完整恢复

```bash
# 1. 解压备份包
tar -xzf server-backup-YYYYMMDD.tar.gz

# 2. 恢复sing-box
cp 01-sing-box/config.json /etc/sing-box/
docker restart sing-box

# 3. 恢复FRP
cp 02-frp/* /root/frp_0.60.0_linux_amd64/
systemctl restart frps

# 4. 恢复脚本
cp 03-scripts/* /root/scripts/

# 5. 恢复工作区核心文档
cp 04-workspace/* /root/.openclaw/workspace/

# 6. 恢复完整工作区（包含所有子目录）
tar -xzf 05-openclaw-config/openclaw-workspace.tar.gz -C /root/.openclaw/
```

### 仅恢复文档

```bash
# 从备份恢复核心文档
cp 04-workspace/*.md /root/.openclaw/workspace/
```

### 仅恢复工作区数据

```bash
# 恢复完整工作区（包含agents/, memory/, skills/等）
tar -xzf 05-openclaw-config/openclaw-workspace.tar.gz -C /root/.openclaw/
```

## 手动执行备份

```bash
bash /root/scripts/nas_backup.sh
```

## 定时任务

备份脚本通过cron每天凌晨2:00执行：

```
0 2 * * * /root/scripts/nas_backup.sh
```

## 备份存储位置

- **NAS地址**: `http://47.119.177.194:5005`
- **备份路径**: `/aliyun_backup/server-backup/YYYYMMDD/`
- **日志文件**: `/var/log/nas-backup.log`

## 注意事项

1. 完整工作区备份使用tar打包，排除了`.git`和`__pycache__`目录
2. 核心文档单独备份，方便快速查看和恢复
3. 恢复前建议先备份当前配置
4. 日志文件记录每次备份的详细信息和状态
