# Hermes Agent WebUI 管理页面方案对比报告

> 调研日期：2026-05-15

## 快速对比总览

| 项目 | ⭐ Stars | 技术栈 | 最佳场景 | 资源消耗 | 社区活跃度 |
|------|---------|--------|---------|---------|-----------|
| Hermes WebUI | 3.1k | Python + Vanilla JS | 日常聊天交互、移动端 | 低（~200MB RAM） | ★★★★★ |
| Hermes Workspace | 2k | TypeScript + React | 全功能工作台、多Agent编排 | 高（~1GB+ RAM） | ★★★★ |
| Hermes Web UI (EKKO) | 1.5k | TypeScript + Vue + Koa2 | 国内平台（微信/飞书/钉钉） | 中（~400MB RAM） | ★★★★ |
| Hermes Control Interface | 450 | Vanilla JS + Vite | 安全优先、RBAC权限管理 | 低（~200MB RAM） | ★★★ |
| Claw Admin | 577 | Vue + TypeScript | OpenClaw + Hermes 双网关 | 中 | ★★★ |
| Scarf | 239 | Swift / SwiftUI | macOS 原生桌面体验 | 原生应用 | ★★ |

---

## 1. Hermes WebUI（推荐度：★★★★★）

**GitHub**: github.com/nesquena/hermes-webui  
**定位**: 最流行的 Web 聊天界面

### 应用场景
- 日常与 Hermes Agent 对话交互
- 移动端手机浏览器使用
- 快速部署，开箱即用

### 核心特性
- 三栏布局：会话侧边栏 + 聊天区 + 文件浏览
- SSE 流式对话，支持 8+ LLM 提供商切换（OpenAI/Anthropic/Google/DeepSeek/Ollama 等）
- 移动端响应式设计（非简单缩放，专门优化）
- 8 套内置主题 + 自定义 CSS
- Agent 推理过程可视化（调试弱模型有用）
- Token 用量环形指示器

### 部署
```bash
# Docker 一行启动
docker run -d -p 8000:8000 -v ~/.hermes:/home/hermeswebui/.hermes \
  ghcr.io/nesquena/hermes-webui:latest
```

### 优势
- 社区最大（3.1k stars，41 贡献者，164 个 release）
- 无框架依赖（纯 Python + Vanilla JS），轻量
- 移动端体验最好
- 部署最简单

### 劣势
- ❌ 无内嵌终端
- ❌ 无文件编辑器
- ❌ 无 Cron 管理
- ❌ 纯聊天界面，不是完整工作台

---

## 2. Hermes Workspace（推荐度：★★★★）

**GitHub**: github.com/outsourc-e/hermes-workspace  
**定位**: IDE 风格全功能工作台

### 应用场景
- 开发者需要终端 + 文件 + 记忆一体化管理
- 多 Agent 协作编排（Conductor 模式）
- Swarm 多 Agent 团队调度

### 核心特性
- **嵌入式终端**：xterm.js，无需单独 SSH
- **文件浏览器**：Monaco 编辑器
- **Conductor 编排器**：复杂任务自动分解 → 多 Agent 子任务 → 结果合并（独有功能）
- **Swarm 模式**：tmux 持久 Worker，角色化调度（builder/reviewer/docs/ops/QA）
- **看板任务板**：backlog → running → review → done
- **记忆浏览器**：Markdown 实时编辑 Agent 记忆
- **Skills Hub**：2000+ 技能浏览安装
- **MCP 管理**：完整 /mcp 页面

### 部署
```bash
npx hermes-workspace
# 或 Docker Compose（包含 Hermes Agent 本体）
docker compose up -d
```

### 优势
- 功能最全面，真正的"命令中心"
- 多 Agent 编排独有
- 零 fork 设计，直接用官方 hermes-agent

### 劣势
- ❌ 资源消耗高（React + xterm.js + Monaco，2GB+ RAM 推荐）
- ❌ 对小规格 VPS 不友好
- ❌ 上手复杂度较高

---

## 3. Hermes Web UI - EKKO 版（推荐度：★★★★）

**GitHub**: github.com/EKKOLearnAI/hermes-web-ui  
**定位**: 国内平台友好，功能全面

### 应用场景
- 国内团队使用微信/飞书/钉钉/QQ 与 Agent 交互
- 需要使用量分析和费用追踪
- 多语言团队

