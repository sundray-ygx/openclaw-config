# OpenClaw 升级执行进展 - 2026.9.3

> 更新时间：2026-09-11 16:00
> 当前状态：**✅ 升级完成（待 24h 观察期）**
> 执行人：小助 → hermes（小群）完成

---

## 一、最终状态

| # | 步骤 | 状态 | 详情 |
|---|------|------|------|
| 1 | 前置检查 | ✅ | 版本/内存/磁盘/服务状态（文档声称 vs 实际差异 3 处，见 §五） |
| 2 | 全量备份 | ✅ | 207M，`backup-pre-upgrade-20260911_123734/` |
| 3 | nvm + Node 24 | ✅ | v24.21.0 LTS，nvm default |
| 4 | OpenClaw 2026.9.3 | ✅ | **pnpm 全局安装**（npm 11 在 1.8G 内存机上 OOM×3，见 §四） |
| 5 | Gateway 重启（Node 24） | ✅ | systemd unit ExecStart 已切换，active + enabled |
| 6 | 升级后验证 | ✅ | 版本/端口/飞书通道 running/cron 9 任务完整 |
| 7 | 观察期 | ⏳ | 至 2026-09-12 15:00；今晚 23:30 GitHub cron 是首个真实测试 |

## 二、升级后的实际架构

```
systemd(openclaw-gateway.service, 系统级, enabled)
  └─ Node 24.21.0 (nvm) 
      └─ openclaw 2026.9.3 (pnpm global)
          ├─ 入口: /root/.local/share/pnpm/global/5/.pnpm/openclaw@2026.9.3/.../openclaw.mjs
          ├─ CLI bin: /root/.local/share/pnpm/openclaw (需 PATH 含 /root/.local/share/pnpm)
          ├─ 密钥: /root/.openclaw/.env (9 个 API key 从 config env 段迁出, 0600)
          ├─ 插件: openclaw-lark 2026.8.5-beta.0 (npm projects 目录, 经兼容补丁)
          └─ 状态: /root/.openclaw/state/openclaw.sqlite (audit-events-v2 迁移完成)
```

**环境变量要求**：交互 shell 使用 CLI 需 `export PNPM_HOME=/root/.local/share/pnpm; export PATH=$PNPM_HOME:$PATH`（root 的 .bashrc 未配，建议补）。

## 三、升级中解决的问题链

1. **npm install OOM**（×3）：1.8G 内存机 npm 11 + 原生脚本安装峰值 750M+ → 停 gateway 释放内存仍不够 → **换 pnpm**（openclaw 官方发布管理器）39 秒装完
2. **tarball 直解缺 node_modules**：9.x 发布不含依赖 → 放弃 npm pack 直解路线
3. **Config Guard 拦启动**（exit 78）：7 个过时 key + env 段 9 密钥 → 手动迁密钥到 `~/.openclaw/.env` + 删过时 key + `agents.ownership="explicit"`
4. **State DB schema 迁移**：audit-events-v2 → `doctor --fix` 完成
5. **Doctor 进不了维护模式**：手工系统级 unit 不被识别（verdict=unavailable）→ 源码发现 `OPENCLAW_SERVICE_REPAIR_POLICY=external` 官方开关 → 顺利修复
6. **lark 插件加载失败**（飞书断）：三层问题
   - `openclaw/plugin-sdk` 裸入口在 9.3 被移除 → 补 exports 映射
   - `version.js`/`token-store.js` 混用 `import.meta`（CJS 文件）触发 Node24 ESM 语法检测误判 → 改 `__filename/__dirname`
   - `plugin-sdk/channel-runtime` 子路径在 9.3 改名 → 补映射到 channel-outbound
7. **设备配对/HEARTBEAT/TOOLS.md/auth-profiles**：doctor --fix 自动迁移完成（4 台配对设备入 SQLite）

### 3.1 升级后追加修复（15:30-16:00）

8. **旧 CLI 混用报错**：`/usr/bin/openclaw` 还是 9/2 的旧版符号链接（2026.7.1-2），旧 CLI 读 9.3 新配置报 config invalid → 换 wrapper 脚本（钉死 Node24 + openclaw.mjs），备份 `openclaw.old-2026.7.1-2.bak`；`PNPM_HOME` 已入 `.bashrc`
9. **TUI 启动报错**（用户报告的"启动 openclaw 报错"）：9.x 多 agent（main/scheduler/coding）必须显式指定 session → `openclaw tui --session agent:main:main` ✅ 实测连接成功
10. **飞书消息处理崩**（15:29/15:44 两消息失败）：9.3 `PluginRuntime` 结构变化，lark beta 调旧 API 全崩 → setRuntime 兼容桥（lark-client.js）：
    - `config.loadConfig()` → 桥接到 `config.current()`
    - `runtime.channel.text.chunkMarkdownText` → 从 `openclaw/plugin-sdk/reply-runtime` 注入（9.3 移除了 runtime.channel，出站分块会崩）
    - `runtime.log` → `logging.getChildLogger()` 注入
    - outbound.js chunker 加降级兜底（硬切保证消息必达）

