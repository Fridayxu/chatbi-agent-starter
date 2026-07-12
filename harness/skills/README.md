# L2 技能注册表 (Skill Registry)

> 统一管理项目中所有技能的来源、用途和调用规则。
> **新增、修改、删除技能后必须同步更新本文件。** 注册表与技能文件不一致时，以注册表为准。

---

## ⚠️ 同步规则

| 触发操作 | 必须更新注册表 |
|----------|---------------|
| 新增技能（创建 SKILL.md） | 在对应分类表中添加条目 |
| 删除技能（移除文件） | 从注册表所有相关位置删除该条目（分类表 + 快速对照表） |
| 修改技能描述/用途 | 更新对应条目的"用途"和"何时调用"列 |
| 切换案例 | 更新 🟠 案例技能表，标注当前案例名称 |

> **技能文件删了但注册表没删 = 误导。技能用途改了但注册表没改 = 过时。保持一致是 L2 层的基本纪律。**

---

## 一、技能分类与来源

### 🔵 ChatBI 平台技能（永久保留，所有案例通用）

| 技能名称 | 位置 | 来源 | 用途 | 何时调用 |
|----------|------|------|------|----------|
| `visualization_standard` | `harness/skills/visualization_standard.md` | 自定义 | 图表 + PDF 报告 + Dashboard 格式规范（配色/要素/间距/表格/图片） | 所有阶段的可视化产出 |
| `pdf-report` | `harness/skills/pdf-report/SKILL.md` | 本地新增 | PDF 格式化报告生成（基于 CJKReport 引擎，封面+摘要+图表+表格+附录） | Phase 7 PDF 报告生成 |
| `humanizer-zh` | `harness/skills/humanizer-zh/SKILL.md` | 本地新增 | 去除 AI 写作痕迹（24 种模式检测：夸大象征、宣传语言、AI 词汇、破折号过度等） | 报告/文档/文字输出前润色 |
| `markitdown` | `harness/skills/markitdown/SKILL.md` | 自动安装 | 文件格式转换（PDF/DOCX→MD） | 需要解析外部文档时 |
| `power-bi-model-design-review` | `harness/skills/power-bi-model-design-review/SKILL.md` | 自动安装 | Power BI 数据模型设计审查 | Power BI 看板方案时 |
| `power-bi-performance-troubleshooting` | `harness/skills/power-bi-performance-troubleshooting/SKILL.md` | 自动安装 | Power BI 性能问题诊断 | Power BI 性能调优时 |
| `powerbi-modeling` | `harness/skills/powerbi-modeling/SKILL.md` | 自动安装 | Power BI 数据建模（表/关系/度量） | Power BI 建模方案时 |
| `power-bi-report-design-consultation` | `harness/skills/power-bi-report-design-consultation/SKILL.md` | 本地新增 | Power BI 报表可视化设计咨询（图表选择/布局/配色/交互/移动端适配） | Power BI 报表设计方案时 |
| `power-bi-pbip-build` | `harness/skills/power-bi-pbip-build/SKILL.md` | 本地新增 | PBIP 项目完整构建方法论（文件结构/数据模型/视觉对象/排错清单） | Power BI PBIP 项目构建时 |

### 📦 外部已安装 Skills

