# new-api 数据审计方案（待决策）

> 状态: 🔶 评估完成，待 Boss 决策 | 2026-09-13
> 决策点见文末三项

## 需求

1. 审计可见性：哪些客户端、何时、调什么模型、具体交互内容
2. 内容管控：交互内容筛选/过滤，满足数据审计要求

## 现状实测（2026-09-13）

- 链路: 客户端 → nginx(443) → new-api 容器(:3000, calciumion/new-api:latest, 2026-09-08 上线) → 上游(GLM→火山→DeepSeek)
- 存储: SQLite `/opt/new-api/data/one-api.db`
- 活跃客户端（近7天）: nas-hermes 1942次/119M tok、ecs-openclaw 896次/64M、ecs-claude-code 349次、ecs-hermes 228次、mac-hermes/mac-openclaw/mac-pro-openclaw/nas-claude-code 等 8 令牌
- logs 表: 仅元数据（token_name/ip/model/prompt_tokens/completion_tokens/use_time/is_stream/request_id），**content 为空，对话正文不落库**
- 二进制确认内置: `CheckSensitiveEnabled` / `CheckSensitiveOnPromptEnabled` / `SensitiveWords` / `CheckSensitiveText`（请求侧敏感词，当前未启用；未见响应侧开关）
- 日志外发: 支持 `LOG_SQL_DSN` 独立日志库 + ClickHouse TTL
- `RequestLogURL` 字符串为 Stripe 支付字段，与请求日志无关（排除）

## 结论

- "谁/何时/什么模型/多少量" → 现状已满足，零改动
- "具体交互内容" → 内置做不到，需加内容记录层
- "内容过滤" → 请求侧可内置开启；双侧过滤+留存需代理层

## 三档方案

### 方案一: 纯内置（30min，零风险）
开启敏感词检查+词表。只有访问审计+请求侧拦截；无内容留存、无响应侧过滤。

### 方案二: LiteLLM 审计前置层 ⭐推荐
```
客户端 → LiteLLM → new-api → 上游
            ↓ callback
     PostgreSQL（全量 prompt/completion，流式重组）
```
- 双侧 guardrails: 敏感词/PII 掩码(presidio)/prompt injection 检测
- 可选 Langfuse 自托管做审计工作台（trace 检索/告警看板）
- new-api 保留管渠道路由与计费；LiteLLM 不碰上游 key
- 客户端改 baseUrl（8 令牌 × 3 平台，复用 2026-09-08 切换文档与回滚脚本）
- 风险: 多一跳故障点，需监控+回滚预案；loopback 延迟可忽略

### 方案三: LiteLLM 全面替换 new-api
推翻 5 天前迁移，成本高，不推荐。

## 分期路线（方案二）

| 阶段 | 内容 | 耗时 | 风险 |
|---|---|---|---|
| P1 | 开启内置敏感词 + 确认 IP 记录 | 30min | 零 |
| P2 | LiteLLM + Postgres 全量内容落库，单客户端灰度→全量 | 半天 | 中 |
| P3 | Langfuse 工作台 + 90天内容TTL/元数据长期 + 备份纳管 | 1-2h | 低 |

存储预估: 2.6 亿 tok/7天 ≈ 全文几百 MB，Postgres 单机无压力。

注: LiteLLM/Langfuse 特性基于既有知识，外网搜索工具当轮受限未核对最新版本，P2 执行前先小规模验证。

## 待决策三项

1. **方案选型**: 方案二分期（推荐）/ 方案一仅内置 / 方案三全面替换
2. **过滤语义**: 拦截+留存都要（推荐）/ 只记录+告警 / 只拦截
3. **留存边界**: PII 脱敏后全量留存（推荐）/ 全量原文 / 只留命中审计规则的

## 相关

- 部署文档: `knowledge/tech/infrastructure/new-api-gateway-deployment.md`
- NAS 切换文档: `knowledge/tech/infrastructure/nas-agent-gateway-cutover.md`
- 切换教训: `memory/lessons.md` [2026-09-08] baseUrl 必须带 /v1
