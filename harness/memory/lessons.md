# 经验教训

> 棘轮效应：每犯一个错误，就变成一条永久记录
> 原则：同样的错误不犯第二次
> 格式：日期 + 问题 + 根因 + 修复 + 预防

## ⚡ 何时追加

以下时机必须在本文件末尾追加新教训记录：
- 代码运行报错且需要修改代码才能修复
- 数据分析结论被 reviewer 驳回
- GitHub/网络/环境等基础设施问题导致操作失败
- 数据质量发现新问题（新的缺失值模式、新的异常值类型）
- Workflow 执行中某个 stage 被 reviewer 标记为 🟡 或 🔴

> **不加 = 下次还会踩同一个坑。棘轮只能向前转。**

---

## 2026-06-28 | GitHub 网络不可达导致 Skill 安装失败

- **问题**：`npx skills add` 命令因 GitHub 连接超时失败，4 个 skill 多次重试均无法安装。尝试了 ghproxy.cn（DNS 不存在）、ghproxy.com（443 端口不可达）、本地 HTTP 代理扫描（无代理运行）、git insteadOf 配置等多种方式
- **根因**：
  - 当前网络环境对 GitHub（github.com:443）不可达
  - ghproxy.cn 域名不存在，ghproxy.com 从此网络也无法连接
  - 本地无 HTTP 代理进程运行（加速器可能仅作用于浏览器，终端流量不走代理）
- **修复**：用户手动下载 skill 并放置到 `.agents/skills/`
- **预防**：
  - 将来在新环境中搭建项目时，首先验证 `git clone https://github.com` 是否可达
  - 如不可达，确认加速器/VPN 是否正确配置了终端代理
  - 备选方案：准备 skills 离线安装包

---

## 2026-06-28 | Streamlit Dashboard 运行时依赖缺失

- **问题**：`streamlit run results/dashboard/app.py` 报 `ModuleNotFoundError: No module named 'streamlit'`，用户无法启动 Dashboard
- **根因**：`pip install streamlit` 安装耗时较长（含 pyarrow/altair/gitpython 等大型依赖），未在交付前确认安装完成
- **修复**：`pip install streamlit` 完成安装后正常运行
- **预防**：加入 L6 建议 6"交付前自检 → 依赖检查"，交付前逐一确认 `import` 成功。优先提供 HTML Dashboard（零依赖），Streamlit 作为可选项

## 2026-06-28 | resample() 需要 DatetimeIndex 导致 TypeError

- **问题**：`filtered.groupby('Date')['Units Sold'].resample('W').sum()` 报 `TypeError: Only valid with DatetimeIndex`
- **根因**：`load_data()` 未将 Date 列设为索引，`groupby` 后索引变为 RangeIndex
- **修复**：用 `pd.Grouper` 按周分组替代 `resample`：将 Date 转为 Week 列再 `groupby('Week').sum()`，不依赖 DatetimeIndex
- **预防**：加入 L6 建议 6"交付前自检 → 代码可运行检查"，Python 文件必须先跑通再交付。涉及时间序列时优先用 `pd.Grouper` 或 `dt.to_period` 而非 `resample`

## 2026-06-28 | 库存明细表列名不匹配导致 KeyError

- **问题**：`inventory_summary.json` 中 products 数据只有 9 个字段，但 Dashboard 的 `cols` 列表引用了 `daily_demand_avg` 和 `daily_demand_std`（实际在 JSON 中不存在），导致 `KeyError`
- **根因**：Phase 4 生成的 JSON 与 Dashboard 的字段列表不同步。JSON 按 products 结构序列化，Dashboard 期望了额外的列
- **修复**：删除 `cols` 和 `col_map` 中的 `daily_demand_avg` 和 `daily_demand_std`，与 JSON 实际字段对齐
- **预防**：生成 JSON 和消费 JSON 的代码要保持字段同步。Dashboard 中引用外部 JSON 字段时，先 `print(data.keys())` 确认实际字段名

## 2026-07-06 | pbi table create --m-expression 文件路径模式导致 M 表达式存储为文件名

