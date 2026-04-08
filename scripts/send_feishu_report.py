#!/usr/bin/env python3
"""发送飞书文档报告"""

import json
import subprocess
import sys

def send_feishu_doc(title, content):
    """使用 feishu_mcp_create_doc 发送文档"""
    
    # 构建 markdown 内容
    markdown = f"""<callout emoji="📊" background-color="light-blue">
本报告汇总 OpenClaw 从 3.23 升级至 4.2 版本的核心变更、新特性、应用场景及对当前业务的影响分析。
</callout>

## 一、升级概览

<grid cols="3">
<column>

**当前版本**

`2026.4.7`

</column>
<column>

**升级跨度**

3.23 → 4.2

</column>
<column>

**主要版本**

4.0 / 4.1 / 4.2

</column>
</grid>

---

## 二、核心新特性

### 1. 持久化任务流 (Durable Task Flow)

<callout emoji="⚡" background-color="light-green">
**4.2 重磅功能** — 背景任务编排支持持久化状态跟踪和恢复
</callout>

- **托管模式 vs 镜像模式**：支持同步模式选择
- **状态/版本跟踪**：任务流状态持久化，可独立运维
- **检查/恢复原语**：`openclaw flows` 命令集支持任务检查和恢复
- **子任务管理**：支持托管子任务生成和取消意图传递

**应用场景**：
- 长时间运行的自动化工作流
- 需要断点续传的后台任务
- 跨会话的复杂编排任务

---

### 2. 多媒体生成能力

| 类型 | 支持模型/提供商 | 版本 |
|------|----------------|------|
| **视频生成** | xAI Grok、阿里万相、Runway | 4.0+ |
| **音乐生成** | Google Lyria、MiniMax、ComfyUI | 4.0+ |
| **图像生成** | 扩展支持更多提供商 | 4.0+ |

**新增内置工具**：
- `video_generate` — 视频生成
- `music_generate` — 音乐生成

---

### 3. 记忆系统升级 — "Dreaming" 实验功能

<callout emoji="🧠" background-color="light-yellow">
智能记忆提升系统，自动提炼和归档重要信息
</callout>

**三阶段协作模式**：
1. **Light（浅层）** — 短期记忆快速检索
2. **Deep（深层）** — 中期记忆整合
3. **REM（深度）** — 长期记忆沉淀

**新增功能**：
- 加权短期回忆提升
- `/dreaming` 命令和 Dreams UI
- 多语言概念标签
- 可配置老化控制（半衰期、最大天数）
- Dream Diary 界面

**应用场景**：
- 自动整理每日笔记到 `dreams.md`
- 智能识别需要长期保存的信息
- 减少手动维护 MEMORY.md 的工作量

---

### 4. 提供商生态扩展

**新增提供商支持**：

| 提供商 | 功能 | 版本 |
|--------|------|------|
| **Qwen** | 对话、嵌入 | 4.0+ |
| **Fireworks AI** | 对话 | 4.0+ |
| **StepFun** | 对话 | 4.0+ |
| **MiniMax** | TTS、搜索、音乐 | 4.0+ |
| **Ollama Web Search** | 搜索 | 4.0+ |
| **SearXNG** | 搜索聚合 | 4.1+ |

**Amazon Bedrock 增强**：
- Mantle 支持 + 推理配置文件自动发现
- Guardrails 安全护栏支持 (4.1+)
- 自动请求区域注入

---

### 5. 飞书集成增强

<callout emoji="📋" background-color="light-blue">
针对飞书平台的深度优化
</callout>

**新增功能**：
- **文档评论事件流**：支持 Drive 文档评论的上下文解析和回复
- **评论线程处理**：整文档评论、延迟回复查找优化
- **会话路由改进**：支持话题路由和作用域继承

**应用场景**：
- 文档协作中的 AI 辅助回复
- 评论工作流的自动化处理

---

### 6. 提示缓存优化 (Prompt Caching)

**改进点**：
- 跨传输回退保持提示前缀可复用
- 确定性 MCP 工具排序
- 上下文压缩优化
- 嵌入式图片历史处理
- 规范化系统提示指纹

**效果**：后续对话更容易命中缓存，降低 API 调用成本

---

### 7. 执行审批系统改进

**4.2 重要变更**：
- **默认 YOLO 模式**：gateway/node 主机执行默认使用 `security=full` + `ask=off`
- **原生审批 UI**：WebChat 使用原生审批界面，不再提示粘贴 `/approve` 命令
- **Matrix 审批**：支持 Matrix 原生执行审批提示
- **iOS 审批**：支持 APNs 推送通知 + 应用内审批弹窗

---

### 8. 多语言支持

**控制 UI 本地化**：
简体中文、繁体中文、巴西葡萄牙语、德语、西班牙语、日语、韩语、法语、土耳其语、印尼语、波兰语、乌克兰语

---

## 三、破坏性变更 (Breaking Changes)

<callout emoji="⚠️" background-color="light-red">
升级前必须关注的配置变更
</callout>

### 4.0 版本

1. **配置路径清理**：移除遗留的公共配置别名
   - `talk.voiceId` / `talk.apiKey` → 使用标准路径
   - `agents.*.sandbox.perSession` → 使用 `enabled`
   - `browser.ssrfPolicy.allowPrivateNetwork` → 使用标准路径
   - `hooks.internal.handlers` → 使用标准路径
   - 频道/群组/房间的 `allow` 切换 → 使用 `enabled`

2. **Claude CLI 后端移除**：新用户不再配置 `anthropic:claude-cli`，现有配置仍可运行

3. **CLI 文本提供商后端移除**：移除 `agents.defaults.cliBackends` 配置项

### 4.2 版本

1. **xAI 搜索配置迁移**：
   - 旧路径：`tools.web.x_search.*`
   - 新路径：`plugins.entries.xai.config.xSearch.*`
   - 认证：`plugins.entries.xai.config.webSearch.apiKey` / `XAI_API_KEY`

2. **Firecrawl 配置迁移**：
   - 旧路径：`tools.web.fetch.firecrawl.*`
   - 新路径：`plugins.entries.firecrawl.config.webFetch.*`

**迁移命令**：
```bash
openclaw doctor --fix
```

---

## 四、对当前业务的影响分析

### ✅ 积极影响

| 领域 | 影响 | 建议操作 |
|------|------|----------|
| **定时任务** | Task Flow 持久化提升可靠性 | 评估将重要 cron 任务迁移到 Task Flow |
| **记忆管理** | Dreaming 功能减少手动维护 | 启用 dreaming 实验功能，观察效果 |
| **飞书集成** | 文档评论支持增强协作 | 探索文档协作自动化场景 |
| **成本优化** | 提示缓存降低 API 费用 | 监控缓存命中率 |
| **多语言** | 控制 UI 支持中文 | 无操作，自动生效 |

### ⚠️ 需要注意

| 领域 | 风险 | 缓解措施 |
|------|------|----------|
| **配置兼容性** | 旧配置别名被移除 | 运行 `openclaw doctor --fix` 自动修复 |
| **执行审批** | 默认 YOLO 模式可能增加风险 | 检查 `~/.openclaw/exec-approvals.json` 配置 |
| **Claude CLI** | 新用户不再支持旧后端 | 现有配置不受影响，新配置使用 ACP 运行时 |

---

## 五、升级建议

### 立即执行

1. **配置检查与修复**
   ```bash
   openclaw doctor
   openclaw doctor --fix
   ```

2. **验证关键功能**
   ```bash
   openclaw status
   openclaw config validate
   ```

### 短期规划 (1-2 周)

1. **启用 Dreaming 功能**
   - 在配置中开启 `memory.dreaming.enabled`
   - 观察记忆整理效果

2. **评估 Task Flow 迁移**
   - 识别需要持久化状态的后台任务
   - 规划从 cron 到 Task Flow 的迁移

### 中期规划 (1 个月)

1. **探索多媒体生成**
   - 配置视频/音乐生成提供商
   - 测试 `video_generate` 和 `music_generate` 工具

2. **优化飞书工作流**
   - 利用文档评论功能增强协作
   - 评估 Drive 评论自动回复场景

---

## 六、版本变更日志摘要

### 4.2 (2026.4.2)
- ✅ Task Flow 持久化恢复
- ✅ 执行审批默认 YOLO 模式
- ✅ xAI/Firecrawl 配置迁移
- ✅ Matrix 原生审批支持
- ✅ 提供商传输安全加固

### 4.1 (2026.4.1)
- ✅ `/tasks` 聊天原生任务看板
- ✅ SearXNG 搜索支持
- ✅ Bedrock Guardrails 支持
- ✅ macOS 语音唤醒
- ✅ 大量稳定性修复

### 4.0 (2026.4.0)
- ✅ 多媒体生成（视频/音乐/图像）
- ✅ Dreaming 记忆实验功能
- ✅ 新提供商（Qwen/Fireworks/StepFun/MiniMax）
- ✅ 提示缓存优化
- ✅ 多语言控制 UI
- ⚠️ 配置别名清理（破坏性变更）

---

<callout emoji="📌" background-color="light-gray">
**总结**：4.x 系列是 OpenClaw 的重大升级，重点在任务持久化、多媒体生成、智能记忆和飞书深度集成。建议尽快运行 `openclaw doctor --fix` 完成配置迁移，并尝试启用 Dreaming 功能体验智能记忆管理。
</callout>"""
    
    # 使用 feishu_mcp_create_doc 工具
    result = subprocess.run(
        ['feishu_mcp_create_doc', '--title', title, '--markdown', markdown],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("文档创建成功")
        print(result.stdout)
    else:
        print("文档创建失败")
        print(result.stderr)
    
    return result.returncode == 0

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 send_feishu_report.py <title> <content_file>")
        sys.exit(1)
    
    title = sys.argv[1]
    with open(sys.argv[2], 'r') as f:
        content = f.read()
    
    success = send_feishu_doc(title, content)
    sys.exit(0 if success else 1)
