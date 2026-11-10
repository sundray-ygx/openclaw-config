# NAS Hermes v0.23.0 TUI 启动故障诊断 + 回滚受阻根因分析

日期：2026-11-07 · 模式：决策门（只读核实完毕，未动 NAS 任何配置）· 诊断人：小群（ECS 会话）

---

## 〇、结论先行

**两个故障、两个独立根因、一条共同诱因线：**

| # | 故障 | 根因 | 严重度 |
|---|---|---|---|
| 1 | `hermes --tui` 报 `pm-runtime: packaged PM runtime is missing` | **install-stamp.json 的 `distribution: "docker"` 触发 v0.23.0 的 pm 打包运行时门禁**，而 tarball 手动安装根本没有 pm-runtime 目录 | 高（TUI 不可用） |
| 2 | `hermes-rollback` 报 `uv: command not found` | v0.19.0 venv 的 uv 托管 Python 3.11.15 **确实缺失**，rollback 脚本自动安装路径首次被触发，但脚本只 `export PATH="$HOME/.local/bin"`，**NAS 上 uv 不在该路径**（大概率 10-31 DSM 升级清 rootfs 时连同 uv 本体一起被清） | 高（回滚通道断） |

**共同诱因**：v0.22.4 时期（2026-10-23）为修 `vunknown` 补 stamp 时，`write_install_stamp.py` 的 `--distribution` 只接受 `docker/nix/desktop-app/apt-termux` 四个值（**没有 source/tarball 选项**），当时选了 `docker`。该组合在 v0.22.4 上只影响版本显示（当时只验证过 `--version`/gateway，**从未跑过 TUI**），到 v0.23.0 首次跑 `--tui` 才引爆——潜伏 15 天的坑。

**生产影响待核实**：TUI 报错 ≠ gateway 挂。gateway 是否已切到 v0.23.0、飞书通道是否存活，需按第三节清单核实（这是修复方向选择的关键输入）。

---

## 一、故障 1 根因链（源码级，全部对照 v0.23.0 tag 实源码）

### 1.1 调用链

```
hermes --tui
  → hermes_cli/main.py:1740 cmd_chat
  → main_tui_launch.py:254 _make_tui_argv        # TUI 前端是 Node/Ink，需 npm 工具链
  → hermes_cli/source_build.py:52 source_build_env
  → pm/client.py:195 ensure("npm")
  → pm/runtime.py:59 is_runtime()
  → pm/runtime.py:84 _resident_runtime()  ← 炸点
  → InstallError("pm-runtime", "packaged PM runtime is missing", "reinstall this application")
```

### 1.2 `_resident_runtime()` 的判定逻辑（pm/runtime.py v0.23.0 实源码）

```python
project = repo_root()                      # = Path(pm/runtime.py).resolve().parent.parent
                                           # resolve() 穿透软链 → /volume1/hermes-data/hermes-agent-v0.23.0
payload = project.parent if (project.parent / "manifest.json").is_file() else None
                                           # /volume1/hermes-data/manifest.json 不存在 → payload=None（非 desktop payload 形态）
# ↓ 走 stamp 分支：
stamp_path = install_stamp_path(project)   # = <project>/install-stamp.json
stamp = json.loads(...)                    # NAS 上此文件存在（10-23 教训后必补）
if stamp.get("distribution") not in ("nix", "docker"):
    return None                            # ← source 形态从这里放行，永远不会报本错
value = stamp.get("pmRuntime")             # tarball 安装从未写过此字段
if not isinstance(value, str) or not Path(value).is_absolute():
    raise InstallError("pm-runtime", "packaged PM runtime is missing", ...)  # ← 必炸
```

### 1.3 三方证据互证

1. **上游 Dockerfile 441-445 行**：docker 形态的 stamp 必须配 `stamp["pmRuntime"] = "/opt/hermes/pm-runtime"`，且 pm-runtime 目录由 CI `stage_manager_runtime` 构建出来。tarball 手动安装两者皆无。
2. **write_install_stamp.py 300-302 行**：`--distribution` choices 只有 `("docker", "nix", "desktop-app", "apt-termux")`——**不存在合法的 source/tarball 值**，10-23 修 vunknown 时被逼选了 docker。
3. **hermes-upgrade-assessment skill 443 行**（10-23 实战记录）：补 stamp 命令明确带着 `--distribution docker`，且当时验证项只有 `--version`（stamp 即时生效）——TUI 从未验证。

### 1.4 为什么 v0.22.4 时期没炸

