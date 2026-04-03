# NAS自动备份系统文档

## 概述

NAS自动备份系统是一个专门为服务器环境设计的自动化备份解决方案，采用WebDAV协议将重要数据备份到远程存储服务器。该系统每天凌晨2:00自动执行，确保关键配置和工作区的安全备份。

### 主要特性

- **定时自动备份**: 每天凌晨2:00自动执行
- **结构化备份**: 按功能分类组织备份内容
- **WebDAV上传**: 自动上传到远程备份服务器
- **详细文档**: 每次备份生成完整的恢复说明文档
- **日志记录**: 详细的备份过程日志记录

### 备份服务器信息

- **WebDAV URL**: `http://47.119.177.194:5005`
- **基础路径**: `/aliyun_backup/server-backup/`
- **访问认证**: WebDAV用户认证
- **存储位置**: 按日期分类存储 `YYYYMMDD/` 目录

---

## 备份脚本详解

### 脚本位置
`/root/.openclaw/workspace/scripts/backup/nas_backup.sh`

### 执行权限
```bash
chmod +x /root/.openclaw/workspace/scripts/backup/nas_backup.sh
```

### 手动执行
```bash
/root/.openclaw/workspace/scripts/backup/nas_backup.sh
```

### 配置参数

```bash
# WebDAV服务器配置
WEBDAV_URL="http://47.119.177.194:5005"
WEBDAV_USER="aliyun-ygx"
WEBDAV_PASS='%dOr91[#'
WEBDAV_BASE="/aliyun_backup/server-backup"

# 本地临时目录
LOCAL_BACKUP_DIR="/tmp/backup-$BACKUP_DATE"

# 日志文件
LOG_FILE="/var/log/nas-backup.log"
```

---

## 备份内容结构

### 1. 网络代理配置 (01-sing-box/)
```
01-sing-box/
└── config.json                    # sing-box代理节点配置
```

**包含内容**:
- `/etc/sing-box/config.json` - 网络代理主配置文件

**恢复命令**:
```bash
cp /aliyun_backup/server-backup/日期/01-sing-box/config.json /etc/sing-box/
docker restart sing-box
```

### 2. 内网穿透配置 (02-frp/)
```
02-frp/
├── frps                           # FRP服务端程序
├── frpc                           # FRP客户端程序
├── frps.toml                     # FRP服务端配置
└── frpc.toml                     # FRP客户端配置
```

**包含内容**:
- FRP服务端和客户端二进制文件
- 配置文件 (frps.toml, frpc.toml)

**恢复命令**:
```bash
cp /aliyun_backup/server-backup/日期/02-frp/* /root/frp_0.60.0_linux_amd64/
systemctl restart frps
```

### 3. 自动化脚本 (03-scripts/)
```
03-scripts/
├── morning_briefing.py           # 早间简报生成脚本
├── daily_report.py               # 工作日报生成脚本
├── nas_backup.sh                 # NAS备份脚本
└── rss_news_fetch.py             # RSS资讯抓取脚本
```

**包含内容**:
- 自动化运维脚本
- 数据处理脚本
- 备份管理脚本

**恢复命令**:
```bash
cp /aliyun_backup/server-backup/日期/03-scripts/* /home/openclaw/.openclaw/workspace/scripts/
```

### 4. OpenClaw工作区核心文档 (04-workspace/)
```
04-workspace/
├── AGENTS.md                     # 代理配置和行为规范
├── SOUL.md                       # AI助手身份和性格
├── USER.md                       # 用户配置
├── TOOLS.md                      # 工具和环境配置
├── HEARTBEAT.md                  # 定时任务配置
├── IDENTITY.md                   # 身份标识
└── backup-info.json              # 备份元数据
```

**包含内容**:
- AI助手配置文件
- 用户偏好设置
- 工具配置信息
- 备份元数据

**恢复命令**:
```bash
cp /aliyun_backup/server-backup/日期/04-workspace/* /home/openclaw/.openclaw/workspace/
```

### 5. OpenClaw完整配置 (05-openclaw-config/)
```
05-openclaw-config/
└── openclaw-workspace.tar.gz    # 完整工作区压缩包
```

**包含内容**:
- 完整的OpenClaw工作区数据
- 排除 .git, __pycache__, node_modules 等冗余数据

**恢复命令**:
```bash
tar -xzf /aliyun_backup/server-backup/日期/05-openclaw-config/openclaw-workspace.tar.gz \
    -C /home/openclaw/.openclaw/
```

### 6. 安全基线脚本 (06-security-scripts/)
```
06-security-scripts/
├── check_config.sh              # 配置防护检查
├── monitor-suspicious-process.sh # 可疑进程监控
├── self-integrity-check.sh      # 脚本完整性自检
└── *.sh                        # 其他安全脚本
```

**包含内容**:
- 系统安全检查脚本
- 进度监控脚本
- 自检验证脚本

**恢复命令**:
```bash
cp /aliyun_backup/server-backup/日期/06-security-scripts/* /home/openclaw/.openclaw/scripts/
```

---

## 恢复指南

### 完整系统恢复

1. **准备工作**:
   ```bash
   # 创建临时目录
   mkdir -p /tmp/restore
   cd /tmp/restore
   
   # 下载备份包
   curl -u aliyun-ygx:%dOr91[# -o backup.tar.gz \
        http://47.119.177.194:5005/aliyun_backup/server-backup/20260402/server-backup-20260402.tar.gz
   
   # 解压备份包
   tar -xzf backup.tar.gz
   ```

