# AI Native 平台度量 - SDD 开发方案

> **目标**: 8小时内完成 AI Native 度量平台 1:1 复刻
> **方法**: Spec-Driven Development + Claude Code 分阶段提示词驱动
> **架构**: 前后端分离，后端 Python/FastAPI + ES，前端 React/Vue

---

## ⚠️ 核心原则

> **🚨 复刻平台的实际页面是唯一真实来源。**
>
> 本文档中的 API 路径、字段名、查询参数、指标名称等均基于需求文档的**初步分析**，
> **必须在实际提取原型页面 JSON 后进行确认和调整。**
>
> 如果 JSON 提取结果与本文档描述不一致，**以 JSON 为准，修改本文档和代码。**

---

## 一、需求分析摘要（待 JSON 确认）

> ⚠️ 以下内容基于原始需求文档分析，仅供参考。实际字段名、指标名称、筛选条件等以原型页面提取的 JSON 为准。

### 两个核心功能模块（初步）

| 模块 | 数据源（初步） | 核心指标（初步） | 下钻层级 |
|------|--------------|----------------|---------|
| Token 使用量 | ai_token_usage + hrm_user | 待 JSON 确认 | 体系→团队→个人（待 JSON 确认） |
| 硅基含量 | commits_ai_code + hrm_user | 待 JSON 确认 | 体系→团队→个人（待 JSON 确认） |

### 关键约束（数据层，不影响前端）

**ES 脏数据处理（3种，必须过滤）**：

| # | 脏数据类型 | 说明 | 处理方式 |
|---|----------|------|----------|
| 1 | 人员多部门 | 同一成员在 hrm_user 中存在多条记录（不同部门） | 按 nameid 去重，保留一条 |
| 2 | token 数据无对应人员 | ai_token_usage 中有用户不在 hrm_user 中 | 以 hrm_user 为基准，过滤掉不在册的用户 |
| 3 | 请求失败记录 | ai_token_usage 中 total_price = -1 | 直接排除 |

**其他约束**：
- 只有 hrm_user 中在职人员才纳入统计
- 接口响应 ≤ 3秒
- 入参校验防注入

### 阈值定义（初步，待 JSON 确认默认值）

- **AI-Native 用户**: 日均 Token ≥ 100K tokens/天
- **硅基人员**: AI代码匹配行数/总代码行数 ≥ 阈值（默认值待 JSON 确认）

### 职类映射（初步）

- 开发类: zhilei ∈ [开发类, 软件开发类]
- 测试类: zhilei ∈ [测试类]
- 其它类: 排除上述两类

---

## 二、技术架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend    │────▶│Elasticsearch│
│  React/Vue   │     │  FastAPI     │     │  (只读)      │
│  :80         │     │  :8080/api   │     │  :8200      │
└─────────────┘     └──────────────┘     └─────────────┘
```

### 后端 API 设计（⚠️ 待前端 JSON 确认后调整）

> ⚠️ 以下 API 路径和参数是基于需求文档的**初步设计**。
> **必须在阶段 0 提取原型页面 JSON 后，根据实际前端页面的筛选字段、表格列名、交互方式来调整 API 设计。**
>
> 调整原则：
> 1. 前端筛选栏有几个字段，API 就接收几个查询参数
> 2. 前端表格有几列，API 就返回几列数据
> 3. 前端指标卡片有几个，API 就提供几个汇总数据
> 4. 前端下钻路径有几层，API 就提供几层接口

**初步 API 设计**（待调整）:

```
# Token 使用量（路径和参数待确认）
GET /api/token-usage/overview     — 体系级概览（返回字段待确认）
GET /api/token-usage/team         — 团队级下钻（参数待确认）
GET /api/token-usage/person       — 个人级下钻（参数待确认）

# 硅基含量（路径和参数待确认）
GET /api/silicon/overview         — 体系级概览（返回字段待确认）
GET /api/silicon/team             — 团队级下钻（参数待确认）
GET /api/silicon/person           — 个人级下钻（参数待确认）

