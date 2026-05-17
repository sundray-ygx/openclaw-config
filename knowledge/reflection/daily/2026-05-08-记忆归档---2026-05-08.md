---
{
  "source": "memory",
  "date": "2026-05-08",
  "tags": [
    "tech",
    "lessons"
  ],
  "created_at": "2026-05-09T05:00:12.486930",
  "status": "pending_review"
}
---

# 记忆归档 - 2026-05-08

**自动标签**: tech, lessons

**建议归档位置**:
- tech
- lessons

---

## 原始内容

# 2026-05-08 日志

### [PROJECT:OpenClaw] 系统性切换至 zai/glm-5

- **结论**: 已完成系统性替换，删除百炼 API key 相关内容，所有 AI 调用统一使用 zai/glm-5
- **修改文件**:
  1. `config/openclaw.json`
     - 删除整个 bailian provider 配置
     - 设置默认模型为 `zai/glm-5`
     - 更新所有 agent 模型为 `zai/glm-5`
  2. `scripts/daily/daily_reflection.py`
     - 删除百炼 API key 读取逻辑
     - 改为通过 OpenClaw CLI 调用 zai/glm-5
  3. `scripts/daily/weekly_review.py`
     - 删除百炼 API 配置加载逻辑
     - 改为通过 OpenClaw CLI 调用 zai/glm-5
  4. `scripts/send_todo_report.py`
     - 删除"百炼 API 配额确认"部分
  5. `scripts/send_system_status_report.py`
     - 删除"百炼 API 配额确认"部分
  6. `memory/2026-04-05.md`
     - 更新历史记录，将百炼 API 问题改为 zai/glm-5 解决方案
  7. `MEMORY.md`
     - 更新最近日志和关键事项
- **业务影响**: 无影响，所有现有业务正常运行
- **标签**: #zai-glm5 #api-migration #config-cleanup

### [PROJECT:feishu-bill-import] 飞书账单导入 Skill + 历年财务报表
- **结论**: 完成 feishu-bill-import Skill 创建，支持飞书上传账单→导入 Notion、历史查询、报表生成。同步生成 2022-2026 历年财务对比报表（HTML+PNG）
- **文件变更**:
  - `skills/feishu-bill-import/` — 新建 Skill（SKILL.md + scripts/bill_api.sh + scripts/bill_report.py + references/api_guide.md）
  - `knowledge/finance/个人财务报表2022-2026.html` — 交互式 ECharts 报表
  - `knowledge/finance/财务趋势总览.png` — 趋势图
  - `knowledge/finance/支出结构分析.png` — 支出结构图
- **教训**: 服务器无中文字体导致 matplotlib 乱码，需安装 wqy-microhei-fonts
- **关键发现**: 2023年4月提前还贷 ¥301,164；2025年8月提前还贷 ¥501,238；理财通属于资产转移不计入收支
- **标签**: #finance #bill-import #notion #report


---

## 人工整理说明

1. 阅读以上内容
2. 确认标签是否准确
3. 移动到对应目录: `knowledge/{category}/`
4. 重命名为: `YYYY-MM-DD-title.md`
5. 删除此 inbox 文件
