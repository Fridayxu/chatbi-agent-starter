# 关键决策记录

> 记录每个重要决策的背景、选项、选择理由和影响
> 原则：决策可追溯，后人可理解"为什么当时这样选"
> 格式：日期 + 标题 + 背景 + 选项 + 选择 + 理由 + 影响

## ⚡ 何时追加

以下时机必须在本文件末尾追加新决策记录：
- 技术选型（选 A 方案而非 B 方案）
- 架构调整（为什么改了 Agent/Workflow/Phase 设计）
- 参数定版（为什么选这个阈值/这个模型/这个配置）
- 外部依赖选择（为什么用这个库/这个服务/这个数据源）
- 回滚决策（为什么放弃之前的做法，回到什么状态）

> **不加 = 丢失可追溯性，三个月后没人知道当时怎么想的。**

---

## 2026-06-27 | 选择 Harness Engineering 作为工程方法论

- **背景**：需要为 ChatBI 项目选择一套工程方法论，确保分析结果的质量、可复现性和可追溯性
- **选项**：
  - A: 无框架，每次分析从零开始
  - B: CRISP-DM（传统数据挖掘流程）
  - C: Harness Engineering 六层架构
- **选择**：C — Harness Engineering
- **理由**：
  - 六层架构天然适配 AI Agent 辅助开发场景（模型+Harness = Agent）
  - L1-L6 的分层设计将"要做什么"（spec）、"怎么做"（skills/workflows）、"做对了没"（evaluation/scripts）分离
  - 棘轮效应（lessons.md）确保知识只进不出
  - 社区验证：同一模型仅改进 Harness 即可将基准得分从 52.8% 提升至 66.5%
- **影响**：整个项目的目录结构、开发流程、质量保证体系均基于此方法论构建

---

## 2026-06-27 | 选择 Retail Store Inventory Forecasting 为首个验证案例

- **背景**：ChatBI 需要具体业务案例验证框架有效性，需选择数据集
- **选项**：
  - A: Retail Store Inventory Forecasting（Kaggle，73,100 行 × 15 列）
  - B: Inventory Optimization for Retail（3 文件，29 列）
  - C: UCI Online Retail（400K 交易记录）
- **选择**：A
- **理由**：
  - 字段覆盖完整：库存、销售、补货、定价、促销、天气、竞争六大维度
  - 零缺失值，开箱即用
  - 15 列结构清晰，适合作为首个验证案例
  - 供应链库存分析是 ChatBI 典型业务场景
- **影响**：L1 层 data_spec.md 基于此数据集编写；L3 层 forecaster/inventory_analyst/pricing_analyst 三个 Agent 为此案例定制

---

## 2026-06-28 | 确定框架"不变与可变"原则

- **背景**：需要在项目规范中明确哪些结构是固定骨架、哪些内容随业务变化
- **选项**：
  - A: 全部内容固定，所有案例共用一套 Agents/Workflows/Phases
  - B: 全部内容可变，每个案例自由组织
  - C: 六层目录骨架不变，Agents/Workflows/Phases/Skills/Metrics 按需定制
- **选择**：C — "不变与可变"分离
- **理由**：
  - 固定的六层目录确保每次分析都在统一的工程框架下运行
  - 可变的 Agents/Workflows/Phases 适配不同业务场景（库存 ≠ 财务 ≠ 销售）
  - 既保证了质量控制的一致性，又保留了业务灵活性
- **影响**：写入 project_spec.md 作为框架设计原则；每次新任务开始前需阅读并确认

---

## 2026-06-28 | L6 约束从强制改为建议

- **背景**：最初将 execution_rules.md 设计为硬约束（不通过则中止），但考虑到不同场景的灵活性
- **选项**：
  - A: 保持硬约束，所有检查项不通过则 exit(1)
  - B: 改为软建议，缺失项输出 💡 建议但不阻塞
- **选择**：B — 软建议
- **理由**：
  - 简单任务可能不需要所有检查项就位
  - 硬阻塞会导致框架在轻量场景下"太重"而难以坚持使用
  - 建议不阻塞确保框架始终可用，同时保留引导作用
- **影响**：execution_rules.md 全部改写；check_task_readiness.py 改为始终 exit(0)；workflow stage_0 改为 on_fail: warn

---

## 2026-06-28 | L2 工具系统层技能选型

- **背景**：ChatBI 需要看板搭建、报告生成、数据分析等能力，需选择合适的 skills
- **选项**：见 L2 技能候选清单讨论
- **选择**：安装 6 个 skills（build-dashboard / kpi-dashboard-design / firecrawl-dashboard-reporting / developing-with-streamlit / document-pdf / elegant-reports）
- **理由**：
  - 看板搭建：Anthropic 官方 build-dashboard + kpi-dashboard-design（10.7K安装）+ firecrawl-dashboard-reporting（21.1K）+ Streamlit
  - 报告生成：document-pdf + elegant-reports
  - 已内置 headroom MCP（token压缩）、Harness L4（记忆）、WebSearch/WebFetch（网络查询）、Read/Write/Edit（文件读写）
- **影响**：L2 层能力矩阵已就绪；剩余 3 个 skill 待网络恢复后安装

---

## 2026-06-28 | L6 新增"交付前自检"规则

- **背景**：Streamlit Dashboard 交付后出现 `ModuleNotFoundError` 和 `TypeError: resample needs DatetimeIndex` 两个错误，说明交付前缺少系统性自检步骤
- **选项**：
  - A: 不做系统性检查，遇到报错再修
  - B: 在 L6 execution_rules.md 中新增"建议 6：交付前自检"，覆盖代码可运行检查、输出格式检查、数据一致性检查三大类
- **选择**：B
- **理由**：自检是 Harness 质量保证的最后一道防线。交付前没跑过的代码一定有问题
- **影响**：新增了 15 项自检清单；完成首次全项目自检（52 通过/0 错误/0 警告）；发现两条经验教训已记录
