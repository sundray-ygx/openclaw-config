# HEARTBEAT.md — 心跳清单（2026-10-06 起）

## 网关内存告警口径（硬规则）
- 用**进程 RSS**（`ps -o rss= -p $(pgrep -f openclaw-gateway | head -1)`），阈值 **750M** 才报
- ⚠️ **勿用 cgroup `MemoryCurrent`**——它含可回收 page cache，会把 68% 真实占用报成 94% 假警报（2026-10-06 诊断结论）
- 该检查已内建在 `scripts/utils/heartbeat_syscheck.sh`（每小时 cron 零 LLM），心跳 turn **不要重复做**内存/磁盘/swap 检查（AGENTS.md 硬规则）

## 重启策略（2026-10-06 起）
- gateway 由 systemd timer **Mon/Thu 04:30** 定期重启（原每日，诊断确认无泄漏后降频）
- 04:30 重启后 1 小时内 RSS 冲高（启动潮 ~800M）属正常，勿告警