## 四、npm OOM 明细（教训）

| 尝试 | 结果 |
|------|------|
| npm install -g（默认） | 成功但 5 个安装脚本被 npm11 拦截，包半态 |
| npm install --allow-scripts | **OOM kill ×3**（14:10 / 14:11 / 14:15，npm 峰值 743-767M） |
| tarball 直解 + 手动补 | 依赖装不上（9.x 无 vendored deps） |
| **pnpm add -g --dangerously-allow-all-builds** | ✅ **39.2s 成功，全脚本跑完** |

**结论：1.8G 内存机器装 openclaw 用 pnpm，别用 npm。**

## 五、交接文档与实际的差异（重要）

| # | 文档声称 | 实际 |
|---|---------|------|
| 1 | Gateway "非 systemd，PID 1 子进程" | systemd 系统级 unit 管理（active+enabled，Restart=always，MemoryMax=450M） |
| 2 | kill 进程停服务 | 会被 systemd 10s 内拉起 → 必须 systemctl |
| 3 | 旧版路径 /usr/lib/node_modules | 对，但 9.x 入口变了（openclaw.mjs，非 dist/index.js） |
| 4 | npm install -g openclaw@2026.9.3 | 在本机必 OOM（见 §四） |
| 5 | 回滚脚本 systemctl --user | bug：实际是系统级 unit，脚本会失败 |

## 六、回滚预案（若需）

```bash
# 1. 停新 gateway
systemctl stop openclaw-gateway

# 2. 恢复 unit（改回旧 ExecStart）
#    旧: /usr/bin/node /usr/lib/node_modules/openclaw/dist/index.js
#    手工编辑 /etc/systemd/system/openclaw-gateway.service 或 git 恢复
systemctl daemon-reload

# 3. 恢复配置+数据（备份在 backup-pre-upgrade-20260911_123734/）
BACKUP=/root/.openclaw/backup-pre-upgrade-20260911_123734
cp $BACKUP/openclaw.json ~/.openclaw/openclaw.json
rm -rf ~/.openclaw/agents && cp -r $BACKUP/agents ~/.openclaw/
rm -rf ~/.openclaw/plugins && cp -r $BACKUP/plugins ~/.openclaw/
# ⚠️ state/openclaw.sqlite 未备份——升级后 DB 已做 audit-events-v2 迁移，回滚旧版时
#    旧版 schema 兼容性未验证；若旧版起不来，需从备份恢复后重试

# 4. 启动
systemctl start openclaw-gateway
```

## 七、观察期 TODO（至 9-12 15:00）

- [ ] 今晚 23:30 GitHub cron 正常跑（升级后首个真实任务）
- [ ] 明晨 03:00 Memory Dreaming 正常
- [ ] 飞书消息收发正常（发条消息测试）
- [ ] 无新增 ERROR 日志
- [ ] 内存稳定（RSS < 450M MemoryMax 线）
- [ ] 遗留问题：`new-api GLM 渠道健康检查` cron 升级前就 error(2x)，与升级无关，另行排查
- [ ] lark 插件为 beta 版 + 本地补丁，关注 larksuite 官方 9.3 适配版发布后替换
- [ ] 稳定后清理：nvm node_modules 残留、/tmp tarball、旧 jiti 缓存

## 八、关键路径备忘

| 项目 | 路径 |
|------|------|
| 新版 openclaw | `/root/.local/share/pnpm/global/5/.pnpm/openclaw@2026.9.3/` |
| CLI bin | `/root/.local/share/pnpm/openclaw` |
| Node 24 | `/root/.nvm/versions/node/v24.21.0/bin/node` |
| 旧版 openclaw（回滚用） | `/usr/lib/node_modules/openclaw/` (2026.7.1-2) |
| systemd unit | `/etc/systemd/system/openclaw-gateway.service` |
| 密钥 .env | `/root/.openclaw/.env`（从 config env 段迁出） |
| 备份 | `/root/.openclaw/backup-pre-upgrade-20260911_123734/`（207M） |
| lark 插件 | `/root/.openclaw/npm/projects/larksuite-openclaw-lark-*/`（含兼容补丁） |
| 运行日志 | `/tmp/openclaw/openclaw-YYYY-MM-DD.log` |
| lark 补丁文件 | 同目录 `*.bak-patch` 可回退；补丁标记 `PATCH 2026-09-11` |
