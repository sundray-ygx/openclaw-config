# note.ygxpro.online POST 超时故障诊断报告

> 日期：2026-11-17 ｜ 诊断方：ECS Hermes
> 任务书来源：WebDAV nas-recovery/ecs-task-note-proxy-20261117.md（NAS Hermes 19:10 发起）
> 状态：根因已锁定，修复方案待 Boss 批准（决策门）

## 一、任务书事实核查

| # | 任务书声称 | ECS 实测 | 判定 |
|---|-----------|---------|------|
| 1 | note/kuma 外网全部超时（GET/POST 均挂） | GET 实测全通（note=200/0.06s，kuma=302/0.03s，外网真路径）；**POST /login 实测 000 挂死 10s+** | ⚠️ 部分属实：GET 已恢复，POST 仍挂 |
| 2 | 故障在 ECS 侧二选一：frps 假活 / nginx 进程异常 | frps(pid 2343043) 自 6/11 稳定运行，7000/6800/3001 全监听，控制连接 ESTABLISHED；nginx active，nginx -t 通过，磁盘 75%、inode 29% 无压力 | ❌ 两个预设方向均不成立 |
| 3 | frpc 重启（18:14）与故障无关 | 属实：18:14 是后端从 SiYuan 切到 calibre-web 的窗口，nginx error.log 18:03-18:14 大量 upstream prematurely closed（新旧后端交替），18:14 后 GET 恢复 | ✅ 补充了真实关联 |

## 二、分层定位证据链（全部只读实测）

1. **外网真路径**：GET https://note.ygxpro.online/login = 200（0.06s）；POST = 000 超时（复现 Boss 症状）
2. **frps 回环直连**：GET/POST 直打 127.0.0.1:6800 → GET 200 / POST 400，均毫秒级 → **隧道与 calibre-web 后端对 POST 完全正常**
3. **nginx 本机链路**：POST 经 https://127.0.0.1（SNI note）→ 挂死（verbose 显示请求体 3 字节已发完、0 字节响应）→ **毒点在 nginx 转发层**
4. **判别实验（决定性）**：直打 6800 复刻 nginx 转发头：
   - T1 POST + `Connection: upgrade` → **000 挂死 8s（复现）**
   - T2 POST + 正常头 → 400（0.016s，正常）
   - T3 GET + `Connection: upgrade` → 200（不受影响）
   - T4 GET + 正常头 → 200

## 三、根因

`/etc/nginx/conf.d/note.conf`（2026-11-13 为 SiYuan 部署）硬编码：

```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";   # ← 毒点：无条件加 upgrade
```

标准写法应有 map 兜底（无 Upgrade 头时 Connection 应为 close）。该头对 SiYuan 无害，但**今天 6800 后端换成 calibre-web（Python 后端）后，POST + `Connection: upgrade` 组合使后端挂死不响应**；GET 不受影响。kuma.conf 同款写法但 uptime-kuma 是 Node 后端，实测 POST 404 快速返回，不受影响。

时间线完全吻合：18:03-18:14 后端切换窗口（GET 也断，upstream prematurely closed）→ 18:14 calibre-web 稳定 → GET 恢复、POST 持续挂（Boss 18:14 后实测 POST 502/499，浏览器 499=放弃等待）。

## 四、修复方案（待批）

**方案（最小化，nginx 官方标准模式）**：note.conf 顶部（server 块外，http 上下文）加 map，替换硬编码：

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
# server 内：
proxy_set_header Connection $connection_upgrade;   # 原为 "upgrade" 硬编码
```

- 效果：POST/GET（无 Upgrade 头）→ Connection: close → calibre-web 正常；未来若换回需 WS 的后端，浏览器带 Upgrade 头时自动升级，兼容保留
- 备选方案 B（更简）：直接删 Upgrade/Connection 两行（calibre-web 纯 HTTP 无 WS 需求）——diff 更小但丢失未来 WS 兼容
- 生效：nginx -t && systemctl reload nginx（零中断，仅重读配置）
- 回滚：cp note.conf.bak 恢复 + reload，30 秒内
- kuma.conf 不动（Node 后端实测无恙，uptime-kuma 需要 WS）
- 不涉及 frps 重启、不涉及磁盘清理

## 五、验证清单（2026-11-17 19:30 修复后实测，全过）

- [x] POST https://note.ygxpro.online/login -d 'x=1' → **400 / 0.096s**（calibre-web 对无效表单正常拒绝；修复前 000 超时 10s+）
- [x] GET https://note.ygxpro.online/login → 200 ×3（0.036-0.083s）
- [x] https://kuma.ygxpro.online/ → 302（回归确认）
- [x] console.ygxpro.online → 200、api.ygxpro.online → 200（现有服务无回归）
- [x] 回写 WebDAV 任务书回执区（PUT 204，回读 md5 一致）+ 通知 NAS 侧复验

## 六、附带发现（不在本任务书范围，仅报告）

1. **pdf.ygxpro.online 后端挂了**：ECS 直打 127.0.0.1:18080 立即断连（000/0.009s，frps 端口在但隧道对端无响应=NAS 侧 stirling-pdf 容器未起/挂死）。nginx error.log 每 5 分钟一条（NAS Kuma 探测），自 03:28 起累计 190 条。→ 需 NAS 侧检查容器
2. **frps 被扫描器探测**：18:09 两个来自 193.149.185.169 的 frpc 0.69.1 伪客户端（hostname=scanner-probe-host-0001）尝试登录 7000 端口，认证失败退出，未造成损害——印证 B2（7000 限源）加固价值