v0.22.4 的 `pm/runtime.py` 有**完全相同**的门禁代码（逐行核对过 v0.22.4 tag），但 NAS 上 v0.22.4 只做过 `--version` / `sessions list` / `gateway run` 冒烟（10-22 记录），这些命令不走 `source_build_env` → `ensure("npm")` 链。**只有 TUI 启动才触发**。ECS 侧不受影响：ECS 的 0.22.4/0.19.0 是 npm bridge/pip 形态，stamp 是 postinstall 自动写的 source 形态（distribution 非 docker/nix），直接从 1.2 的放行分支通过。

---

## 二、故障 2 根因链（rollback 脚本 uv 缺失）

### 2.1 脚本行为（repo 内 hermes-version-switch.sh = NAS /usr/local/sbin/hermes-rollback 同源，10-22 三版本路由版）

```bash
target_pyvenv_home=$(grep "^home = " "$target/venv/pyvenv.cfg" ...)
# home 指向 uv 托管解释器目录，如 /root/.local/share/uv/python/cpython-3.11.15-.../bin
if [ 解释器缺失 ]; then
    echo "Python $want_ver 缺失，自动安装 (~15s)..."
    export PATH="$HOME/.local/bin:$PATH"        # ← 只找了这一个位置
    uv python install "$want_ver"               # ← uv: command not found
fi
```

### 2.2 推理链

1. 输出「Python 3.11.15 缺失」说明 v0.19.0 venv 的 `pyvenv.cfg` home 指向的 uv 托管解释器目录确实没了。
2. uv 托管 Python 装在 `/root/.local/share/uv/python/`，uv 本体（若手动装过）常在 `/root/.local/bin/` 或 `/usr/local/bin/`——两者都在 rootfs。
3. **10-31 DSM 升级清空 rootfs**（灾后恢复案卷 S1-S9）：恢复清单聚焦 ~/.hermes、软链、venv、容器，**uv 本体 + uv python 目录极可能不在恢复清单**——当时生产在 v0.19.0 且 venv 自带解释器完整（若 venv 在 /volume1 则解释器随 venv 存活……此处存疑，见待核实项 3）。
4. rollback 脚本的「自动装 Python」路径是 10-05 加的防御性增强，**首次被真正走到就是今天**——潜伏 bug：uv 不在 `~/.local/bin` 时无兜底（不找 /usr/local/bin，不找版本目录 .uv_bin）。

### 2.3 v0.19.0 解释器为何缺失的两种可能（待 NAS 核实区分）

- **可能 A**：DSM 升级清 rootfs 把 `/root/.local/share/uv/python/` 清了（v0.19.0 venv 的 home 指向 rootfs 下的 uv 目录）。
- **可能 B**：脚本检测逻辑误报（home 目录在但 `ls | grep "^python3"` 判定失败——例如权限/挂载点异常）。

---

## 三、NAS 只读核实清单（修复前置，全部无风险，请 Boss 或 NAS 侧小群执行）

```bash
# ① 生产现状（决定修复方向的黄金输入）
systemctl is-active hermes-gateway
readlink -f /usr/local/lib/hermes-agent
journalctl -u hermes-gateway --since "2026-11-05" --no-pager | grep -E "Started|FAILURE|connected to wss" | tail -20
# 飞书发条消息测通道是否活着（黄金指标）

# ② stamp 根因直接证据
cat /volume1/hermes-data/hermes-agent-v0.23.0/install-stamp.json
ls /volume1/hermes-data/hermes-agent-v0.23.0/pm-runtime 2>&1        # 预期 No such file
cat /volume1/hermes-data/hermes-agent-v0.22.4/install-stamp.json 2>/dev/null   # 对照（同款坑）

# ③ v0.19.0 venv 解释器实况（区分可能 A/B）
grep -E "^(home|version)" /volume1/hermes-data/hermes-agent-v0.19.0/venv/pyvenv.cfg
ls -la <上一行home路径>/ 2>&1 | head -5
which uv; ls -la /root/.local/bin/uv /usr/local/bin/uv 2>&1
ls /root/.local/share/uv/python/ 2>&1

# ④ v0.23.0 安装时间线 + NAS 侧记录（补全来龙去脉）
stat -c '%y %n' /volume1/hermes-data/hermes-agent-v0.23.0/install-stamp.json
grep -rn "0\.23" /root/workspace/memory/2026-11-0*.md 2>/dev/null | head -5

# ⑤ 方案乙可行性输入（node/npm 是否现成）
which node npm; node --version 2>&1
```

---

## 四、修复方案比选

### 方案甲（推荐）：先保生产回滚 v0.19.0，再从容修 v0.23.0

