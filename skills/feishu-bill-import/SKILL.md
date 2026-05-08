---
name: feishu-bill-import
description: |
  飞书账单导入工具。通过飞书上传支付宝/微信/银联账单，自动解析并导入 Notion，查询历史记录，生成账单报表。

  **触发条件**：
  (1) 用户在飞书发送 CSV/XLS/XLSX 账单文件
  (2) 用户提到"导入账单"、"上传账单"、"账单历史"、"月度报表"、"账单统计"、"账单导入"
  (3) 用户想查看 Notion 账单数据统计
---

# 飞书账单导入 Skill

## 概述

将 Import_Bill_To_Notion 项目的账单导入功能集成到飞书工作流。用户在飞书发送账单文件，自动解析并导入 Notion。

## 核心流程

```
飞书发文件 → feishu_im_user_fetch_resource 下载 → 调用后端 API 导入 → 返回结果
```

## 前置条件

- Import_Bill_To_Notion 服务运行在 localhost:8000
- SQLite 数据库路径：/home/ygx/python/Import_Bill_To_Notion/data/database.sqlite

## 功能模块

### 1. 账单导入

当用户在飞书发送文件时：
1. 用 `feishu_im_user_fetch_resource` 下载文件（message_id + file_key, type="file"）
2. 保存到 /tmp/bill_import/ 目录
3. 调用 `POST http://localhost:8000/api/upload` 上传文件（multipart/form-data）
4. 解析返回结果，格式化回复用户

**API 调用方式**：
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/tmp/bill_import/xxx.csv" \
  -F "sync_type=immediate"
```

**返回格式**：
```json
{
  "success": true,
  "import_result": {
    "success": true,
    "detected_platform": "Alipay",
    "total_records": 21,
    "imported": 21,
    "updated": 0,
    "skipped": 0
  }
}
```

### 2. 账单历史查询

直接查询本地 SQLite 数据库：

```sql
SELECT ih.id, uu.original_file_name, uu.platform, 
       ih.total_records, ih.imported_records, ih.skipped_records,
       ih.status, ih.started_at
FROM import_history ih 
LEFT JOIN user_uploads uu ON ih.upload_id = uu.id 
ORDER BY ih.started_at DESC 
LIMIT 10;
```

### 3. 账单报表

基于 Notion 数据库数据生成报表。查询 SQLite 获取汇总信息，或通过 Notion API 按月统计。

**按月统计 SQL**（基于导入历史）：
```sql
SELECT 
  strftime('%Y-%m', ih.started_at) as month,
  uu.platform,
  SUM(ih.total_records) as total_records,
  SUM(ih.imported_records) as imported_records,
  COUNT(*) as upload_count
FROM import_history ih 
LEFT JOIN user_uploads uu ON ih.upload_id = uu.id 
WHERE ih.status = 'success'
GROUP BY strftime('%Y-%m', ih.started_at), uu.platform
ORDER BY month DESC;
```

### 4. 服务状态检查

```bash
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/docs
```

## 回复格式

### 导入成功
```
✅ 账单导入完成
- 平台：支付宝
- 记录数：21 条
- 成功：21 条
- 跳过：0 条
```

### 导入失败
```
❌ 导入失败：[错误原因]
请检查文件格式是否正确。
```

### 历史记录
```
📋 最近导入记录：
1. 支付宝 4月账单 - 21条 | 5/6
2. 微信 4月账单 - 85条 | 5/6
3. 支付宝 3月账单 - 16条 | 4/1
```

### 月度报表
```
📊 2026年 账单概览：
| 月份 | 支付宝 | 微信 | 总计 |
|------|--------|------|------|
| 4月  | 21条   | 85条 | 106条|
| 3月  | 16条   | 71条 | 87条 |
| 2月  | 29条   | 125条| 154条|
| 1月  | 35条   | 99条 | 134条|
```

## 注意事项

- 文件仅支持 .csv / .xls / .xlsx 格式
- 下载飞书文件需要 message_id 和 file_key
- 如果后端服务未运行，提示用户启动服务
- 飞书群聊中不自动触发导入，需用户明确要求或私聊

## 飞书文件下载流程

当用户在飞书发送账单文件时：
1. 从消息内容中提取 `file_key`（格式：`file_xxx`）和 `message_id`（格式：`om_xxx`）
2. 调用 `feishu_im_user_fetch_resource` 下载文件：
   ```json
   {
     "message_id": "om_xxx",
     "file_key": "file_xxx",
     "type": "file"
   }
   ```
3. 保存到 `/tmp/bill_import/` 目录
4. 调用后端 API 完成导入
