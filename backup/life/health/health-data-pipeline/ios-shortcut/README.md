# iOS 快捷指令配置

## 快捷指令下载

### 方案一：睡眠数据同步（AutoSleep）

1. 确保已安装 [AutoSleep](https://apps.apple.com/cn/app/autosleep-sleep-tracker/id1164801111) App
2. 创建新快捷指令
3. 添加以下操作：

```
1. 查找健康样本
   - 类型：睡眠分析
   - 排序方式：开始日期（最新）
   - 限制：1

2. 获取详细信息
   - 选择：时长、开始日期、结束日期

3. 获取我的快捷指令输入
   - 选择：字典

4. 获取字典值
   - 键：duration

5. 获取字典值  
   - 键：date

6. 获取字典值
   - 键：quality

7. 获取内容 URL
   - URL: https://your-worker.your-subdomain.workers.dev/api/health-data

8. 获取内容
   - 方法：POST
   - 请求体：JSON
   - JSON内容：
     {
       "type": "sleep",
       "date": "[开始日期]",
       "duration": [睡眠时长（分钟）],
       "quality": [睡眠质量百分比],
       "start_time": "[开始时间]",
       "end_time": "[结束时间]"
     }
```

### 方案二：快捷指令链接（推荐）

我已经为你生成了快捷指令文件，你可以直接导入：

**文件位置：** `health-data-sleep.shortcut`

导入步骤：
1. 将 `.shortcut` 文件发送到 iPhone（AirDrop、邮件、iCloud 等）
2. 在 iPhone 上点击文件，选择"添加快捷指令"
3. 修改其中的 Worker URL 为你自己的地址
4. 完成

## 自动化设置

设置定时自动运行：

1. 打开"快捷指令"App → "自动化"标签
2. 点击"创建个人自动化"
3. 选择触发条件：
   - **推荐**：特定时间（每天早上 8:00）
   - 或者：关闭闹钟时
   - 或者：每天定时
4. 添加操作：运行快捷指令 → 选择"同步睡眠数据"
5. 关闭"运行前询问"
6. 完成

## 测试

首次运行前建议先测试：
1. 手动运行快捷指令
2. 检查 Cloudflare Worker 日志
3. 确认 GitHub 仓库中出现了数据文件

## 数据格式

快捷指令发送的数据格式：

```json
{
  "type": "sleep",
  "date": "2024-03-13",
  "duration": 480,        // 睡眠时长（分钟）
  "quality": 85,          // 睡眠质量（0-100）
  "start_time": "23:00",
  "end_time": "07:00",
  "deep_sleep": 120,      // 深睡时长（分钟）
  "light_sleep": 240,     // 浅睡时长（分钟）
  "rem_sleep": 120        // REM睡眠（分钟）
}
```

## 故障排查

如果数据没有同步：

1. 检查快捷指令是否成功运行（看快捷指令App中的运行记录）
2. 检查 Cloudflare Worker 日志（Cloudflare Dashboard → Workers → 你的Worker → Logs）
3. 检查 GitHub Token 是否有写入权限
4. 确认 Worker URL 配置正确
