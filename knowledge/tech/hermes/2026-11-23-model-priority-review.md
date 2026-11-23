# Hermes 模型选择优先级巡检与调整规划（2026-11-23）

> 状态：待 Boss 决策（决策点 D1-D4）
> 性质：只读巡检已完成，未做任何变更

## 一、当前配置核实（只读取证）

### 1. default profile（对话主力，即本会话）

**主模型**（`model:` 块）：

| 项 | 值 |
|---|---|
| provider | custom（new-api 网关） |
| base_url | https://api.ygxpro.online/v1 |
| default | **glm-5.3** |
| context_length | 1048576（1M） |

**fallback_providers 优先级**（列表顺序 = 切换顺序，主模型失败后从 1 开始依次尝试）：

| 序 | 模型 | 家族 | 定位 |
|---|---|---|---|
| F1 | doubao-seed-2-0-pro-260215 | 豆包 | 2.0 旗舰 |
| F2 | glm-5.3-flash | GLM | 5.3 快速版 |
| F3 | deepseek-v4-flash | DS | v4 快速版 |
| F4 | deepseek-v4-pro | DS | v4 旗舰 |

触发条件（0.19.0 内置）：429（限流）/ 529（过载）/ 503（服务错误）/ 连接失败。

### 2. scheduler profile（推送通道）

- 主模型：同 default（glm-5.3，1M ctx）
- fallback 链（3 个）：**doubao-seed-2-0-pro-260215 → deepseek-v4-flash → deepseek-v4-pro**
- 与 default 差异：**缺 F2 glm-5.3-flash**，其余一致

### 3. 运行环境

- 生产网关 PID 1122225 自 11-04 跑 **v0.19.0**，`gateway.multiplex_profiles: true`（一个网关多路复用两个 profile）
- 当前 fallback 链中 4 个模型均在网关可用清单内，无死链

## 二、网关可用模型清单（/v1/models 实测，14 个）

```
deepseek-flash
deepseek-v4-flash
deepseek-v4-flash-ga-260731      ← GA 稳定快照，未入链
deepseek-v4-flash-vision-exp      ← 视觉实验版
deepseek-v4-pro
deepseek-v4-pro-ga-260813         ← GA 稳定快照，未入链
doubao-seed-2-0-code-preview-260215  ← coding 专用，未入链
doubao-seed-2-0-pro-260215        ← 现任F1
doubao-seed-2-1-turbo-260628      ← 豆包2.1 turbo（更新一代），未入链
doubao-seed-evolving
glm-4.6v                          ← 视觉，未入链
glm-5-3-flash-260828              ← glm flash 日期快照，未入链
glm-5.3                           ← 现任主力
glm-5.3-flash                     ← 现任F2
```

## 三、观察点（我的判断）

1. **F2 家族分散缺陷**：glm-5.3 故障时，F2 glm-5.3-flash 大概率同家族连坐（同一上游），白白多一跳切换延迟。当前链的家族次序是 豆包→GLM→DS→DS，F2 是链上唯一"可能与主模型同生共死"的位。
2. **GA 快照未对齐**：fallback 用的 deepseek-v4-pro / deepseek-v4-flash 均有更新的 GA 稳定快照（ga-260813 / ga-260731），当前用的是无日期后缀的浮动名——浮动名可能指向滚动升级版，行为不可钉死。
3. **豆包有更新一代**：doubao-seed-2-1-turbo-260628（6-28 快照）比现任 F1 的 2-0-pro（2-15）新一代；turbo 定位快，适合当"顶班第一顺位"。
4. **双 profile 不一致**：scheduler 少一个 fallback 层，推送通道容错薄一层。

## 四、候选方案（供决策）

### 方案A：保守对齐（最小变更）
仅把 DS 系换成 GA 快照，顺序结构不动：
```
doubao-seed-2-0-pro-260215 → deepseek-v4-pro-ga-260813 → glm-5.3-flash → deepseek-v4-flash-ga-260731
```

### 方案B：家族分散重构（我的推荐）
去掉 GLM 同家族连坐位，GA 对齐，豆包上新一代：
```
doubao-seed-2-1-turbo-260628 → deepseek-v4-pro-ga-260813 → deepseek-v4-flash-ga-260731 → glm-5.3-flash
```
理由：glm-5.3 挂 → 豆包 2.1 turbo 顶班（新一代+快）；豆包也挂 → DS GA 旗舰；再挂 → DS flash；GLM flash 殿后（仅当 DS 全挂而 GLM flash 单独存活时用）。

### 方案C：Boss 自定顺序
基于上面 14 个可用模型清单任意指定 4-5 个及顺序（也可含 glm-5-3-flash-260828、doubao-seed-evolving 等）。

