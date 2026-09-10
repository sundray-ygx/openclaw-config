# new-api 网关部署方案与实施记录

- **日期**: 2026-09-08
- **状态**: Phase 1 部署完成并验证通过，灰度切换待执行
- **标签**: #gateway #new-api #llm #infrastructure

## 1. 背景与目标

统一管理三家算力采购渠道（GLM Coding Plan、火山引擎 Coding Plan、DeepSeek 按量），
通过 `https://api.ygxpro.online` 提供 OpenAI / Anthropic 双协议兼容入口，
供 OpenClaw、Hermes Agent、Claude Code 等 AI Agent 统一配置使用。

## 2. 选型结论

**new-api**（calciumion/new-api，Go 单二进制，v1.0.0-rc.35）
- 内存 ~150M，适配 2C/1.8G ECS
- 支持 OpenAI + Anthropic 双协议（/v1/messages 可转 OpenAI 上游）
- 渠道管理/令牌分账/故障转移/用量统计
- 对比淘汰：one-api（更新放缓、Anthropic 弱）、LiteLLM（Python 400M+ 内存吃不消）

## 3. 架构（实际部署）

```
Agent → https://api.ygxpro.online (nginx TLS, SSE 透传)
        → new-api 容器 127.0.0.1:3000 (SQLite, --memory=300m, restart=always)
            ├─ GLM-Coding    → http://172.17.0.1:8081/zai/v1/* → api.z.ai/api/coding/paas/v4/*
            ├─ Volc-Coding   → http://172.17.0.1:8081/volc/v1/* → ark.cn-beijing.volces.com/api/coding/v3/*
            └─ DeepSeek-Paygo → api.deepseek.com/v1/*（直连）
```

**关键设计决策**：
- new-api type=1（OpenAI 兼容）渠道固定拼接 `/v1/chat/completions`，
  而 z.ai 真实路径是 `/api/coding/paas/v4/chat/completions`、火山是 `/api/coding/v3/chat/completions`
- **解法**：nginx 监听 docker0 (172.17.0.1:8081)，路径重写桥接（`/zai/v1/ → api.z.ai/.../v4/`），
  仅容器可达，不对公网暴露
- 上游 key 从现有配置迁移：deepseek/volc 取自 openclaw.json env，zai 取自 auth_profile_store (SQLite)

## 4. 部署清单（已完成）

| 项 | 内容 |
|---|---|
| 容器 | `docker run -d --name new-api --restart=always --memory=300m -p 127.0.0.1:3000:3000 -v /opt/new-api/data:/data -e TZ=Asia/Shanghai calciumion/new-api:latest` |
| nginx | `/etc/nginx/conf.d/newapi.conf`（443 TLS 反代+SSE）、`/etc/nginx/conf.d/newapi-upstream.conf`（8081 上游桥接） |
| 证书 | 复用 `/etc/letsencrypt/live/ygxpro.online/` 泛域名证书 |
| 管理入口 | https://api.ygxpro.online （root，密码在 `/opt/new-api/admin-credentials.txt`，0600） |
| 渠道 | GLM-Coding(p30) / Volc-Coding(p20) / DeepSeek-Paygo(p10)，均 type=1 |
| 令牌 | openclaw / hermes / claude-code 三枚，无限额度（值存 /opt/new-api/data/one-api.db tokens 表） |

## 5. 验证结果（2026-09-08）

- ✅ OpenAI 格式 chat/completions：glm-4.7-flash、glm-5.3、doubao-seed-2-1-turbo、deepseek-v4-flash 全通
- ✅ Anthropic /v1/messages：glm-4.7、doubao 正常返回（含 thinking 内容块）
- ⚠️ z.ai 偶发 429：上游 Coding Plan 限流，非网关问题
- 注：GLM 5.3/5.1 系列为强制 thinking 模型，小 max_tokens 会导致 content 为空（thinking 吃掉预算）

## 6. 灰度切换步骤（手动执行）

### Step 1 — Claude Code（先切）
```bash
export ANTHROPIC_BASE_URL=https://api.ygxpro.online
export ANTHROPIC_AUTH_TOKEN=<claude-code 令牌>
# 验证：跑一个编码任务；控制台 https://api.ygxpro.online 看"日志"页有请求记录
```
观察 1-2 天。

### Step 2 — Hermes Agent
- provider baseUrl → https://api.ygxpro.online，key → <hermes 令牌>
- 验证对话 + 工具调用各一轮

### Step 3 — OpenClaw（最后切）
- 备份 `cp /root/.openclaw/openclaw.json openclaw.json.bak-20260908`
- providers 各家 baseUrl → https://api.ygxpro.online，apiKey → <openclaw 令牌>
- 重启 gateway，验证对话/定时任务
- 回滚：恢复备份重启

### 回滚预案
每个 agent 独立配置，任一异常恢复原 env/json 即回滚，互不影响。

## 7. 运维（待办）

- [ ] /opt/new-api/data 纳入 02:00 NAS 备份
- [ ] 巡检脚本加 new-api 容器存活检查
- [ ] 切换稳定后观察 SQLite 日志增长