```
步骤 0：跑第三节核实清单（5 分钟）
步骤 1：恢复 uv + Python 3.11.15（通道二选一，见 D2）
        1a. ECS 传 uv 静态二进制 → NAS /usr/local/bin/uv，chmod +x
            （ECS 已核实现成：/usr/lib/node_modules/hermes-agent/.uv_bin/uv = uv 0.12.2 x86_64 静态，
             NAS DSM 也是 x86_64，架构匹配）
            → NAS 上 uv python install 3.11.15
            （python-build-standalone 走 GitHub 默认源大概率被 NAS TLS 重置挡；
             修不通时改用手动下载：curl 拉 tarball 解压到 /root/.local/share/uv/python/
             cpython-3.11.15-x86_64...，URL 构造参考 10-22 pm 补丁经验。失败重试 2-3 次，间歇性）
        1b. 兜底（1a 失败时用）：ECS 0.22.4 备位目录托管 Python 实测就是 3.11.15
            （/usr/lib/node_modules/hermes-agent/runtime/python/cpython-3.11-linux-x86_64-gnu/，
             /usr/local/bin/python3 --version 实测 Python 3.11.15）——整目录 tar 打包传 NAS，
            解压到 uv python 目录并对齐 v0.19.0 pyvenv.cfg 期望的 home 路径命名
步骤 2：hermes-rollback 回 v0.19.0（软链+gateway 重启）
        验证四件套：is-active / readlink / journalctl 无 FAILURE / 飞书 WebSocket connected
步骤 3：修 v0.23.0 stamp —— "distribution": "docker" 改为 "distribution": null
        （version_info.py 对非 docker/nix/desktop-app 值一律转 None，版本显示不受影响；
         runtime.py 从放行分支通过。改前留 .bak）
步骤 4：rollback 脚本加 uv 兜底路径（PATH 追加 /usr/local/bin，找不到 uv 时明确报错而非裸 command not found）
步骤 5：v0.23.0 择机重切验证 TUI（此时才可能连环撞 npm ensure/TLS 坑，按 10-22 补丁经验处理）
```

- 优点：生产恢复路径最短最稳；v0.19.0 是已验证跑过 schema 32 的版本；所有步骤可回退
- 耗时：约 30-60 分钟（含网络重试余量）

### 方案乙：就地修 v0.23.0（不回滚）

```
只改 stamp 一行 → hermes --tui 重试
```

- 优点：一步
- 缺点：修完 stamp 后 ensure("npm") 大概率继续撞——NAS 无现成 node/npm 则要 pm 装 npm，走 pm downloader，撞 NAS TLS 重置坑（v0.22.4 时期要打 curl 兜底源码补丁，v0.23.0 新目录要重打）。工作量不可控。
- **仅当核实清单显示 gateway 已稳定跑在 v0.23.0 且飞书正常、只差 TUI 时才值得选**

### 方案丙：暂不动（若 gateway 还活着且飞书通）

TUI 不可用先忍着，等窗口期从容走方案甲。不推荐久拖——TUI 是 NAS 主力交互面。

---

## 五、决策点（待 Boss 批示）

| # | 决策项 | 我的建议 |
|---|---|---|
| D1 | 修复方向 | ✅ 方案甲（先回滚保生产）。若核实显示 gateway 已在 v0.23.0 稳定+飞书通，可改走乙省一步 |
| D2 | uv/Python 恢复通道 | ✅ 1a（ECS 传 uv 二进制 + tuna 镜像装 3.11.15）；失败兜底 1b |
| D3 | stamp 修复口径 | ✅ distribution 置 null（保留 commit/版本字段）；同步把「tarball 安装禁用 docker distribution」教训固化进 hermes-upgrade-assessment skill |
| D4 | 执行人 | ✅ Boss 在 NAS shell 逐条跑（我提供每步完整命令+预期输出），或 NAS 侧小群会话执行、ECS 侧出报告 |
| D5 | 附带事项 | WebDAV 通道（ygxpro.online 域名今天从 ECS 解析失败、IP 直连 5006 超时）是否要顺手排查——与本案无关，但影响 ECS→NAS 传文件的 1a 通道，若 WebDAV 不通则改用 GitHub 中转或 Boss 手动 U 盘/scp |

批复格式：回复「批准 D1-D5」或指定调整项。

---

## 六、遗留教训（待固化）

1. **tarball 手动安装的 stamp 禁用 `--distribution docker`**——write_install_stamp.py 没有合法 source 值是上游设计缺口，手改 JSON 置 null 是正解。docker/nix distribution 是"承诺本目录有打包运行时"的强声明，不是随手的版本标签。
2. **补 stamp 后必须冒烟的命令清单要覆盖实际使用面**——10-23 验证了 `--version` 没验证 TUI，15 天后爆雷。
3. **rollback 脚本的依赖自愈路径要真实验证过一次**——「自动安装」写了两个月，首次触发就死在 uv 不在预设 PATH。
4. DSM 灾后恢复清单应包含 uv 本体 + uv python 目录（若生产依赖 uv 托管解释器）。
