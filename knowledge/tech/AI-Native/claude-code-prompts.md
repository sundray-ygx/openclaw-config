# AI Native 度量平台 - Claude Code 执行手册

> **使用方法**: 考试时按阶段顺序，复制提示词到 Claude Code 执行
> **配合文档**: development-plan.md + frontend-replication-guide.md
> **⚠️ 核心原则**: 一切以实际提取的 JSON 为准，不要硬编码需求文档中的字段名

---

## 📋 会话通用前缀（每次新建 Claude Code 会话时粘贴）

```
你是专业的全栈开发工程师，正在完成 AI Native 平台度量项目。

项目概述：
- 度量平台，分析研发团队 AI 工具使用和代码硅基含量
- 前后端分离，后端连 Elasticsearch（只读）
- 两个核心功能：Token使用量分析、硅基含量分析
- ES地址: http://10.65.134.124:8200
- 原型参考: http://10.65.134.124:8080/metrics

⚠️ 核心原则：
- 复刻平台的实际页面是唯一真实来源
- 所有字段名、指标名称、筛选条件以实际提取的 JSON 为准
- 如果发现实际页面与需求文档不一致，以实际页面为准
- API 设计必须根据前端 JSON 提取结果确认后再实现

核心数据源：
1. hrm_user — 组织架构（nameid/zhilei/dept_1~4/user_status）
2. ai_token_usage — Token消耗（total_tokens/total_price/username/request_time）
3. commits_ai_code — 硅基含量（committer_user/file_ai_code_match_lines/diff_lines/commit_at）

ES 脏数据（3种，必须过滤）：
1. 人员多部门 — 同一 nameid 在 hrm_user 中有多条记录，需去重
2. token 无对应人员 — ai_token_usage 中的用户不在 hrm_user 中，需过滤
3. 请求失败 — total_price=-1，需排除

技术约束：
- ES查询响应 ≤ 3秒，用aggregation不要全量拉取
- 严格入参校验防注入
- 只统计在职人员

开发方式：严格TDD，先写测试→确认失败→实现→确认通过→提交。
```

---

## 🚀 阶段 0: 项目初始化 + 前端信息采集（~20min）

### 提示词 0-1: 归档旧代码 + 从 master 重置

```
请执行以下操作：

1. 归档当前分支的代码（保留在 git 历史中）：
   - git add -A && git commit -m "archive: 旧方案代码归档，切换新方案"
   - git tag archive-before-redesign

2. 将当前分支重置为 master 最新代码：
   - git fetch origin
   - git reset --hard origin/master

3. 分析并输出以下信息：
   a) 项目结构树（3层深度）
   b) 前端技术栈：框架、UI组件库、构建工具
   c) 后端技术栈：语言、框架、已有的路由/模型
   d) docker-compose.yml 中的服务配置
   e) ES 连接配置在哪里
   f) 已有的依赖（package.json / requirements.txt）

4. 确认项目骨架能正常启动：
   - 本地启动后端，确认健康检查 API 正常
   - 本地启动前端，确认页面能加载
   - 确认能连接 ES: http://10.65.134.124:8200

不要修改基础设施配置（docker-compose.yml、ES 连接等）。
输出完整的项目分析报告。
```

### 提示词 0-2: 提取原型页面结构（在 PowerShell 中执行）

> 这一步在 Claude Code 外部执行，使用 scripts/frontend/ 下的脚本

```powershell
# 环境检查
python check_env.py

# 提取三个页面
python extract_structure.py http://10.65.134.124:8080/metrics -o page-overview.json
python extract_structure.py http://10.65.134.124:8080/metrics/token-usage -o page-token.json
python extract_structure.py http://10.65.134.124:8080/metrics/silicon -o page-silicon.json

# 测试下钻交互
python extract_structure.py http://10.65.134.124:8080/metrics --drill-down "终端安全产品研发部" -o drill-down.json

# 如需登录
# python extract_structure.py http://10.65.134.124:8080/metrics --cookie cookies.json -o page-overview.json
```

### 提示词 0-3: 确认 API 设计

> 将提取的 JSON 结果粘贴给 Claude Code

