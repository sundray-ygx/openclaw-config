# 技术笔记：Skillhub 技能管理

日期：2026-03-17

## 技能搜索
```bash
skillhub search <关键词>
```

## 技能安装
```bash
skillhub install <skill-name>
```

安装路径：`/root/.openclaw/workspace/skills/<skill-name>/`

## 技能结构
```
skills/<skill-name>/
├── SKILL.md          # 使用说明
└── scripts/          # 可执行脚本
    └── *.py
```

## 使用流程
1. 搜索技能：`skillhub search nano-banana-pro`
2. 阅读 SKILL.md 了解依赖要求
3. 安装技能：`skillhub install nano-banana-pro`
4. 按说明配置环境（API Key、依赖包等）
5. 测试运行

## 注意事项
- 安装前检查 Python 版本要求
- 注意区分 `uv run` 和 `python3` 运行方式
- API Key 优先从环境变量读取，其次命令行参数
