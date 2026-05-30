# AI 模型配置参考手册

> 生成日期：2026-05-30 | 适用于 OpenClaw / Hermes Agent / Claude Code / 任意 OpenAI 兼容环境

---

## 1. Provider 总览

| Provider | 厂商 | 计费模式 | API 协议 |
|----------|------|---------|---------|
| **zai** | 智谱 (BigModel) | Coding Plan Lite 套餐 | OpenAI 兼容 |
| **volcengine** | 火山引擎 (豆包) | Coding Plan Lite 套餐 | OpenAI 兼容 |
| **deepseek** | DeepSeek | 按量计费 | OpenAI 兼容 |

### 1.1 凭证信息

| Provider | Base URL | API Key |
|----------|----------|---------|
| zai | `https://open.bigmodel.cn/api/coding/paas/v4` | `2bddea05b57e4b879d299be08f0d7f9e.jOiXmQ6w0braLKMt` |
| volcengine | `https://ark.cn-beijing.volces.com/api/v3` | `ark-24e6fbcb-b4de-4790-904a-7e280cb7bb14-2cffe` |
| deepseek | `https://api.deepseek.com` | `sk_REDACTED` |

### 1.2 计费优先级原则

```
套餐内模型（零边际成本）> 按量计费模型（有边际成本）

优先使用：zai 套餐 → volcengine 套餐 → deepseek 按量
```

---

## 2. 全量模型清单

### 2.1 智谱 (zai) — 套餐内 11 个模型

| 模型 ID | 上下文窗口 | 最大输出 | 推理 | 视觉 | 定位 |
|---------|----------|---------|------|------|------|
| `glm-5.1` | 202,800 | 131,100 | ✅ | ❌ | 旗舰推理 |
| `glm-5` | 202,800 | 131,100 | ✅ | ❌ | 日常默认 |
| `glm-5-turbo` | 202,800 | 131,100 | ✅ | ❌ | 加速版 |
| `glm-4.7` | 204,800 | 131,072 | ✅ | ❌ | 上代旗舰 |
| `glm-4.7-flash` | 200,000 | 131,072 | ✅ | ❌ | 快速低成本 |
| `glm-4.6` | 204,800 | 131,072 | ✅ | ❌ | 中端均衡 |
| `glm-4.6v` | 128,000 | 32,768 | ✅ | ✅ | 视觉理解 |
| `glm-4.5` | 131,072 | 98,304 | ✅ | ❌ | 基础通用 |
| `glm-4.5-air` | 131,072 | 98,304 | ✅ | ❌ | 轻量 |
| `glm-4.5-flash` | 131,072 | 98,304 | ✅ | ❌ | 免费额度 |
| `glm-4.5v` | 64,000 | 16,384 | ✅ | ✅ | 轻量视觉 |

> ⚠️ 以下模型在当前套餐不可用（已验证）：`glm-5v-turbo`（套餐未开放）、`glm-4.7-flashx`（需额外资源包）、`glm-4.5-airx`（需额外资源包）

### 2.2 火山引擎 (volcengine) — 套餐内 10 个模型

| 模型 ID | 上下文窗口 | 最大输出 | 推理 | 视觉 | 定位 |
|---------|----------|---------|------|------|------|
| `doubao-seed-2-0-pro-260215` | 128K | 16,384 | ✅ | ✅ | 豆包旗舰 |
| `doubao-seed-2-0-lite-260428` | 128K | 16,384 | ✅ | ✅ | 轻量快速 |
| `doubao-seed-2-0-mini-260428` | 128K | 16,384 | ✅ | ✅ | 极速 |
| `doubao-seed-2-0-code-preview-260215` | 128K | 16,384 | ✅ | ✅ | 代码专用 |
| `doubao-seed-1-6-250615` | 128K | 16,384 | ✅ | ✅ | 上代旗舰 |
| `doubao-seed-1-6-vision-250815` | 128K | 16,384 | ✅ | ✅ | 视觉专用 |
| `doubao-1-5-vision-pro-32k-250115` | 32K | 16,384 | ✅ | ✅ | 视觉备选 |
| `deepseek-v4-pro-260425` | 128K | 16,384 | ✅ | ❌ | DS Pro（套餐内） |
| `deepseek-v4-flash-260425` | 128K | 16,384 | ✅ | ❌ | DS Flash（套餐内） |
| `glm-4-7-251222` | 128K | 131,072 | ✅ | ❌ | GLM-4.7（套餐内） |

