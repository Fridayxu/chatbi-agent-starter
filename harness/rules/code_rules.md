# 代码红线规则

> 性质：软约束。代码规范影响可维护性和可复用性。src/ 中的代码需严格执行，notebooks/ 中可放宽。

---

## src/ 源码规范（严格执行）

### 1. 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 模块/文件 | `snake_case` | `forecast_metrics.py`, `data_loader.py` |
| 函数 | `snake_case`，动词开头 | `calculate_mape()`, `load_raw_data()` |
| 类 | `PascalCase` | `ForecastModel`, `DataValidator` |
| 常量 | `UPPER_SNAKE_CASE` | `DEFAULT_SERVICE_LEVEL`, `MAX_MISSING_RATIO` |
| 变量 | `snake_case`，描述性 | `weekly_sales_avg`，不是 `wsa` |

### 2. 类型标注

所有公开函数必须有完整的类型标注：

```python
# ✅ 正确
def calculate_mape(actual: np.ndarray, forecast: np.ndarray, min_actual: float = 0.1) -> float:

# ❌ 错误
def calculate_mape(actual, forecast, min_actual=0.1):
```

### 3. 文档字符串

每个公开函数必须有 docstring，包含：
- 功能描述（一句话）
- Args：参数名、类型、含义
- Returns：返回值类型和含义
- 关键边界条件（除零处理、空数组处理等）

### 4. 不可硬编码

- ❌ 不可在函数体内硬编码路径、阈值、参数
- ✅ 路径通过参数传入或从 `config/` 读取
- ✅ 阈值在 `quality_gates.yaml` 中定义，代码中引用

### 5. 不可静默失败

- ❌ 不可 `try: ... except: pass`
- ✅ 异常必须记录日志或向上抛出，附带上下文信息
- ✅ 边界条件（除零、空数组）必须显式处理，不可依赖默认行为

---

## notebooks/ 探索代码（建议）

- 分析逻辑可接受一定程度的探索性写法
- 但被 ≥ 2 个 notebook 复用的逻辑必须提取到 `src/`
- notebook 顶部需标注分析日期、数据来源、前置条件

---

## 检查方式

- reviewer 在 review 阶段抽查 `src/` 中函数的类型标注和 docstring 完整性
- 新增 CI 后，可配置 `mypy` 或 `pyright` 进行类型检查
