#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel数据提取工具
直接解析Excel XML，提取数据并生成Markdown文档
"""

import zipfile
import xml.etree.ElementTree as ET
import re
from datetime import datetime
import os

def get_sheet_names(xlsx_path):
    """获取所有sheet名称"""
    with zipfile.ZipFile(xlsx_path) as z:
        with z.open('xl/workbook.xml') as f:
            tree = ET.parse(f)
            sheets = []
            for sheet in tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet'):
                sheet_name = sheet.get('name', '')
                sheets.append(sheet_name)
            return sheets

def extract_sheet_data(xlsx_path, sheet_index=0):
    """直接解析Excel的XML，提取数据"""
    with zipfile.ZipFile(xlsx_path) as z:
        # 读取共享字符串
        shared_strings = []
        try:
            with z.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                for si in tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                    t = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                    if t is not None:
                        shared_strings.append(t.text if t.text else '')
        except:
            pass

        # 读取worksheet数据
        worksheet_path = f'xl/worksheets/sheet{sheet_index+1}.xml'
        with z.open(worksheet_path) as f:
            tree = ET.parse(f)
            rows = []
            for row in tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
                # 获取行号
                r_num = int(row.get('r', 0))

                # 处理每个单元格
                cells = {}
                for cell in row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                    # 获取单元格位置（如A1, B2）
                    cell_ref = cell.get('r', '')
                    # 提取列字母
                    col_match = re.match(r'([A-Z]+)', cell_ref)
                    if col_match:
                        col_letter = col_match.group(1)
                        # 转换为列索引（A=0, B=1, ...）
                        col_idx = 0
                        for c in col_letter:
                            col_idx = col_idx * 26 + (ord(c) - ord('A') + 1)
                        col_idx -= 1
                    else:
                        col_idx = 0

                    # 获取单元格值
                    cell_value = ''
                    v = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                    if v is not None:
                        cell_type = cell.get('t')
                        if cell_type == 's':  # 共享字符串
                            idx = int(v.text)
                            if idx < len(shared_strings):
                                cell_value = shared_strings[idx]
                        else:
                            cell_value = v.text if v.text else ''

                    cells[col_idx] = cell_value

                # 按列索引排序，确保顺序正确
                max_col = max(cells.keys()) if cells else 0
                row_data = [cells.get(i, '') for i in range(max_col + 1)]
                rows.append(row_data)
            return rows

def rows_to_markdown(rows, sheet_name, source_file):
    """将行数据转换为Markdown格式"""

    # 文档头部
    md_content = f"""# {sheet_name}

> **数据来源**：{source_file}
> **提取时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> **版本**：V2.0（基于5月7日更新版本）

---

"""

    # 如果数据为空
    if not rows:
        md_content += "*此表格无数据*\n"
        return md_content

    # 尝试识别标题行（通常是第一行非空行）
    header_row = None
    header_index = 0
    for i, row in enumerate(rows):
        if any(cell.strip() for cell in row):
            header_row = row
            header_index = i
            break

    if header_row is None:
        md_content += "*无法识别标题行*\n"
        return md_content

    # 生成Markdown表格
    max_cols = max(len(row) for row in rows)

    # 表头
    md_content += "| " + " | ".join(header_row) + " |\n"
    md_content += "| " + " | ".join(["---"] * len(header_row)) + " |\n"

    # 数据行
    for i, row in enumerate(rows[header_index+1:], start=header_index+1):
        # 填充空单元格，确保所有行列数一致
        while len(row) < max_cols:
            row.append('')

        # 跳过全空行
        if not any(cell.strip() for cell in row):
            continue

        md_content += "| " + " | ".join(row) + " |\n"

    return md_content

def extract_to_markdown(xlsx_path, output_dir):
    """提取Excel所有Sheet到Markdown文件"""
    sheet_names = get_sheet_names(xlsx_path)

    os.makedirs(output_dir, exist_ok=True)

    results = []
    for i, sheet_name in enumerate(sheet_names):
        print(f"正在提取 Sheet {i+1}/{len(sheet_names)}: {sheet_name}")

        rows = extract_sheet_data(xlsx_path, i)
        md_content = rows_to_markdown(rows, sheet_name, os.path.basename(xlsx_path))

        # 文件名清理
        safe_name = sheet_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        output_file = os.path.join(output_dir, f"{safe_name}.md")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        results.append({
            'sheet_name': sheet_name,
            'output_file': output_file,
            'rows': len(rows),
            'cols': max(len(r) for r in rows) if rows else 0
        })

    return results

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("用法: python extract_excel.py <xlsx文件> <输出目录>")
        sys.exit(1)

    xlsx_path = sys.argv[1]
    output_dir = sys.argv[2]

    print(f"开始提取: {xlsx_path}")
    results = extract_to_markdown(xlsx_path, output_dir)

    print(f"\n提取完成！共提取 {len(results)} 个Sheet：")
    for r in results:
        print(f"  - {r['sheet_name']}: {r['rows']}行 × {r['cols']}列 → {os.path.basename(r['output_file'])}")
