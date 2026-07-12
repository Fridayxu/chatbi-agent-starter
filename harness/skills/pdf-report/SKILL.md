---
name: pdf-report
description: |
  生成格式化的 PDF 分析报告。适用于 ChatBI 所有业务案例。
  基于 `harness/scripts/cjk_pdf_utils.py` 的 CJKReport 引擎，解决 CJK+ASCII 混排换行问题。
  核心流程：加载数据 → 字段校验 → para() 写正文 → data_table() 做表格 → 嵌入图表 → 输出。
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
metadata:
  trigger: 生成 PDF 报告、输出分析报告、生成报告
  source: ChatBI 项目定制
  dependencies:
    primary: harness/scripts/cjk_pdf_utils.py (CJKReport)
    python: fpdf2, json, os, base64
---

# PDF Report Generator — ChatBI 格式化报告生成

你是 ChatBI 的报告生成引擎，负责将各阶段分析结果组装为专业格式的 PDF 报告。

## 核心渲染引擎

**必须使用 `harness/scripts/cjk_pdf_utils.py` 中的 `CJKReport` 类**，而非 reportlab。

### 为什么用 CJKReport（fpdf2）替代 reportlab

| 问题 | reportlab | CJKReport (fpdf2) |
|------|-----------|-------------------|
| CJK+ASCII 混排 | `multi_cell()` 按西方单词边界断行，中英混排提前换行 | `para()` 逐字测量宽度，字符级断行，**混排不翻车** |
| 表格宽度 | 手动指定 mm 宽度，超宽需反复调整 | `data_table()` 自动按比例撑满页宽 |
| 字体注册 | 需 `pdfmetrics.registerFont(TTFont(...))` | fpdf2 原生 `add_font()`，更简洁 |
| 代码量 | 大量 ParagraphStyle/TableStyle 配置 | API 简洁，`para()` + `data_table()` 覆盖 80% 需求 |

### 导入和使用

```python
import sys
sys.path.insert(0, 'harness/scripts')
from cjk_pdf_utils import CJKReport

pdf = CJKReport()             # 自动加载微软雅黑
pdf.add_page()
pdf.cover_title('报告标题', ['副标题1', '副标题2'])
pdf.title1('一、章节标题')
pdf.para('正文段落，支持中英混排和任意长度文本...')
pdf.title2('1.1 小节标题')
pdf.data_table(['列1', '列2', '列3'], [['a','b','c'], ['d','e','f']], [30, 50, 40])
pdf.output('output/report.pdf')
```

---

## 执行流程

### 1. 加载数据源

从 `results/tables/` 加载各阶段 JSON 汇总：
- `eda_summary.json` → 数据概览
- `forecast_summary.json` → 预测准确度
- `abc_xyz_summary.json` → ABC/XYZ 分类
- `inventory_summary.json` → 库存策略
- `promo_summary.json` → 促销影响
- `pricing_summary.json` → 竞争定价

### 2. 检查数据完整性（必须，不可跳过）

生成前先验证各 JSON 的字段可用性：
```python
for key, data in sources.items():
    print(f"{key}: {list(data.keys())}")
```

只使用 JSON 中实际存在的字段，不假设字段名。遇到 KeyError 时先确认字段名再修改代码，不要硬编码不存在字段。

### 3. 用 `para()` 写正文 — 混排不翻车

```python
pdf.para('''
这是正文段落。CJKReport.para() 使用逐字测量宽度的方法断行，
因此无论是纯中文、纯英文、还是中英混排，都能保持均匀的右边界。

关键原理：对每个字符调用 get_string_width()，累加到超过页宽时换行。
这与 reportlab multi_cell() 按西方单词边界（空格）断行的方式截然不同。
''')
```

