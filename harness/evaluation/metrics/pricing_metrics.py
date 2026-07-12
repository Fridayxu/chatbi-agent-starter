"""🟠 案例专用 — 当前案例：库存分析
切换案例时，请根据新业务需求替换或创建新的 metrics 文件。

库存案例 — 定价分析评估指标

包含：Price Elasticity, Promotional Lift, Revenue Uplift, ROI
适用场景：定价策略和促销效果的量化评估
"""

import numpy as np
from scipy import stats


def calculate_price_elasticity(
    demand: np.ndarray,
    price: np.ndarray
) -> dict:
    """自有价格弹性 — 需求量变化率与价格变化率之比。

    使用对数-对数回归：ln(Q) = α + β × ln(P) + ε
    β 即为价格弹性系数。
    - β < -1：弹性需求（奢侈品、可选品）
    - -1 < β < 0：非弹性需求（必需品）
    - β > 0：吉芬商品（罕见）

    Args:
        demand: 需求量（Units Sold）
        price: 价格
    Returns:
        dict: {elasticity, intercept, r_squared, p_value, n_samples}
    """
    # 去除零值和负值
    mask = (demand > 0) & (price > 0)
    q = np.log(demand[mask])
    p = np.log(price[mask])

    if len(q) < 10:
        return {'elasticity': None, 'error': f'insufficient data (n={len(q)})'}

    slope, intercept, r_value, p_value, std_err = stats.linregress(p, q)

    return {
        'elasticity': round(slope, 4),
        'intercept': round(intercept, 4),
        'r_squared': round(r_value ** 2, 4),
        'p_value': round(p_value, 4),
        'significant': p_value < 0.05,
        'n_samples': int(len(q)),
        'demand_type': 'elastic' if slope < -1 else 'inelastic' if slope < 0 else 'giffen'
    }


def calculate_cross_elasticity(
    demand: np.ndarray,
    own_price: np.ndarray,
    competitor_price: np.ndarray
) -> dict:
    """交叉价格弹性 — 需求量变化率与竞争者价格变化率之比。

    ln(Q) = α + β₁ × ln(P_own) + β₂ × ln(P_comp) + ε
    β₂ > 0：替代品（竞品涨价→我方需求增加）
    β₂ < 0：互补品

    Returns:
        dict: {own_elasticity, cross_elasticity, r_squared, p_value_cross}
    """
    mask = (demand > 0) & (own_price > 0) & (competitor_price > 0)
    q = np.log(demand[mask])
    p_own = np.log(own_price[mask])
    p_comp = np.log(competitor_price[mask])

    if len(q) < 10:
        return {'cross_elasticity': None, 'error': f'insufficient data (n={len(q)})'}

    # 多元回归
    X = np.column_stack([np.ones(len(q)), p_own, p_comp])
    try:
        coeffs, residuals, rank, sv = np.linalg.lstsq(X, q, rcond=None)
        # 简单R²
        q_pred = X @ coeffs
        ss_res = np.sum((q - q_pred) ** 2)
        ss_tot = np.sum((q - np.mean(q)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        return {
            'own_elasticity': round(float(coeffs[1]), 4),
            'cross_elasticity': round(float(coeffs[2]), 4),
            'r_squared': round(float(r_squared), 4),
            'n_samples': int(len(q)),
            'relationship': 'substitute' if coeffs[2] > 0 else 'complement'
        }
    except np.linalg.LinAlgError:
        return {'cross_elasticity': None, 'error': 'linear algebra error'}


def calculate_promotional_lift(
    baseline_sales: np.ndarray,
    promo_sales: np.ndarray
) -> dict:
    """促销提升效果 — 促销期销量相比基线期的提升幅度。

    Lift = (promo_avg - baseline_avg) / baseline_avg × 100%

    使用 Welch's t-test 检验提升是否统计显著。
    典型提升：15-40%（标准促销），80-200%（促销+陈列+海报）

    Args:
        baseline_sales: 非促销期的销量（对照组）
        promo_sales: 促销期的销量（实验组）
    Returns:
        dict: {lift_pct, t_statistic, p_value, significant, baseline_avg, promo_avg}
    """
    baseline_avg = np.mean(baseline_sales)
    promo_avg = np.mean(promo_sales)

    if baseline_avg == 0:
        return {'lift_pct': None, 'error': 'baseline average is zero'}

    lift_pct = float((promo_avg - baseline_avg) / baseline_avg * 100)

    # Welch's t-test
    if len(baseline_sales) >= 2 and len(promo_sales) >= 2:
        t_stat, p_value = stats.ttest_ind(promo_sales, baseline_sales, equal_var=False)
    else:
        t_stat, p_value = None, None

    return {
        'lift_pct': round(lift_pct, 2),
        't_statistic': round(float(t_stat), 4) if t_stat is not None else None,
        'p_value': round(float(p_value), 4) if p_value is not None else None,
        'significant': p_value < 0.05 if p_value is not None else None,
        'baseline_avg': round(float(baseline_avg), 2),
        'promo_avg': round(float(promo_avg), 2),
        'baseline_n': len(baseline_sales),
        'promo_n': len(promo_sales),
    }


def calculate_roi(
    incremental_revenue: float,
    promo_cost: float
) -> dict:
    """促销 ROI — 促销活动的投资回报率。

    ROI = (增量收入 - 促销成本) / 促销成本
    ROI > 1：每投入1元，回收 > 2元
    ROI > 0：正向回报
    ROI < 0：亏损

    Args:
        incremental_revenue: 促销带来的增量收入
        promo_cost: 促销总成本（折扣让利 + 增量库存成本 + 营销费用）
    Returns:
        dict: {roi, is_positive}
    """
    if promo_cost == 0:
        return {'roi': float('inf'), 'is_positive': True, 'note': 'zero cost'}
    roi = float(incremental_revenue / promo_cost)
    return {
        'roi': round(roi, 2),
        'is_positive': roi > 0,
        'roi_gt_1': roi > 1,
        'net_return': round(float(incremental_revenue - promo_cost), 2)
    }


def calculate_revenue_uplift(
    current_revenue: float,
    optimized_revenue: float
) -> dict:
    """收入提升 — 优化定价方案相比当前方案的收入变化。

    Args:
        current_revenue: 当前定价下的收入
        optimized_revenue: 推荐定价下的预期收入
    Returns:
        dict: {uplift_pct, uplift_absolute, is_positive}
    """
    if current_revenue == 0:
        return {'uplift_pct': None, 'error': 'current revenue is zero'}
    uplift_abs = float(optimized_revenue - current_revenue)
    uplift_pct = float(uplift_abs / current_revenue * 100)
    return {
        'uplift_pct': round(uplift_pct, 2),
        'uplift_absolute': round(uplift_abs, 2),
        'is_positive': uplift_abs > 0
    }