- **问题**：`pbi table create Inventory --m-expression temp_m.txt` 将文件路径 `temp_m.txt` 作为 M 表达式文本存储（而非文件内容），导致 partition M 表达式为字面量 `temp_m.txt`，刷新时报 "无法识别名称 temp_m.txt"
- **根因**：`--m-expression` 接受的是 M 表达式文本本身，不是文件名。当传入文件路径时，它被当作普通字符串存储
- **修复**：使用 stdin 管道传递 M 表达式：`echo '<M code>' | pbi table create NAME --m-expression -`
- **预防**：始终通过 stdin（`-`）传递 M/DAX 表达式，避免文件路径混淆

## 2026-07-06 | TOM 创建表后列不自动发现 — 需手动创建列

- **问题**：通过 `pbi table create --m-expression` 创建表后，表只显示 RowNumber 列，M 表达式中的源列不会自动发现
- **根因**：TOM（Tabular Object Model）创建表时只存储分区定义，Power Query 列评估不会自动触发。列元数据需要通过 TOM 显式添加
- **修复**：创建表后使用 `pbi column create --source-column` 为每个源列手动添加列定义，然后再 `pbi table refresh`
- **关键流程**：
  1. `echo '<M>' | pbi table create NAME --m-expression -` → 创建表壳
  2. `pbi column create COL --table NAME --data-type DT --source-column SRC` → 逐列添加
  3. `pbi table refresh NAME` → 触发数据加载
  4. `pbi dax execute` → 验证数据行数

## 2026-07-06 | 语义模型中源列名必须与 CSV 表头精确匹配

- **问题**：`pbi column create --source-column "Store ID"` 但 CSV 表头为 `StoreID`（无空格），导致刷新后数据为空
- **根因**：`sourceColumn` 参数必须与 Power Query `Table.PromoteHeaders` 产生的列名完全一致（大小写、空格、特殊字符）
- **修复**：先查看 CSV 表头确定精确列名，再在 `--source-column` 中使用相同名称
- **预防**：生成 CSV 时避免列名包含空格（使用 CamelCase），或在 `pbi column create` 时严格对照 CSV 表头

## 2026-07-06 | 维度表必须有唯一键才能建立关系

- **问题**：Product Dim 有 100 行（5 stores × 20 products），Store Dim 有 5 行但有重复 StoreID，导致 `pbi relationship create` 失败
- **根因**：关系 "一" 侧要求键列唯一。合成数据集中 Product+Category 组合因 store 变化而产生重复
- **修复**：
  1. 对维度表做 `drop_duplicates(subset=['Key'])` 确保键唯一
  2. 将随维度变化的属性（如 Category）移至事实表
  3. 最终 Product Dim: 20 行，Store Dim: 5 行，Calendar Dim: 731 行
- **预防**：创建维度表后先用 `df['Key'].nunique() == len(df)` 验证键唯一性

## 2026-07-06 | PBIP 项目 .platform v2.0 与 model.bim (TMSL) 的兼容性

- **问题**：`.platform` version "2.0" 期望 TMDL 格式（定义在 `definition/` 文件夹），但使用 `model.bim` (TMSL) 格式。PBI Desktop 显示 "无标题" 表示未加载 model.bim
- **根因**：PBI Desktop v2.155.756.0 的 TMDL 支持不完整（所有 TMDL 格式均被拒绝），而 `model.bim` 包含表定义时会触发 "序列不包含任何元素" 错误
- **修复**（本次使用）：
  1. 使用**最小 model.bim**（仅 compatibilityLevel + annotations，无表定义）
  2. 所有数据模型操作通过 **pbi-cli TOM** 连接 PBI Desktop 完成
  3. 表、列、关系、度量值全部在 PBI Desktop 运行期间通过 TOM 创建
  4. 数据在 PBI Desktop 内存中，通过 Ctrl+S 保存
- **限制**：关闭 PBI Desktop 后，model.bim 不会被更新（PBI Desktop 不写回 TMSL），项目重新打开时需重新加载数据

## 2026-07-06 | .pbip 文件 schema 错误 — semanticModel 应为 dataset