| 技能名称 | 位置 | 安装来源 | 用途 | 何时调用 |
|----------|------|----------|------|----------|
| `build-dashboard` | `.agents/skills/` | `anthropics/knowledge-work-plugins@build-dashboard` | Anthropic 官方 Dashboard 构建 | Phase 7 看板搭建 |
| `kpi-dashboard-design` | `.agents/skills/` | `wshobson/agents@kpi-dashboard-design` | KPI 仪表板设计 | Phase 7 看板 KPI 布局 |
| `firecrawl-dashboard-reporting` | `.agents/skills/` | `firecrawl/firecrawl-workflows@firecrawl-dashboard-reporting` | Dashboard + 报告一体化 | Phase 7 报告生成 |
| `developing-with-streamlit` | `.agents/skills/` | `streamlit/agent-skills@developing-with-streamlit` | Streamlit 仪表板开发 | Phase 7 Streamlit 方案 |
| `document-pdf` | `.agents/skills/` | `vasilyu1983/ai-agents-public@document-pdf` | PDF 文档生成（外部备选） | 需要特殊 PDF 操作时 |
| `elegant-reports` | `.agents/skills/` | `jdrhyne/agent-skills@elegant-reports` | 精美分析报告 | Phase 7 报告美化 |
| `excel-analysis` | `harness/skills/` | 自动安装 | Excel 数据分析 | 需要分析 .xlsx 时 |
| `dashboard-builder` | `harness/skills/` | 自动安装 | Dashboard 构建辅助 | Phase 7 辅助看板 |

### 🟠 库存案例技能（当前案例专用，切换案例时替换或停用）

> 当前无案例专用技能。库存案例的分析方法（预测评估、ABC 分类、安全库存计算）已内嵌在各 Agent 定义文件和 metrics 脚本中，未抽离为独立 skill。
> 如需新增案例技能，按下方"技能生命周期管理"流程操作。

---

## 二、任务 → 技能快速对照表

| 我需要... | 使用这个技能 |
|-----------|-------------|
| 画图表 / 做表格 / 排 PDF 格式 | `visualization_standard` (harness/skills/) |
| 生成 PDF 分析报告 | `pdf-report` (harness/skills/) — 项目定制，优先使用 |
| 润色报告文字（去 AI 痕迹） | `humanizer-zh` (harness/skills/) |
| 构建 HTML Dashboard | `build-dashboard` (.agents/skills/) |
| 搭建 Streamlit 仪表板 | `developing-with-streamlit` (.agents/skills/) |
| 搭建 Power BI 看板 | `powerbi-modeling` + `power-bi-model-design-review` (harness/skills/) |
| Power BI 报表可视化设计咨询 | `power-bi-report-design-consultation` (harness/skills/) |
| 构建 Power BI PBIP 项目（全流程） | `power-bi-pbip-build` (harness/skills/) — 文件结构/数据模型/视觉对象/排错 |
| 美化报告排版 | `elegant-reports` (.agents/skills/) |
| 转换文档格式（PDF→MD） | `markitdown` (harness/skills/) |
| 分析 Excel 数据 | `excel-analysis` (harness/skills/) |

---

## 三、技能调用规则

1. **优先使用自定义技能**：`pdf-report`、`visualization_standard`、`humanizer-zh` 是项目定制的，优先于外部同名技能
2. **外部技能互补**：`.agents/skills/` 中的技能补充自定义技能未覆盖的能力
3. **新增必注册**：任何新增的技能必须在此注册表添加条目并按 ⚠️ 同步规则更新，否则不保证被工作流调用
4. **删除必清理**：删除技能文件时，必须同步从此注册表的**所有位置**移除引用（分类表 + 快速对照表）
5. **内容即资格**：技能文件内容为空或仅为 TODO 占位的，视为不存在，应从注册表移除
6. **Power BI 任务自动连接 MCP**：创建 PBIP 项目、修改 TMDL 或绑定 visual 时，自动调用 `harness/MCP/power-bi-modeling.md` 中定义的 Power BI Modeling MCP Server 进行模型校验

---

## 四、技能生命周期管理

| 操作 | 步骤 |
|------|------|
| **新增技能** | 1. 确定来源和用途 2. 在注册表中添加条目 3. 标记 🔵平台 或 🟠案例 |
| **删除技能** | 1. 删除技能文件 2. 从注册表分类表中移除条目 3. 从快速对照表中移除引用 4. 检查是否有 Agent/Workflow 依赖该技能 |
| **切换案例** | 1. 🟠案例技能标记为"待替换" 2. 添加新案例技能条目 3. 🔵平台技能保持不变 |
| **更新技能** | `npx skills update` 更新外部技能，同步更新注册表中的描述信息 |
