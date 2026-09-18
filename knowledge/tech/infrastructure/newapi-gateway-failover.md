# new-api 网关故障切换手册（NAS ↔ ECS 热备）

- **建立**: 2026-09-18 | **背景**: 2026-09-17 new-api 已迁 NAS（见 newapi-nas-migration-*.md），ECS 保留热备
- **用途**: NAS 侧网关故障时一键切回 ECS；NAS 恢复后一键切回。两个脚本均幂等、可重复执行

## 一、30 秒决策树

```
api.ygxpro.online 挂了吗？（curl -s -o /dev/null -w '%{http_code}' https://api.ygxpro.online/api/status）
├─ 非 200 且确认 NAS 侧问题（容器挂/frp 断/家宽断/硬件）
│    → bash /root/.openclaw/workspace/scripts/utils/failover-to-ecs.sh     # 切回 ECS 热备，约 5 秒
├─ 200，但之前切到了 ECS，现在 NAS 已恢复
│    → bash /root/.openclaw/workspace/scripts/utils/failover-back-to-nas.sh # 切回 NAS，零停机
└─ 200 → 一切正常，别动
```

不确定时先跑 `DRY_RUN=1 bash <脚本>` 只读预演（不动任何服务，打印当前四项状态）。

## 二、脚本用法

### failover-to-ecs.sh（故障 → ECS 热备）

```bash
DRY_RUN=1 bash /root/.openclaw/workspace/scripts/utils/failover-to-ecs.sh   # 预演（推荐先跑）
bash /root/.openclaw/workspace/scripts/utils/failover-to-ecs.sh             # 正式切换
```

动作：旧容器未跑则 `docker start`（常驻时跳过）→ nginx `3100→3000` → reload → 公网 status 三连 + LLM 双渠道验证。
日志：`/tmp/newapi-failover-ecs.log`

### failover-back-to-nas.sh（恢复 → 切回 NAS）

```bash
DRY_RUN=1 bash /root/.openclaw/workspace/scripts/utils/failover-back-to-nas.sh
bash /root/.openclaw/workspace/scripts/utils/failover-back-to-nas.sh
```

动作：**强制前置检查 3100 可达（NAS 未恢复拒绝切换）** → nginx `3000→3100` → reload → 验证。
日志：`/tmp/newapi-failover-back.log`

## 三、⚠️ 数据一致性须知（必读）

1. **ECS 热备数据 = 2026-09-17 23:15 快照**。切回 ECS 后：
   - 用量统计：23:15 后的记账数据不在 ECS 库（断层，接受）
   - **NAS 控制台期间做过的配置变更（渠道/令牌/价格）会"暂时不可见"**——数据仍在 NAS 完好无损，切回 NAS 即恢复
2. 切回 ECS 期间产生的用量数据写在 ECS 库，**不要**在 NAS 恢复后合并（各记各的，差异极小）
3. 应急原则：**保服务可用 > 数据完整**。故障时先切，别纠结数据

## 四、架构现状（切换相关部分）

```
正常: Agent → api.ygxpro.online → ECS nginx:443(TLS) → frp(ECS:3100) → NAS new-api:3000
热备: Agent → api.ygxpro.online → ECS nginx:443(TLS) → ECS new-api:3000（本地旧实例）
渠道: GLM-Coding → ECS/NAS 本地桥接(172.17.0.1:8081 路径重写) → api.z.ai（两侧各一套桥接，配置相同）
      Volc-Coding → 同上 → ark.cn-beijing.volces.com
      DeepSeek-Paygo → api.deepseek.com 直连
```

- ECS 热备容器常驻运行（`docker ps` 可见，Up 状态，占 ~61MB，接收 0 流量）——故障时免启动秒级切换
- 两侧渠道/令牌数据同源（2026-09-17 迁移），`ecs-openclaw` 令牌在两侧库中均有效

## 五、验证方式（脚本自动做，也可手动）

```bash
# 链路
curl -s -o /dev/null -w '%{http_code}\n' https://api.ygxpro.online/api/status   # 200
# 真实调用（key 从 /opt/new-api/data/one-api.db tokens 表取 ecs-openclaw）
curl -s -X POST https://api.ygxpro.online/v1/chat/completions \
  -H "Authorization: Bearer sk-<key>" -H 'Content-Type: application/json' \
  -d '{"model":"glm-5.3-flash","messages":[{"role":"user","content":"reply ok"}],"max_tokens":1000}'
```

已知非故障：`glm-4.7-flash` 报 model_not_found 属正常（渠道模型列表本就无此模型，待补配）。

## 六、切换历史

| 时间 | 方向 | 原因 | 执行 |
|---|---|---|---|
| 2026-09-17 23:25 | NAS→ECS（自动回滚） | 首次迁移编排等待超时 | 编排脚本自动 |
| 2026-09-17 23:41 | ECS→NAS（迁移完成） | hermes 修复后切流 | 手动 sed+reload |
| （待续） | | | |
