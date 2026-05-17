# 前端页面修复方案

## 问题诊断

### 问题1：前端页面与原平台存在视觉差异
- 当前方案是手动编写前端代码，无法 100% 还原原平台样式
- 方案 B（下载原平台静态资源）是正确方向，但需要正确集成

### 问题2：前端未显示后端数据
- 原平台 API 使用相对路径 `/api/...`
- 需要确保前端请求被正确代理到后端
- 或者后端 API 路径与原平台一致

## 原平台 API 完整清单（已确认）

| # | API | 方法 | 说明 |
|---|-----|------|------|
| 1 | `/api/metrics/token-usage/dept-tree?team_type=department` | GET | 部门树 |
| 2 | `/api/metrics/token-usage/dept-tree` | GET | 部门树（无参） |
| 3 | `/api/metrics/token-usage/zhilei-list` | GET | 职类列表 |
| 4 | `/api/metrics/token-usage/stats-by-project` | POST | 核心统计 |

### stats-by-project 请求参数
```json
{
  "days": 30,
  "limit": 10000,
  "start_date": null,
  "end_date": null,
  "teams": [],
  "zhilei": [],
  "ai_native_threshold": 0.1,
  "team_type": "department"
}
```

### stats-by-project 返回结构
```
data: {
  cards_by_zhilei: {
    dev: { ai_native_count, ai_native_percentage, total_members, total_tokens, total_price, external_*, local_* },
    other: { ... },
    test: { ... },
    total: { ... }
  },
  daily_median: number,
  filter_days: number,
  projects: [
    {
      project_name: string,        // 部门名
      ai_native_count: number,     // AI-Native人数
      total_members: number,       // 总人数
      total_tokens: number,        // Token总量
      request_count: number,       // 请求次数
      total_price: number,         // 总费用
      external_price: number,      // 外部费用
      local_price: number,         // 本地费用
      has_children: boolean,       // 是否可下钻
      children_data: [             // 子部门
        { name, dept_id, has_children, children }
      ]
    }
  ]
}
```

### 页面表格结构
| # | 团队名称 | AI-NATIVE人数/总人数(%) | TOTAL TOKENS | 请求次数 | 人均费用/总费用(占比) | 操作 |
|---|---------|----------------------|-------------|---------|-------------------|------|

示例行数据：
- 溯源研发部: 123/132 93% | 21732.42M | 329.16k | 0.13/17.53万元 11.7% | 成员明细
- 操作列按钮文字: "成员明细"

### 筛选栏
1. "全部团队" (button) - 触发 dept-tree
2. "全部职类" (button) - 触发 zhilei-list
3. "最近 30 天" (button) - 时间范围
4. 阈值输入框 (number input, 默认 0.1)
5. "刷新" (button) - 触发查询

---

## 修复方案

### Step 1: 用下载的原平台前端替换当前前端（解决样式问题）
### Step 2: 确保后端 API 路径与原平台一致（解决数据不显示问题）
### Step 3: 配置代理或统一端口（解决跨域/路径问题）

---

## Claude Code 提示词

### 提示词 A：诊断 API 不通问题

```
请帮我诊断前端页面无法显示后端数据的问题。

已知信息：
1. 原平台 API 清单（全部使用相对路径 /api/...）：
   - GET  /api/metrics/token-usage/dept-tree?team_type=department
   - GET  /api/metrics/token-usage/dept-tree
   - GET  /api/metrics/token-usage/zhilei-list
   - POST /api/metrics/token-usage/stats-by-project

2. 后端是 Python/FastAPI，ES 地址 http://10.65.134.124:8200

请执行以下检查：

1. 检查当前后端的路由：
   - 后端 API 路径是否以 /api/ 开头？
   - 是否匹配以上 4 个 API 路径？
   - 如果路径不一致，列出差异

2. 启动后端，用 curl 测试每个 API：
   curl http://localhost:8080/api/metrics/token-usage/dept-tree?team_type=department
   curl http://localhost:8080/api/metrics/token-usage/dept-tree
   curl http://localhost:8080/api/metrics/token-usage/zhilei-list
   curl -X POST http://localhost:8080/api/metrics/token-usage/stats-by-project \
     -H "Content-Type: application/json" \
     -d '{"days":30,"limit":10000,"start_date":null,"end_date":null,"teams":[],"zhilei":[],"ai_native_threshold":0.1,"team_type":"department"}'

3. 如果 API 不存在或路径不对，请修改后端路由使其匹配以上路径
4. 确认每个 API 返回的数据格式与原平台一致（参考上面的返回结构）

不要修改前端代码，只修后端。
```

### 提示词 B：集成原平台前端（替换当前前端）

```
请帮我用下载的原平台前端替换当前项目的前端代码。

背景：
- 已用 Playwright 下载了原平台的完整前端资源到 original-frontend/ 目录
- 这是 Vue + Vite 构建的 SPA
- API 使用相对路径 /api/...（与 origin 同域即可）
- 后端已经实现了正确的 API 路径

请执行：

1. 查看当前项目结构，找到前端代码目录

2. 备份当前前端代码：
   - mv frontend frontend-backup

3. 用原平台前端替换：
   - 把 original-frontend/index.html 放到前端入口
   - 把 original-frontend/static/ 放到对应位置

4. 配置前端服务（根据项目情况选择一种）：
   a) 如果用 Vite dev server → 配置 proxy 把 /api 转发到后端
   b) 如果用 nginx → 配置 location /api/ 代理到后端
   c) 如果是 Flask/FastAPI 托管静态文件 → 挂载 static 目录

5. 关键：确保 SPA 路由正常（所有前端路由都返回 index.html）

6. 启动测试：
   - 前端能正常加载
   - 打开浏览器 Console 检查是否有 API 报错
   - 确认数据正常显示

不要修改后端 API 代码。
```

### 提示词 C：修复具体问题（如果上面还有差异）

```
前端页面还有以下问题需要修复：

1. [描述具体问题，如：筛选栏缺少XXX、表格某列数据格式不对等]

2. 打开浏览器 Console (F12)，把报错信息贴给我

3. 打开浏览器 Network 标签，筛选 XHR，截图或列出 API 请求状态

请逐项修复，每次修一个，修完确认效果。
```