> 🔥 火山引擎套餐**内置了 DeepSeek V4 和 GLM-4.7**，可免费使用，无需额外付费。

### 2.3 DeepSeek — 按量计费 2 个模型

| 模型 ID | 上下文窗口 | 最大输出 | 推理 | 视觉 | 定位 |
|---------|----------|---------|------|------|------|
| `deepseek-v4-flash` | 128K | 16,384 | ✅ | ❌ | 快速推理 |
| `deepseek-v4-pro` | 128K | 16,384 | ✅ | ❌ | 深度推理 |

> 仅在套餐额度不足时作为兜底使用。

---

## 3. 场景速查表

### 3.1 按场景推荐

| 场景 | 首选模型 | 备选模型 | 切换命令 |
|------|---------|---------|---------|
| **日常对话** | `zai/glm-5` | `zai/glm-5-turbo` | 默认 / `/model GLM-Turbo` |
| **复杂推理/分析** | `zai/glm-5.1` | `volcengine/doubao-seed-2-0-pro` | `/model GLM` / `/model Doubao-Pro` |
| **代码生成** | `volcengine/doubao-seed-2-0-code` | `deepseek/deepseek-v4-pro` | `/model Doubao-Code` / `/model DS-Pro` |
| **图片理解** | `volcengine/doubao-seed-2-0-pro` | `zai/glm-4.6v` | `/model Doubao-Pro` / `/model GLM-Vision` |
| **数学/逻辑** | `deepseek/deepseek-v4-pro` | `volcengine/deepseek-v4-pro` | `/model DS-Pro` / `/model Volc-DS-Pro` |
| **快速查询** | `zai/glm-4.7-flash` | `volcengine/doubao-seed-2-0-mini` | `/model GLM-Flash` / `/model Doubao-Mini` |
| **长文档处理** | `zai/glm-5` (202K) | `zai/glm-4.7` (204K) | 默认 / `/model GLM-4.7` |
| **子代理/后台任务** | `zai/glm-4.7-flash` | `zai/glm-4.5-flash` | `/model GLM-Flash` / `/model GLM-Free` |
| **中文写作** | `volcengine/doubao-seed-2-0-pro` | `zai/glm-5` | `/model Doubao-Pro` |
| **第二意见** | `volcengine/deepseek-v4-pro` | `volcengine/glm-4-7` | `/model Volc-DS-Pro` / `/model Volc-GLM` |

### 3.2 别名速查

| 别名 | 完整模型 ID |
|------|-----------|
| `GLM` | zai/glm-5.1 |
| `GLM-Turbo` | zai/glm-5-turbo |
| `GLM-4.7` | zai/glm-4.7 |
| `GLM-Flash` | zai/glm-4.7-flash |
| `GLM-4.6` | zai/glm-4.6 |
| `GLM-Vision` | zai/glm-4.6v |
| `GLM-4.5` | zai/glm-4.5 |
| `GLM-Air` | zai/glm-4.5-air |
| `GLM-Free` | zai/glm-4.5-flash |
| `GLM-4.5V` | zai/glm-4.5v |
| `Doubao-Pro` | volcengine/doubao-seed-2-0-pro-260215 |
| `Doubao-Lite` | volcengine/doubao-seed-2-0-lite-260428 |
| `Doubao-Mini` | volcengine/doubao-seed-2-0-mini-260428 |
| `Doubao-Code` | volcengine/doubao-seed-2-0-code-preview-260215 |
| `Doubao-Vision` | volcengine/doubao-seed-1-6-vision-250815 |
| `Volc-DS-Pro` | volcengine/deepseek-v4-pro-260425 |
| `Volc-DS-Flash` | volcengine/deepseek-v4-flash-260425 |
| `Volc-GLM` | volcengine/glm-4-7-251222 |
| `DS-Flash` | deepseek/deepseek-v4-flash |
| `DS-Pro` | deepseek/deepseek-v4-pro |

---

## 4. Fallback 链策略

```
第1级: zai/glm-5 (默认, 套餐)
  ↓ 失败
第2级: zai/glm-5-turbo (套餐, 加速版)
  ↓ 失败
第3级: zai/glm-4.7-flash (套餐, 快速版)
  ↓ 失败
第4级: volcengine/doubao-seed-2-0-pro (套餐, 豆包旗舰)
  ↓ 失败
第5级: volcengine/deepseek-v4-flash (套餐内, DS Flash)
  ↓ 失败
兜底: deepseek/deepseek-v4-flash (按量, 独立API)
```

