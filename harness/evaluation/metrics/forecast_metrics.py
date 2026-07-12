"""🟠 案例专用 — 当前案例：库存分析
切换案例时，请根据新业务需求替换或创建新的 metrics 文件。

库存案例 — 需求预测评估指标

包含：MAPE, WMAPE, Bias, Tracking Signal, RMSE, MAE, R²
适用场景：回归型时间序列预测的准确度评估
"""

import numpy as np
import pandas as pd


def calculate_mape(actual: np.ndarray, forecast: np.ndarray, min_actual: float = 0.1) -> float:
    """MAPE — 平均绝对百分比误差。

    避免除零：当 actual < min_actual 时，使用 min_actual 代替。
    建议仅对周均销量 > 50 的 SKU 单独报告 MAPE。

    Args:
        actual: 实际值数组
        forecast: 预测值数组
        min_actual: 最小实际值阈值，避免除零放大误差
    Returns:
        MAPE 百分比 (e.g., 25.3 表示 25.3%)
    """
    actual_safe = np.where(actual < min_actual, min_actual, actual)
    return float(np.mean(np.abs((actual - forecast) / actual_safe)) * 100)


def calculate_wmape(actual: np.ndarray, forecast: np.ndarray) -> float:
    """WMAPE — 加权平均绝对百分比误差。

    以实际销量为权重，避免低销量 SKU 主导指标。
    这是财务部门最关心的 KPI。

    Args:
        actual: 实际值数组
        forecast: 预测值数组
    Returns:
        WMAPE 百分比
    """
    total_actual = np.sum(actual)
    if total_actual == 0:
        return 0.0
    return float(np.sum(np.abs(actual - forecast)) / total_actual * 100)


def calculate_bias(actual: np.ndarray, forecast: np.ndarray) -> float:
    """预测偏差 — 平均符号误差。

    - 正值 = 系统性高估（库存积压风险）
    - 负值 = 系统性低估（缺货风险）
    - 健康范围：±5% 以内

    Returns:
        Bias 百分比
    """
    total_actual = np.sum(actual)
    if total_actual == 0:
        return 0.0
    return float(np.sum(forecast - actual) / total_actual * 100)


def calculate_tracking_signal(actual: np.ndarray, forecast: np.ndarray) -> float:
    """追踪信号 — 模型漂移的早期警报。

    TS = 累计误差 / MAD
    - |TS| < 4：模型正常
    - |TS| ≥ 4：模型已漂移，需重新训练或更换方法

    Returns:
        Tracking Signal 值
    """
    errors = forecast - actual
    cumulative_error = np.sum(errors)
    mad = np.mean(np.abs(errors))
    if mad == 0:
        return 0.0
    return float(cumulative_error / mad)


def calculate_rmse(actual: np.ndarray, forecast: np.ndarray) -> float:
    """RMSE — 均方根误差（原始单位）。

    对大误差敏感，适合模型训练的损失函数。
    """
    return float(np.sqrt(np.mean((actual - forecast) ** 2)))


def calculate_mae(actual: np.ndarray, forecast: np.ndarray) -> float:
    """MAE — 平均绝对误差（原始单位）。

    比 RMSE 更鲁棒，不受极端误差的平方放大影响。
    """
    return float(np.mean(np.abs(actual - forecast)))


def calculate_r2(actual: np.ndarray, forecast: np.ndarray) -> float:
    """R² — 决定系数。

    衡量模型相比均值预测的改进程度。
    范围 (-∞, 1]，接近 1 表示预测完美，< 0 表示不如直接猜均值。
    """
    ss_res = np.sum((actual - forecast) ** 2)
    ss_tot = np.sum((actual - np.mean(actual)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1 - ss_res / ss_tot)


def evaluate_forecast(
    actual: np.ndarray,
    forecast: np.ndarray,
    model_name: str = "model"
) -> dict:
    """一键评估预测模型，输出所有指标的汇总字典。

    Args:
        actual: 实际值
        forecast: 预测值
        model_name: 模型标识名
    Returns:
        包含所有指标的 dict，可直接序列化
    """
    return {
        'model': model_name,
        'n_samples': len(actual),
        'MAPE': round(calculate_mape(actual, forecast), 2),
        'WMAPE': round(calculate_wmape(actual, forecast), 2),
        'Bias': round(calculate_bias(actual, forecast), 2),
        'Tracking_Signal': round(calculate_tracking_signal(actual, forecast), 2),
        'RMSE': round(calculate_rmse(actual, forecast), 2),
        'MAE': round(calculate_mae(actual, forecast), 2),
        'R2': round(calculate_r2(actual, forecast), 4),
    }