```
请分析以下原型页面 JSON 提取结果，帮我确认 API 设计。

[粘贴 page-token.json 的内容]

[粘贴 page-silicon.json 的内容]

[粘贴 drill-down.json 的内容]

请输出一份「API 设计确认报告」，包括：

1. 导航 Tab：实际有几个？文字是什么？
2. 筛选字段：实际有几个？分别是什么类型？name 和 id 是什么？
3. 指标卡片：实际有几个？标题分别是什么？
4. 表格列名：实际有几列？列名分别是什么？
5. 下钻层级：实际有几层？每层的表格列是否不同？
6. 网络请求：前端调用了哪些 API？

基于以上分析，输出后端需要实现的 API 清单：
- 每个 API 的路径、方法、查询参数
- 每个 API 的返回字段（字段名、类型）
- 前后端数据格式约定

这份报告将作为后续阶段 1-3 的输入，请务必准确。
```

---

## 🔍 阶段 1: 数据层（~30min）

### 提示词 1-1: ES 数据结构探索

```
请帮我探索 Elasticsearch 数据，理解实际数据结构：

ES地址: http://10.65.134.124:8200

1. 查询三个索引的 mapping：
   GET /hrm_user/_mapping
   GET /ai_token_usage/_mapping  
   GET /commits_ai_code/_mapping

2. 每个索引取 5 条样本数据

3. 数据质量检查（ES 脏数据 3 种类型）：

   a) 脏数据1 - 人员多部门：
      hrm_user 中 nameid 是否有重复
      → 按 nameid 聚合，找出 count > 1 的 nameid
   
   b) 脏数据2 - token无对应人员：
      ai_token_usage 中有多少用户不在 hrm_user 中
      → ai_token_usage 的 username 去重后，与 hrm_user nameid 做差集
   
   c) 脏数据3 - 请求失败：
      ai_token_usage 中 total_price=-1 的数量和占比

4. 输出完整的字段清单和数据质量报告
```

### 提示词 1-2: 构建数据查询层（TDD）

```
基于 ES 数据结构分析，以及阶段 0 确认的 API 设计报告：

[粘贴 API 设计确认报告]

请构建后端数据查询层。严格TDD。

先写测试，再写实现。

test_data_service.py 测试用例：
1. test_get_active_users - 获取在职用户，nameid去重（脏数据1）
2. test_get_active_users_filter_team - 按团队过滤
3. test_get_active_users_filter_job_type - 按职类过滤
4. test_get_token_stats - Token聚合，排除total_price=-1（脏数据3）
5. test_get_token_stats_filter_non_hrm - 过滤不在hrm_user中的用户（脏数据2）
6. test_get_silicon_stats - 硅基含量聚合
7. test_threshold - 阈值判定逻辑

data_service.py 实现：
1. es_client - ES连接（地址从配置读取）
2. get_active_users(team=None, job_type=None) 
   - 查 hrm_user，user_status=在职
   - nameid 去重（脏数据1：同一人在多部门，取一条）
   - 返回用户列表
   
3. get_token_stats(user_names, start_date, end_date)
   - 查 ai_token_usage，username in user_names（脏数据2：只查在册用户）
   - 排除 total_price=-1（脏数据3）
   - 按用户聚合：SUM(total_tokens), COUNT, SUM(total_price)
   - 返回字段严格按 API 设计报告
   
4. get_silicon_stats(user_names, start_date, end_date, threshold)
   - 查 commits_ai_code
   - 按用户聚合
   - 返回字段严格按 API 设计报告

关键约束：
- 用 ES terms aggregation 做聚合，不要全量拉到内存
- 查询响应要 ≤ 3秒
- 参数化查询防注入

运行测试确保全部通过。
```

---

## 🔌 阶段 2: API 层（~30min）

### 提示词 2-1: 构建 REST API（TDD）

```
基于已有的 data_service，以及阶段 0 确认的 API 设计报告：

[粘贴 API 设计确认报告]

请构建 API 层。严格TDD。

⚠️ 重要：严格按照 API 设计报告中的端点、参数、返回字段实现。
如果发现实现中有字段对不上，先报告，不要自行修改。

先写测试，再实现。

test_api.py 测试用例：
1. 根据报告中的每个 API 端点写一个测试
2. test_input_validation - 入参校验（非法日期、注入字符等）
3. test_dirty_data_filtered - 验证 3 种脏数据被正确过滤

API 端点：按 API 设计报告实现

通用查询参数：按报告中的筛选字段实现

入参校验：
- 日期格式 YYYY-MM-DD
- 防止 ES 注入（参数化查询）
- 阈值范围校验

职类映射（如报告中有职类筛选）：
- dev → zhilei in ['开发类', '软件开发类']
- test → zhilei in ['测试类']  
- other → 排除上述

运行测试确保全部通过。
```