前 5 级全部在套餐内，零额外成本。

---

## 5. 多平台配置片段

### 5.1 OpenClaw (`openclaw.json`)

将以下内容合并到 `~/.openclaw/openclaw.json` 中：

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "zai": {
        "baseUrl": "https://open.bigmodel.cn/api/coding/paas/v4",
        "api": "openai-completions",
        "apiKey": "2bddea05b57e4b879d299be08f0d7f9e.jOiXmQ6w0braLKMt",
        "models": [
          {"id":"glm-5.1","name":"GLM-5.1","reasoning":true,"input":["text"],"contextWindow":202800,"maxTokens":131100},
          {"id":"glm-5","name":"GLM-5","reasoning":true,"input":["text"],"contextWindow":202800,"maxTokens":131100},
          {"id":"glm-5-turbo","name":"GLM-5 Turbo","reasoning":true,"input":["text"],"contextWindow":202800,"maxTokens":131100},
          {"id":"glm-4.7","name":"GLM-4.7","reasoning":true,"input":["text"],"contextWindow":204800,"maxTokens":131072},
          {"id":"glm-4.7-flash","name":"GLM-4.7 Flash","reasoning":true,"input":["text"],"contextWindow":200000,"maxTokens":131072},
          {"id":"glm-4.6","name":"GLM-4.6","reasoning":true,"input":["text"],"contextWindow":204800,"maxTokens":131072},
          {"id":"glm-4.6v","name":"GLM-4.6V","reasoning":true,"input":["text","image"],"contextWindow":128000,"maxTokens":32768},
          {"id":"glm-4.5","name":"GLM-4.5","reasoning":true,"input":["text"],"contextWindow":131072,"maxTokens":98304},
          {"id":"glm-4.5-air","name":"GLM-4.5 Air","reasoning":true,"input":["text"],"contextWindow":131072,"maxTokens":98304},
          {"id":"glm-4.5-flash","name":"GLM-4.5 Flash","reasoning":true,"input":["text"],"contextWindow":131072,"maxTokens":98304},
          {"id":"glm-4.5v","name":"GLM-4.5V","reasoning":true,"input":["text","image"],"contextWindow":64000,"maxTokens":16384}
        ]
      },
      "volcengine": {
        "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
        "api": "openai-completions",
        "apiKey": "ark-24e6fbcb-b4de-4790-904a-7e280cb7bb14-2cffe",
        "models": [
          {"id":"doubao-seed-2-0-pro-260215","name":"Doubao Seed 2.0 Pro","reasoning":true,"input":["text","image"],"contextWindow":128000,"maxTokens":16384},
          {"id":"doubao-seed-2-0-lite-260428","name":"Doubao Seed 2.0 Lite","reasoning":true,"input":["text","image"],"contextWindow":128000,"maxTokens":16384},
          {"id":"doubao-seed-2-0-mini-260428","name":"Doubao Seed 2.0 Mini","reasoning":true,"input":["text","image"],"contextWindow":128000,"maxTokens":16384},
          {"id":"doubao-seed-2-0-code-preview-260215","name":"Doubao Seed 2.0 Code","reasoning":true,"input":["text","image"],"contextWindow":128000,"maxTokens":16384},
          {"id":"doubao-seed-1-6-250615","name":"Doubao Seed 1.6","reasoning":true,"input":["text","image"],"contextWindow":128000,"maxTokens":16384},
          {"id":"doubao-seed-1-6-vision-250815","name":"Doubao Seed 1.6 Vision","reasoning":true,"input":["text","image"],"contextWindow":128000,"maxTokens":16384},
          {"id":"doubao-1-5-vision-pro-32k-250115","name":"Doubao 1.5 Vision Pro","reasoning":true,"input":["text","image"],"contextWindow":32000,"maxTokens":16384},
          {"id":"deepseek-v4-pro-260425","name":"DeepSeek V4 Pro (Volcengine)","reasoning":true,"input":["text"],"contextWindow":128000,"maxTokens":16384},
          {"id":"deepseek-v4-flash-260425","name":"DeepSeek V4 Flash (Volcengine)","reasoning":true,"input":["text"],"contextWindow":128000,"maxTokens":16384},
          {"id":"glm-4-7-251222","name":"GLM-4.7 (Volcengine)","reasoning":true,"input":["text"],"contextWindow":128000,"maxTokens":131072}
        ]
      },
      "deepseek": {
        "baseUrl": "https://api.deepseek.com",
        "api": "openai-completions",
        "apiKey": "sk_REDACTED",
        "models": [
          {"id":"deepseek-v4-flash","name":"DeepSeek V4 Flash","reasoning":true,"input":["text"],"contextWindow":128000,"maxTokens":16384},
          {"id":"deepseek-v4-pro","name":"DeepSeek V4 Pro","reasoning":true,"input":["text"],"contextWindow":128000,"maxTokens":16384}
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "zai/glm-5",
        "fallbacks": [
          "zai/glm-5-turbo",
          "zai/glm-4.7-flash",
          "volcengine/doubao-seed-2-0-pro-260215",
          "volcengine/deepseek-v4-flash-260425",
          "deepseek/deepseek-v4-flash"
        ]
      },
      "models": {
        "zai/glm-5.1": {"alias":"GLM"},
        "zai/glm-5": {},
        "zai/glm-5-turbo": {"alias":"GLM-Turbo"},
        "zai/glm-4.7": {"alias":"GLM-4.7"},
        "zai/glm-4.7-flash": {"alias":"GLM-Flash"},
        "zai/glm-4.6": {"alias":"GLM-4.6"},
        "zai/glm-4.6v": {"alias":"GLM-Vision"},
        "zai/glm-4.5": {"alias":"GLM-4.5"},
        "zai/glm-4.5-air": {"alias":"GLM-Air"},
        "zai/glm-4.5-flash": {"alias":"GLM-Free"},
        "zai/glm-4.5v": {"alias":"GLM-4.5V"},
        "volcengine/doubao-seed-2-0-pro-260215": {"alias":"Doubao-Pro"},
        "volcengine/doubao-seed-2-0-lite-260428": {"alias":"Doubao-Lite"},
        "volcengine/doubao-seed-2-0-mini-260428": {"alias":"Doubao-Mini"},
        "volcengine/doubao-seed-2-0-code-preview-260215": {"alias":"Doubao-Code"},
        "volcengine/doubao-seed-1-6-vision-250815": {"alias":"Doubao-Vision"},
        "volcengine/deepseek-v4-pro-260425": {"alias":"Volc-DS-Pro"},
        "volcengine/deepseek-v4-flash-260425": {"alias":"Volc-DS-Flash"},
        "volcengine/glm-4-7-251222": {"alias":"Volc-GLM"},
        "deepseek/deepseek-v4-flash": {"alias":"DS-Flash"},
        "deepseek/deepseek-v4-pro": {"alias":"DS-Pro"}
      }
    }
  }
}
```

配置后运行 `openclaw gateway restart` 生效。

### 5.2 Hermes Agent (`config.yaml`)

Hermes Agent 通过 CLI 或直接编辑 `~/.hermes/config.yaml` 配置。以下是需要执行的配置命令和手动编辑内容。

#### 方法一：CLI 命令（推荐，让 Hermes 读取后执行）

```bash
# === 智谱 (zai) ===
hermes config set providers.zai.base_url "https://open.bigmodel.cn/api/coding/paas/v4"
hermes config set providers.zai.api_key "2bddea05b57e4b879d299be08f0d7f9e.jOiXmQ6w0braLKMt"
hermes model add zai:glm-5.1
hermes model add zai:glm-5
hermes model add zai:glm-5-turbo
hermes model add zai:glm-4.7
hermes model add zai:glm-4.7-flash
hermes model add zai:glm-4.6
hermes model add zai:glm-4.6v
hermes model add zai:glm-4.5
hermes model add zai:glm-4.5-air
hermes model add zai:glm-4.5-flash
hermes model add zai:glm-4.5v

