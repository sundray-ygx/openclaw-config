# Knowledge 知识库

## 目录结构

```
knowledge/
├── README.md                    # 本文件
├── inbox/                       # 待分类缓冲区（自动归档入口）
├── finance/                     # 财务相关
│   ├── rent/                    # 租金账单模板与记录
│   └── libs/                    # 财务脚本库
├── lessons/                     # 经验教训（按日期归档）
├── people/                      # 人物信息
├── productivity/                # 效率提升
│   ├── personal/                # 个人效率
│   ├── reflection/              # 反思记录与方法论
│   └── weekly-planning/         # 周计划方法
├── projects/                    # 项目文档
│   └── sam-daigou/
├── security/                    # 安全知识
│   └── system-reports/          # 安全巡检报告
├── tech/                        # 技术知识
│   ├── AI-Native/               # AI Native 研究
│   ├── automation/              # 自动化技术（cron, mail, news）
│   ├── data-pipeline/           # 数据处理（健康数据等）
│   ├── industry-analysis/       # 行业分析
│   ├── infrastructure/          # 基础设施（singbox, frp 等）
│   └── openclaw/                # OpenClaw 相关技术
└── work/                        # 工作相关
    ├── AI-Native/               # AI Native 落地推进
    ├── BP/                      # 业务伙伴
    ├── IPD/                     # IPD 流程
    ├── OKR/                     # OKR 管理
    ├── others/                  # 其他工作记录
    └── plans/                   # 工作计划
```

## 归档规则

### 文件命名
- 日期类：`YYYY-MM-DD-title.md`
- 人物类：`person-name.md`
- 项目类：`README.md` 或描述性名称

### 什么放 Knowledge
✅ 技术方案、经验教训、项目总结、工作流程文档
❌ 运行时脚本（→ `scripts/`）、临时文件、敏感信息

### 自动归档流程
1. 每日反思 → 按标签自动分类到对应子目录
2. 日报 → `archive/daily/YYYY-MM/`
3. 记忆日志 → `memory/YYYY-MM-DD.md`

## 维护
- inbox 应保持为空（定期清理）
- 每周检查 workspace 根目录，及时归档散落文件
