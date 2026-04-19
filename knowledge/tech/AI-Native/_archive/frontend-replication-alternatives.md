# 前端页面复刻替代方案汇总

> 针对 minimax 2.7 上下文窗口限制，避免使用截图方式的替代方案

---

## 问题背景

**当前方案**: 依赖截图方式获取页面信息
**限制**: minimax 2.7 模型上下文窗口较小，截图极易超过上限导致中止
**目标**: 探索其他方式实现 1:1 复刻前端页面

---

## 方案对比

| 方案 | 依赖 | 上下文占用 | 准确性 | 自动化程度 | 推荐度 |
|------|------|-----------|--------|-----------|--------|
| Playwright (Python) | pip install playwright | 🟢 低（纯文本） | ⭐⭐⭐⭐⭐ | 🔥 完全自动化 | ⭐⭐⭐⭐⭐ |
| Selenium (Python) | 已安装 | 🟢 低（纯文本） | ⭐⭐⭐⭐ | 🔥 完全自动化 | ⭐⭐⭐⭐ |
| BeautifulSoup + lxml | 已安装 | 🟢 低（纯文本） | ⭐⭐⭐ | 🔥 完全自动化 | ⭐⭐⭐ |
| web_fetch + 手动 | 内置工具 | 🟢 低（纯文本） | ⭐⭐ | ⚡ 半自动 | ⭐⭐ |
| 手动复制粘贴 | 无 | 🟢 低（纯文本） | ⭐⭐⭐⭐⭐ | ❌ 手工 | ⭐⭐ |
| 混合方案 | Playwright + 人工补充 | 🟡 中 | ⭐⭐⭐⭐⭐ | 🟡 半自动 | ⭐⭐⭐⭐⭐ |

---

## 方案 1: Playwright (Python) ⭐⭐⭐⭐⭐

### 优势
- 🟢 **上下文占用极低** - 输出纯文本（HTML 结构 + 文本内容）
- 🔥 **完全自动化** - 自动访问页面、提取 DOM、交互测试
- ⭐⭐⭐⭐⭐ **准确性高** - 能执行 JavaScript，获取渲染后的真实 DOM
- 📦 **功能强大** - 支持点击、输入、下钻等交互操作
- 🎯 **精准提取** - 可用选择器精确定位元素

### 实现方式

#### 1. 安装 Playwright
```bash
pip3 install playwright
playwright install chromium
```

#### 2. 提取脚本示例
```python
# scripts/frontend/extract_structure.py
from playwright.sync_api import sync_playwright
import json

def extract_page_structure(url, output_file):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        # 等待页面加载
        page.wait_for_load_state('networkidle')

        # 提取导航 Tab
        tabs = page.query_selector_all('[role="tab"]')
        nav_tabs = [{'text': tab.text_content().strip(), 'href': tab.get_attribute('href')} for tab in tabs]

        # 提取筛选栏
        filters = page.query_selector_all('.filter-bar input, .filter-bar select')
        filter_fields = [
            {
                'label': filter.get_attribute('placeholder') or filter.get_attribute('name'),
                'type': filter.get_attribute('type') or 'text',
                'id': filter.get_attribute('id')
            }
            for filter in filters
        ]

        # 提取指标卡片
        cards = page.query_selector_all('.metric-card')
        metric_cards = [
            {
                'title': card.query_selector('.title').text_content().strip(),
                'value': card.query_selector('.value').text_content().strip(),
                'subvalue': card.query_selector('.subvalue').text_content().strip() if card.query_selector('.subvalue') else None
            }
            for card in cards
        ]

        # 提取表格
        table = page.query_selector('table')
        headers = [th.text_content().strip() for th in table.query_selector_all('th')]
        rows = []
        for tr in table.query_selector_all('tbody tr'):
            cells = [td.text_content().strip() for td in tr.query_selector_all('td')]
            rows.append(cells)

        # 提取面包屑
        breadcrumb = page.query_selector('.breadcrumb')
        breadcrumb_items = [item.text_content().strip() for item in breadcrumb.query_selector_all('.breadcrumb-item')] if breadcrumb else []

        result = {
            'url': url,
            'nav_tabs': nav_tabs,
            'filter_fields': filter_fields,
            'metric_cards': metric_cards,
            'table_headers': headers,
            'table_rows': rows[:3],  # 只取前3行作为示例
            'breadcrumb': breadcrumb_items
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        browser.close()

if __name__ == '__main__':
    extract_page_structure(
        'http://10.65.134.124:8080/metrics',
        '/root/.openclaw/workspace/knowledge/tech/AI-Native/prototype-structure.json'
    )
```