# === 火山引擎 (volcengine) ===
hermes config set providers.volcengine.base_url "https://ark.cn-beijing.volces.com/api/v3"
hermes config set providers.volcengine.api_key "ark-24e6fbcb-b4de-4790-904a-7e280cb7bb14-2cffe"
hermes model add volcengine:doubao-seed-2-0-pro-260215
hermes model add volcengine:doubao-seed-2-0-lite-260428
hermes model add volcengine:doubao-seed-2-0-mini-260428
hermes model add volcengine:doubao-seed-2-0-code-preview-260215
hermes model add volcengine:doubao-seed-1-6-250615
hermes model add volcengine:doubao-seed-1-6-vision-250815
hermes model add volcengine:deepseek-v4-pro-260425
hermes model add volcengine:deepseek-v4-flash-260425
hermes model add volcengine:glm-4-7-251222

# === DeepSeek ===
hermes config set providers.deepseek.base_url "https://api.deepseek.com"
hermes config set providers.deepseek.api_key "sk_REDACTED"
hermes model add deepseek:deepseek-v4-flash
hermes model add deepseek:deepseek-v4-pro

# === 设置默认模型 ===
hermes model zai:glm-5

# === 添加 fallback ===
hermes fallback add zai:glm-5-turbo
hermes fallback add zai:glm-4.7-flash
hermes fallback add volcengine:doubao-seed-2-0-pro-260215
hermes fallback add volcengine:deepseek-v4-flash-260425
hermes fallback add deepseek:deepseek-v4-flash
```

#### 方法二：手动编辑 `~/.hermes/config.yaml`

在 `providers` 和 `fallback_providers` 部分添加：

```yaml
providers:
  zai:
    base_url: "https://open.bigmodel.cn/api/coding/paas/v4"
    api_key: "2bddea05b57e4b879d299be08f0d7f9e.jOiXmQ6w0braLKMt"
    api_mode: openai
  volcengine:
    base_url: "https://ark.cn-beijing.volces.com/api/v3"
    api_key: "ark-24e6fbcb-b4de-4790-904a-7e280cb7bb14-2cffe"
    api_mode: openai
  deepseek:
    base_url: "https://api.deepseek.com"
    api_key: "sk_REDACTED"
    api_mode: openai