# 筛选器（字段待确认）
GET /api/filters/teams            — 团队列表
GET /api/filters/job-types        — 职类选项
```

**初步查询参数**（待确认）:
```
team:        团队名称（可选，待确认字段名）
job_type:    职类（待确认选项值）
start_date:  开始日期
end_date:    结束日期
threshold:   阈值（待确认默认值和范围）
```

---

## 三、开发流程（⚠️ 已调整顺序）

> **核心改动：先提取前端结构 → 确认 API → 再开发后端**
>
> 原因：后端 API 必须服务前端页面，而前端页面的实际结构可能与需求文档不一致。
> 先确认前端需要什么数据，再设计后端 API，避免返工。

### 阶段 0: 项目初始化 + 前端信息采集（20分钟）

**目标**: 初始化项目 + 提取原型页面真实结构

#### 步骤 1: 从远程 master 拉取最新代码 + 创建本地新分支（5分钟）

> **工作流程**：从远程分支 master 拉取最新代码，创建本地新分支 `feature-52273`（仅创建本地分支，先不创建远程分支），后续均在新分支 `feature-52273` 下开发。

**Claude Code 提示词**:
```
请帮我完成以下操作：

1. 检查当前 git 状态，如果未提交的改动：
   - 保存当前改动：git stash push -m "保存当前改动，准备切换到 feature-52273 分支"

2. 切换到 master 分支并拉取最新代码：
   - git checkout master
   - git pull origin master

3. 创建本地新分支：
   - git checkout -b feature-52273

4. 如果之前有保存的改动，恢复到新分支：
   - git stash pop

5. 分析项目结构，告诉我：
   - 前端用了什么框架（React/Vue/其他）
   - 后端用了什么框架（FastAPI/Flask/Django）
   - 已有的目录结构和配置文件
   - docker-compose.yml 中的服务配置
   - ES 连接配置在哪里

6. 确认项目骨架能正常启动：
   - 本地启动后端，确认健康检查 API 正常
   - 本地启动前端，确认页面能加载
   - 确认能连接 ES: http://10.65.134.124:8200

7. 确认当前分支：
   - git branch -v
   - 当前应该在 feature-52273 分支（本地）

当前在本地分支 feature-52273 开发，暂不创建远程分支。
```

#### 步骤 2: 提取原型页面结构 + 样式信息（15分钟）

> **已确认**：`/metrics` 是单页应用（SPA），token-usage 和 silicon 不是独立路由，是同一页面内的内容切换。
> 因此只需提取 `/metrics` 一个 URL 即可获取全部信息。

##### 2a. 页面结构提取（Selenium，已完成）

```powershell
python extract_structure.py http://10.65.134.124:8080/metrics -o page-overview.json
```

> 已生成 `page-overview.json`，包含 API 清单、表格结构、筛选字段等。

##### 2c. 下载原平台完整前端资源（方案 B，推荐）

> **直接下载原平台的所有前端资源（HTML/CSS/JS/图片/字体），替换 API 地址即可 100% 复刻。**
> 不需要自己写前端代码，不需要手动还原样式。

**执行**：
```powershell
python download_frontend.py http://10.65.134.124:8080/metrics -o original-frontend
```

**输出**：
- `original-frontend/index.html` — 渲染后 HTML
- `original-frontend/static/` — 所有 CSS、JS、图片、字体
- `original-frontend/screenshot-original.png` — 原平台截图
- `original-frontend/replace-api.sh` — API 地址替换脚本
- `original-frontend/download-report.json` — 下载报告（含发现的 API 路径和配置）

**替换 API 地址**：
```bash
bash replace-api.sh http://你的后端地址:端口
```

**本地测试**：
```bash
cd original-frontend
python -m http.server 3000
# 浏览器访问 http://localhost:3000
```

#### 步骤 3: 确认 API 设计报告

> **已从 page-overview.json 确认实际 API**，无需重新分析。

**已确认 API 清单**：

| API | 方法 | 参数 | 说明 |
|-----|------|------|------|
| `/api/metrics/token-usage/dept-tree?team_type=department` | GET | team_type | 部门树（带层级） |
| `/api/metrics/token-usage/dept-tree` | GET | - | 部门树 |
| `/api/metrics/token-usage/zhilei-list` | GET | - | 职类列表（24个） |
| `/api/metrics/token-usage/stats-by-project` | POST | days, limit, start_date, end_date, teams, zhilei, ai_native_threshold, team_type | 核心统计数据 |

**POST body 示例**：
```json
{"days":30,"limit":10000,"start_date":null,"end_date":null,"teams":[],"zhilei":[],"ai_native_threshold":0.1,"team_type":"department"}
```

**返回数据结构**：
- `cards_by_zhilei` — 指标卡片（dev/other/test/total 四组）
- `projects` — 表格数据（project_name, ai_native_count, total_tokens, request_count, total_price, has_children, children_data）
- `daily_median` — 日均中位数

**表格列**：# | 团队名称 | AI-NATIVE人数 | TOTAL TOKENS | 请求次数 | 人均费用/总费用（占比） | 操作

**筛选字段**：全部团队（按钮）、全部职类（按钮）、最近30天（按钮）、阈值输入框（number, 默认0.1）、刷新按钮

**下钻逻辑**：has_children=true 的行可点击，展示 children_data

**验证**: API 清单已确认，可直接进入阶段1开发

---

### 阶段 1: 数据层（30分钟）

**目标**: 连接 ES，理解数据结构，构建数据查询层

**Claude Code 提示词 1 - ES 数据探索**:
```
请帮我探索 Elasticsearch 数据结构：

