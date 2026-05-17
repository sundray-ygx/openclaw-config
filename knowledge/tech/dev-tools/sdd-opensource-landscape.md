# AI Coding 领域 SDD（Spec-Driven Development）开源项目调研

> 调研时间：2026-05-13
> 关键词：Spec-Driven Development, SDD, AI Coding, Vibe Coding → 结构化开发

---

## 一、SDD 概述

**Spec-Driven Development（SDD）** 是一种以**规格说明（Spec）为第一公民**的软件开发方法论。核心理念：

- **先写 Spec，再写代码** — Spec 是单一事实来源（Single Source of Truth）
- **Spec 可执行** — 不是死文档，而是直接驱动 AI Agent 生成代码的契约
- **替代 Vibe Coding** — 解决 AI 编码中上下文丢失、产出不一致的问题

**SDD 工作流通用模式：**
```
需求 → Spec 编写 → Spec 评审 → AI Agent 生成代码 → 验证 → 迭代
```

**Thoughtworks 技术雷达** 已将 SDD 列为值得关注的技术趋势。

---

## 二、核心开源项目

### 1. GitHub Spec Kit ⭐ 97.7k

| 项目 | 详情 |
|------|------|
| **仓库** | https://github.com/github/spec-kit |
| **Star** | 97.7k |
| **Fork** | 8.5k |
| **License** | MIT |
| **最新版本** | 0.8.9（2026-05-12） |
| **维护方** | GitHub 官方 |

**应用场景：**
- 个人开发者或团队用 AI Coding Agent（Copilot、Claude Code、Gemini CLI）开发功能
- 需要将需求转化为结构化 Spec，再由 AI 根据 Spec 生成代码
- 替代"对话式"的 Vibe Coding，让开发过程可追溯、可重复

**技术方案：**
- **CLI 工具**：`spec-kit` 命令行初始化项目，生成 Spec 模板
- **Spec 文件格式**：Markdown 格式的结构化规格说明，包含：
  - 产品场景描述
  - 技术约束
  - 验收标准
  - 实现计划
- **Agent 无关**：支持 Copilot、Claude Code、Gemini CLI 等多种 AI 编码工具
- **工作流**：`spec-kit init` → 编写 spec → 喂给 AI Agent → 生成代码 → 验证

**快速上手：**
```bash
# 安装
npm install -g @github/spec-kit

# 初始化项目
spec-kit init

# 查看生成的 spec 模板，根据项目需求填写
# 然后用你的 AI Coding Agent 读取 spec 生成代码
```

**特点：**
- ✅ GitHub 官方出品，生态集成好
- ✅ Agent 无关设计，不绑定特定 AI 工具
- ✅ 社区活跃，模板丰富
- ⚠️ 偏轻量级，不包含多 Agent 协作

---

### 2. BMAD-METHOD ⭐ 47k

| 项目 | 详情 |
|------|------|
| **仓库** | https://github.com/bmad-code-org/BMAD-METHOD |
| **Star** | 47k |
| **Fork** | 5.5k |
| **License** | MIT |
| **全称** | Breakthrough Method for Agile AI-Driven Development |
| **最新版本** | v6（活跃迭代中） |

**应用场景：**
- 企业级复杂系统的 AI 驱动开发
- 需要多角色（产品经理、架构师、开发者、QA）协作的项目
- 从需求分析到架构设计到代码生成的全流程管理
- 游戏开发等复杂领域

**技术方案：**
- **多 Agent 角色系统**：12+ 专业 AI Agent 角色，包括：
  - 产品负责人（Product Owner）
  - 架构师（Architect）
  - 开发者（Developer）
  - QA 工程师
  - Scrum Master
- **阶段化工作流**：
  1. 需求收集与用户故事
  2. 架构设计文档
  3. 技术规格说明
  4. 实现计划与任务分解
  5. 代码生成
  6. 质量验证
- **文档驱动**：每个阶段产出结构化文档，作为下一阶段的输入
- **Skills 架构**：支持自定义 Agent 技能扩展
- **BMAD Builder**：可视化构建工作流

**快速上手：**
```bash
# 克隆仓库
git clone https://github.com/bmad-code-org/BMAD-METHOD.git

# 按照文档选择适合的 Agent 角色配置
# 将 BMAD 的 prompt 文件放入你的 AI Coding Agent 的工作目录
# 开始按阶段推进
```

**特点：**
- ✅ 最全面的企业级 SDD 框架
- ✅ 多 Agent 角色分工明确
- ✅ 适合复杂项目
- ⚠️ 学习曲线较陡
- ⚠️ 对简单项目可能过度工程化

---

### 3. OpenSpec ⭐ 约 8k+