fallback_providers:
  - zai:glm-5-turbo
  - zai:glm-4.7-flash
  - volcengine:doubao-seed-2-0-pro-260215
  - volcengine:deepseek-v4-flash-260425
  - deepseek:deepseek-v4-flash
```

切换模型命令：
```bash
hermes model                          # 交互式选择模型
hermes model zai:glm-5.1              # 切到 GLM-5.1
hermes model volcengine:doubao-seed-2-0-pro-260215  # 切到豆包旗舰
```

### 5.3 Claude Code

Claude Code 支持通过环境变量或 `settings.json` 配置 OpenAI 兼容模型。

#### 方法一：环境变量

```bash
# 智谱
export OPENAI_API_KEY="2bddea05b57e4b879d299be08f0d7f9e.jOiXmQ6w0braLKMt"
export OPENAI_BASE_URL="https://open.bigmodel.cn/api/coding/paas/v4"
# 模型: glm-5, glm-5.1, glm-5-turbo, glm-4.7-flash, glm-4.6v 等

# 火山引擎（切换时修改）
export OPENAI_API_KEY="ark-24e6fbcb-b4de-4790-904a-7e280cb7bb14-2cffe"
export OPENAI_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
# 模型: doubao-seed-2-0-pro-260215, doubao-seed-2-0-code-preview-260215 等