ES 地址: http://10.65.134.124:8200

1. 查询三个索引的 mapping：
   - hrm_user
   - ai_token_usage
   - commits_ai_code

2. 每个索引各取 3 条样本数据，分析字段格式

3. 验证以下数据问题（ES 脏数据 3 种类型）：
   - 脏数据1: hrm_user 中 nameid 是否有重复（同一人在多部门）
     → 查询: 按 nameid 聚合，找出 count > 1 的 nameid
   - 脏数据2: ai_token_usage 中有多少用户不在 hrm_user 中
     → 查询: ai_token_usage 的 user 去重后，与 hrm_user nameid 做差集
   - 脏数据3: ai_token_usage 中 total_price=-1 的数量和占比
     → 查询: 统计 total_price=-1 的文档数

4. 输出每个索引的完整字段清单和数据质量报告
```

**Claude Code 提示词 2 - 数据查询层**:
```
基于上面的 ES 数据结构分析，以及阶段 0 确认的 API 设计报告：

[粘贴 API 设计确认报告]

请帮我构建后端数据查询层：

要求：
1. 创建 ES 客户端连接模块
2. 根据确认的 API 设计，创建对应的数据查询函数
3. 查询函数的返回字段必须与 API 设计报告中的返回字段一致

关键约束：
   - ES 聚合查询优化（用 terms aggregation 而非全量拉取）
   - 查询响应时间 ≤ 3秒
   - 入参校验（防注入）
   - 脏数据1: hrm_user 中 nameid 去重（同一人在多部门，保留一条）
   - 脏数据2: ai_token_usage 中的用户必须存在于 hrm_user（不在册的过滤掉）
   - 脏数据3: ai_token_usage 中 total_price=-1 排除
   - 只统计在职人员

请先写测试，再写实现。
```

**验证**: 数据查询层能正确聚合 ES 数据，返回字段与 API 设计报告一致

---

### 阶段 2: API 层（30分钟）

**Claude Code 提示词**:
```
基于已有的数据查询服务层，以及阶段 0 确认的 API 设计报告：

[粘贴 API 设计确认报告]

请帮我构建 API 层：

要求：
1. 严格按照 API 设计报告中的端点、参数、返回字段实现
2. 不要假设任何字段，一切以报告为准
3. 如果发现实现中有字段对不上，先报告，不要自行修改

入参校验：
   - 日期格式 YYYY-MM-DD
   - 防止 ES 注入（参数化查询）
   - 阈值范围校验

写集成测试验证每个端点。
```

**验证**: 所有 API 端点返回的数据字段与 API 设计报告一致

---

### 阶段 3: 前端页面（60分钟）

> 详见 `frontend-replication-guide.md`

**核心原则**: 以提取的 JSON 为准，1:1 复刻原型页面。

**Claude Code 提示词**（阶段 1-3 合并，参考 frontend-replication-guide.md 第四章）:
```
请严格根据以下原型页面结构 JSON 搭建前端，1:1 复刻。