---

## 🎨 阶段 3: 前端页面（~60min）

> 详见 frontend-replication-guide.md

### 提示词 3-1: 搭建页面骨架

```
请严格根据以下原型页面结构 JSON 搭建前端骨架，1:1 复刻。

[粘贴 page-token.json 的内容]

[粘贴 page-silicon.json 的内容]

要求：
1. 根据 JSON 中的 navigation.tabs 创建路由，Tab 数量和文字严格一致
2. 根据 JSON 中的 filters.fields 创建筛选栏，字段类型、数量、名称严格一致
3. 公共组件：Layout（导航Tab）、FilterBar、MetricCard、DataTable、Breadcrumb
4. 先搭静态骨架，用 Mock 数据确认布局正确

不要假设有任何字段，一切以 JSON 为准。
如果 JSON 中有 3 个 Tab 就创建 3 个，有 5 个筛选字段就创建 5 个。
```

### 提示词 3-2: 各页面功能实现

```
请根据以下 JSON 实现各页面的完整功能，严格 1:1 复刻原型。

Token 使用量页面 JSON:
[粘贴 page-token.json 的内容]

硅基含量页面 JSON:
[粘贴 page-silicon.json 的内容]

下钻测试结果:
[粘贴 drill-down.json 的内容]

API 设计报告:
[粘贴 API 设计确认报告]

实现要求：
1. 指标卡片：数量、标题、数值格式严格以 JSON 中的 metric_cards 为准
2. 表格列：列名、列数严格以 JSON 中的 table.headers 为准
3. 筛选栏：字段类型、数量、默认值严格以 JSON 中的 filters.fields 为准
4. 导航 Tab：文字、数量严格以 JSON 中的 navigation.tabs 为准
5. 下钻交互：层级路径严格以 drill-down.json 中的 drill_down_path 为准
6. API 调用：路径和参数按 API 设计报告

交互要求：
- 表格行 hover 高亮，行可点击下钻
- 面包屑显示当前层级路径
- 筛选条件变更后重新查询当前层级
- 空数据显示"暂无数据"，加载中显示 loading
- 下钻时保持筛选条件

不要使用任何文档之外的任何假设。
JSON 中有几个卡片就实现几个，有几列就实现几列。
```

---

## 🔧 阶段 4: 联调与优化（~30min）

### 提示词 4-1: 联调验证

```
请完成以下联调工作：

1. 数据一致性验证：
   - 用相同筛选条件对比原型页面和本地页面的数据
   - 逐字段对比指标卡片数值
   - 逐列对比表格数据

2. 性能优化：
   - 检查所有 ES 查询的响应时间
   - 如果超过 3 秒，用 terms aggregation 替代全量扫描
   - 前端添加 loading 状态和防抖

3. 脏数据过滤验证：
   - 验证脏数据1: hrm_user 中只有在职人员被统计，nameid 去重
   - 验证脏数据2: ai_token_usage 中不在 hrm_user 的用户已被过滤
   - 验证脏数据3: total_price=-1 被排除

4. 边界情况处理：
   - 空数据时显示"暂无数据"
   - 日期范围验证
   - 阈值边界值测试
```

---

## ✅ 阶段 5: 自测验证（~20min）

### 提示词 5-1: 本地构建测试（Win10，无 Docker）

```
请完成本地自测（Win10 环境，不使用 Docker）：

1. 本地启动后端：
   - 确认能连接 ES
   - 确认健康检查 API 正常

2. 本地启动前端：
   - 确认页面能正常加载

3. 自动化对比验证（在 PowerShell 中执行）：
   python extract_structure.py http://localhost:{前端端口}/metrics -o local-overview.json
   python extract_structure.py http://localhost:{前端端口}/metrics/token-usage -o local-token.json
   python extract_structure.py http://localhost:{前端端口}/metrics/silicon -o local-silicon.json

4. 逐项对比本地 JSON 与原型 JSON：
   □ 导航 Tab：数量、文字一致
   □ 筛选栏：字段数量、类型一致
   □ 指标卡片：数量、标题一致
   □ 表格列名：完全一致
   □ 下钻路径：一致
   □ 数据值：用相同筛选条件对比

5. 记录所有差异并修复，修复后重新对比，直到一致
```

