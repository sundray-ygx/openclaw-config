# OpenClaw Config

个人 OpenClaw AI 助手配置仓库，用于跨环境同步记忆和经验。

## 📁 仓库结构

```
.
├── README.md                 # 本文件
├── .env.example              # 环境变量模板（需复制为 .env）
├── setup.sh                  # 新环境一键恢复脚本
├── .github/workflows/        # GitHub Actions 自动同步
│   └── auto-sync.yml
├── config/                   # 脱敏后的系统配置
│   └── openclaw.json
├── AGENTS.md                 # 助手行为规范
├── SOUL.md                   # 助手身份定义
├── USER.md                   # 用户信息
├── TOOLS.md                  # 工具配置
├── HEARTBEAT.md              # 定时任务定义
├── IDENTITY.md               # 助手标识
├── memory/                   # 记忆文件
│   ├── projects.md
│   ├── lessons.md
│   └── YYYY-MM-DD.md
├── skills/                   # 自定义 Skills
├── agents/                   # 多代理配置
├── archive/                  # 归档内容
└── knowledge/                # 知识库（整合原 growth/life/work）

```

## 🚀 快速开始

### 新环境恢复

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/openclaw-config.git
cd openclaw-config

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实 API keys

# 3. 运行恢复脚本
./setup.sh
```

### 环境变量说明

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `BAILIAN_API_KEY` | 百炼/通义千问 API Key | [阿里云](https://dashscope.aliyun.com) |
| `TAVILY_API_KEY` | Tavily 搜索 API | [Tavily](https://tavily.com) |
| `FIRECRAWL_API_KEY` | Firecrawl API | [Firecrawl](https://firecrawl.dev) |
| `NOTION_API_KEY` | Notion API | [Notion](https://notion.so) |
| `FEISHU_MAIN_APP_ID` | 飞书主应用 ID | 飞书开放平台 |
| `FEISHU_MAIN_APP_SECRET` | 飞书主应用密钥 | 飞书开放平台 |
| `FEISHU_USER_ID` | 飞书用户 ID | 飞书管理后台 |

## 🔄 自动同步

本仓库配置了 GitHub Actions，每天凌晨自动检测变更并推送。

手动触发同步：
```bash
git add -A
git commit -m "手动同步"
git push
```

## 📝 记忆同步说明

- **MEMORY.md**: 核心记忆索引
- **memory/projects.md**: 项目状态跟踪
- **memory/lessons.md**: 踩坑记录
- **memory/YYYY-MM-DD.md**: 每日日志

## 🔒 安全说明

- ✅ 同步: 配置模板、记忆文件、Skills
- ❌ 不同步: API Keys、认证信息、设备配对

敏感信息存储在 `.env` 文件中，**不要提交到仓库**。

## 🛠️ 维护

- 定期清理 `memory/` 中的旧日志
- 更新 `README.md` 记录重大变更
- 检查 `.env.example` 是否包含新配置项
