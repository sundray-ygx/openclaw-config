# 工作笔记：备份脚本与 Workspace 结构对齐

日期：2026-03-17

## 背景
Workspace 目录结构重新整理后，NAS 备份脚本中引用的路径失效。

## 原问题
- `04-docs/` 目录原指向 `docs/frp-config.md` 和 `system-services-report.md`，但 `docs/` 目录已不存在
- `06-archives/` 原备份 `daily-reports/`，但该目录已移至 `archive/`

## 解决方案
更新 `/root/scripts/nas_backup.sh`：

| 目录 | 原内容 | 新内容 |
|------|--------|--------|
| 04-docs/ | docs/frp-config.md, system-services-report.md | workspace 根目录核心文档：AGENTS.md, SOUL.md, USER.md, TOOLS.md, HEARTBEAT.md, IDENTITY.md |
| 06-archives/ | daily-reports/ | archive/（包含 daily/ 和 weekly/） |

## 关键命令
```bash
# 验证文件存在
ls -la /root/.openclaw/workspace/*.md

# 语法检查
bash -n /root/scripts/nas_backup.sh

# 测试备份源
ls -la /root/.openclaw/workspace/archive/
```

## 经验
1. 目录结构调整后，同步更新相关脚本
2. 使用 `2>/dev/null || echo "不存在"` 处理可能缺失的文件
3. 脚本更新后进行语法检查和源文件存在性验证
