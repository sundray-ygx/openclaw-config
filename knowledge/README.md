# Knowledge 知识库

OpenClaw 知识库 - 存储经验、教训、技术方案和工作记录。

## 目录结构

```
knowledge/
├── README.md                    # 本文件
├── lessons/                     # 经验教训
│   └── YYYY-MM-DD-title.md
├── people/                      # 人物信息
│   └── person-name.md
├── productivity/                # 效率提升
│   ├── personal/                # 个人效率
│   └── weekly-planning/         # 周计划方法
├── projects/                    # 项目文档
│   └── project-name/
│       └── README.md
├── security/                    # 安全知识
│   └── YYYY-MM-DD-title.md
├── tech/                        # 技术知识
│   ├── automation/              # 自动化技术
│   ├── data-pipeline/           # 数据处理
│   └── infrastructure/          # 基础设施
└── work/                        # 工作相关
    └── YYYY-MM-DD-title.md
```

## 文件命名规范

- **日期类文档**: `YYYY-MM-DD-title.md`（短横线分隔）
- **人物文档**: `person-name.md`（小写，短横线分隔）
- **项目文档**: `README.md` 或 `YYYY-MM-DD-title.md`
- **说明文档**: `README.md` 或 `topic-name.md`

## 归档规则

### 什么应该放入 Knowledge

✅ **应该放入**:
- 技术方案、架构设计文档
- 踩坑记录、经验教训
- 项目总结、复盘报告
- 工具使用指南
- 工作流程文档

❌ **不应该放入**:
- 运行时脚本（放 `workspace/scripts/`）
- 临时文件、缓存
- 大型二进制文件
- 敏感信息（密码、密钥）

### 自动归档流程

1. **日报生成** → `workspace/archive/daily/YYYY-MM/`
2. **记忆生成** → `workspace/memory/YYYY-MM-DD.md`
3. **知识沉淀** → 手动归档到 `knowledge/` 对应目录

## 维护责任

- 定期清理过期内容
- 保持命名规范一致
- 及时归档有价值的经验
