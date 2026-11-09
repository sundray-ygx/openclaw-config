# NAS 备份系统说明文档

## 概述

本系统是一个基于 WebDAV 的服务器自动备份解决方案，每天凌晨2:00自动执行，将服务器的关键配置和文档备份到远程 NAS 存储设备。

## 系统架构

### 备份源
- **服务器**: 47.119.177.194 (阿里云轻量应用服务器)
- **操作系统**: Linux 5.10.134-19.2.al8.x86_64
- **主要应用**: sing-box代理、FRP内网穿透、OpenClaw AI助手

### 备份目标
- **WebDAV服务器**: http://47.119.177.194:5005
- **备份路径**: /aliyun_backup/server-backup/
- **备份频率**: 每日凌晨2:00

### 备份配置
- **WebDAV用户**: aliyun-ygx
- **WebDAV密码**: %dOr91[#
- **备份版本**: 3.0 (Workspace结构优化版本)

## 备份内容结构

```
server-backup-YYYYMMDD.tar.gz
├── 01-sing-box/              # 网络代理配置
│   └── config.json           # sing-box代理节点配置
├── 02-frp/                   # 内网穿透配置
│   ├── frps.toml            # FRP服务端配置
│   ├── frpc.toml            # FRP客户端配置
│   ├── frps                 # FRP服务端程序
│   └── frpc                 # FRP客户端程序
├── 03-scripts/              # 自动化脚本
│   ├── morning_briefing.py  # 早间简报生成
│   ├── daily_report.py      # 工作日报生成
│   ├── nas_backup.sh        # 本备份脚本
│   └── rss_news_fetch.py    # RSS资讯抓取
├── 04-workspace/            # OpenClaw工作区核心文档
│   ├── AGENTS.md           # 代理配置和行为规范
│   ├── SOUL.md             # AI助手身份和性格
│   ├── USER.md             # 用户配置
│   ├── TOOLS.md            # 工具和环境配置
│   ├── HEARTBEAT.md        # 定时任务配置
│   └── IDENTITY.md        # 身份标识
├── 05-openclaw-config/     # OpenClaw完整配置
│   └── openclaw-workspace.tar.gz  # 完整工作区打包
├── 06-security-scripts/    # 安全基线脚本
│   ├── check_config.sh      # 配置防护检查
│   ├── monitor-suspicious-process.sh  # 可疑进程监控
│   └── self-integrity-check.sh  # 脚本完整性自检
├── backup-info.json        # 备份元数据
└── README.txt              # 恢复说明文档
```

## 核心功能

### 1. 自动化备份
- 使用 cron 定时任务，每日凌晨2:00自动执行
- 支持完整的目录结构和文件备份
- 自动生成备份说明文档
- 自动清理临时文件

### 2. 增量备份策略
- 每日创建独立的备份目录
- 按功能模块分类备份
- 排除不必要的文件（如.git、__pycache__等）

### 3. WebDAV 远程同步
- 支持标准的 WebDAV 协议
- 自动创建远程目录结构
- 支持断点续传和错误重试

### 4. 完整性验证
- 自动生成备份信息文件
- 支持备份文件完整性检查
- 详细的操作日志记录

## 备份脚本详细说明

### 脚本路径
```
/root/.openclaw/workspace/scripts/backup/nas_backup.sh
```

### 执行方式
```bash
# 手动执行
/root/.openclaw/workspace/scripts/backup/nas_backup.sh

# 或通过 cron
0 2 * * * /root/.openclaw/workspace/scripts/backup/nas_backup.sh
```

### 主要功能模块

#### 1. 配置备份
- **sing-box配置**: `/etc/sing-box/config.json`
- **FRP配置**: `/root/frp_0.60.0_linux_amd64/` 目录下的所有文件
- **OpenClaw核心文档**: `/home/openclaw/.openclaw/workspace/` 目录下的配置文件

#### 2. 脚本备份
- 早间简报生成脚本
- 工作日报生成脚本
- NAS备份脚本
- RSS资讯抓取脚本

#### 3. 完整工作区备份
- 使用 tar 命令打包整个 OpenClaw 工作区
- 排除不必要的文件和目录
- 保持原有的目录结构

#### 4. 安全脚本备份
- 配置防护检查脚本
- 可疑进程监控脚本
- 脚本完整性自检脚本

### 错误处理
- 自动处理 WebDAV 连接错误
- 支持 HTTP 状态码检查
- 详细的错误日志记录
- 失败重试机制

## 恢复操作指南

### 1. 恢复 sing-box 代理配置
```bash
# 解压备份文件
tar -xzf server-backup-YYYYMMDD.tar.gz

# 恢复配置
cp 01-sing-box/config.json /etc/sing-box/

# 重启服务
docker restart sing-box
```

### 2. 恢复 FRP 内网穿透配置
```bash
# 解压备份文件
tar -xzf server-backup-YYYYMMDD.tar.gz

# 恢复配置和程序
cp 02-frp/* /root/frp_0.60.0_linux_amd64/

# 重启服务
systemctl restart frps
```

### 3. 恢复自动化脚本
```bash
# 解压备份文件
tar -xzf server-backup-YYYYMMDD.tar.gz

# 恢复脚本
cp 03-scripts/* /home/openclaw/.openclaw/workspace/scripts/
```

### 4. 恢复 OpenClaw 工作区核心文档
```bash
# 解压备份文件
tar -xzf server-backup-YYYYMMDD.tar.gz

# 恢复核心配置文件
cp 04-workspace/* /home/openclaw/.openclaw/workspace/
```

### 5. 恢复完整 OpenClaw 工作区
```bash
# 解压备份文件
tar -xzf server-backup-YYYYMMDD.tar.gz

# 恢复完整工作区
tar -xzf 05-openclaw-config/openclaw-workspace.tar.gz -C /home/openclaw/.openclaw/
```

## 服务管理命令

### sing-box 代理服务
```bash
# 查看容器状态
docker ps | grep sing-box

# 重启 sing-box
docker restart sing-box

# 查看 sing-box 日志
docker logs sing-box
```

### FRP 内网穿透服务
```bash
# 查看服务状态
systemctl status frps

# 重启服务
systemctl restart frps

# 查看服务日志
journalctl -u frps -f
```

### OpenClaw 服务测试
```bash
# 测试早间简报
python3 /home/openclaw/.openclaw/workspace/scripts/briefing/morning_briefing.py

# 测试工作日报
python3 /home/openclaw/.openclaw/workspace/scripts/daily/daily_report.py
```

## 定时任务配置

### 早间简报
- **时间**: 每天8:00
- **脚本**: `/home/openclaw/.openclaw/workspace/scripts/briefing/morning_briefing.py`
- **功能**: 生成每日工作简报

### OpenClaw 资讯推送
- **时间**: 每天8:00
- **脚本**: `/home/openclaw/.openclaw/workspace/scripts/news/rss_news_fetch.py`
- **功能**: 抓取和推送新闻资讯

### 工作日报生成
- **时间**: 每天22:00
- **脚本**: `/home/openclaw/.openclaw/workspace/scripts/daily/daily_report.py`
- **功能**: 生成每日工作总结

### NAS 自动备份
- **时间**: 每天2:00
- **脚本**: `/root/.openclaw/workspace/scripts/backup/nas_backup.sh`
- **功能**: 自动备份服务器配置和数据

## 监控和日志

### 日志文件位置
```bash
/var/log/nas-backup.log
```

### 监控要点
- 备份任务执行时间
- WebDAV 上传状态
- 错误信息和警告
- 备份文件大小变化

### 常见问题解决
1. **WebDAV 连接失败**: 检查网络连接和服务器状态
2. **上传失败**: 检查存储空间和权限设置
3. **脚本执行错误**: 检查文件路径和权限

## 安全注意事项

### 数据安全
- WebDAV 密码已加密存储
- 备份文件包含敏感信息，需妥善保管
- 定期更换 WebDAV 密码

### 访问控制
- 限制 WebDAV 服务器的访问权限
- 使用 HTTPS 协议进行数据传输
- 定期审计访问日志

### 备份验证
- 定期验证备份文件的完整性
- 测试恢复流程的有效性
- 保持多个备份副本

## 版本历史

### 版本 3.0 (当前版本)
- 优化目录结构，按功能模块分类
- 增加安全脚本备份
- 改进 WebDAV 上传流程
- 增强错误处理和日志记录

### 版本 2.0
- 增加 OpenClaw 工作区完整备份
- 改进备份策略和效率
- 增加恢复说明文档

### 版本 1.0
- 初始版本，基本备份功能
- 支持核心配置文件备份
- WebDAV 远程同步

## 联系信息

如有问题或建议，请联系系统管理员。

---
**文档版本**: 1.0  
**更新时间**: 2026-03-31  
**维护人员**: 系统管理员