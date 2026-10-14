# new-api 网关切换机制（ECS ⇄ NAS 双活切换）

- **建立**: 2026-10-14
- **现状基线**: **ECS 为主网关**（2026-09-27 NAS 僵死后反转架构），NAS 为热备，随时可切
- **用途**: 快速查询切换机制、执行切换、验证状态，防遗忘防踩坑
- **标签**: #gateway #new-api #switch #failover #frp #nginx

---

## 一、拓扑总览

```
公网请求
  │
  ▼
api.ygxpro.online ──► ECS nginx:443 (TLS 终端)
                              │
              ┌───────────────┴───────────────┐
              │                               │
        proxy_pass 3000                proxy_pass 3100
        （ECS 本地，主）               （frp 隧道 → NAS，备）
              │                               │
              ▼                               ▼
        ECS new-api:3000          NAS new-api:3000
        ├ GLM → 本地桥接 8081      ├ GLM → NAS 本地桥接 8081
        ├ Volc → 本地桥接 8081     ├ Volc → NAS 本地桥接 8081
        └ DeepSeek → 直连          └ DeepSeek → 直连
```

**关键设计**：
- 域名/DNS/令牌**全部不变**，客户端零感知
- 3100 端口不进阿里云安全组，公网扫不到（ECS 本机回环连接）
- 切换动作仅一条：改 nginx `proxy_pass` 端口 + reload，**秒级完成**
- 两侧 new-api 都常驻运行（ECS 接流量，NAS 待命），切换无冷启动

---

## 二、30 秒决策树

```
当前 ECS 是主，正常运行 → 别动

发现 ECS new-api 挂了（3000 不通 / 容器死了 / 502）
  → 先看 NAS 热备健康: curl 127.0.0.1:3100/api/status
  ├ 200 → bash /root/scripts/utils/newapi-switch.sh to-nas     # 切到 NAS 热备
  └ 非200 → 先修 ECS 容器，别盲目切

故障恢复后（ECS new-api 活了）
  → bash /root/scripts/utils/newapi-switch.sh to-ecs           # 切回 ECS 主
  （建议低峰执行，避免来回抖动）

不确定当前谁是主
  → bash /root/scripts/utils/newapi-switch.sh status           # 只读查看
```

---

## 三、统一入口：newapi-switch.sh

**脚本路径**：`/root/scripts/utils/newapi-switch.sh`

### 命令清单

| 命令 | 作用 | 是否改流量 |
|---|---|---|
| `status` | 查看当前主备状态、两端探活、conf 指向 | ❌ 只读 |
| `verify` | 全链路验证（两端探活 + 公网 + 双渠道 LLM 调用） | ❌ 只读 |
| `to-nas` | 切到 NAS 热备（3000→3100） | ✅ 改 |
| `to-ecs` | 切回 ECS 主（3100→3000） | ✅ 改 |

### 安全模式（推荐）：先预演

```bash
DRY_RUN=1 bash /root/scripts/utils/newapi-switch.sh to-nas
```
只打印将要执行的动作和当前状态，**不动任何服务**。

### 正式切换

```bash
# 切到 NAS 热备（ECS 挂了应急）
bash /root/scripts/utils/newapi-switch.sh to-nas

# 切回 ECS 主（故障恢复后）
bash /root/scripts/utils/newapi-switch.sh to-ecs
```

每次切换自动：前置探活 → 备份 conf → sed 改端口 → `nginx -t` → reload → 公网 status 三连 → 双渠道 LLM 验证。
失败自动回滚 conf + reload，不会留半态。

### 日志

- `to-nas`：`/tmp/newapi-switch-nas.log`
- `to-ecs`：`/tmp/newapi-switch-ecs.log`

---

## 四、手动应急（脚本挂了也能切）

记住这 4 行，任何时候都能手切：

```bash
# 查看当前指向
grep proxy_pass /etc/nginx/conf.d/newapi.conf

# 切到 NAS（3000 → 3100）
sed -i 's|proxy_pass http://127.0.0.1:3000;|proxy_pass http://127.0.0.1:3100;|' /etc/nginx/conf.d/newapi.conf
nginx -t && nginx -s reload

# 切回 ECS（3100 → 3000）
sed -i 's|proxy_pass http://127.0.0.1:3100;|proxy_pass http://127.0.0.1:3000;|' /etc/nginx/conf.d/newapi.conf
nginx -t && nginx -s reload
```

