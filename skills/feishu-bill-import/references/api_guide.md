# Import_Bill_To_Notion API 参考

## 服务信息

- 地址：http://localhost:8000
- 项目目录：/home/ygx/python/Import_Bill_To_Notion/
- 数据库：/home/ygx/python/Import_Bill_To_Notion/data/database.sqlite
- 模式：多租户（但 /api/upload 路由无需认证）

## 无认证接口

### POST /api/upload
上传并导入账单文件。
```
Content-Type: multipart/form-data
- file: 账单文件
- platform: (可选) alipay/wechat/unionpay
- sync_type: immediate | scheduled
```

### GET /api/upload/files
获取已上传文件列表。

### GET /api/upload/service-info
获取服务状态信息。

### GET /api/upload/logs
获取服务日志。

## 数据库表结构

### import_history
| 字段 | 说明 |
|------|------|
| id | 主键 |
| user_id | 用户ID |
| upload_id | 关联上传记录 |
| total_records | 总记录数 |
| imported_records | 已导入 |
| skipped_records | 跳过 |
| failed_records | 失败 |
| status | 状态 (success/failed) |
| started_at | 开始时间 |
| completed_at | 完成时间 |

### user_uploads
| 字段 | 说明 |
|------|------|
| id | 主键 |
| user_id | 用户ID |
| file_name | 存储文件名 |
| original_file_name | 原始文件名 |
| file_path | 文件路径 |
| file_size | 文件大小 |
| platform | 平台 (Alipay/WeChatPay/UnionPay) |
| status | 状态 |
| created_at | 创建时间 |

## Notion 数据库结构

### 收入/支出数据库
- Name (标题) - 记录名称
- Price (数字) - 金额
- Date (日期) - 交易日期
- Category (选择) - 分类
- Counterparty (富文本) - 交易对方
- Remarks (富文本) - 备注
- Income Expense (选择) - 收/支
- Payment Method (选择) - 支付方式
- From (选择) - 平台来源

## 支持的账单格式
- 支付宝 CSV
- 微信支付 CSV/XLS
- 银联 CSV