[粘贴 page-token.json]
[粘贴 page-silicon.json]
[粘贴 drill-down.json]

要求：
1. 导航 Tab 数量和文字严格以 JSON 为准
2. 筛选栏字段数量和类型严格以 JSON 为准
3. 指标卡片数量和标题严格以 JSON 为准
4. 表格列名和列数严格以 JSON 为准
5. 下钻路径严格以 drill-down.json 为准
6. 调用后端 API 获取数据（API 路径见 API 设计报告）

不要使用任何文档之外的假设。JSON 中有几个就实现几个。
```

**验证**: 页面展示与原型一致（对比 JSON 验证）

---

### 阶段 4: 联调与优化（30分钟）

**Claude Code 提示词**:
```
请帮我完成以下联调优化工作：

1. 数据一致性验证：
   - 用相同筛选条件对比原型页面和本地页面的数据
   - 逐字段对比指标卡片数值
   - 逐列对比表格数据

2. 性能优化：
   - 检查所有 ES 查询的响应时间
   - 如果超过 3 秒，优化方案：
     a) 使用 ES 的 terms aggregation 替代全量扫描
     b) 添加 query filter cache
     c) 使用 composite aggregation 分页
   - 前端添加 loading 状态和防抖

3. 数据过滤验证：
   - 验证脏数据1: hrm_user 中只有在职人员被统计，nameid 去重
   - 验证脏数据2: ai_token_usage 中不在 hrm_user 的用户已被过滤
   - 验证脏数据3: total_price=-1 被排除

4. 边界情况处理：
   - 空数据时显示"暂无数据"
   - 日期范围验证
   - 阈值边界值测试

（Docker 构建测试移至阶段 5，在本地测试通过后执行）
```

---

### 阶段 5: 自测验证（20分钟）

> **测试顺序**: 先在 Win10 本地构建测试 → 通过后再到远程 Docker 环境测试

#### 步骤 1: 本地构建测试（Win10，无 Docker）

**Claude Code 提示词**:
```
请帮我完成本地自测（Win10 环境，不使用 Docker）：

1. 本地启动后端：
   - 根据项目框架，直接运行后端服务（如 python main.py 或 uvicorn）
   - 确认能连接 ES: http://10.65.134.124:8200
   - 确认健康检查 API 正常

2. 本地启动前端：
   - npm run dev 或等效命令
   - 确认页面能正常加载

3. 自动化对比验证：
   - 运行提取脚本对比本地页面和原型页面的 JSON：
     python extract_structure.py http://localhost:8080/metrics -o local-metrics.json
     python extract_structure.py http://localhost:8080/metrics/token-usage -o local-token.json
     python extract_structure.py http://localhost:8080/metrics/silicon -o local-silicon.json

4. 逐项对比：
   a) 导航 Tab：数量、文字是否一致
   b) 筛选栏：字段数量、类型是否一致
   c) 指标卡片：数量、标题是否一致
   d) 表格列名：是否完全一致
   e) 下钻路径：是否一致
   f) 数据值：用相同筛选条件对比原型和本地的数值

5. 记录所有差异并修复，修复后重新对比，直到一致
```

#### 步骤 2: 远程 Docker 环境测试

**本地测试通过后**，在远程服务器进行 Docker 构建测试：

**Claude Code 提示词**:
```
本地测试已通过，现在请帮我完成 Docker 环境测试：

1. Docker 构建：
   - docker-compose build
   - 确认构建成功
   - 确认 6 个环境变量未被修改

2. Docker 启动：
   - docker-compose up -d
   - 确认所有服务正常启动
   - 检查日志无错误

3. 运行与本地相同的对比验证（提取脚本对比 Docker 环境页面和原型页面）

4. 如有差异，修复后重新构建测试
```

---

### 阶段 6: 提交发布（10分钟）

**Claude Code 提示词**:
```
请帮我完成代码提交：

1. 确认 git config 正确（user.name 和 user.email）
2. 提交所有修改到个人分支
3. 推送到远程
4. 等待自动构建验证结果
5. 构建成功后，创建 Merge Request（注意：只允许一次）