### scheduler 同步策略
- S1：与 default 完全一致（补齐同一链）
- S2：保持少一层（现状）

## 七、Boss 决策（2026-11-23 第二轮）与最终方案（待批 D1-D4）

Boss 口述：DS 系换最新 GA、豆包换 2.1-turbo、**主模型切豆包 2.1-turbo**、glm 次之、DS 系殿后。

**目标配置（两个 profile）**：

| 项 | 现值 | 目标值 |
|---|---|---|
| model.default | glm-5.3 | **doubao-seed-2-1-turbo-260628** |
| fallback F1 | doubao-seed-2-0-pro-260215 | **glm-5.3** |
| fallback F2 | glm-5.3-flash | **deepseek-v4-pro-ga-260813** |
| fallback F3 | deepseek-v4-flash | **deepseek-v4-flash-ga-260731** |
| fallback F4 | deepseek-v4-pro | （删除，链缩为 3 层） |

**实测背书**：四模型经 new-api 网关 chat/completions 全部可路由（豆包热态 1.3-2.9s；DS-pro-ga 需放开 max_tokens，reasoning 占额度，hermes 默认额度充足无碍）。

**已排雷**：
- 05:00 pull.sh 只 rsync skills/，**不碰 /root/.hermes/config.yaml**——本地改动不会被次日同步覆盖（repo 是 NAS 镜像，ECS 纯消费者不回提交）
- scheduler profile 写法：`HERMES_HOME=/root/.hermes/profiles/scheduler hermes config set ...`
- `hermes config set` 标量键（model.default）可靠；fallback_providers 为 dict 列表，CLI 传 JSON 是否保结构待实测，失败则走 Python 定段文本替换（不 yaml 全量重写，防丢注释）+ .bak 备份 + safe_load 校验
- 本 TUI 会话（09:17 起）固化 glm-5.3，改后本会话不切换，属预期；网关新会话是否即时生效看 gateway 代码加载时机，执行阶段核实

**遗留决策点**：
- D1：链序确认（表 above）
- D2：context_length——豆包 2.1-turbo 实标 ctx 网关未暴露。建议 262144 保守值（配 1M 而实标 256K 的话，超长会话会撞 400，而 fallback 不吃 400→会话直接报错）；或 Boss 给准数；或维持 1M 赌它支持
- D3：scheduler 同步（默认同步）
- D4：网关生效验证——若 gateway 进程缓存配置（11-04 起），需重启窗口才对飞书流量生效，届时另批

## 八、执行步骤（批准后）

1. 双 profile config.yaml 各留 .bak-20261123
2. default：set model.default → set model.context_length（按 D2）→ fallback_providers（CLI JSON 实测→不行则定段替换）
3. scheduler：HERMES_HOME 指向后同法
4. 校验：双文件 yaml.safe_load + config get 回读 + 模型名逐字核对（幻字纪律）
5. 实弹：`hermes chat -q` 一次性进程打新主模型；`hermes doctor`
6. 网关生效核实：查 gateway.py 配置加载时机；如缓存→报告+重启窗口另批
7. 结果回写本报告；NAS 侧网关（另一部署）不在本次范围，如需同步另开任务

## 九、执行结果（2026-11-23 10:02-10:15，全部完成）

| 步骤 | 结果 |
|---|---|
| 备份 | 双 profile config.yaml.bak-20261123 ✓ |
| default 主模型 | config set → 回读 doubao-seed-2-1-turbo-260628 ✓ |
| default fallback | **踩坑**：CLI 传 JSON 存成带引号字符串（YAML list 结构破坏）→ 预案B Python 定段文本替换 → safe_load 校验 3 层链序正确 ✓ |
| scheduler | HERMES_HOME 指定后同法全过 ✓（旧链 豆包2.0-pro→DS浮动名×2 已整体换出） |
| ctx | 双 profile 维持 1048576 ✓ |
| 实弹 | `hermes chat -q` 会话 20261123_100200_9280cd，state.db session_model_usage 实证 **doubao-seed-2-1-turbo-260628 服务** ✓ |
| doctor | 无模型/fallback 相关报错 ✓ |
| 网关生效 | config.py mtime 缓存自动失效（stat 每次调用）→ **无需重启**，网关新会话自动取新配置 ✓ |
| 覆盖风险 | 05:00 pull.sh 只 rsync skills/，不碰 config.yaml ✓ |

**已知边界**：本 TUI 会话（09:17 起）固化 glm-5.3 属预期，Boss 下次开新会话即走豆包 2.1-turbo。飞书 scheduler 推送会话若为存量长会话，同样在会话轮转后生效。

**教训沉淀**（已入 memory）：0.19.0 `hermes config set` 传 JSON 列表值会存成带引号字符串，fallback_providers 类列表键必须定段文本替换。
