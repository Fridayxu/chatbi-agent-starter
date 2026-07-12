---
name: power-bi-pbip-build
description: Power BI PBIP project complete build methodology—file structure, data model, visuals, and troubleshooting for PBI Desktop v2.155 (June 2026).
---

# Power BI PBIP 项目构建方法论

> 适用于 PBI Desktop v2.155.756.0 (June 2026) | PBIP v1.0 + PBIR schema 2.7.0

---

## 一、项目文件结构（必须严格遵守）

```
Project.pbip                              ← 仅含 report artifact
Project.Report/
  .platform                                ← pbi-cli 生成（v2.0）
  definition.pbir                          ← datasetReference → SemanticModel
  definition/
    report.json                            ← 主题、设置
    version.json                           ← "2.0.0"
    pages/
      pages.json                           ← 页面顺序
      <page_name>/
        page.json
        visuals/
          <visual_name>/
            visual.json
Project.SemanticModel/
  definition.pbism                         ← {"version": "1.0"}
  model.bim                                ← 最小化（仅 compatibilityLevel）
```

### 关键文件内容

**`.pbip`**（仅 report，不包含 dataset artifact）：
```json
{
  "version": "1.0",
  "artifacts": [{"report": {"path": "Project.Report"}}]
}
```

**`definition.pbir`**（数据集引用）：
```json
{
  "version": "4.0",
  "datasetReference": {
    "byPath": {"path": "../Project.SemanticModel"}
  }
}
```

**`definition.pbism`**（最小化，PBI Desktop 打开后自动补全）：
```json
{"version": "1.0"}
```

**`model.bim`**（最小化）：
```json
{
  "name": "Project",
  "compatibilityLevel": 1605,
  "model": {
    "culture": "en-US",
    "defaultMode": "import",
    "annotations": [{"name": "PBID_Version", "value": "PowerBI_V3"}]
  }
}
```

---

## 二、构建流程（按顺序执行）

### 阶段 1：项目骨架

```bash
cd output/
pbi report create Project --name "Project Display Name" --dataset-path "../Project.SemanticModel"

# 修复 .pbip：移除任何 dataset/semanticModel artifact，只保留 report
# 修复 definition.pbir：确保 path 指向正确的 SemanticModel 文件夹名（注意空格）
```

**检查点**：PBI Desktop 能打开 `.pbip` 文件且不报错。

### 阶段 2：数据准备

- CSV 列名避免空格，使用 CamelCase
- 事实表：所有分析列（含 Category, Region）
- 维度表：仅含唯一键列（用 `drop_duplicates(subset=['Key'])` 确保唯一）
- 验证：`df['Key'].nunique() == len(df)`

### 阶段 3：在 PBI Desktop 中加载数据

**必须通过 UI 操作，不能用 TOM 创建 import 表**：
1. 打开 `.pbip` 文件
2. Get Data → Text/CSV → 逐个加载 CSV
3. **注意**：CSV 导入时勾选 "Use First Row as Headers"

加载后通过 pbi-cli 重命名表：
```bash
pbi connect
pbi table rename <filename> "<DesiredName>"
```

### 阶段 4：关系

PBI Desktop 会自动检测同名列创建关系。
通过 `pbi relationship create` 补充缺失的关系。

### 阶段 5：度量值

**必须通过 Python subprocess 执行**（避免 bash 对 `#` 等特殊字符的转义）：
```python
import subprocess
def create_measure(name, dax, table='Inventory', folder=None):
    cmd = f"echo '{dax}' | pbi measure create '{name}' -t '{table}' -e -"
    if folder:
        cmd += f" --folder '{folder}'"
    subprocess.run(['bash', '-c', cmd], capture_output=True, text=True)
```

### 阶段 6：页面和视觉对象

**规则：一次创建，一次绑定，不重复操作。**

```python
# 创建页面
subprocess.run(['pbi', 'report', '--no-sync', 'add-page', 
                '--display-name', 'Page Name', '--name', 'page_id'])

# 创建视觉对象
subprocess.run(['pbi', 'visual', '--no-sync', 'add', 
                '--page', 'page_id', '--type', 'card', 
                '--name', 'viz_name', '--x', '10', '--y', '10', 
                '--width', '220', '--height', '120'])

# 绑定（只做一次！）
subprocess.run(['pbi', 'visual', '--no-sync', 'bind', 'viz_name',
                '--page', 'page_id', '--field', 'Inventory[MeasureName]'])
```

### 阶段 7：清理空角色

**必须执行**——`pbi visual add` 创建的模板包含空 `Legend`/`MaxValue` 等角色，会导致 "Missing_References"。

```python
for role in list(qs.keys()):
    if len(qs[role].get('projections', [])) == 0:
        del qs[role]
```

### 阶段 8：Gauge MaxValue 补充

`pbi visual bind` 不支持 gauge 的 `--max` 选项，需手动添加：
```json
"MaxValue": {
  "projections": [{
    "field": {
      "Measure": {
        "Expression": {"SourceRef": {"Entity": "Inventory"}},
        "Property": "TargetMeasureName"
      }
    },
    "queryRef": "Inventory.TargetMeasureName",
    "nativeQueryRef": "TargetMeasureName"
  }]
}
```

### 阶段 9：加载变更

**修改 visual.json/pages.json 后，必须关闭并重新打开 PBI Desktop。**
`Ctrl+Shift+F5`（`pbi report reload`）只重载数据模型，不重载报表布局。

### 阶段 10：验证

```bash
pbi connect
pbi report validate          # JSON 结构检查
pbi dax execute -            # DAX 度量值检查
```

---

## 三、常见错误速查

| 错误 | 原因 | 解决 |
|------|------|------|
| `Property 'semanticModel/dataset' has not been defined` | .pbip 含非法 artifact | 只保留 `report` artifact |
| `Required artifact is missing: definition.pbism` | 文件不存在或 schema 错误 | `{"version": "1.0"}` |
| `Property 'model/database' has not been defined` | definition.pbism 含非法属性 | 只保留 `version` |
| `Missing_References` | visual.json 有空角色 | 删除所有空 projections 角色 |
| 视觉对象无变化 | PBIR 未重载 | 关闭并重新打开 PBI Desktop |
| 重复的 projections | 多次 bind 叠加 | 重建 visual，只 bind 一次 |
| bash `#` 截断 | shell 注释 | 用 Python subprocess |
| `分区无法识别` | TOM 创建的表分区不兼容 | 用 Get Data UI 加载数据 |

---

## 四、核心原则

1. **文件结构是铁律** — `.pbip`、`definition.pbir`、`definition.pbism` 内容严格如上
2. **数据加载走 UI** — 不要用 TOM 创建 import 表
3. **一次创建一次绑定** — visual 不重复 bind
4. **空角色必清理** — 每个 visual 检查后保存
5. **PBIR 改完必重启** — 不依赖 Ctrl+Shift+F5
6. **特殊字符用 Python** — 不经过 bash 传参
7. **度量值引用用显式** — 不依赖隐式聚合