| 项目 | 详情 |
|------|------|
| **仓库** | https://github.com/Fission-AI/OpenSpec |
| **License** | MIT |
| **发布** | npm `@fission-ai/openspec` |
| **要求** | Node.js 20.19.0+ |

**应用场景：**
- 中小型项目的 Spec 驱动开发
- 棕地项目（Brownfield）改造，已有代码库上增加 SDD 流程
- 需要轻量级、迭代式 Spec 工作流

**技术方案：**
- **CLI + Dashboard**：提供终端命令和可视化仪表板
- **Artifact 引导工作流**：
  ```
  /opsx:propose "your idea"  → 生成 proposal.md + specs/ + design.md + tasks.md
  /opsx:apply                → AI 按任务清单逐步实现
  /opsx:archive              → 归档完成的变更
  ```
- **目录结构**：
  ```
  openspec/
  ├── changes/
  │   └── add-dark-mode/
  │       ├── proposal.md    # 为什么做、改什么
  │       ├── specs/         # 需求和场景
  │       ├── design.md      # 技术方案
  │       └── tasks.md       # 实现清单
  └── changes/archive/       # 归档
  ```
- **Profile 系统**：支持不同工作流模式（rapid、TDD 等）
- **设计哲学**：流动不僵化、迭代不瀑布、简单不复杂

**快速上手：**
```bash
# 全局安装
npm install -g @fission-ai/openspec@latest

# 在项目目录初始化
cd your-project
openspec init

# 告诉你的 AI Agent
# /opsx:propose <你想构建什么>
```

**特点：**
- ✅ 最轻量、最容易上手
- ✅ 支持棕地项目，不要求从零开始
- ✅ Artifact 引导，产出物清晰
- ✅ 社区活跃，Discord 支持
- ⚠️ 功能相对简单

---

### 4. Claude Task Master (Taskmaster AI) ⭐ 27.1k

| 项目 | 详情 |
|------|------|
| **仓库** | https://github.com/eyaltoledano/claude-task-master |
| **Star** | 27.1k |
| **Fork** | 2.5k |
| **License** | MIT |
| **定位** | AI 驱动的任务管理系统 |

**应用场景：**
- 从 PRD（产品需求文档）自动拆解任务
- 多阶段项目的任务依赖管理
- 配合 Cursor、Windsurf、Roo Code 等 AI IDE 使用

**技术方案：**
- **PRD 驱动**：输入产品需求文档，自动解析为任务树
- **任务管理**：
  - 任务拆解与依赖关系
  - 优先级排序
  - 进度追踪
  - 子任务管理
- **CLI-first**：命令行优先设计
- **Agent 集成**：原生支持多种 AI IDE

**快速上手：**
```bash
# 安装
npm install -g task-master-ai

# 在项目中初始化
task-master init

# 从 PRD 生成任务
task-master parse prd.md

# 查看任务列表
task-master list
```

**特点：**
- ✅ PRD → Task 自动化拆解
- ✅ 任务依赖可视化
- ✅ 兼容多种 AI IDE
- ⚠️ 偏任务管理层面，非完整 SDD 框架
- ⚠️ 与 Claude Code 绑定较深

---

### 5. GSD (Get Stuff Done) ⭐ 7.4k

| 项目 | 详情 |
|------|------|
| **仓库** | https://github.com/gsd-build/gsd-2 |
| **Star** | 7.4k |
| **Fork** | 760 |
| **License** | MIT |
| **定位** | 元提示（Meta-Prompting）+ 上下文工程 + SDD |

**应用场景：**
- 长时间自主运行的 AI Agent 任务（解决上下文腐烂问题）
- 跨多文件、多模块的复杂功能开发
- 需要 AI Agent 持续数小时工作而不"失忆"

**技术方案：**
- **三阶段框架**：Plan → Build → Verify
- **上下文工程**：解决 AI Agent 长时间运行后上下文丢失的核心问题
- **Write Gate 机制**：控制 AI Agent 何时可以写文件，防止幻觉产出
- **Meta-Prompting**：通过精心设计的提示模板引导 Agent 行为
- **Session 管理**：支持断点续传，Agent 可以从上次停止的地方继续

**快速上手：**
```bash
# 安装
npm install -g @anthropic/gsd

# 在项目中初始化
gsd init

# 使用三阶段工作流
gsd plan "build user auth system"
gsd build
gsd verify
```

**特点：**
- ✅ 解决 AI Agent 上下文腐烂这一核心痛点
- ✅ 适合长时间自主开发
- ✅ Write Gate 防止幻觉
- ⚠️ 与 Claude Code 生态绑定
- ⚠️ 有多个 Fork 版本（Copilot 版、Kilo Code 版等）

---

### 6. Kiro (AWS) — 非 GitHub 开源，但需了解