---

## 五、数据一致性须知（必读）

两侧 new-api 是**各自独立的 SQLite 库**，不做实时同步。切换后：

1. **令牌、渠道、价格配置**：两侧都是 2026-09-27 反转时的同源快照，日常配置变更（加渠道/改价格）在哪端做的，**切到另一端就暂时不可见**——切回即恢复，数据不会丢
2. **用量统计**：各记各的，断层可接受，不需要合并
3. **应急原则**：保服务可用 > 数据完整。故障时先切，别纠结数据
4. **配置变更建议**：日常只在 ECS 主上做变更；要在 NAS 上改的话，记得同步回 ECS（或接受"切回就恢复原状"）

---

## 六、自动探测与告警

- **脚本**：`/root/scripts/utils/ecs-failover-probe.sh`
- **逻辑**：cron 每 5 分钟探 ECS 本地 3000，连续 2 次失败 → 自动切 3100（NAS 热备） + 飞书红卡告警
- **恢复**：ECS 恢复后发绿卡通知**人工切回**（不自动切，防抖动）
- **人工切回**：`bash /root/scripts/utils/ecs-failover-probe.sh switchback`
- **状态文件**：`/tmp/ecs-newapi-probe.state`（mode:main/backup, fails:N）

> 注意：自动探测只在 ECS → NAS 方向自动切，反向（NAS → ECS）必须人工。

---

## 七、依赖清单

| 依赖 | 位置 | 作用 |
|---|---|---|
| nginx conf | `/etc/nginx/conf.d/newapi.conf` | 切换开关 |
| frp 隧道 | ECS frps → NAS frpc，remote_port 3100 | NAS 热备链路 |
| ECS new-api 容器 | `docker ps` name=new-api，127.0.0.1:3000 | 主网关 |
| NAS new-api 容器 | NAS Docker，frpc 映射 3100 | 热备网关 |
| 桥接 nginx | ECS/NAS 各一套 172.17.0.1:8081 | GLM/Volc 路径重写 |
| 桥接配置 | `/etc/nginx/conf.d/newapi-upstream.conf` | ECS 侧桥接规则 |

---

## 八、架构演进时间线

| 时间 | 事件 | 主/备 |
|---|---|---|
| 2026-09 上旬 | new-api 跑在 ECS，单实例 | ECS 独苗 |
| 2026-09-17 | 迁 NAS 为主，ECS 留热备 | NAS 主 / ECS 备 |
| 2026-09-18 | 建 failover 双向脚本 + 手册 | NAS 主 / ECS 备 |
| **2026-09-27** | **NAS new-api 僵死事故，反转架构：ECS 转正，NAS 降热备** | **ECS 主 / NAS 备** |
| 2026-09-27 | 部署 ecs-failover-probe.sh 自动探测 + 自动切 NAS | ECS 主 / NAS 备 |
| 2026-10-14 | 整理本文档，统一入口 newapi-switch.sh | ECS 主 / NAS 备 |

---

## 九、相关文档与脚本

| 资产 | 路径 | 状态 |
|---|---|---|
| 本机制文档（主） | `knowledge/tech/infrastructure/newapi-gateway-switch-mechanism.md` | ✅ 当前 |
| 旧 failover 手册（NAS 主视角） | `knowledge/tech/infrastructure/newapi-gateway-failover.md` | ⚠️ 已过时，仅作历史参考 |
| 迁移可行性评估 | `knowledge/tech/infrastructure/newapi-nas-migration-feasibility.md` | 历史档案 |
| ECS 侧迁移执行手册 | `knowledge/tech/infrastructure/newapi-nas-migration-ecs-side-runbook.md` | 历史档案 |
| NAS 侧迁移执行手册 | `knowledge/tech/infrastructure/newapi-nas-migration-nas-side-runbook.md` | 历史档案 |
| 统一切换脚本（新） | `/root/scripts/utils/newapi-switch.sh` | ✅ 当前 |
| 自动探测脚本 | `/root/scripts/utils/ecs-failover-probe.sh` | ✅ 在用 |
| 旧脚本 failover-to-ecs.sh | `/root/scripts/utils/failover-to-ecs.sh` | 复用中（被 wrapper 调用） |
| 旧脚本 failover-back-to-nas.sh | `/root/scripts/utils/failover-back-to-nas.sh` | 复用中（被 wrapper 调用） |