- **问题**：PBI Desktop 打开 `.pbip` 文件时报错 `Property 'semanticModel' has not been defined and the schema does not allow additional properties` / `Required properties are missing from object: report`
- **根因**：`.pbip` v1.0 schema 的 `artifacts` 数组只接受 `report` 和 `dataset` 两种类型，使用 `semanticModel` 会被 schema 验证拒绝
- **修复**：将 `artifacts[1].semanticModel` 改为 `artifacts[1].dataset`，路径保持不变
- **预防**：创建 `.pbip` 文件时始终使用 `dataset` 类型名称引用语义模型，不要使用 `semanticModel`
- **修正**：PBI Desktop v2.155 的 `.pbip` schema 仅接受 `report` artifact，不支持 `dataset`。数据集通过 `definition.pbir` 引用

## 2026-07-06 | .pbip artifact `dataset` 同样被 schema 拒绝 — 仅支持 `report`

- **问题**：改为 `dataset` 后仍报错 `Property 'dataset' has not been defined`
- **根因**：PBI Desktop v2.155 的 `.pbip` v1.0 schema **仅接受 `report` 类型 artifact**，不接受 `dataset` 或 `semanticModel`
- **修复**：`.pbip` 只保留 `report` artifact，数据集引用在 `definition.pbir` 中通过 `datasetReference.byPath` 完成
- **预防**：PBI Desktop v2.155 的 `.pbip` 文件 artifacts 数组只放 `report`，不放 `dataset`

## 2026-07-06 | definition.pbism 强制存在且 schema 极其严格

- **问题**：`definition.pbism` 被 PBI Desktop 强制要求存在，但 `model`/`database`/`semanticModel`/`dataset` 所有属性均被 schema 拒绝
- **根因**：PBI Desktop v2.155 的 `definition.pbism` schema 只接受 `{"version": "1.0"}` (或 PBI Desktop 自己写的带有 `$schema` + `settings` 的格式)
- **修复**：`definition.pbism` 内容为 `{"version": "1.0"}`；PBI Desktop 打开项目后会自动补充 `$schema` 和 `settings`
- **最终结构**：
  ```
  .SemanticModel/
    definition.pbism          ← {"version": "1.0"}
    model.bim                 ← 最小化（仅 compatibilityLevel）
  ```

## 2026-07-06 | .platform v2.0 期望 TMDL → 导致 model.bim 被忽略和 TOM 刷新失败

- **问题**：SemanticModel 存在 `.platform` v2.0 时，PBI Desktop 期望 TMDL 格式，导致 model.bim 不可用、TOM 分区刷新失败
- **修复**：删除 SemanticModel 的 `.platform` 文件，仅保留 `definition.pbism` + `model.bim`
- **预防**：不要手动创建 SemanticModel 的 `.platform` 文件；让 PBI Desktop 自己管理

## 2026-07-06 | pbi table create 和 TOM 数据加载不可靠 → 使用 Get Data 手动加载

- **问题**：`pbi table create --m-expression` 在 TOM 模式下创建的表，分区 M 表达式无法正确触发 Power Query 评估，导致数据刷新反复失败（"无法识别名称 Partition_XXX"）
- **根因**：TOMXMLA 创建的 import 表与 TMDL/TMSL 格式之间存在兼容性问题
- **修复**：通过 PBI Desktop 的 **Get Data → Text/CSV** 手动加载 CSV，表名以文件名为准，再通过 `pbi table rename` 重命名
- **预防**：数据加载优先使用 PBI Desktop UI（Get Data），不要依赖 TOM 创建 import 表

## 2026-07-06 | pbi visual bind 会叠加而非替换 projections → 导致重复绑定

- **问题**：多次执行 `pbi visual bind` 会在 visual.json 中叠加 projections，导致同一字段出现 2-4 次重复
- **根因**：`pbi visual bind` 的语义是**添加**绑定，不清除已有 projections
- **修复**：绑定前必须用 `pbi visual delete` + `pbi visual add` 完全重建，或直接写 JSON 文件清理 projections
- **预防**：绑定规则：**一次创建，一次绑定，不再重复操作**。如需修改，删除视觉对象后完整重建

## 2026-07-06 | visual.json 中的空角色导致 "Missing_References" 错误

