# NAS自动备份系统文档

## 概述

### 系统架构
- **备份脚本位置**: `/root/.openclaw/workspace/scripts/backup/nas_backup.sh`
- **WebDAV服务器**: http://47.119.177.194:5005
- **备份路径**: /aliyun_backup/server-backup/
- **执行时间**: 每天凌晨2:00
- **日志文件**: `/var/log/nas-backup.log`

### 功能特性
- ✅ 自动化完整服务器备份
- ✅ 结构化目录组织
- ✅ 详细恢复说明文档
- ✅ WebDAV远程存储
- ✅ 完整日志记录

## 备份内容结构

```
aliyun_backup/server-backup/
├── 20260405/
│   └── server-backup-20260405.tar.gz
├── 20260404/
│   └── server-backup-20260404.tar.gz
└── ... (按日期归档)
```

### 压缩包内部结构
```
server-backup-YYYYMMDD.tar.gz
├── 01-sing-box/
│   └── config.json              # 网络代理配置
├── 02-frp/
│   ├── frps.toml                # FRP服务端配置
│   ├── frpc.toml                # FRP客户端配置
│   ├── frps                     # FRP服务端程序
│   └── frpc                     # FRP客户端程序
├── 03-scripts/
│   ├── morning_briefing.py      # 早间简报生成脚本
│   ├── daily_report.py          # 工作日报生成脚本
│   ├── nas_backup.sh            # 本备份脚本
│   └── rss_news_fetch.py        # RSS资讯抓取脚本
├── 04-workspace/
│   ├── AGENTS.md                # 代理配置和行为规范
│   ├── SOUL.md                  # AI助手身份和性格
│   ├── USER.md                  # 用户配置
│   ├── TOOLS.md                 # 工具和环境配置
│   ├── HEARTBEAT.md             # 定时任务配置
│   ├── IDENTITY.md              # 身份标识
│   └── ...                      # 其他核心配置
├── 05-openclaw-config/
│   └── openclaw-workspace.tar.gz # 完整OpenClaw工作区
├── 06-security-scripts/
│   ├── check_config.sh          # 配置防护检查
│   ├── monitor-suspicious-process.sh # 可疑进程监控
│   └── self-integrity-check.sh  # 脚本完整性自检
├── backup-info.json            # 备份元数据
└── README.txt                  # 详细恢复说明
```

## 恢复指南

### 1. 恢复sing-box代理配置
```bash
# 解压备份包
tar -xzf server-backup-YYYYMMDD.tar.gz

# 复制配置文件
cp 01-sing-box/config.json /etc/sing-box/

# 重启容器
docker restart sing-box
```

### 2. 恢复FRP内网穿透
```bash
# 复制配置和二进制文件
cp 02-frp/* /root/frp_0.60.0_linux_amd64/

# 重启服务
systemctl restart frps
```

### 3. 恢复脚本文件
```bash
# 复制脚本到工作区
cp 03-scripts/* /home/openclaw/.openclaw/workspace/scripts/
```

### 4. 恢复OpenClaw工作区
```bash
# 恢复核心文档
cp 04-workspace/* /home/openclaw/.openclaw/workspace/

# 恢复完整工作区
tar -xzf 05-openclaw-config/openclaw-workspace.tar.gz -C /home/openclaw/.openclaw/
```

### 5. 恢复安全脚本
```bash
cp 06-security-scripts/* /home/openclaw/.openclaw/scripts/
```

## 服务管理命令

### 系统服务监控
```bash
# 查看sing-box状态
docker ps | grep sing-box
docker restart sing-box

# 查看FRP状态
systemctl status frps
systemctl restart frps

# 查看备份日志
tail -f /var/log/nas-backup.log
```

### 脚本测试
```bash
# 早间简报测试
python3 /home/openclaw/.openclaw/workspace/scripts/briefing/morning_briefing.py

# 工作日报测试
python3 /home/openclaw/.openclaw/workspace/scripts/daily/daily_report.py
```

## 定时任务配置

### 主要定时任务
- **早间简报**: 每天8:00
- **OpenClaw资讯**: 每天8:00  
- **工作日报**: 每天22:00
- **NAS备份**: 每天2:00

### Cron表达式
```bash
# 查看当前cron任务
crontab -l

# 编辑cron任务
crontab -e

# NAS备份定时任务示例
0 2 * * * /root/.openclaw/workspace/scripts/backup/nas_backup.sh
```

## WebDAV配置

### 服务器信息
- **地址**: http://47.119.177.194:5005
- **用户名**: aliyun-ygx
- **基础路径**: /aliyun_backup/server-backup/

### 手动上传测试
```bash
# 创建测试文件
echo "test content" > /tmp/test.txt

# 上传文件
curl -T /tmp/test.txt -u aliyun-ygx:'%dOr91[#' "http://47.119.177.194:5005/aliyun_backup/test.txt"
```

## 故障排除

### 常见错误

#### 1. WebDAV连接失败
```bash
# 检查服务状态
curl -I http://47.119.177.194:5005

# 检查网络连通性
ping 47.119.177.194
```

#### 2. 权限问题
```bash
# 确认WebDAV目录权限
curl -X PROPFIND -u user:pass "http://47.119.177.194:5005/path/"
```

#### 3. 备份包过大
```bash
# 检查备份大小
ls -lh /tmp/backup-*/
du -sh /tmp/backup-*/
```

### 日志分析

```bash
# 查看最近的备份记录
tail -20 /var/log/nas-backup.log

# 搜索错误信息
grep "失败\|error\|ERROR" /var/log/nas-backup.log

# 统计成功率
grep "备份完成" /var/log/nas-backup.log | tail -10
```

## 监控和维护

### 备份健康检查
```bash
# 检查备份目录大小
du -sh /aliyun_backup/server-backup/

# 统计备份文件数量
find /aliyun_backup/server-backup/ -name "*.tar.gz" | wc -l

# 检查最近7天的备份
find /aliyun_backup/server-backup/ -name "*.tar.gz" -mtime -7
```

### 存储管理
```bash
# 清理超过30天的备份
find /aliyun_backup/server-backup/ -name "*.tar.gz" -mtime +30 -delete

# 归档历史备份
mkdir -p /archive/nas-backup/$(date +%Y%m)
find /aliyun_backup/server-backup/ -name "*.tar.gz" -mtime +30 -exec mv {} /archive/nas-backup/$(date +%Y%m)/ \;
```

## 版本历史

### v3.0 (当前版本)
- ✅ 优化目录结构，按功能分类
- ✅ 增加安全脚本备份
- ✅ 改进README文档格式
- ✅ 添加详细恢复说明

### v2.0
- ✅ 支持WebDAV自动上传
- ✅ 结构化备份目录
- ✅ 自动生成元数据

### v1.0
- ✅ 基础备份功能
- ✅ tar打包压缩

## 联系信息

- **维护人员**: 系统管理员
- **脚本版本**: 3.0
- **最后更新**: 2026-04-05
- **文档版本**: 1.0

---

**注意**: 本文档随备份系统更新而维护，请参考最新版本的备份脚本。