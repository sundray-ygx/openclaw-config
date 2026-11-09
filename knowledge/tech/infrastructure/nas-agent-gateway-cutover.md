# NAS 服务器 AI Agent 网关灰度切换指南

- **日期**: 2026-09-08（v2，融入 ECS 实战教训）
- **前置**: ECS 已部署 new-api 网关 `https://api.ygxpro.online`，本文档指导 NAS 侧完成同样切换
- **标签**: #gateway #new-api #nas #cutover

## ⚠️ 密钥安全规范（必读）

1. 明文 key 仅允许出现在 **`.env` 环境变量文件**中，**禁止**直接写入 config 配置文件
2. 本文档执行完成后，**必须删除文中明文 key**（本文档在 NAS 的 hermes 执行后自行清理）
3. `.env` 文件权限设为 `600`

## 0. 预检（切换前必须全部通过）

```bash
# NAS 能否出公网访问网关
curl -s -o /dev/null -w '%{http_code}\n' https://api.ygxpro.online/api/status
# 预期: 200
# DNS 不通则检查 NAS 的 DNS/代理配置
```

## 0.5 直连基线验证（关键，不可跳过）

切换前先测 NAS 侧**现有直连 key 的存活状态**，这决定回滚预案是否有退路：

```bash
# 按现有配置的 key 逐个测（示例）
# zai/bigmodel:
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://open.bigmodel.cn/api/coding/paas/v4/chat/completions \
  -H "Authorization: Bearer $现有ZAI_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"glm-4.7-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":50}'
# deepseek / volcengine 同理
```

- **200** → 该平台直连有效，回滚后有退路
- **401/403** → 该平台直连已死，**切换后不可逆**（只能依赖网关），需在执行记录中标注

> ECS 教训：zai 直连 key 在切换当天中午失效，切换后发现"回滚了也没用"。提前知道基线，才不会误判切换失败。

## 1. 写入 .env（所有 key 统一入口）

```bash
# 建议路径: ~/.env 或各 agent 对应的 .env，权限 600
cat >> /path/to/.env <<'EOF'
NEWAPI_BASE_URL=https://api.ygxpro.online
NEWAPI_KEY_OPENCLAW=sk-aVQ…luRW
NEWAPI_KEY_HERMES=sk-YvD…onB6
NEWAPI_KEY_CLAUDE_CODE=sk-0Ie…Ex2j
EOF
chmod 600 /path/to/.env
```

> 三个 nas- key 已实测可用（2026-09-08），与 ECS 的 ecs- key 用量在网关侧分账统计。

## 2. Step 1 — Claude Code

用 shell 环境变量注入（ECS 验证过的方案，避免明文落盘）：

```bash
# 先备份现有配置（如有 ~/.claude/settings.json）
cp ~/.claude/settings.json ~/.claude/settings.json.bak 2>/dev/null
# 启动环境注入（写入 profile 或启动脚本）
export ANTHROPIC_BASE_URL=https://api.ygxpro.online   # 裸域名，Claude 自己拼 /v1/messages
export ANTHROPIC_AUTH_TOKEN=<nas-claude-code 的 key，从 .env source>
export ANTHROPIC_MODEL=glm-5.3
```

**验证**（两步都做）:
```bash
# 1) 实际调用
claude -p "只回复两个字:成功" --model glm-4.7
# 预期输出: 成功
# 2) 网关侧核对: https://api.ygxpro.online 控制台 → 日志，应出现 nas-claude-code 令牌记录
```

> ⚠️ GLM 5.3/5.1 强制 thinking：max_tokens 过小会返回**空 content**，验证时如果收到空回复，先加大 max_tokens 重测再判定失败。

## 3. Step 2 — Hermes Agent

