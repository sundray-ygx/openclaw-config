#!/bin/bash
# 账单导入 API 封装脚本
# 用法: bill_api.sh upload <file_path> [platform]
#       bill_api.sh history [limit]
#       bill_api.sh report [year]
#       bill_api.sh service-info

API_BASE="http://localhost:8000"
DB_PATH="/home/ygx/python/Import_Bill_To_Notion/data/database.sqlite"
PY_QUERY="import sqlite3,json,sys; db=sqlite3.connect('$DB_PATH'); db.row_factory=sqlite3.Row; cur=db.execute(sys.argv[1]); print(json.dumps([dict(r) for r in cur.fetchall()]))"

case "$1" in
  upload)
    FILE_PATH="$2"
    PLATFORM="${3:-}"
    if [ ! -f "$FILE_PATH" ]; then
      echo '{"success": false, "error": "文件不存在"}'
      exit 1
    fi
    if [ -n "$PLATFORM" ]; then
      curl -s -X POST "$API_BASE/api/upload" \
        -F "file=@$FILE_PATH" \
        -F "platform=$PLATFORM" \
        -F "sync_type=immediate"
    else
      curl -s -X POST "$API_BASE/api/upload" \
        -F "file=@$FILE_PATH" \
        -F "sync_type=immediate"
    fi
    ;;
  history)
    LIMIT="${2:-10}"
    python3 -c "$PY_QUERY" "
      SELECT ih.id, uu.original_file_name, uu.platform,
             ih.total_records, ih.imported_records, ih.skipped_records,
             ih.status, ih.started_at
      FROM import_history ih 
      LEFT JOIN user_uploads uu ON ih.upload_id = uu.id 
      ORDER BY ih.started_at DESC 
      LIMIT $LIMIT"
    ;;
  report)
    YEAR="${2:-$(date +%Y)}"
    python3 -c "$PY_QUERY" "
      SELECT 
        strftime('%m', ih.started_at) as month,
        uu.platform,
        SUM(ih.total_records) as total_records,
        SUM(ih.imported_records) as imported_records,
        COUNT(*) as upload_count
      FROM import_history ih 
      LEFT JOIN user_uploads uu ON ih.upload_id = uu.id 
      WHERE ih.status = 'success' AND strftime('%Y', ih.started_at) = '$YEAR'
      GROUP BY strftime('%Y-%m', ih.started_at), uu.platform
      ORDER BY month DESC"
    ;;
  status)
    curl -s -o /dev/null -w '%{http_code}' "$API_BASE/docs"
    ;;
  *)
    echo "用法: bill_api.sh {upload|history|report|status} [args]"
    exit 1
    ;;
esac