#### 3. 执行方式
```bash
# 单次提取
python3 scripts/frontend/extract_structure.py

# 批量提取多个页面
python3 -c "
import json
urls = [
    'http://10.65.134.124:8080/metrics',
    'http://10.65.134.124:8080/metrics/token-usage',
    'http://10.65.134.124:8080/metrics/silicon'
]
for url in urls:
    extract_page_structure(url, f'{url.split(\"/\")[-1]}.json')
"
```

#### 4. 下钻测试
```python
def test_drill_down(page, team_name):
    # 模拟点击某一行
    team_row = page.query_selector(f'table tbody tr:has-text("{team_name}")')
    if team_row:
        team_row.click()
        page.wait_for_load_state('networkidle')

        # 提取下钻后的数据
        # ...

# 在 extract_page_structure 中调用
test_drill_down(page, '终端安全产品研发部')
```

### 输出格式（JSON）
```json
{
  "url": "http://10.65.134.124:8080/metrics",
  "nav_tabs": [
    {"text": "度量管理", "href": "/metrics"},
    {"text": "Token使用量", "href": "/metrics/token-usage"},
    {"text": "硅基含量", "href": "/metrics/silicon"}
  ],
  "filter_fields": [
    {"label": "团队", "type": "select", "id": "team-select"},
    {"label": "职类", "type": "select", "id": "job-type-select"},
    {"label": "日期", "type": "date", "id": "date-range"},
    {"label": "阈值", "type": "number", "id": "threshold"}
  ],
  "metric_cards": [
    {"title": "AI-Native人数", "value": "XX", "subvalue": null},
    {"title": "Token消耗总量", "value": "XXX万", "subvalue": null}
  ],
  "table_headers": ["团队名称", "AI-Native人数", "Token消耗总量", "请求总次数", "总费用", "人均费用"],
  "table_rows": [
    ["终端安全产品研发部", "12", "5.2万", "1200", "¥200", "¥16.67"],
    ["网络安全产品研发部", "8", "3.1万", "800", "¥150", "¥18.75"]
  ],
  "breadcrumb": ["体系整体"]
}
```

### 上下文占用估算
- 单个页面 JSON: ~2-3 KB
- 3 个页面: ~6-9 KB
- **远低于 minimax 2.7 上下文限制**

---

## 方案 2: Selenium (Python) ⭐⭐⭐⭐

### 优势
- ✅ **系统已安装** - 无需额外安装
- 🟢 **上下文占用低** - 纯文本输出
- 🔥 **完全自动化**
- ⭐⭐⭐⭐ 准确性较高

### 实现方式

```python
# scripts/frontend/extract_structure_selenium.py
from selenium import webdriver
from selenium.webdriver.common.by import By
import json

def extract_with_selenium(url, output_file):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    # 等待加载
    driver.implicitly_wait(10)

    # 提取导航
    tabs = driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
    nav_tabs = [{'text': tab.text, 'href': tab.get_attribute('href')} for tab in tabs]

    # 提取表格
    table = driver.find_element(By.TAG_NAME, 'table')
    headers = [th.text for th in table.find_elements(By.TAG_NAME, 'th')]
    rows = [[td.text for td in tr.find_elements(By.TAG_NAME, 'td')] for tr in table.find_elements(By.CSS_SELECTOR, 'tbody tr')]

    result = {
        'url': url,
        'nav_tabs': nav_tabs,
        'table_headers': headers,
        'table_rows': rows[:3]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    driver.quit()
```

### 劣势
- ⚠️ 需要 Chrome/Chromedriver
- 🐛 版本兼容性问题（Selenium 3.141.0 较旧）

---

## 方案 3: BeautifulSoup + lxml ⭐⭐⭐

### 优势
- ✅ **系统已安装**
- 🟢 **上下文占用低**
- 🔥 **轻量快速**

### 实现方式

```python
# scripts/frontend/extract_structure_bs.py
from bs4 import BeautifulSoup
import requests
import json

def extract_with_bs(url, output_file):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')

    # 提取导航
    tabs = soup.select('[role="tab"]')
    nav_tabs = [{'text': tab.text.strip(), 'href': tab.get('href')} for tab in tabs]

    # 提取表格
    table = soup.find('table')
    headers = [th.text.strip() for th in table.find_all('th')]
    rows = [[td.text.strip() for td in tr.find_all('td')] for tr in table.find_all('tr')[1:4]]

    result = {
        'url': url,
        'nav_tabs': nav_tabs,
        'table_headers': headers,
        'table_rows': rows
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
```

### 劣势
- ❌ **不能执行 JavaScript** - 无法获取动态渲染的内容
- ⚠️ 如果原型是 SPA（React/Vue），可能获取不到真实数据

---

## 方案 4: web_fetch + 手动分析 ⭐⭐

### 优势
- ✅ **内置工具**
- 🟢 **上下文占用低**
- ⚡ **快速**

### 实现方式

```bash
# 使用 web_fetch 获取 HTML
web_fetch http://10.65.134.124:8080/metrics --extractMode text

# 然后手动提取关键信息
```

