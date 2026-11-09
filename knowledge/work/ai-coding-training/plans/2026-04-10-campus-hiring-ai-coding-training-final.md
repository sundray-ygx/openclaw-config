# 校招新员工AI Coding入职培训方案（完整版）

> **版本**: v1.0  
> **适用对象**: 校招入职软件开发工程师  
> **执行周期**: 5个工作日  
> **评审方式**: 代码审查 + 10分钟演示

---

## 一、培训目标

1. **掌握SDD规范驱动编程**: 理解并实践OpenSpec框架的完整流程
2. **熟练使用AI Coding工具**: 能够高效使用Claude/Codex等AI助手进行开发
3. **建立工程化思维**: 从需求分析到验收测试的完整闭环
4. **快速融入团队**: 熟悉团队的代码规范和工作流程

---

## 二、SDD流程规范（基于OpenSpec）

### 2.1 流程概览

```
Day 1          Day 2          Day 3          Day 4          Day 5
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│  Proposal   │   Specs     │   Design    │ Implement   │  Verify     │
│   + Specs   │   (完善)     │   + Tasks   │   (编码)     │   + Demo    │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

### 2.2 各阶段交付物

| 阶段 | 交付文件 | 关键要求 |
|------|----------|----------|
| **Proposal** | `proposal.md` | 背景、目标、范围、验收标准 |
| **Specs** | `specs/*.md` | Given/When/Then格式，覆盖正常+异常场景 |
| **Design** | `design.md` | 架构图、模块划分、接口定义、技术选型 |
| **Tasks** | `tasks.md` | 原子任务列表，可勾选追踪 |
| **Implementation** | 源代码 + Git历史 | 按Task提交，commit message规范 |
| **Verification** | 测试报告 + 运行截图 | 测试通过率≥80%，核心功能演示 |

### 2.3 OpenSpec初始化命令

```bash
# 1. 安装OpenSpec CLI
npm install -g @fission-ai/openspec@latest

# 2. 在项目目录初始化
cd your-project
openspec init --tools claude

# 3. 创建变更
openspec new change feature-xxx

# 4. 按提示创建各阶段文档
openspec instructions --change feature-xxx
```

---

## 三、8个精选课题

### 课题1: 智能Git提交助手
**难度**: ⭐⭐  
**推荐背景**: 全栈、DevOps方向  
**技术栈**: Python/Node.js + Git命令 + LLM API

**核心功能**:
- 读取git diff/staged changes
- 调用LLM生成符合Conventional Commits规范的message
- 支持交互式编辑确认
- 支持自定义prompt模板

**学习要点**:
- 命令行工具开发
- Git命令行操作
- LLM API调用
- 交互式CLI设计

---

### 课题2: CSV数据清洗工具
**难度**: ⭐⭐  
**推荐背景**: 后端、数据方向  
**技术栈**: Python (pandas) / Node.js

**核心功能**:
- 读取CSV并自动检测编码、分隔符
- 数据类型自动推断和转换
- 缺失值处理策略（删除/填充/插值）
- 数据验证规则配置
- 输出清洗报告

**学习要点**:
- 数据处理能力
- 文件编码处理
- 数据质量规则设计

---

### 课题3: RESTful任务管理API
**难度**: ⭐⭐⭐  
**推荐背景**: 后端方向  
**技术栈**: Python(FastAPI) / Node.js(Express/Nest.js) + SQLite

**核心功能**:
- 任务的增删改查（CRUD）
- 多条件过滤（状态、优先级、时间范围）
- 分页和排序
- 数据验证和错误处理
- API文档自动生成（OpenAPI/Swagger）

**学习要点**:
- RESTful API设计
- 数据库操作
- 接口测试

---

### 课题4: API自动化测试框架
**难度**: ⭐⭐⭐  
**推荐背景**: 测试、QA、后端方向  
**技术栈**: Python/Node.js + HTTP客户端

**核心功能**:
- YAML/JSON格式的测试用例定义
- 环境变量和参数化支持
- 断言库（状态码、响应体、响应时间）
- 测试套件组织和执行
- HTML/JSON测试报告

**学习要点**:
- 测试框架设计
- 声明式配置
- 报告生成

---

### 课题5: 代码质量检查工具
**难度**: ⭐⭐⭐  
**推荐背景**: 全栈、工具链方向  
**技术栈**: Node.js/Python + 文件遍历 + 正则/AST

**核心功能**:
- 递归扫描指定目录的源代码
- 可配置的规则集（内置+自定义）
- 支持忽略模式（.gitignore类似）
- 输出检查报告（终端表格/HTML）
- 支持作为pre-commit钩子

**学习要点**:
- 静态分析基础
- 规则引擎设计
- Git hooks

---

### 课题6: 日志分析工具
**难度**: ⭐⭐⭐  
**推荐背景**: 后端、运维方向  
**技术栈**: Python/Node.js + 正则表达式

**核心功能**:
- 支持常见日志格式（Apache/Nginx/自定义）
- 按时间/级别/关键词过滤
- 聚合统计（PV/UV/错误率/响应时间分布）
- 支持大文件流式处理
- 输出摘要报告

**学习要点**:
- 日志解析
- 流式处理
- 数据统计分析

---

### 课题7: 待办事项Web应用
**难度**: ⭐⭐⭐  
**推荐背景**: 前端、全栈方向  
**技术栈**: React/Vue + LocalStorage/IndexedDB

**核心功能**:
- 任务的增删改查
- 拖拽排序
- 状态切换（待办/进行中/已完成）
- 数据持久化
- 响应式设计

**学习要点**:
- 前端状态管理
- 拖拽交互实现
- 本地存储

---

### 课题8: API Mock服务器
**难度**: ⭐⭐⭐  
**推荐背景**: 前端、全栈方向  
**技术栈**: Node.js(Express) / Python(FastAPI)

**核心功能**:
- JSON/YAML格式的API定义
- 根据定义自动生成路由和响应
- 支持动态数据（faker.js类似功能）
- 请求验证和延迟模拟
- 响应模板和状态码配置

**学习要点**:
- Mock服务原理
- 动态数据生成
- 前后端联调工具

---

## 四、执行指南

### 4.1 环境准备

```bash
# 1. 安装Node.js (v18+)
# 2. 安装Python (v3.9+)
# 3. 安装OpenSpec
npm install -g @fission-ai/openspec@latest

# 4. 安装AI Coding工具（推荐Claude Code）
npm install -g @anthropic-ai/claude-code

# 5. 配置Git
git config --global user.name "Your Name"
git config --global user.email "your.email@company.com"
```

### 4.2 项目初始化流程

```bash
# 1. 创建项目目录
mkdir ai-coding-training
cd ai-coding-training

# 2. 初始化Git
git init

# 3. 初始化OpenSpec
openspec init --tools claude

# 4. 创建变更
openspec new change my-feature

# 5. 按阶段创建文档（按Day 1-5执行）
```

### 4.3 各阶段详细要求

#### Day 1: Proposal + Specs初稿

**proposal.md 模板**:
```markdown
# Proposal: [课题名称]

## 背景
[为什么要做这个工具/服务]

## 目标
[具体要实现什么]

## 范围
### 包含
- [功能1]
- [功能2]

### 不包含
- [超出范围的功能]

## 验收标准
- [ ] 标准1: 具体可验证的条件
- [ ] 标准2: 具体可验证的条件

## 技术栈
- 语言: [Python/Node.js/...]
- 主要依赖: [列出关键库]
```

**Specs编写规范**:
```markdown
### Requirement: [功能名称]
The system SHALL [功能描述]

#### Scenario: [场景名称]
- GIVEN [前置条件]
- WHEN [操作]
- THEN [预期结果]

#### Scenario: [异常场景]
- GIVEN [前置条件]
- WHEN [错误操作]
- THEN [错误处理结果]
```

#### Day 2: 完善Specs

- 每个核心功能至少2个场景（正常+异常）
- 边界条件覆盖
- 使用RFC 2119关键词（SHALL/MUST/SHOULD/MAY）

#### Day 3: Design + Tasks

**design.md 模板**:
```markdown
# Design: [课题名称]

## 架构概览
[文字描述或简单架构图]

## 模块划分
### Module 1: [名称]
- 职责: [描述]
- 接口: [关键函数/方法]

### Module 2: [名称]
...

## 数据模型
[如果有数据存储，描述数据结构]

## 技术选型说明
- 选择X而不是Y的原因
```

**tasks.md 模板**:
```markdown
# Tasks: [课题名称]

## Phase 1: 基础架构
- [ ] Task 1.1: [具体任务]
- [ ] Task 1.2: [具体任务]

## Phase 2: 核心功能
- [ ] Task 2.1: [具体任务]
- [ ] Task 2.2: [具体任务]

## Phase 3: 测试与优化
- [ ] Task 3.1: 编写单元测试
- [ ] Task 3.2: 集成测试
```

#### Day 4: Implementation

**AI Coding最佳实践**:
1. **按Task逐个实现**，每完成一个Task提交一次代码
2. **Commit Message规范**:
   ```
   feat: 添加XXX功能
   fix: 修复XXX问题
   test: 添加XXX测试
   docs: 更新XXX文档
   ```
3. **与AI协作模式**:
   - 先给AI看当前Task的Specs
   - 要求AI先生成代码，再解释关键逻辑
   - Review AI生成的代码，要求改进

#### Day 5: Verification + Demo准备

**验证清单**:
- [ ] 所有Specs场景都有对应测试
- [ ] 测试通过率≥80%
- [ ] 核心功能可演示
- [ ] 代码风格统一
- [ ] 无严重bug

**Demo准备**:
- 3分钟: 项目介绍 + 技术栈说明
- 5分钟: 功能演示（按Specs场景走）
- 2分钟: SDD过程回顾（遇到的挑战、AI使用心得）

---

## 五、评审标准

### 5.1 SDD过程完整性（40分）

| 检查项 | 分值 | 说明 |
|--------|------|------|
| proposal.md | 5分 | 目标清晰、范围明确 |
| specs/*.md | 10分 | 格式规范、覆盖完整 |
| design.md | 10分 | 架构合理、设计清晰 |
| tasks.md | 5分 | 任务可执行、追踪完整 |
| Git提交记录 | 10分 | 按Task提交、message规范 |

### 5.2 代码质量（30分）

| 检查项 | 分值 | 说明 |
|--------|------|------|
| 功能完整性 | 10分 | 核心功能实现 |
| 代码可读性 | 10分 | 命名规范、结构清晰 |
| 测试覆盖 | 10分 | 有测试、覆盖主要场景 |

### 5.3 AI工具使用（20分）

| 检查项 | 分值 | 说明 |
|--------|------|------|
| AI协作效率 | 10分 | 有效利用AI加速开发 |
| Prompt质量 | 10分 | 给AI的指令清晰、上下文完整 |

### 5.4 演示表现（10分）

| 检查项 | 分值 | 说明 |
|--------|------|------|
| 功能演示 | 5分 | 流畅展示核心功能 |
| 过程回顾 | 5分 | 能总结SDD执行心得 |

**总分**: 100分  
**通过线**: 70分  
**优秀线**: 85分

---

## 六、常见问题FAQ

### Q1: 遇到AI生成的代码有bug怎么办？
**A**: 这是正常的。把错误信息和相关代码给AI，让它修复。记录你发现的AI常见错误模式。

### Q2: Specs写得不完整，实现时发现漏了怎么办？
**A**: 回退到Specs阶段补充，然后继续。SDD是迭代过程，不是瀑布。

### Q3: 5天时间不够怎么办？
**A**: 优先保证SDD流程完整，功能可以裁剪。与导师沟通调整范围。

### Q4: 可以复制开源代码吗？
**A**: 可以参考，但必须理解并用自己的方式实现。禁止直接复制粘贴。

### Q5: 如何证明我正确使用了AI？
**A**: 保留与AI的对话截图或导出，作为过程产物的一部分。

---

## 七、资源链接

- **OpenSpec文档**: https://github.com/fission-ai/openspec
- **Conventional Commits**: https://www.conventionalcommits.org/
- **示例项目**: [待补充]
- **评审Checklist**: 见本文档第五章

---

## 八、附录：课题选择建议

| 新员工背景 | 推荐课题 | 理由 |
|-----------|----------|------|
| 后端为主 | 课题2、3、4、6 | 数据处理、API设计、测试框架 |
| 前端为主 | 课题7、8 | Web应用、Mock服务 |
| 全栈方向 | 课题1、5 | 工具开发、全链路实践 |
| DevOps/工具链 | 课题1、5 | Git工具、代码检查 |
| 基础较弱 | 课题1、2 | 难度适中，功能聚焦 |
| 基础较好 | 课题4、6 | 有挑战性，技术深度 |

---

*文档生成时间: 2026-04-10*  
*版本: v1.0*