⚠️ 提交前确认：
- 6 个环境变量未被修改
- docker-compose.yml 格式正确
- 所有代码已提交
```

---

## 四、关键提示词模板

### 通用前缀（每次 Claude Code 会话开始时使用）

```
你是一个专业的全栈开发工程师，正在完成 AI Native 平台度量项目的开发。

项目背景：
- 这是一个度量平台，分析研发团队的 AI 工具使用情况和代码硅基含量
- 前后端分离架构，后端连接 Elasticsearch（只读）
- 需要实现两个核心功能：Token使用量分析、硅基含量分析
- 支持多维度过滤和逐级下钻

⚠️ 重要原则：
- 复刻平台的实际页面是唯一真实来源
- 所有字段名、指标名称、筛选条件以实际提取的 JSON 为准
- 如果发现实际页面与需求文档不一致，以实际页面为准

技术约束：
- ES 查询响应 ≤ 3秒
- 严格入参校验
- 数据有脏数据需要过滤处理

需求文档在: knowledge/tech/AI-Native/requirement.md
开发方案在: knowledge/tech/AI-Native/development-plan.md
前端复刻指南: knowledge/tech/AI-Native/frontend-replication-guide.md

请严格遵循 TDD 方式开发：先写测试 → 确认失败 → 实现 → 确认通过 → 提交。
```

### 调试提示词模板

```
遇到问题时的排查思路：
1. 先看错误日志，确认是前端还是后端问题
2. 如果是 ES 查询问题，先在 Kibana (http://10.65.134.124:8601) 中测试查询
3. 如果是数据不对，对比原型页面 (http://10.65.134.124:8080/metrics) 的数据
4. 如果是前端布局问题，对比提取的 JSON 验证结构是否一致
```

---

## 五、时间分配建议

| 阶段 | 时间 | 说明 |
|------|------|------|
| 阶段0: 初始化 + 前端信息采集 | 20min | 从远程 master 拉取最新代码，创建本地分支 feature-52273，前端提取步骤 |
| 阶段1: 数据层 | 30min | 输入改为 API 设计确认报告 |
| 阶段2: API层 | 30min | 严格按确认报告实现 |
| 阶段3: 前端页面 | 60min | 以 JSON 为准 |
| 阶段4: 联调优化 | 30min | 增加 JSON 对比验证 |
| 阶段5: 自测验证 | 20min | 增加自动化对比 |
| 阶段6: 提交发布 | 10min | - |
| **缓冲时间** | **约4h** | 充足 |

---

## 六、风险点 & 应对

| 风险 | 应对 |
|------|------|
| 需求文档与实际页面不一致 | **阶段0先提取 JSON，以 JSON 为准** |
| 模板技术栈未知 | 阶段0先分析，再决定具体实现方式 |
| ES 查询性能不达标 | 用 aggregation 替代全量扫描，加 filter cache |
| 脏数据处理复杂 | 3 种脏数据：人员多部门去重、token 无对应人员过滤、失败请求排除 |
| API 设计与前端不匹配 | **阶段0确认 API 设计后，再开发后端** |
| Docker 构建失败 | 不修改 docker-compose.yml 的 6 个环境变量 |
| 考试超时 | 先实现核心功能，DFX和非功能需求最后处理 |
| 考试方反自动化限制 | 脚本已内置反检测措施（见 frontend-replication-guide.md 2.4节）+ CDP 兜底 + 手动 F12 保底 |
| API 拦截失效（SSR/WebSocket） | 自动检测并警告，降级到手动 F12 抓包（见 frontend-replication-guide.md 2.5节） |

---

## 七、配套文档

| 文件 | 用途 |
|------|------|
| `development-plan.md` | 总体开发方案（本文档） |
| `frontend-replication-guide.md` | 前端复刻完全指南（环境+脚本+策略+提示词） |
| `requirement.md` | 原始需求文档 |

---

*方案版本: v2.1*
*更新时间: 2026-04-20*
*方案版本: v3.0*
*更新时间: 2026-04-20*
*核心改动: 新增 Playwright 样式提取方案，用于前端页面 1:1 复刻；API 清单已确认*