```bash
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak
cp ~/.hermes/.env ~/.hermes/.env.bak
# config.yaml（key 走环境变量引用，不落明文）:
#   model:
#     provider: custom
#     base_url: https://api.ygxpro.online/v1      # ⚠️ 必须带 /v1，hermes 拼接规则=base_url+/chat/completions
#     api_key: ${NEWAPI_API_KEY}
#     default: glm-5.3
# .env 追加:
#   NEWAPI_API_KEY=<nas-hermes 的 key，即 NEWAPI_KEY_HERMES>
```

> 注意：Hermes **无模型级 fallback**（单模型配置），网关内部渠道冗余（GLM→火山→DeepSeek）是它唯一的容错层。

**⚠️ 联动警告（NAS 特有）**: NAS 是 hermes-config git 仓的 hub，ECS 每天 05:00 从这里拉取配置。**NAS 侧修改 hermes config.yaml 后 git push，会影响 ECS 的 hermes**。若 NAS 与 ECS 的 hermes 配置不同（各自用各自 key），需确认 push 范围或使用分支，避免覆盖 ECS 已切好的配置。

**验证**: 重启 hermes gateway → 跑一轮对话 + 一轮工具调用 → 控制台日志确认 `nas-hermes` 令牌记录。

## 4. Step 3 — OpenClaw（三处对齐，原子化操作）

**ECS 实战教训**：OpenClaw 取 key 的真实路径与文档直觉不同，provider 配置里的 `apiKey` 字段**不生效**。必须三处同时对齐：

| # | 位置 | 改什么 |
|---|------|--------|
| 1 | `openclaw.json` → `models.providers.{deepseek,volcengine,zai}.baseUrl` | `https://api.ygxpro.online/v1`（**必须带 /v1**，OpenClaw 拼接规则=baseUrl+`/chat/completions`，缺 /v1 → 404 且报"Connection error"极具迷惑性）|
| 2 | `openclaw.json` → `env.DEEPSEEK_API_KEY` / `env.VOLCENGINE_API_KEY` | nas-openclaw 的 key（deepseek/volcengine provider 按 env 约定取 key）|
| 3 | SQLite `~/.openclaw/agents/main/agent/openclaw-agent.sqlite` → auth_profile_store | `zai:default` / `volcengine:default` 两个 profile 的 key（zai/volcengine 走 profile，优先级高于一切）|

**原子化脚本**（一次改完+校验，杜绝"改了一半"的中间态）：

```bash
cp /root/.openclaw/openclaw.json /root/.openclaw/openclaw.json.bak-cutover

python3 <<'EOF'
import json, sqlite3, os
tok = os.environ['NEWAPI_KEY_OPENCLAW']   # 从 .env source 后执行本脚本
c = json.load(open('/root/.openclaw/openclaw.json'))
for name in ['deepseek','volcengine','zai']:
    c['models']['providers'][name]['baseUrl'] = 'https://api.ygxpro.online/v1'
c['env']['DEEPSEEK_API_KEY'] = tok
c['env']['VOLCENGINE_API_KEY'] = tok
json.dump(c, open('/root/.openclaw/openclaw.json','w'), indent=2, ensure_ascii=False)

sdb = sqlite3.connect(os.path.expanduser('~/.openclaw/agents/main/agent/openclaw-agent.sqlite'))
j = json.loads(sdb.execute("SELECT store_json FROM auth_profile_store WHERE store_key='primary'").fetchone()[0])
for p in ['zai:default','volcengine:default']:
    if p in j['profiles']: j['profiles'][p]['key'] = tok
sdb.execute("UPDATE auth_profile_store SET store_json=? WHERE store_key='primary'", (json.dumps(j),))
sdb.commit()
# 输出校验
c2 = json.load(open('/root/.openclaw/openclaw.json'))
print({n: v['baseUrl'] for n,v in c2['models']['providers'].items()})
EOF

openclaw gateway restart
```