# DeepSeek（切换时修改）
export OPENAI_API_KEY="sk_REDACTED"
export OPENAI_BASE_URL="https://api.deepseek.com"
# 模型: deepseek-v4-pro, deepseek-v4-flash
```

#### 方法二：`~/.claude/settings.json` 多 Provider 配置

```json
{
  "modelProviders": {
    "zai": {
      "baseUrl": "https://open.bigmodel.cn/api/coding/paas/v4",
      "apiKey": "2bddea05b57e4b879d299be08f0d7f9e.jOiXmQ6w0braLKMt"
    },
    "volcengine": {
      "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
      "apiKey": "ark-24e6fbcb-b4de-4790-904a-7e280cb7bb14-2cffe"
    },
    "deepseek": {
      "baseUrl": "https://api.deepseek.com",
      "apiKey": "sk_REDACTED"
    }
  }
}
```

### 5.4 通用 OpenAI 兼容环境（Cursor / Windsurf / Continue / Cline 等）

所有这些工具都支持 OpenAI 兼容 API。通用配置格式：

```json
{
  "models": [
    {
      "title": "GLM-5 (智谱套餐)",
      "provider": "openai",
      "model": "glm-5",
      "apiBase": "https://open.bigmodel.cn/api/coding/paas/v4",
      "apiKey": "2bddea05b57e4b879d299be08f0d7f9e.jOiXmQ6w0braLKMt"
    },
    {
      "title": "GLM-5.1 (智谱套餐)",
      "provider": "openai",
      "model": "glm-5.1",
      "apiBase": "https://open.bigmodel.cn/api/coding/paas/v4",
      "apiKey": "2bddea05b57e4b879d299be08f0d7f9e.jOiXmQ6w0braLKMt"
    },
    {
      "title": "GLM-4.6V 视觉 (智谱套餐)",
      "provider": "openai",
      "model": "glm-4.6v",
      "apiBase": "https://open.bigmodel.cn/api/coding/paas/v4",
      "apiKey": "2bddea05b57e4b879d299be08f0d7f9e.jOiXmQ6w0braLKMt"
    },
    {
      "title": "Doubao Seed 2.0 Pro (火山套餐)",
      "provider": "openai",
      "model": "doubao-seed-2-0-pro-260215",
      "apiBase": "https://ark.cn-beijing.volces.com/api/v3",
      "apiKey": "ark-24e6fbcb-b4de-4790-904a-7e280cb7bb14-2cffe"
    },
    {
      "title": "Doubao Seed 2.0 Code (火山套餐)",
      "provider": "openai",
      "model": "doubao-seed-2-0-code-preview-260215",
      "apiBase": "https://ark.cn-beijing.volces.com/api/v3",
      "apiKey": "ark-24e6fbcb-b4de-4790-904a-7e280cb7bb14-2cffe"
    },
    {
      "title": "DeepSeek V4 Pro 火山套餐内",
      "provider": "openai",
      "model": "deepseek-v4-pro-260425",
      "apiBase": "https://ark.cn-beijing.volces.com/api/v3",
      "apiKey": "ark-24e6fbcb-b4de-4790-904a-7e280cb7bb14-2cffe"
    },
    {
      "title": "DeepSeek V4 Pro 独立",
      "provider": "openai",
      "model": "deepseek-v4-pro",
      "apiBase": "https://api.deepseek.com",
      "apiKey": "sk_REDACTED"
    },
    {
      "title": "DeepSeek V4 Flash 独立",
      "provider": "openai",
      "model": "deepseek-v4-flash",
      "apiBase": "https://api.deepseek.com",
      "apiKey": "sk_REDACTED"
    }
  ]
}
```

> 根据具体工具，字段名可能略有不同（`apiBase` / `baseUrl` / `baseURL` / `apiEndpoint`），但结构一致。

---

## 6. 注意事项

### 套餐限制

| Provider | 套餐名称 | 已知限制 |
|----------|---------|---------|
| zai | Coding Plan Lite | 不含 glm-5v-turbo（需单独开通）、glm-4.7-flashx 和 glm-4.5-airx 需额外资源包 |
| volcengine | Coding Plan Lite | 不含 glm-4-5-air、qwen 系列（返回 404）、含 doubao 全系列 + DS V4 + GLM-4.7 |
| deepseek | 按量 | 无套餐限制，按 token 计费 |

### 特殊配置要点

1. **智谱 API 路径**：使用 `/api/coding/paas/v4`（Coding Plan 专用路径），不是通用的 `/api/paas/v4`
2. **火山引擎模型调用**：不需要创建 Endpoint，直接用模型 ID 作为 `model` 参数调用即可
3. **火山引擎 Endpoint**：`ep-20260529105255-qgflf` 映射到 `doubao-seed-1-6-250615`，可保留也可不用
4. **DeepSeek 推理**：所有模型都支持深度推理（返回 `reasoning_content` 字段）
5. **豆包 Seed 2.0 系列**：都支持视觉输入（image），即使不是 Vision 专用模型
6. **智谱视觉模型**：只有 glm-4.6v 和 glm-4.5v 支持图片输入，glm-5 系列暂不支持

### 成本优化建议

- **日常使用**：默认 glm-5（套餐），不用额外花钱
- **需要视觉**：优先用火山引擎的 Seed 2.0 Pro（套餐内，支持视觉）
- **代码任务**：优先用火山引擎的 Seed 2.0 Code（套餐内，代码优化）
- **DeepSeek 独立 API**：仅在火山引擎套餐内的 DS 不可用时才使用
- **子代理/批量任务**：用 glm-4.7-flash 或 glm-4.5-flash，成本最低
