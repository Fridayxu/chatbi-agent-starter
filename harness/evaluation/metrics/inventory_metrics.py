"""🟠 案例专用 — 当前案例：库存分析
切换案例时，请根据新业务需求替换或创建新的 metrics 文件。

库存案例 — 库存优化评估指标

包含：Service Level, Fill Rate, Inventory Turnover,
      Weeks of Supply, Stockout Rate, Excess Inventory Ratio
适用场景：库存策略的KPI评估与对比
"""

import numpy as np
import pandas as pd


def calculate_service_level(
    demand: np.ndarray,
    fulfilled: np.ndarray
) -> float:
    """服务水平（Service Level）— 从现有库存中满足的需求比例。

    SL = 1 - (未满足的需求量 / 总需求量)
    等价于 fulfilled / demand。

    行业标准：
    - A类品：≥ 97%
    - B类品：≥ 95%
    - C类品：≥ 90%

    Args:
        demand: 客户需求量数组
        fulfilled: 实际从库存中满足的数量（fulfilled ≤ demand）
    Returns:
        服务水平 (0-1), e.g., 0.97 表示 97%
    """
    total_demand = np.sum(demand)
    if total_demand == 0:
        return 1.0
    return float(np.sum(fulfilled) / total_demand)


def calculate_fill_rate(
    demand: np.ndarray,
    fulfilled: np.ndarray
) -> float:
    """订单满足率 — 需求被完全满足的天数比例。

    Args:
        demand: 每日需求量
        fulfilled: 每日实际满足量
    Returns:
        满足率 (0-1)
    """
    if len(demand) == 0:
        return 1.0
    fully_fulfilled = np.sum(fulfilled >= demand)
    return float(fully_fulfilled / len(demand))


def calculate_inventory_turnover(
    sales: float,
    avg_inventory: float
) -> float:
    """库存周转率 — 一定时期内库存被"卖掉"的次数。

    Turnover = 销售成本(或销售额) / 平均库存

    越高表示库存效率越好，但需与服务水平平衡。

    Args:
        sales: 时期内的总销售额（或销售成本）
        avg_inventory: 时期内的平均库存水平
    Returns:
        周转次数
    """
    if avg_inventory == 0:
        return float('inf')
    return float(sales / avg_inventory)


def calculate_weeks_of_supply(
    current_inventory: float,
    weekly_sales_avg: float
) -> float:
    """库存周数 — 按当前销售速度，现有库存能支撑几周。

    健康范围：4-8 周
    < 3 周：缺货风险
    > 12 周：库存积压
    > 26 周：严重积压，触发清仓评估

    Args:
        current_inventory: 当前库存量
        weekly_sales_avg: 近N周的周均销量
    Returns:
        库存周数
    """
    if weekly_sales_avg == 0:
        return float('inf')
    return float(current_inventory / weekly_sales_avg)


def calculate_stockout_rate(
    inventory_level: np.ndarray,
    demand: np.ndarray
) -> float:
    """缺货率 — 库存不足以覆盖需求的天数比例。

    Args:
        inventory_level: 每日期初库存
        demand: 每日需求量
    Returns:
        缺货率 (0-1)
    """
    if len(inventory_level) == 0:
        return 0.0
    stockout_days = np.sum(inventory_level < demand)
    return float(stockout_days / len(inventory_level))


def calculate_excess_inventory_ratio(
    weeks_of_supply_values: np.ndarray,
    threshold: float = 26.0
) -> float:
    """积压库存占比 — 库存周数超过阈值的SKU比例。

    目标：< 5% of SKUs

    Args:
        weeks_of_supply_values: 各SKU的库存周数数组
        threshold: 积压阈值（默认26周）
    Returns:
        积压占比 (0-1)
    """
    if len(weeks_of_supply_values) == 0:
        return 0.0
    excess = np.sum(weeks_of_supply_values > threshold)
    return float(excess / len(weeks_of_supply_values))


def evaluate_inventory_policy(
    demand: np.ndarray,
    fulfilled: np.ndarray,
    inventory: np.ndarray,
    sales: float,
    avg_inventory: float,
    weekly_sales: float,
    label: str = "policy"
) -> dict:
    """一键评估库存策略，输出所有KPI汇总。

    Returns:
        dict: 所有库存KPI
    """
    return {
        'label': label,
        'n_periods': len(demand),
        'service_level': round(calculate_service_level(demand, fulfilled), 4),
        'fill_rate': round(calculate_fill_rate(demand, fulfilled), 4),
        'inventory_turnover': round(calculate_inventory_turnover(sales, avg_inventory), 2),
        'weeks_of_supply': round(calculate_weeks_of_supply(inventory[-1], weekly_sales), 2) if weekly_sales > 0 else float('inf'),
        'stockout_rate': round(calculate_stockout_rate(inventory, demand), 4),
    }
