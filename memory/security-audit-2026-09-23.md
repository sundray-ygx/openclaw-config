# Security Audit Log 2026-09-23

## 审计:Jev + LLM Wiki 三仓库(skill 落地评估,未安装) <!-- project: github.com/sundray-ygx/openclaw-config -->

- **范围**: kerpopule/hermes-jev-skills、ajensenwaud/hermes-jev-plugin、praneybehl/llm-wiki-plugin
- **方式**: SSH 克隆到 /tmp/skill-review 全量审查(API 元数据 + 全文件树 + 关键文件逐行)
- **结果**: 全部允许进入"待批准安装"状态,均未发现高危项
- **关键结论**:
  - 三仓库均 MIT;无 curl|bash、无全局 pip/npm、无 shell rc/PATH 篡改、无自动 git push
  - kerpopule install.py: 复制+软链+config.yaml 文本编辑(自动 .bak-jev-* 备份),不碰密钥
  - 网络面: api.typesafe.ai(Jev 决策)/ models.dev(目录)/ openrouter.ai(可选)/ PyPI+HuggingFace(llm-wiki init 时固定版本)/ api.anthropic.com(仅可选 evolve runner)
  - fail-open 代码级验证: hermes-jev __init__.py:275(路由失败保持当前模型)、supervise.py(失败=继续等待)、computer-use(失败/低置信→reobserve);唯一 fail-closed 例外:注入筛选状态未知按可疑处理
  - 环境适配: 系统 python3=3.6.8 不达标(需 3.9+/3.10+);Hermes venv=3.11.15 可用;~/.hermes/bin/uv 存在;ECS HTTPS git 被封需 SSH 克隆
- **风险定级**: llm-wiki 低 / kerpopule jev 中(云端 API+付费+年轻项目) / ajensenwaud jev 中(同上+单日项目+httpx 依赖,仅作备选不推荐)
- **行动**: 未执行任何安装,等待 Boss 批准;详细方案见本次会话报告

## 补充:OpenClaw 侧落地执行(同日 10:44 指令)

- **已安装**: llm-wiki → `~/.openclaw/skills/llm-wiki/`(原生第 4 优先级 managed/shared 根,新会话自动发现);jev CLI 暂存 `~/.local/bin/jev`(bin/jev 已补丁指 Hermes venv 3.11.15,无 key)
- **试点结果**(/root/wiki-pilot): init 结构✅;手工降级 ingest 2 页✅;lint 无问题✅;BM25 检索✅;图谱 extract 2 节点 3 边✅(节点 id 格式 `concept:<slug>`/`source:<slug>`);stats✅
- **已知限制**: 语义嵌入模型下载失败(httpx Errno 101,但 curl 对 huggingface.co 与 hf-mirror.com 均 200)→ 疑 Python 栈 IPv6 解析问题,修复路径:强制 IPv4 或手动放置模型;BM25 为可用回退
- **Jev 失败路径实测**: 无 key→doctor 干净报告;伪 key→{"error":"auth_failed"};mock→reobserve;离线单测 931 例中 11 失败均为环境依赖型(无 ~/.hermes 安装/无 key),非恶意行为
- **未装**: jev SKILL.md 未进 OpenClaw skill 目录(等 key 决策); TYPESAFE_API_KEY 未配置