- **问题**：PBI Desktop 报 "基本错误: Missing_References"，但所有 Measure/Column 引用均正确
- **根因**：`pbi visual add` 创建的模板包含空 `Legend`、`MaxValue` 等角色（projections: []），PBI Desktop 将其视为缺失引用
- **修复**：删除 visual.json 中所有 `projections: []` 的空角色
- **预防**：视觉对象创建后，检查并清除所有空 projections 的角色节点

## 2026-07-06 | Ctrl+Shift+F5 仅重载数据模型，不重载报表布局（PBIR）

- **问题**：修改 visual.json / pages.json 后 `pbi report reload` 不生效，视觉对象无变化
- **根因**：`Ctrl+Shift+F5`（`pbi report reload`）触发的是数据模型刷新，不重载 PBIR 报表布局文件
- **修复**：关闭 PBI Desktop 后重新打开 `.pbip` 文件，才能加载 PBIR 文件变更
- **预防**：修改报表层文件（visual.json、pages.json、report.json）后必须完整重启 PBI Desktop

## 2026-07-06 | `#` 等特殊字符在 bash 中被转义截断

- **问题**：`pbi visual bind ... --field "Inventory[# Products]"` 中 `#` 被 bash 解释为注释，导致绑定不完整
- **根因**：bash 将 `#` 视为注释起始符，后续内容被截断
- **修复**：使用 Python `subprocess.run()` 直接调用 pbi-cli，避免 bash 转义
- **预防**：所有包含 `#`、`$`、`!` 等特殊字符的 pbi-cli 命令，统一通过 Python subprocess 执行

## 2026-07-06 | 隐式度量值引用 (UnitsSold as Measure) 不总是被 PBI Desktop 识别

- **问题**：图表 Y 轴使用 `Measure[Inventory].[UnitsSold]`（隐式 SUM）时，PBI Desktop 可能不识别为有效度量值
- **根因**：PBI Desktop 对隐式度量值的处理依赖模型设置（`discourageImplicitMeasures`）和上下文
- **修复**：创建显式度量值 `Total Units Sold = SUM(Inventory[UnitsSold])`，用显式度量值替代隐式引用
- **预防**：所有 `--value` 绑定优先使用显式 DAX 度量值，避免依赖隐式聚合

## 2026-07-06 | 最佳实践：PBIP 项目完整构建流程

- **问题**：多次试错后总结出的可靠 PBIP 构建流程
- **流程**：
  1. `.pbip` → 仅含 `report` artifact
  2. `definition.pbir` → `datasetReference.byPath` 指向 `../<Name>.SemanticModel`
  3. `definition.pbism` → `{"version": "1.0"}`
  4. `model.bim` → 最小化（compatibilityLevel + annotations）
  5. 数据加载 → 在 PBI Desktop 中通过 Get Data 手动加载 CSV
  6. 表重命名 → `pbi table rename` 匹配 visual 引用
  7. 关系 → PBI Desktop 自动检测 + `pbi relationship create` 补充
  8. 度量值 → `pbi measure create` 通过 Python subprocess（避免 bash 转义）
  9. 视觉对象 → 一次 `pbi visual add` + 一次 `pbi visual bind`，不重复操作
  10. 清理空角色 → 删除 visual.json 中所有空 projections 的角色
  11. 重启 PBI Desktop → 加载 PBIR 变更
  12. 验证 → DAX 查询 + 目视检查

## 2026-07-12 | EdgeOne Makers Agent 部署 — Claude Agent SDK 模型名不兼容

