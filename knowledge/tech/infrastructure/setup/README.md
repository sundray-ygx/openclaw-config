# OpenClaw 环境恢复脚本

**位置**: `knowledge/tech/infrastructure/setup/`  
**用途**: OpenClaw 环境初始化与恢复

---

## 文件说明

| 文件 | 类型 | 用途 |
|------|------|------|
| `setup.sh` | Bash脚本 | 环境恢复脚本，创建目录结构、生成配置 |
| `README.md` | 说明文档 | 本文件 |

---

## 使用方法

```bash
# 从 workspace 根目录执行
./setup.sh
```

## 功能

1. 检查 `.env` 配置文件
2. 创建 OpenClaw 目录结构
3. 备份现有配置
4. 生成 `openclaw.json`
5. 同步工作区文件
6. 同步扩展

---

## 归档历史

- **2026-04-10**: 从 workspace 根目录迁移至此
