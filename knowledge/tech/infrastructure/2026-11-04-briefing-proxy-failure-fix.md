# 2026-11-04 早间简报代理故障根因与修复归档

## 一句话结论
机场（sub987.top）数据面入口自 11-01 起逐渐瘫痪，11-04 简报时段全断 → 简报里走 socks5 1080 的 GitHub 双仓库 + GitHub 热榜两个板块静默缺失（国内 RSS 直连不受影响）。

## 根因证据链
1. 日志归因：08:00 运行中双仓库/热榜全部 `curl rc=7`（SOCKS 连接失败），国内 RSS/LLM 全部成功 → 断点在代理
2. 分层验证：1080 端口活着（docker-proxy 监听）、sing-box 容器 Up 6 天 → 入站正常；经 1080 探 GitHub 报 `SOCKS connection (1) general failure` → sing-box 向上游建连失败
3. sing-box 日志实锤：简报时刻 `dial tcp 13.196.197.238:35675: i/o timeout` ——机场入口 TCP 超时
4. 全网测试：84 节点只解析到 3 个入口 IP（AWS SG/US/JP）；所有 anytls 端口 TIMEOUT，Clash API 显示 10 区域 0 存活
5. 控制面 vs 数据面分离：订阅服务器 HTTP 200、节点列表与现配置一致 → 刷新订阅无用

## 修复内容（F1+F2+F3 全做，Boss 批准）

### F1｜脚本多源回退（P0，治本于简报）
- 新增 `_fetch_url_multi()` 三级回退：① socks5 1080 主路 → ② gh-proxy.com 镜像直连 → ③ jsDelivr CDN（仅热榜仓库）
- `get_repo_updates()` 和 `fetch_trending_report()` 都改用该回退函数
- py3.6 兼容（f-string 无 =、无 walrus、无 3.7+ 特性）
- 回退链成功时日志打印 `[注] ... 经回退链 [mirror|cdn] 取得`

### F2｜代理看门狗（P1，治未来）
- `heartbeat_syscheck.sh` 新增第 7 项：代理链路探活
- 探活方式：`curl --socks5-hostname 127.0.0.1:1080 https://github.com/` 拿到真实 HTTP 200/301/302 才算通（仅 TCP 连 1080 不代表上游机场通）
- 状态文件：`/tmp/heartbeat-syscheck/proxy-dead.count`（累计死亡小时数）+ `proxy-down.state`（告警去抖）
- 行为：连续死 ≥6h → 推红卡「⚠️ 代理链路故障」；1h 内不重复；恢复瞬间推绿卡「✅ 代理链路已恢复」并清零
- .state 后缀不被末尾 `rm -f *.last` 清除 → 去抖可靠

### F3｜卡片缺席注记（P2，透明化）
- 双仓库缺席：`本期缺席：数据源不可达（代理与镜像均未取到，详见日志归因）`
- 热榜缺席：`本期缺席：数据源不可达（代理与镜像均未取到）`
- 双仓库回退成功时，标题行追加 `⚠️ 经镜像回退取得(机场代理不通)`

## 验证
- ✅ py3.6 `py_compile` 通过
- ✅ bash `-n` 语法通过
- ✅ cron 同款 `env -i + /usr/bin/python3` 环境下单测：双仓库各 1 条、热榜 3 条解析正常
- ✅ 真实发送验证：移防重发标记后重发简报卡，双板块正常出现（你收到了当日第二张卡）
- ✅ F2 看门狗 fake-curl 模拟：6h 告警 / 7-8h 去抖静默 / 恢复绿卡 / 恢复后不重复 — 全部符合预期
- ✅ 真实告警卡已推送（测试期间推了一次红卡+恢复卡）

## 文件清单
- 修改：`/root/scripts/briefing/morning_briefing.py`（新增 +40 行 `_fetch_url_multi`；改 `get_repo_updates` `fetch_trending_report` `generate_briefing` 双仓库/热榜渲染）
- 修改：`/root/scripts/utils/heartbeat_syscheck.sh`（新增 35 行代理看门狗 + 探活函数）
- 备份：`.bak-20261104` × 2
- 防重发标记备份：`/root/mail-reports/briefing_sent.json.bak-20261104-verify`

## 不做的事（仍有效）
- 不重启/不改 sing-box 配置（容器健康，问题在上游机场）
- 不刷新订阅（域名没换、入口不通，刷新无用）
- 不改简报解释器、不动 1080/9090 端口绑定
- 不删除代理主路（镜像只是回退，机场恢复后自动切回）

## 后续观察
- 机场入口何时恢复未知（取决于服务商），F1+F2 确保断了也有内容、断了也知道
- 镜像 gh-proxy.com 和 jsDelivr CDN 为第三方公益服务，若未来也被封，需再加镜像节点（回退链函数已设计为可扩展）