### 提示词 5-2: 远程 Docker 环境测试（本地通过后）

```
本地测试已通过，现在完成 Docker 环境测试：

1. Docker 构建：
   - docker-compose build
   - 确认构建成功
   - 确认 6 个环境变量未被修改

2. Docker 启动：
   - docker-compose up -d
   - 确认所有服务正常启动
   - 检查日志无错误

3. 运行与本地相同的对比验证

4. 如有差异，修复后重新构建测试
```

---

## 📤 阶段 6: 提交发布（~10min）

### 提示词 6-1: 代码提交

```
准备提交代码：

1. 检查 git config：
   git config user.name  → 应该是 "姓名+工号" 格式
   git config user.email → 应该是 "工号@sangfor.com" 格式

2. 检查未提交的修改：
   git status
   git diff

3. 确认以下事项：
   □ docker-compose.yml 的 6 个环境变量未被修改
   □ 所有功能已实现并测试通过
   □ 无调试代码残留（console.log/print等）

4. 提交：
   git add .
   git commit -m "feat: 实现AI Native度量平台 - Token使用量+硅基含量分析"
   git push origin feature-xxx

5. 等待自动构建结果

6. 构建成功后创建 Merge Request（⚠️只能创建一次）
```

---

## 🐛 调试模板

### 遇到 ES 查询问题

```
排查 ES 查询问题：

1. 先在 Kibana (http://10.65.134.124:8601/app/dev_tools#/console) 中测试查询
2. 用 _search api 验证查询语法
3. 检查是否用了正确的字段名（区分 keyword 和 text 类型）
4. 如果聚合慢，用 _profile API 分析：GET /index/_search?profile=true
5. 常见问题：
   - keyword 字段需要用 .keyword 后缀
   - 日期字段格式可能不一致
   - 聚合嵌套层级错误
```

### 遇到数据不一致

```
排查数据不一致问题：

1. 确认筛选条件完全一致（团队/职类/日期范围）
2. 检查 3 种脏数据过滤：
   - 脏数据1: nameid 去重（同一人在多部门）
   - 脏数据2: 不在 hrm_user 中的用户是否被过滤
   - 脏数据3: total_price=-1 是否被排除
3. 检查是否只统计了在职人员
4. 检查职类映射：开发类=[开发类,软件开发类]
5. 检查阈值是否一致
```

### 遇到前端布局不一致

```
排查前端布局问题：

1. 重新运行提取脚本对比：
   python extract_structure.py http://localhost:{端口}/metrics -o local.json
   对比 local.json 与原型提取的 JSON

2. 逐项检查差异：
   - Tab 数量和文字
   - 筛选字段数量和类型
   - 卡片数量和标题
   - 表格列名
   - 下钻路径

3. 如果 CSS 选择器提取失败，用 Chrome F12 检查实际选择器
```

---

## ⏰ 时间管理参考

| 时间点 | 应完成 | 状态检查 |
|--------|--------|----------|
| 0:20 | 阶段0完成：归档+重置+JSON提取+API确认 | 产出 API 设计确认报告 |
| 0:50 | 阶段1完成：数据层 | 单元测试全部通过 |
| 1:20 | 阶段2完成：API层 | API测试全部通过 |
| 2:20 | 阶段3完成：前端页面 | 页面可正常展示数据 |
| 2:50 | 阶段4完成：联调优化 | 数据对比一致 |
| 3:10 | 阶段5完成：本地自测 | JSON 对比一致 |
| 3:30 | 阶段6完成：提交发布 | 构建成功 |
| 3:30+ | 缓冲时间 | 处理意外情况 |

> 8小时考试，核心开发约3-4小时，剩余时间处理意外情况。

---

*文档版本: v2.0*
*更新时间: 2026-04-19*
*核心改动: 以 JSON 为准、先前端后后端、3种脏数据、本地测试优先*
