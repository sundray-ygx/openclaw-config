# ECS 备份修复任务结果（nas-ecs-fix-task-20261110.md · 2026-11-10 执行回写）

> 执行：ECS Hermes。git 提交：见文末。全程 diff+验证证据在下。
> ⚠️ 前置说明：本任务书与 ECS 侧当日更早批次（Boss 会话直批 D1-D4）高度重叠，差异部分已按任务书对齐加固。

## O1 假删除修复（nas_backup.sh）

**改动**：
1. href 提取（L429-431）：`grep -oP '(?<=<href>)...'`（按行、被 `<D:href>` 前缀击穿）→ `tr '\n' ' ' | grep -oP '(?<=href>)[^<>]+(?=</)'`（压单段+href> 锚定，兼容前缀变体与跨行——任务书参考的 NAS 侧 re.findall 同思路）
2. DELETE 校验（L433-440）：`curl -o /dev/null` 吞码 → `-w "%{http_code}"` 逐项捕获，204/200/201/404=成功，403/405/207=失败
3. 计数如实（L426,451）：deleted_count 只数校验通过项；新增 delete_fail 计数
4. 失败告警+退出码（L453-457）：失败>0 → 飞书卡 + **exit 1**
5. 版本号 v5.0 → v5.1（backup-info.json）

**验证**（2026-11-10 12:06 手动全链真跑，非干跑）：
- 解析实测：20260322 真实 DSM XML → 新逻辑提取 9/9 项 ✓；旧逻辑 0 项（bug 根因复现）✓
- 真跑日志：清理段对 3 散目录 36→14 项 DELETE 全部如实报失败（403/207），`清理完成: 删除 0 项, 失败 14 项`，exit=1 ✓ 假绿消除
- **⚠️ 任务书预期「散目录被真删」未能达成——非代码问题**：下午 16 项对照实验实锤 DSM 对这批老文件返回 403（同账号删自建文件正常 204），属属主/ACL 锁。ECS 侧已到边界，**需 NAS 侧本地删除**：`rm -rf /volume1/aliyun_backup/server-backup/{20260322,20260509,20260512}`（或 File Station）。删除前每晚清理将如实报失败推飞书——诚实遥测非噪声，NAS 侧删后自愈。
- 上传链：65M/2m55s/HTTP 204/远程 HEAD 200 ✓

## O2 v5.1 扩范围

**改动**（11 项 → 15 项）：新增 10b-hermes-default（default state.db sqlite3 .backup 一致性快照）、11b-ecs-misc（cron.d tar/nginx.conf/daemon.json/acme tar/**.ssh tar**/docker-images digest 版/container-meta×2）、11-systemd 2→6 unit。
**验证**（12:06 真跑 tar 下载解包逐项核）：
- [1] 10b state.db 59,817,984 bytes，`PRAGMA integrity_check` = **ok** ✓
- [2] ssh.tar.gz 含 id_rsa/config/known_hosts/authorized_keys 全 6 件 ✓
- [3] acme.sh.tar.gz ✓ [4] systemd 6 unit 齐 ✓ [5] cron.d 4 文件含 hermes-config-pull ✓ [6] nginx.conf 2198B ✓
- [7] docker-images.txt 含 digest（sing-box@sha256:0788ffbd…/new-api@sha256:2e2f2306…/v1.11.3 备胎）✓
- [8] backup-info.json `backup_version: 5.1` ✓
- 顶层结构：01~11b + 10b + backup-info.json 共 14 目录/文件 ✓

## O3 恢复 runbook

- ECS 归档：`knowledge/tech/infrastructure/2026-11-10-ecs-restore-runbook.md`（118 行，Phase 0-4：frps 自举根→tar 拉取→配置→容器/hermes 重建→验证矩阵；含 digest 钉版本基线、npm 壳坑引用、双 profile 验证纪律、缺口声明表）
- NAS 协作区：已 PUT `/aliyun_backup/nas-recovery/ecs-restore-runbook.md`（HTTP 201）✓

## O4 github-sync 新文件盲区

**改动**：sync-to-github.sh 变更检测 `git diff --quiet && git diff --cached --quiet` → `[ -z "$(git status --porcelain)" ]`
**验证**：
- 沙箱对照：未跟踪文件场景旧逻辑漏检/新逻辑检出/干净树不误报 ✓
- 生产实锤：修复后首跑（7461d4e）将 11-07 起滞留 5 个新文件全部补推 GitHub（9002a0f→7461d4e）✓；工作区干净 ✓

## 清理项

- `/root/hermes-backup-20261022-0813.tar.gz`（446,216,818 bytes）已删，释放 426M（df 33%→77% 可用根盘水位不变，/dev/vda3 40G 29G 用）
  实际是 / 77% used（删前同值——426M 对 40G 盘占比 1%，df 取整不可见）。清单留档：27,095 条目，顶层 .hermes/（skills 为主）+ workspace 类，内容已被 git+每日 tar 覆盖（审计报告 P5 结论）。
- NAS 侧待办（见 O1）：本地删 3 散目录。

## git 提交

- 7461d4e（11-10 下午批次：v5.1 主体+sync 修复+审计三件套+runbook v1）
- 本次任务书对齐批次（O1 加固跨行解析/exit 1、O2 .ssh+digest、runbook digest 段）：commit 见 workspace 仓 log（紧随 7461d4e）

## 结论

任务书 4 修复项+1 清理项全部完成；O1 验证项「散目录真删」受 DSM 403 权限锁阻断（ECS 侧边界），已给 NAS 侧命令。v5.1 全链真跑验证通过，今晚 02:00 cron 首个生产运行预期：备份成功卡 + 清理失败卡（3 散目录 403，如实遥测）。
