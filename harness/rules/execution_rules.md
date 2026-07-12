# 执行指引

> **性质：建议与指引，非强制阻塞。缺失项不影响分析继续，仅作为改进提醒。**

---

## 建议 1：任务启动前阅读项目规范

**建议每次新任务开始时，先阅读 `harness/spec/project_spec.md`。**

- 理解 ChatBI 的项目背景和目标
- 理解"不变与可变"的框架设计原则
- 确认当前任务的业务领域和预期产物类型

> 未阅读不影响执行，但推荐了解全貌后再开始。

---

## 建议 2：Agents / Workflows / Phases 按需定制

**建议根据当前业务数据和任务目标调整这三个维度，而非直接复用既有配置。**

| 规划维度 | 依据 | 产物 |
|----------|------|------|
| **Agents** | 当前业务分析需要哪些专业分工？ | 新的 agent 定义文件或对现有 agent 的修订 |
| **Workflows** | 当前分析链路需要哪些步骤？每步的输入输出是什么？ | 新的 workflow YAML 或对现有 workflow 的修订 |
| **Phases** | 当前业务问题如何分解为独立的分析阶段？ | 新的任务 spec 文件（`harness/spec/tasks/`） |

> 直接复用既有配置也可执行，但建议至少审查一遍是否适配当前任务。

---

## 建议 3：执行前运行 Task Readiness 检查

每个 workflow 的 `stage_0` 是 **task_readiness** 阶段，建议在此阶段关注以下事项：

- [ ] 已阅读 `project_spec.md`
- [ ] 已确定当前任务的业务领域和数据源
- [ ] 已确定本次的 Agents（角色种类和数量）
- [ ] 已确定本次的 Workflows（工作流数量和阶段）
- [ ] 已确定本次的 Phases（分析阶段数量和顺序）
- [ ] 已在 `harness/spec/tasks/` 中创建对应的任务规范文件
- [ ] 已确认当前任务的 `data_spec.md` 数据规范到位

> `check_task_readiness.py` 脚本会逐项扫描并给出建议，缺失项不会阻塞执行。

---

## 建议 4：保持六层目录结构

以下八个目录构成了 Harness 工程的标准骨架，建议保持完整：

```
harness/spec/        harness/skills/      harness/agents/
harness/workflows/   harness/memory/      harness/evaluation/
harness/rules/       harness/scripts/
```

> 任务较简单时部分目录暂不填充也完全可行，结构保留即可。

---

## 建议 5：L4 记忆层自动更新

**建议在以下时机自动更新 `harness/memory/` 中的文件：**

| 触发时机 | 更新目标 | 内容 |
|----------|----------|------|
| 每个 Workflow 的 stage 开始/结束时 | `state/current.md` | 更新进度状态和 checklist |
| 做出技术选型或架构决策时 | `decisions.md` | 追加决策记录（背景/选项/选择/理由） |
| 遇到错误或 reviewer 驳回时 | `lessons.md` | 追加教训记录（问题/根因/修复/预防） |
| 对话自然暂停点（~10轮） | `state/current.md` | 更新最后更新时间戳 |

> 记忆层是 Harness 的"大脑"——不更新的记忆等于没有记忆。棘轮只能向前转。

---

## 建议 6：Power BI 任务自动 MCP 校验

**执行 Power BI 相关任务时，自动连接 Power BI Modeling MCP Server 进行校验：**

| 触发时机 | MCP 操作 | 目的 |
|----------|----------|------|
| 创建/修改 TMDL 文件后 | `connection_operations` → `model_operations.Get` | 验证 TMDL 语法，检查表/度量/关系是否正确加载 |
| 添加 visual 并绑定字段后 | `measure_operations.List` → 交叉验证 | 确认 visual 绑定的字段在模型中实际存在 |
| 生成 PBIP 项目后 | `model_operations.Get` 全量检查 | 验证整个模型一致性（表/列/度量/关系/RLS） |
| 发现校验错误时 | 自动修复 + 记录 `lessons.md` | 常见 TMDL 语法错误自动修正并记录 |

> MCP 配置见 `harness/MCP/README.md`。校验不阻塞流程，但校验结果应被 reviewer 审查。

---

## 建议 7：交付前自检 — 先验证再交付

**每次生成输出文件（代码、Dashboard、报告、脚本）后，必须完成以下自检，发现问题先自行修复。**

### 代码可运行检查

- [ ] Python 文件能否无报错执行？
- [ ] 依赖包是否已安装？（`import` 检查）
- [ ] 数据路径是否正确？（相对路径 vs 绝对路径）
- [ ] 数据类型是否匹配？（如 resample 需要 DatetimeIndex）

### 输出文件格式检查

- [ ] HTML 文件能否在浏览器中正常打开和渲染？
- [ ] PDF 文件能否正常打开？页码、图表、中文是否正常？
- [ ] JSON 文件是否为有效 JSON？（`json.load` 验证）
- [ ] CSV 文件行数和列数是否正确？
- [ ] 图片文件是否为有效 PNG？（能否被图片查看器打开）

### 数据一致性检查

- [ ] 报告中引用的数字是否与数据源 JSON 一致？
- [ ] Dashboard 和 PDF 报告中的 KPI 数值是否一致？
- [ ] 图表中的数据是否与表格数据一致？

### 发现报错时的处理流程

1. **先定位根因**：是代码逻辑错误？路径错误？还是依赖缺失？
2. **自行修复**：修改代码后重新运行，确认修复有效
3. **记录教训**：将错误写入 `harness/memory/lessons.md`（问题→根因→修复→预防）
4. **再次验证**：修复后重新运行全部检查项

### 项目交付前全面检查

重大问题（无法运行/数据错误）必须修复。轻微问题（格式/命名）建议修复后交付。

> **交付前没跑过的代码 = 一定有问题。自检不是可选的，是 Harness 质量保证的最后一道防线。**

---

## 检查方式

1. **自动扫描**：`check_task_readiness.py` 在 stage_0 执行，逐项扫描并给出状态和建议
2. **不阻塞**：脚本始终 exit(0)，缺失项仅输出 `💡 建议:` 提示
3. **人工判断**：reviewer agent 在 review 阶段可参考检查输出，由人决定是否需要补充