**验证**（三步）:
```bash
# 1) 链路实测（用 nas-openclaw key 走网关调 glm-4.7-flash）
curl -s -X POST https://api.ygxpro.online/v1/chat/completions \
  -H "Authorization: Bearer $NEWAPI_KEY_OPENCLAW" -H 'Content-Type: application/json' \
  -d '{"model":"glm-4.7-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":500}'
# 预期: 200 且 choices[0].message.content 非空

# 2) 重启后日志核对（应全部指向 api.ygxpro.online/v1 且 status=200，无 401/404）
journalctl -u openclaw-gateway --since '-5 min' | grep -E 'url=|status='

# 3) 控制台核对: nas-openclaw 令牌有请求记录
```

> ⚠️ fallback 现状：OpenClaw 模型级 fallback（glm-5.3→deepseek-v4-pro→doubao-2.1-turbo）切换后**全部指向同一台网关**（方案A）。网关本身挂了 fallback 救不了，依赖 ECS 网关的高可用。

## 5. 回滚预案（三处回滚点，缺一就是半态）

任一步异常，按**对应平台**回滚**全部相关位置**，然后重启对应服务：

```bash
# --- Claude Code（1 处）---
cp ~/.claude/settings.json.bak ~/.claude/settings.json   # + 移除注入的环境变量

# --- Hermes（2 处）---
cp ~/.hermes/config.yaml.bak ~/.hermes/config.yaml
cp ~/.hermes/.env.bak ~/.hermes/.env
# 重启 hermes gateway

# --- OpenClaw（3 处，缺一 = 半态，比不回滚更糟！）---
cp /root/.openclaw/openclaw.json.bak-cutover /root/.openclaw/openclaw.json   # 恢复 baseUrl + env key
# ⚠️ 还必须恢复 auth_profile_store 里的 zai:default / volcengine:default 两个 key！
# 切换前用下面的命令把原 profile key 导出留底（执行切换前必做！）:
#   python3 -c "import json,sqlite3;db=sqlite3.connect('/root/.openclaw/agents/main/agent/openclaw-agent.sqlite');j=json.loads(db.execute(\"SELECT store_json FROM auth_profile_store WHERE store_key='primary'\").fetchone()[0]);json.dump({k:v['key'] for k,v in j['profiles'].items()},open('/root/openclaw-profile-keys-backup.json','w'))"
# 回滚 profile:
#   用备份文件里的原 key 按切换脚本同样方法写回，再 openclaw gateway restart
```

**回滚后必测**：逐平台实测直连可用（对照第 0.5 节基线结果）。若某平台直连 key 在切换期间已失效（如 zai），回滚后该平台仍不可用，只能走网关 —— 这不是回滚失败，是基线事实。

## 6. 执行完成后的清理动作（重要）

- [ ] 删除本文档中「1. 写入 .env」节的明文 key（或整节替换为"见 .env"）
- [ ] 确认 `.env` 权限 600
- [ ] 网关控制台确认三个 nas- 令牌均有请求记录（切换成功的最终证据）
- [ ] 检查 NAS 本地是否有按令牌名查询网关库的巡检/统计脚本（令牌改名后按旧名查会假报错）

## 7. 灰度节奏建议

Claude Code → 观察 1-2 天 → Hermes → 观察 1-2 天 → OpenClaw（同 ECS 侧节奏）

> ⚠️ z.ai 上游偶发 429 = Coding Plan 限流，非网关故障，网关会自动切火山/DeepSeek 渠道兜底。

## 附: 网关信息

| 项 | 值 |
|---|---|
| 入口 | https://api.ygxpro.online（OpenAI `/v1/chat/completions` + Anthropic `/v1/messages` 双协议） |
| 控制台 | 同地址，root，密码见 ECS `/opt/new-api/admin-credentials.txt` |
| 渠道 | GLM Coding(主) → 火山 Coding(备) → DeepSeek 按量(兜底) |
| 已知限制 | GLM 5.3/5.1 强制 thinking，小 max_tokens 会得到空 content；z.ai 偶发 429 属上游限流 |
| URL 拼接规则 | OpenClaw/Hermes: baseUrl 需带 `/v1`；Claude Code: 裸域名 |