- **问题**：EdgeOne Makers 上使用 Claude Agent SDK + 内置免费模型 `@makers/deepseek-v4-flash` 时，SDK 的 Claude CLI 子进程报 "There's an issue with the selected model (@makers/deepseek-v4-flash)"。去掉 `@makers/` 前缀后，EdgeOne AI Gateway 又报 "Model ID must include provider prefix"。形成死锁。
- **根因**：Claude Agent SDK 内部启动 `claude` CLI 子进程，该 CLI 有内置的模型名白名单，不识别 `@makers/` 前缀。而 EdgeOne AI Gateway 的 Anthropic Messages API 端点要求模型名带 `@makers/` 前缀用于路由。两者互斥。
- **修复**：绕过 Claude Agent SDK，直接通过 HTTP (httpx) 调用 EdgeOne AI Gateway 的 OpenAI 兼容端点 (`/v1/chat/completions`)，使用 `@makers/deepseek-v4-flash` 模型名。此端点接受带前缀的模型名。
- **关键配置**：
  - `AI_GATEWAY_BASE_URL` 必须以 `/v1` 结尾（`https://ai-gateway.edgeone.link/v1`）
  - `AI_GATEWAY_MODEL=@makers/deepseek-v4-flash`（带前缀）
  - `edgeone.json` 中 `agents.framework` 设为 `"claude-agent-sdk"`
  - `requirements.txt` 用 `httpx>=0.27.0` 替代 `claude-agent-sdk`
  - 使用 `ctx.utils.sse()` + `ctx.utils.stream_sse(gen())` 做 SSE 流式输出
- **预防**：未来部署 EdgeOne Makers Agent 时，优先使用 Gateway Direct 模式（HTTP 直接调用），避免 Claude Agent SDK 的模型名兼容问题。仅当绑定自有 Anthropic API Key（BYOK）使用真实 Claude 模型时才用 SDK。

## 2026-07-12 | EdgeOne Makers 环境变量和访问控制

- **问题**：部署后站点返回 401，无法公开访问；Agent 无响应
- **根因**：
  1. EdgeOne Makers 预览链接默认开启访问控制，需要 `eo_token` + `eo_time` 参数
  2. 前端 `fetch('/chat')` 不会自动携带 URL 上的 query 参数
  3. `edgeone makers dev/link` 会从云端拉取环境变量覆盖本地 `.env`
- **修复**：
  1. 前端 fetch 时拼接 `window.location.search` 保留 token：`fetch('/chat' + qs)`
  2. 关闭访问控制或使用带 token 的预览链接分享
  3. 本地开发用 `--skip-env-sync` 保留本地 `.env` 配置
  4. 环境变量在 EdgeOne 控制台配置（非仅本地 `.env`）
- **预防**：部署前确认控制台环境变量正确；分享链接时确认访问控制状态

## 2026-07-12 | Python Agent handler 需用 ctx.env 而非 os.environ

- **问题**：Agent 代码中使用 `os.environ` / `load_dotenv()` 读取环境变量，部署后读不到控制台配置的值
- **根因**：EdgeOne Makers 平台规则：`agents/` 目录下 `.py` 文件**禁止**使用 `os.environ`，必须通过 `ctx.env` 读取
- **修复**：所有环境变量通过 handler 的 `ctx.env` 参数获取，不使用 `os.environ` 或 `python-dotenv`
- **预防**：参考 `harness/skills/edgeone-makers-agents/` 中的 skill 规范

## 2026-07-12 | EdgeOne Makers Agent 部署完整检查清单

- **问题**：多次部署失败，根因分散在模型名、环境变量、SDK 兼容性、代码规范等多个层面
- **总结的部署检查清单**：
  1. `edgeone.json` → `agents.framework: "claude-agent-sdk"`, `timeout: 600`
  2. `requirements.txt` → `httpx>=0.27.0`（不用 claude-agent-sdk）
  3. 控制台环境变量：`AI_GATEWAY_API_KEY` / `AI_GATEWAY_BASE_URL`（以 `/v1` 结尾）/ `AI_GATEWAY_MODEL`（带 `@makers/` 前缀）
  4. 代码用 `ctx.env` 读取环境变量（非 `os.environ`）
  5. 用 Gateway Direct 模式（HTTP + OpenAI 兼容端点）而非 Claude Agent SDK
  6. 前端 fetch 拼接 `window.location.search` 保留 eo_token
  7. `ctx.utils.stream_sse(gen())` 做流式输出，事件类型 `ai_response` / `error_message`
  8. 以 `b"data: [DONE]\n\n"` 结束流
  9. 部署后先 curl 测试 `/chat` API，确认返回 SSE 事件后再测前端
  10. 分享链接前确认访问控制状态