### 核心特性
- **国内平台原生支持**：微信/企业微信 QR 登录、钉钉、飞书/Lark、QQ
- **BFF 架构**：Koa2 后端隔离前端与 Agent API，更安全
- **npm 一键安装**：`npm install -g hermes-web-ui && hermes-web-ui start`
- **使用量分析**：按模型/平台/时间范围的 Token 和费用追踪
- **Cron 调度管理**：创建/暂停/恢复/立即执行定时任务
- **多 Agent 聊天室**：Socket.IO 实时消息，@mention 路由
- **8 种语言**：中/英/德/法/西/日/韩/葡
- **Profile 管理**：多配置文件切换、导入导出
- **文件管理**：支持本地/Docker/SSH/Singularity 后端

### 部署
```bash
npm install -g hermes-web-ui
hermes-web-ui start  # http://localhost:8648
```

### 优势
- 国内平台支持最完善
- 安装最快（npm 一行命令）
- BFF 架构更专业安全
- 功能最丰富（Cron + 分析 + 多Agent聊天室）
- SQLite 自建会话数据库

### 劣势
- ❌ 技术栈较重（Vue3 + Koa2 + SQLite）
- ❌ 社区规模小于前两者
- ❌ 部分功能仍在快速迭代中

---

## 4. Hermes Control Interface（推荐度：★★★）

**GitHub**: github.com/xaspx/hermes-control-interface  
**定位**: 安全加固、RBAC 权限管理

### 应用场景
- 团队多人使用，需要权限隔离
- 安全敏感环境
- 需要精细的命令审计

### 核心特性
- **RBAC v2**：3 种角色 × 20 项权限粒度控制
- **安全加固**：CSRF 21 端点、动态 CORS、XSS 全面防护、命令注入修复（18 项安全修复）
- **多 Agent 网关**：启动/停止/配置多个 Hermes Profile
- **Token 分析**：按模型/平台/时间维度的使用统计
- **嵌入式终端 + 文件管理器**
- **systemd 服务管理**
- **单密码门控**

### 优势
- 安全性最好，唯一有 RBAC 的方案
- 零框架（Vanilla JS），攻击面小
- 内嵌终端和文件管理

### 劣势
- ❌ 社区较小
- ❌ UI 精致度不如前三者
- ❌ 更新频率一般

---

## 5. Claw Admin（推荐度：★★★）

**GitHub**: github.com/itq5/OpenClaw-Admin  
**定位**: OpenClaw + Hermes 双网关管理

### 应用场景
- 同时使用 OpenClaw 和 Hermes 的用户
- 需要远程桌面管理
- 多网关统一管理

### 核心特性
- 双网关支持（OpenClaw + Hermes Agent）
- 远程桌面功能
- 统一管理界面

### 优势
- 唯一支持 OpenClaw + Hermes 双管理的方案
- 适合同时使用两套系统的用户

### 劣势
- ❌ 社区中等
- ❌ 功能深度不如专项方案

---

## 6. Scarf（推荐度：★★）

**GitHub**: github.com/awizemann/scarf  
**定位**: macOS 原生桌面应用

### 应用场景
- macOS 用户偏好原生应用
- 管理多台服务器上的 Hermes Agent

### 核心特性
- 原生 SwiftUI 应用
- 多服务器管理
- macOS 系统集成

### 优势
- 唯一原生桌面应用，体验流畅
- 非 Web 方案，无浏览器依赖

### 劣势
- ❌ 仅 macOS
- ❌ 社区最小
- ❌ 功能有限

---

## 选型建议

| 需求 | 推荐 |
|------|------|
| 快速上手、日常聊天 | **Hermes WebUI** |
| 移动端为主 | **Hermes WebUI** |
| 开发者全功能工作台 | **Hermes Workspace** |
| 多 Agent 编排 | **Hermes Workspace** |
| 国内平台（微信/飞书/钉钉） | **EKKO Hermes Web UI** |
| 费用追踪 + Cron 管理 | **EKKO Hermes Web UI** |
| 团队多人使用 + 权限控制 | **Hermes Control Interface** |
| 安全优先 | **Hermes Control Interface** |
| OpenClaw + Hermes 双管 | **Claw Admin** |
| macOS 原生体验 | **Scarf** |
| 低配 VPS（≤512MB） | **Hermes WebUI** 或 **Control Interface** |

### 个人推荐（排序）

1. **EKKO Hermes Web UI** — 国内平台支持 + 功能最全 + 安装最快，综合最优
2. **Hermes WebUI** — 如果主要用移动端或纯聊天场景
3. **Hermes Workspace** — 重度开发者 / 多 Agent 场景
4. **Hermes Control Interface** — 安全优先 / 团队使用