| 项目 | 详情 |
|------|------|
| **官网** | https://kiro.dev |
| **出品方** | AWS (Amazon) |
| **定位** | Spec-Driven AI IDE |
| **开源状态** | 免费使用，非开源 |

**应用场景：**
- 从概念到生产的完整 AI 开发流程
- 需要 IDE 内置 SDD 工作流的团队
- AWS 生态深度集成

**技术方案：**
- **一体化 IDE**：将 SDD 直接嵌入 IDE，不需要额外工具
- **Spec 系统**：结构化规格，自动分解为实现计划
- **Steering**：通过约束引导 AI Agent 行为
- **Hooks**：开发生命周期中的钩子机制
- **Custom Agents**：可自定义 AI Agent

**特点：**
- ✅ IDE 原生集成，体验最流畅
- ✅ AWS 生态加持
- ⚠️ 非开源
- ⚠️ 绑定 AWS 生态

---

### 7. Tessl — 商业平台

| 项目 | 详情 |
|------|------|
| **官网** | https://tessl.io |
| **定位** | Agent Enablement Platform |
| **开源组件** | https://github.com/tesslio/spec-driven-development-tile |
| **状态** | Private Beta |

**应用场景：**
- 团队级 AI 编码规范化
- 需要大规模 Spec Registry（10,000+ 预构建库规格）
- 让 AI Agent 正确使用第三方库

**技术方案：**
- **Spec Registry**：10,000+ 预构建的第三方库规格，告诉 AI 如何正确使用 API
- **Framework**：规格驱动开发框架
- **Tile 系统**：可组合的方法论模块
- **Spec 即代码**：规格本身成为可执行的契约

**特点：**
- ✅ Spec Registry 概念创新
- ✅ 解决 AI Agent 误用第三方库的问题
- ⚠️ 尚未公开，需排队等待
- ⚠️ 商业产品

---

## 三、项目对比矩阵

| 维度 | Spec Kit | BMAD-METHOD | OpenSpec | Taskmaster | GSD |
|------|----------|-------------|----------|------------|-----|
| **Star** | 97.7k | 47k | 8k+ | 27.1k | 7.4k |
| **定位** | 通用 SDD 工具包 | 企业级全流程 | 轻量迭代式 | PRD→任务 | 上下文工程 |
| **复杂度** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Agent 绑定** | 无 | 无 | 无 | Claude | Claude |
| **适合团队** | 1-20人 | 5-50人 | 1-5人 | 1-10人 | 1-5人 |
| **棕地支持** | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| **多角色协作** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **学习曲线** | 低 | 高 | 最低 | 中 | 中 |

---

## 四、选型建议

| 场景 | 推荐 |
|------|------|
| 快速了解 SDD，想今天就用起来 | **OpenSpec** |
| 团队已在用 GitHub 生态 | **Spec Kit** |
| 企业级复杂项目，需要严格流程 | **BMAD-METHOD** |
| 主要痛点是 PRD 拆解和任务管理 | **Taskmaster AI** |
| AI Agent 长时间运行容易"失忆" | **GSD** |
| 想要 IDE 一体化体验 | **Kiro** |

---

## 五、学习路径建议

1. **概念理解**（1天）
   - 阅读 [Martin Fowler: Understanding SDD](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
   - 阅读 [GitHub Blog: Spec-Driven Development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)

2. **动手实践**（2-3天）
   - 用 **OpenSpec** 或 **Spec Kit** 在一个小项目上走一遍完整流程
   - 体验 `propose → spec → implement → verify` 的闭环

3. **深入进阶**（1周）
   - 对比 **BMAD-METHOD** 的多角色工作流，理解企业级 SDD 的不同
   - 尝试 **GSD** 的长时间自主运行场景

4. **对比研究**（推荐阅读）
   - [BMAD vs Spec Kit vs OpenSpec 实测对比](https://ranthebuilder.cloud/blog/i-tested-three-spec-driven-ai-tools-here-s-my-honest-take/)
   - [15 个 SDD 框架对比](https://medium.com/@wasowski.jarek/comparing-15-spec-driven-development-frameworks-artifacts-and-decision-paths-sdd-c052df529274)

---

## 六、关键参考资源

| 资源 | 链接 |
|------|------|
| Martin Fowler SDD 分析 | https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html |
| Thoughtworks 技术雷达 - SDD | https://www.thoughtworks.com/en-us/radar/techniques/spec-driven-development |
| GitHub Blog 官方介绍 | https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/ |
| Augment Code SDD 指南 | https://www.augmentcode.com/guides/what-is-spec-driven-development |
| SDD 2026 综合指南 | https://thebcms.com/blog/spec-driven-development |
| 15 框架对比 | https://medium.com/@wasowski.jarek/comparing-15-spec-driven-development-frameworks-artifacts-and-decision-paths-sdd-c052df529274 |
