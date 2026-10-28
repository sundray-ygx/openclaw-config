# 早间简报二次调优落地记录（D1–D5）

- **日期**：2026-10-28
- **脚本**：`/root/scripts/briefing/morning_briefing.py`（cron 0 8 * * * root）
- **备份**：`morning_briefing.py.bak-20261028`（A 案重构前）、`.bak-20261028-round2`（本轮改后）
- **状态**：已推送验证（Boss 飞书收到本轮卡片）

## D1 — 热榜一句话（问题 / 场景 / 用法 + 分类）
- 解析 `TTlook111/github-trending-daily` 日报的「📖 项目是干什么的」+「🌟 特别亮眼的地方」两段，交 LLM 精炼成一句 60–78 字，卡片上方单列【分类】。
- LLM 输出带校验 `_valid_refined()`（长度/中文量/语义词/自述痕迹/英数残片），校验不过重试 1 次，再不过按规则兜底（首句+亮点句，超长按标点切边界加「…」）。
- 实测 5 条里 4 条 LLM 精炼、1 条兜底，无空白、无半句。

## D2 — AI 要闻仅跟踪 openclaw + hermes-agent，附版本更新摘要
- 数据源从 GitHub REST API 改为 `releases.atom`（原 API 未认证 60 次/小时，实测很快打到 0/60 全 403）。
- 过滤 canary/rc，优先稳定版；release notes 用 LLM 翻成中文一句话（解决什么问题/新增什么能力/对使用者什么价值），失败降级为「新版本发布」。
- 双仓库各保底 1 条，插在 AI 要闻最前，不被维度配额挤掉。

## D3 — 跨源焦点聚合
- 标题+摘要做 2–4 字中文窗口 + 英文词提取（去停用词），两两共享 ≥2 关键词即同焦点，组内加权 +30 分并标「🔥N源报道」。
- 选品后做近重复合并（3-gram Jaccard ≥0.45；含早报/快讯等聚合文放宽到 0.3），同题材只留最高分那条。

## D4 — 创业维度补源
- 36氪（返回 HTML 拦截页）、虎嗅（连接失败）RSS 均已失效 → 换 **爱范儿** + **极客公园**。
- 海外维度从 BBC 中文/大纪元/阿波罗网换成 **TechCrunch / The Verge / Ars Technica**（科技创业向，贴合 PM/创业/AI 关注点）。

## D5 — 四维度各 2 条
- 维度归属用强/弱词加权（强 1.0、弱 0.35），避免「AI」万能词把全部新闻吸进 AI趋势（修前 21 条里 16 条误归类）。
- 早报类聚合文在配额选品**之前**压到 1 条；配额不满时先补未达标维度再按分兜底。
- 实测输出稳定为 2/2/2/2 × 4 维 = 8 条。

## 顺带修复
- 摘要清洗 `clean_summary()`：去图片/链接/引用符/作者行/裸 URL，避免 `> 文 | 小编`、`![Image]` 混进卡片。
- GitHub 标题双括号 `[[🦞 ...]]` 修正。
- LLM 通道坑：new-api 的 `deepseek-v4-flash` 实际路由到推理模型，`reasoning_content` 吃掉 token 预算导致 content 为空 → `max_tokens` 提到 1600 + reasoning 尾部兜底。

## 回滚
```bash
cp /root/scripts/briefing/morning_briefing.py.bak-20261028-round2 /root/scripts/briefing/morning_briefing.py
```
