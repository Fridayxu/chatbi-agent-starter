# Power BI Modeling MCP Server

> 🔵 ChatBI 平台 MCP — 所有 Power BI 相关任务自动调用

## 用途

连接 Power BI Desktop 本地 Analysis Services 实例，提供语义模型的读取和修改能力。

## 核心操作

| 操作类别 | 操作 | 说明 |
|----------|------|------|
| **连接** | `ListConnections` | 列出已有连接 |
| | `ListLocalInstances` | 扫描本地 Power BI Desktop 实例 |
| | `Connect` | 连接到指定模型 |
| **模型** | `Get` | 获取模型概览（表/度量/关系数量） |
| **表** | `List` | 列出所有表 |
| | `Get` | 获取表的列和度量详情 |
| **度量** | `List` | 列出所有度量值 |
| | `Create` | 创建新度量值（DAX 表达式） |
| | `Update` | 更新已有度量值 |
| | `Delete` | 删除度量值 |
| **关系** | `List` | 列出所有关系 |
| | `Create` | 创建表关系 |
| | `Update` | 修改关系属性 |
| **列** | `List` | 列出表的列 |
| | `Update` | 修改列属性（summarizeBy/formatString/隐藏） |

## 何时自动调用

以下场景自动连接并检查：

1. **创建 Power BI 报表时** — 验证 TMDL 模型语法和表/度量引用
2. **添加 visual 后** — 验证 visual 绑定的字段在模型中存在
3. **修改度量值后** — 验证 DAX 语法通过
4. **生成 PBIP 项目后** — 整体验证模型一致性

## 连接流程

```
1. ListLocalInstances → 找到本地 Power BI Desktop 实例
2. Connect → 连接到目标模型
3. Get (model) → 获取当前模型状态
4. 执行需要的操作（创建度量/修改列/添加关系等）
5. 操作后再次 Get → 确认变更生效
```

## 与 TMDL 文件的关系

| TMDL（离线编辑） | MCP（在线操作） |
|------------------|-----------------|
| 直接编辑 .tmdl 文件 | 通过 TOM 接口操作 |
| 无语法校验 | 即时 DAX 语法校验 |
| Power BI Desktop 重开生效 | 即时生效 |
| 适合批量创建 | 适合单次调整和校验 |

> **推荐**：TMDL 做批量创建，MCP 做实时校验。两者互补。