## 8. 踩坑记录

1. new-api rc.35 首次启动需 /api/setup 初始化 root（非默认 root/123456）
2. 管理 API 需 `Authorization: Bearer <access_token>` + `New-API-User: 1` 双头
3. token 列表 API 返回脱敏 key，完整值只能从 SQLite 或控制台取
4. 渠道创建 API 需 `{"mode":"single","channel":{...}}` 包装
5. type=1 固定拼 /v1/*，非标准路径上游必须用 nginx 重写桥接（见 newapi-upstream.conf）
6. Python 3.6 无海象运算符/位置参数 mode，写脚本注意

---

## 2026-09-08 ECS 三平台灰度切换（完成）

- **入口**: https://api.ygxpro.online（OpenAI `/v1/*` + Anthropic `/v1/messages` 双协议）
- **OpenClaw 关键接线（三处必须同时对齐）**:
  1. `openclaw.json` providers baseUrl = `https://api.ygxpro.online/v1`（OpenClaw 拼接规则：baseUrl + `/chat/completions`，不带 /v1 会 404）
  2. env `DEEPSEEK_API_KEY` / `VOLCENGINE_API_KEY`（deepseek/volcengine provider 按 env 约定取 key）
  3. auth_profile_store（SQLite）`zai:default` / `volcengine:default` 的 key（zai/volcengine 走 profile，provider 里的 apiKey 字段无效）
- **Hermes**: config.yaml `base_url: https://api.ygxpro.online/v1` + `.env NEWAPI_API_KEY`（ecs-hermes 令牌）
- **Claude Code**: `ANTHROPIC_BASE_URL=https://api.ygxpro.online`（裸域名，Claude 自己拼 /v1/messages）
- **令牌**: ecs-openclaw / ecs-hermes / ecs-claude-code（ECS 侧）；nas-openclaw / nas-hermes / nas-claude-code（NAS 侧，用量分账）
- **zai 直连 key 已失效**（bigmodel c2078ce9… 带/不带 .Pi7hIjC78fNU89mg 后缀均 401），glm 系列只有网关链路（api.z.ai 渠道 key 有效）
- **运维**: 每日 08:20 巡检 `scripts/utils/check_newapi.sh`；02:00 NAS 备份含 `08-new-api`（SQLite + 凭据 + 容器元数据）
- **NAS 侧切换文档**: `nas-agent-gateway-cutover.md`

---

## 模型定价（2026-09-08 设置）

机制：`输入价 = ModelRatio × $2/1M`，`输出价 = 输入价 × CompletionRatio`。配置备份：`/opt/new-api/price-options-backup.json`

| 模型 | 输入$/1M | 输出$/1M | ≈¥/1M(×7.1) | 来源 |
|---|---|---|---|---|
| glm-5.3 / 5.2 / 5.1 | 1.40 | 4.40 | 9.9 / 31.2 | z.ai 官方 |
| glm-5.3-flash | 0.15 | 0.50 | 1.1 / 3.6 | z.ai 官方 |
| glm-4.7 | 0.60 | 2.20 | 4.3 / 15.6 | z.ai 官方 |
| glm-4.7-flash | 0.07 | 0.40 | 0.5 / 2.8 | z.ai 官方 |
| glm-4.6v | 0.30 | 0.90 | 2.1 / 6.4 | 官方+多源 |
| deepseek-v4-pro | 1.32 | 3.96 | 9.4 / 28.1 | DeepSeek 官方(峰值价，9/14起路由到V4.1-Flash按Flash计费) |
| **deepseek-flash** (V4.1-Flash) | **0.282** | **1.128** | **2.0 / 8.0** | DeepSeek 官方(峰值价，2026-09-10 新增) |
| deepseek-v4-flash / vision-exp | 0.44 | 1.32 | 3.1 / 9.4 | DeepSeek 官方(已下线，路由到V4.1-Flash) |
| doubao pro/code/vision/evolving | 0.11 | 1.13 | 0.8 / 8.0 | ⚠️待核对：seed-1.6 档近似(决策C) |
| doubao lite/mini/turbo | 0.021 | 0.21 | 0.15 / 1.5 | ⚠️待核对：seed-1.6-flash 档近似(决策C) |
| deepseek-v4-*(-ga-260xxx volc 版) | 同官方 | 同官方 | - | volc 托管版按 DeepSeek 官方价近似 |

**验证**：
- glm-4.7-flash: (6pt+225ct) quota=45，手工复算一致 ✓
- deepseek-flash: (36pt+20ct) quota=16，手工复算一致 ✓

**注意**：deepseek 官方有峰谷差价（峰值 北京时间 周一~五 9-12/14-18 点），网关按峰值价保守计；doubao 若后续要定价，从火山控制台抄单价后按 ratio=输入$/2 换算；deepseek-v4-pro 将于 2026-09-14 下线，请求自动路由到 V4.1-Flash 并按 Flash 计费