### 劣势
- ❌ **不能执行 JavaScript**
- ⚠️ 需要手动分析
- ⚠️ 不适合复杂数据提取

---

## 方案 5: 手动复制粘贴 ⭐⭐

### 优势
- ⭐⭐⭐⭐⭐ **准确性最高** - 人工确认
- 🟢 **上下文占用最低**
- ✅ **无需工具**

### 实现方式

让用户手动复制以下信息：
1. 浏览器 F12 → Elements → 复制关键 HTML 片段
2. 表格数据复制到 Excel/CSV
3. 拍照/截图关键区域（局部，非全页）

### 劣势
- ❌ **手工操作** - 费时
- ⚠️ 依赖用户配合
- 🐛 容易遗漏细节

---

## 方案 6: 混合方案（推荐）⭐⭐⭐⭐⭐

### 核心思路
**Playwright 自动化提取 + 人工补充关键信息**

### 实现步骤

#### 步骤 1: 自动提取结构信息（Playwright）
```bash
# 运行提取脚本
python3 scripts/frontend/extract_structure.py
```

**自动获取**:
- ✅ 导航 Tab 结构
- ✅ 表格列名
- ✅ 筛选字段类型
- ✅ 面包屑层级
- ✅ API 请求（通过 Network 面板）

#### 步骤 2: 人工补充关键细节
让用户手动提供：
- 📋 特殊交互逻辑（如点击某行后的动画）
- 🎨 视觉标识（如 AI-Native 用户的特殊样式）
- 📊 数据格式规则（如"5.2万"的格式化）
- 🔄 下钻路径确认

#### 步骤 3: 对比验证
- 用 Playwright 提取的数据与原型对比
- 人工确认关键交互逻辑

### 优势
- ⭐⭐⭐⭐⭐ **准确性最高** - 自动化 + 人工确认
- 🟢 **上下文占用低** - JSON 格式
- 🔥 **效率高** - 90% 自动化，10% 人工
- 🎯 **灵活性强** - 根据需要调整

---

## 推荐方案排序

### 第一选择：混合方案（Playwright + 人工）
- **推荐指数**: ⭐⭐⭐⭐⭐
- **理由**:
  - 准确性最高（自动化覆盖 90%，人工补充 10%）
  - 上下文占用极低
  - 可测试交互逻辑
  - 一次提取，多次使用

### 第二选择：Playwright 纯自动化
- **推荐指数**: ⭐⭐⭐⭐⭐
- **理由**:
  - 完全自动化
  - 上下文占用低
  - 功能强大
  - 可重复执行

### 第三选择：Selenium
- **推荐指数**: ⭐⭐⭐⭐
- **理由**:
  - 系统已安装
  - 无需额外配置
  - 但版本较旧，可能有兼容性问题

### 备选方案
- **BeautifulSoup**: 如果原型是静态页面（非 SPA）
- **手动复制**: 如果自动化方案不可行

---

## 实施建议

### 方案选择决策树

```
需要复刻前端页面？
├─ 原型是否是 SPA（React/Vue）？
│  ├─ 是 → 使用 Playwright（推荐）或 Selenium
│  └─ 否 → 使用 BeautifulSoup（更轻量）
│
├─ 是否需要测试交互逻辑（下钻、点击）？
│  ├─ 是 → 使用 Playwright
│  └─ 否 → 使用 BeautifulSoup 或 web_fetch
│
├─ 用户是否愿意配合手动补充？
│  ├─ 是 → 使用混合方案（Playwright + 人工）
│  └─ 否 → 使用 Playwright 纯自动化
│
└─ 时间是否紧迫？
   ├─ 是 → 使用 Playwright（一次性投入）
   └─ 否 → 手动复制粘贴（零工具成本）
```

### 估算对比

| 方案 | 初始投入时间 | 单次执行时间 | 准确性 |
|------|------------|------------|--------|
| Playwright | 30 分钟（写脚本） | 1 分钟 | ⭐⭐⭐⭐⭐ |
| Selenium | 20 分钟（写脚本） | 1 分钟 | ⭐⭐⭐⭐ |
| BeautifulSoup | 15 分钟（写脚本） | 30 秒 | ⭐⭐⭐ |
| 手动复制 | 0 分钟 | 30 分钟 | ⭐⭐⭐⭐⭐ |
| 混合方案 | 40 分钟（写脚本） | 5 分钟（+人工确认） | ⭐⭐⭐⭐⭐ |

---

## 下一步行动

请确认选择哪个方案后，我将：

1. **编写提取脚本**（根据选择的方案）
2. **测试提取效果**（在原型平台上）
3. **更新 `frontend-replication-guide.md`**（替换截图方案）
4. **提供执行指令**（如何使用脚本）

---

*文档创建: 2026-04-19*
*目的: 解决 minimax 2.7 上下文限制问题*
