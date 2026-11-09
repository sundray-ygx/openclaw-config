# 前端页面结构自动提取工具

## 快速开始

```powershell
# 1. 环境检查
python check_env.py

# 2. 提取页面
python extract_structure.py http://10.65.134.124:8080/metrics -o metrics.json

# 3. 测试下钻
python extract_structure.py http://10.65.134.124:8080/metrics --drill-down "终端安全产品研发部" -o drill-down.json
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `extract_structure.py` | 主脚本（提取 + 下钻测试，合并为一个） |
| `check_env.py` | 环境验证脚本 |

## 环境要求

- Python 3.8+
- Selenium 4.0+
- Chrome/Chromium + 对应版本 ChromeDriver

## 详细文档

[前端页面 1:1 复刻完全指南](../../knowledge/tech/AI-Native/frontend-replication-guide.md)
