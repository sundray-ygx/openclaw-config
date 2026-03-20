# Apple Watch 健康数据管线

数据流：Apple Watch → iOS 快捷指令 → Cloudflare Worker → GitHub → OpenClaw → 飞书报告

## 目录结构

```
health-data-pipeline/
├── cloudflare-worker.js      # Worker 主代码
├── wrangler.toml             # Worker 配置
├── README.md                 # 本文档
├── scripts/
│   └── generate-report.js    # GitHub Actions 报告生成
├── .github/
│   └── workflows/
│       └── generate-report.yml  # GitHub Actions 工作流
├── openclaw/
│   └── health-report.py      # OpenClaw 报告脚本
└── ios-shortcut/
    └── README.md             # iOS 快捷指令配置指南
```

## 快速开始

### 1. 创建 GitHub 仓库

```bash
# 创建新仓库（名字随意，比如 health-data）
# 克隆到本地
git clone https://github.com/YOUR_USERNAME/health-data.git
cd health-data

# 复制本项目的文件
cp -r /path/to/health-data-pipeline/* .

# 创建数据目录
mkdir -p data/{sleep,heartRate,steps,workouts}

# 提交
git add .
git commit -m "Initial setup"
git push
```

### 2. 部署 Cloudflare Worker

```bash
# 安装 wrangler
npm install -g wrangler

# 登录 Cloudflare
wrangler login

# 设置 secrets
wrangler secret put GITHUB_TOKEN      # 你的 GitHub Personal Access Token
wrangler secret put GITHUB_OWNER      # 你的 GitHub 用户名
wrangler secret put GITHUB_REPO       # 仓库名（如 health-data）

# 部署
wrangler deploy
```

部署后会得到一个 URL：`https://health-data-worker.YOUR_SUBDOMAIN.workers.dev`

### 3. 配置 iOS 快捷指令

1. 打开 iPhone 上的"快捷指令"App
2. 创建新快捷指令
3. 按照 `ios-shortcut/README.md` 中的步骤配置
4. 将 Worker URL 替换为你自己的地址

### 4. 配置 OpenClaw

```bash
# 设置环境变量
export GITHUB_TOKEN=your_github_token
export GITHUB_OWNER=your_github_username
export GITHUB_REPO=health-data
export FEISHU_WEBHOOK=your_feishu_webhook_url

# 运行报告脚本
python3 openclaw/health-report.py
```

## 数据格式

### 睡眠数据

```json
{
  "type": "sleep",
  "date": "2024-03-13",
  "duration": 480,
  "quality": 85,
  "start_time": "23:00",
  "end_time": "07:00",
  "deep_sleep": 120,
  "light_sleep": 240,
  "rem_sleep": 120
}
```

### 心率数据

```json
{
  "type": "heartRate",
  "date": "2024-03-13",
  "avg": 72,
  "min": 58,
  "max": 95,
  "resting": 62
}
```

### 步数数据

```json
{
  "type": "steps",
  "date": "2024-03-13",
  "steps": 8500,
  "distance": 6.2,
  "calories": 320
}
```

## 自动化

### iOS 快捷指令自动化

1. 快捷指令 App → 自动化 → 创建个人自动化
2. 选择触发条件：
   - 特定时间（每天早上 8:00）
   - 关闭闹钟时
3. 添加操作：运行快捷指令
4. 关闭"运行前询问"

### GitHub Actions

已配置每天早上 8:00 自动生成报告，推送到仓库的 `reports/` 目录。

### OpenClaw Cron

可以配置定时任务，每天早上发送飞书报告：

```bash
# 添加到 crontab
crontab -e

# 添加行
0 8 * * * cd /path/to/health-data-pipeline && python3 openclaw/health-report.py
```

## API 端点

### POST /api/health-data

接收健康数据并存储到 GitHub。

**请求体：**
```json
{
  "type": "sleep",
  "date": "2024-03-13",
  ...其他字段
}
```

**响应：**
```json
{
  "success": true,
  "path": "data/sleep/2024/03/13.json",
  "github": { ... }
}
```

### GET /health

健康检查，返回 "OK"。

## 故障排查

### Worker 返回 500

检查 Cloudflare Dashboard → Workers → 你的 Worker → Logs，查看错误信息。

### GitHub 推送失败

1. 确认 GitHub Token 有 `repo` 权限
2. 确认 Token 未过期
3. 检查仓库名和用户名是否正确

### 快捷指令运行失败

1. 检查 Worker URL 是否正确
2. 检查快捷指令是否有网络权限
3. 尝试在 Safari 中访问 Worker URL 测试连通性

## 扩展

可以添加更多数据源：

- **体重**：智能体脂秤
- **饮食**：薄荷健康等 App
- **运动**：Keep、Nike Run Club
- **血氧/体温**：Apple Watch 原生数据

只需在快捷指令中添加对应的数据获取步骤，发送到相同的 Worker 端点即可。