2. **按顺序恢复**:
   ```bash
   # 1. 恢复OpenClaw工作区核心文档
   cp -r 04-workspace/* /home/openclaw/.openclaw/workspace/
   
   # 2. 恢复自动化脚本
   cp -r 03-scripts/* /home/openclaw/.openclaw/workspace/scripts/
   
   # 3. 恢复FRP配置
   cp -r 02-frp/* /root/frp_0.60.0_linux_amd64/
   systemctl restart frps
   
   # 4. 恢复sing-box配置
   cp 01-sing-box/config.json /etc/sing-box/
   docker restart sing-box
   
   # 5. 恢复完整OpenClaw工作区
   tar -xzf 05-openclaw-config/openclaw-workspace.tar.gz \
       -C /home/openclaw/.openclaw/
   
   # 6. 恢复安全脚本
   cp -r 06-security-scripts/* /home/openclaw/.openclaw/scripts/
   ```

### 部分组件恢复

#### 仅恢复OpenClaw配置
```bash
tar -xzf /aliyun_backup/server-backup/日期/05-openclaw-config/openclaw-workspace.tar.gz \
    -C /home/openclaw/.openclaw/
```

#### 仅恢复脚本
```bash
cp -r /aliyun_backup/server-backup/日期/03-scripts/* \
    /home/openclaw/.openclaw/workspace/scripts/
```

#### 仅恢复网络配置
```bash
# sing-box
cp /aliyun_backup/server-backup/日期/01-sing-box/config.json /etc/sing-box/
docker restart sing-box

# FRP
cp -r /aliyun_backup/server-backup/日期/02-frp/* /root/frp_0.60.0_linux_amd64/
systemctl restart frps
```

---

## 服务管理

### 定时任务查看
```bash
crontab -l
```

### 备份日志查看
```bash
tail -f /var/log/nas-backup.log
```

### 备份状态检查
```bash
# 查看最近的备份记录
ls -la /aliyun_backup/server-backup/

# 检查备份文件完整性
ls -la /aliyun_backup/server-backup/20260402/
```

### 服务状态检查
```bash
# sing-box状态
docker ps | grep sing-box

# FRP服务状态
systemctl status frps
```

---

## 故障排除

### 常见问题

#### 1. WebDAV上传失败
**症状**: HTTP 405, 404, 或 409 错误

**解决方案**:
```bash
# 检查WebDAV服务状态
curl -I http://47.119.177.194:5005/

# 检查网络连通性
ping 47.119.177.194

# 检查认证信息
curl -u aliyun-ygx:%dOr91[# -I http://47.119.177.194:5005/aliyun_backup/
```

#### 2. 备份脚本执行失败
**症状**: 脚本执行出错或中断

**解决方案**:
```bash
# 查看详细日志
tail -100 /var/log/nas-backup.log

# 手动执行脚本并查看错误
/root/.openclaw/workspace/scripts/backup/nas_backup.sh

# 检查磁盘空间
df -h
```

#### 3. 恢复失败
**症状**: 恢复后服务无法启动

**解决方案**:
```bash
# 检查文件权限
ls -la /home/openclaw/.openclaw/workspace/

# 检查配置文件格式
python3 -m json.tool /etc/sing-box/config.json

# 重启相关服务
systemctl restart frps
docker restart sing-box
```

### 日志分析

#### 错误日志模式
```
# WebDAV连接错误
[2026-03-14 22:57:56] WebDAV连接失败: HTTP 404

# 上传失败
[2026-03-14 23:08:23] 上传失败: config.json-20260314.tar.gz (HTTP 409)

# 脚本路径错误
/bin/sh: /root/scripts/nas_backup.sh: No such file or directory
```

#### 成功日志模式
```
# 正常备份
[2026-04-02 02:00:01] 备份完成: 成功
[2026-04-02 02:00:01] 上传成功: server-backup-20260402.tar.gz (HTTP 201)
```

---

## 维护和优化

### 定期维护

1. **每周清理**: 删除30天前的备份文件
   ```bash
   find /aliyun_backup/server-backup/ -name "*.tar.gz" -mtime +30 -delete
   ```

2. **日志轮转**: 配置日志轮转防止日志过大
   ```bash
   # 编辑 /etc/logrotate.conf
   /var/log/nas-backup.log {
       daily
       rotate 7
       compress
       missingok
       notifempty
   }
   ```

3. **备份验证**: 定期验证备份数据完整性
   ```bash
   # 检查备份文件
   tar -tzf /aliyun_backup/server-backup/20260402/server-backup-20260402.tar.gz | head -10
   ```

### 性能优化

1. **网络优化**: 调整WebDAV超时设置
   ```bash
   # 在脚本中添加超时参数
   curl --connect-timeout 30 --max-time 300 -T file.tar.gz ...
   ```

2. **压缩优化**: 调整压缩级别
   ```bash
   # 使用更高的压缩级别
   tar -czf - file | gzip -9 > file.tar.gz
   ```

3. **并行备份**: 多线程备份大型文件
   ```bash
   # 使用rsync进行增量备份
   rsync -avz --delete /source/ /destination/
   ```

---

## 备份策略建议

### 备份频率
- **每日备份**: 核心配置和工作区 (当前策略)
- **每周备份**: 完整系统镜像
- **每月备份**: 系统配置和应用程序

### 保留策略
- **最近7天**: 每日备份保留
- **最近4周**: 每周备份保留
- **最近12个月**: 每月备份保留
- **长期保留**: 关键配置和年度归档

### 安全建议
1. **加密备份**: 对敏感数据进行加密
2. **异地备份**: 在不同地理位置保留备份副本
3. **访问控制**: 严格控制备份文件的访问权限
4. **定期测试**: 定期测试恢复流程

---

## 联系信息和支持

- **脚本维护**: 自动化运维脚本
- **技术支持**: 系统管理员
- **文档更新**: 定期更新维护

**最后更新**: 2026-04-02
**版本**: 3.0
**文档类型**: 系统备份恢复指南