**para() 使用规则：**
- 所有正文内容都用 `para()`，不要用 `cell()` 直接写长文本
- 段落间用 `\n\n` 分隔，`para()` 内部自动处理空行
- 中英混排文本直接传入，无需特殊处理
- 字号 7.5pt，行距 4.8pt，正文灰色(#323232)

### 4. 用 `data_table()` 做表格 — 自动撑满页宽

```python
headers = ['品类', '提升幅度', 'p值', '是否显著']
rows = [
    ['Groceries', '-0.6%', '0.6398', '否'],
    ['Toys', '-1.2%', '0.3432', '否'],
]
pdf.data_table(headers, rows, col_widths=[40, 30, 30, 30])
# 列宽参数只是比例！实际宽度会自动缩放至撑满页宽
```

**data_table() 使用规则：**
- `col_widths` 是比例关系，不是绝对值——会自动 `ratio = page_width / sum(col_widths)` 缩放
- 第一列默认左对齐，其余列居中对齐
- 表头：深蓝底(#2f5496) 白字 6.5pt 加粗
- 数据行：斑马条纹（浅蓝 #f5f8fc / 白色），6.5pt

### 5. 标题层级

```python
pdf.cover_title('报告标题', ['副标题行1', '副标题行2'])  # 封面专用，居中
pdf.title1('一、章节标题')      # 13pt 加粗 深蓝，章节级
pdf.title2('1.1 小节标题')      # 9.5pt 加粗 深灰，小节级
pdf.note('表1: 说明文字')        # 7pt 灰色 居中，图表标注
pdf.divider()                    # 分隔线
```

### 6. 图片嵌入

CJKReport 基于 fpdf2，使用 `pdf.image()` 嵌入 PNG：
```python
if os.path.exists('results/figures/01_trends.png'):
    pdf.image('results/figures/01_trends.png', x=pdf.l_margin, w=pdf.w - pdf.l_margin - pdf.r_margin)
    pdf.note('图1: 图表说明')
```

---

## 报告结构模板

```
pdf = CJKReport()
pdf.alias_nb_pages()  # 激活 {nb} 总页数占位符

# === 封面 ===
pdf.add_page()
pdf.cover_title('零售库存分析报告', [
    'Retail Store Inventory Forecasting',
    '73,100 行 x 15 列 | 5 门店 x 20 产品 x 731 天',
    'ChatBI 智能分析平台 · Harness Engineering 六层架构 | 2026-06-28',
])

# === 执行摘要 ===
pdf.add_page()
pdf.title1('执行摘要')
pdf.para('本报告对 Retail Store Inventory Forecasting 数据集...')

# === 各章节（逐章 add_page） ===
pdf.add_page()
pdf.title1('一、探索性数据分析')
pdf.para('数据集包含...')
pdf.data_table(headers, rows, col_widths)
pdf.note('表1: 数值变量描述统计')
pdf.image('results/figures/01_trends.png', x=pdf.l_margin, w=170)
pdf.note('图1: 各维度周销售趋势')

# ... 其余章节同理

# === 附录 ===
pdf.add_page()
pdf.title1('附录：分析框架与假设声明')
pdf.para('...')

pdf.output('output/inventory_analysis_report.pdf')
```

---

## 输出前验证

- [ ] 所有 JSON 字段引用有效（先 `print(data.keys())` 确认）
- [ ] 所有图片路径 `os.path.exists()` 验证
- [ ] `data_table()` 的 `col_widths` 是比例值，不为负
- [ ] 无半页空白（`add_page()` 在每章开始处，不断中间留白）
- [ ] `pdf.alias_nb_pages()` 已调用（否则 `{nb}` 显示为 0）
- [ ] 页脚自动含 `page_no()/{nb}`（CJKReport.header/footer 自动处理）
- [ ] 附录含假设声明和数据来源

---

## 与其它技能的协作

| 协作方 | 关系 |
|--------|------|
| `harness/scripts/cjk_pdf_utils.py` | **核心依赖** — 提供 CJKReport 类 |
| `visualization_standard.md` | 格式规范 — 颜色/字号/间距标准 |
| `humanizer-zh` | 上游 — 报告文字先生成人性化版本，再传入 `para()` |
| `data_engineer` / 案例 Agent | 上游 — 提供各阶段 JSON 分析结果 |
| `reviewer` | 下游 — 审查 PDF 报告的完整性、一致性和格式合规性 |
| `document-pdf` (.agents/skills/) | 外部备选 — 需要特殊 PDF 操作（合并/拆分/旋转）时使用 |
