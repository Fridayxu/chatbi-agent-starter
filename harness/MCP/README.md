# MCP 注册表 (MCP Registry)

> 统一管理项目中所有 Model Context Protocol 服务器的配置和调用规则。
> 新增 MCP 后必须在此注册，并指定自动调用条件。

---

## 已注册 MCP

| MCP 名称 | 配置文件 | 用途 | 自动调用条件 |
|----------|----------|------|-------------|
| **Power BI Modeling** | [power-bi-modeling.md](power-bi-modeling.md) | 连接 PBI Desktop，创建/修改/校验语义模型（表/度量/关系/列） | 创建 PBIP 项目、修改 TMDL 文件、添加 visual 绑定后 |
| **headroom** | 内置 | 上下文压缩与检索，降低 token 消耗 | 大型输出自动压缩 |

---

## MCP 生命周期

| 操作 | 步骤 |
|------|------|
| **新增 MCP** | 1. 在 `harness/MCP/` 下创建配置文件 2. 在本文件中添加条目 3. 指定自动调用条件 |
| **停用 MCP** | 标注状态为 `⚠️ 已停用`，保留文件不删除 |

---

## 自动调用规则

- Power BI 相关任务 → 自动连接 Power BI Modeling MCP，执行模型校验
- 输出超 2000 行 → 自动调用 headroom 压缩
- 检查结果发现不一致 → 记录到 `lessons.md`
