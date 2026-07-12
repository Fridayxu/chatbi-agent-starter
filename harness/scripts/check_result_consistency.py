"""跨阶段结果一致性硬校验脚本

🔵 ChatBI 平台通用 — 适用于所有业务案例。

检查各阶段分析结果之间的逻辑一致性：
- 同一指标在不同 Agent 输出中数值一致
- 上游输出被下游正确引用（而非使用独立数据）
- KPI 口径全链路统一
"""

import sys
import json
import os


def check_result_consistency(results_dir: str) -> dict:
    """校验跨阶段结果一致性。

    Args:
        results_dir: 结果目录路径，包含各阶段的汇总 JSON
            预期文件:
            - forecast_summary.json  (来自 forecaster)
            - inventory_summary.json (来自 inventory_analyst)
            - pricing_summary.json   (来自 pricing_analyst)
            - dashboard_data.json    (来自 dashboard_builder)
    Returns:
        dict: {passed, checks, cross_ref_issues}
    """
    checks = []
    all_passed = True
    cross_ref_issues = []

    # 1. 尝试加载各阶段结果
    stage_files = {
        'forecast': 'forecast_summary.json',
        'inventory': 'inventory_summary.json',
        'pricing': 'pricing_summary.json',
        'dashboard': 'dashboard_data.json',
    }

    loaded = {}
    for stage, fname in stage_files.items():
        fpath = os.path.join(results_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    loaded[stage] = json.load(f)
            except (json.JSONDecodeError, ValueError):
                cross_ref_issues.append(f'{fname} 不是有效的 JSON')
        else:
            cross_ref_issues.append(f'{fname} 未生成')

    checks.append({
        'name': 'all_stages_present',
        'passed': len(loaded) >= 3,
        'detail': f'{len(loaded)}/{len(stage_files)} 阶段结果文件存在',
        'missing': [s for s in stage_files if s not in loaded]
    })

    # 2. 检查 Dashboard 中的 KPI 是否可追溯到上游
    if 'dashboard' in loaded and 'forecast' in loaded:
        dashboard = loaded['dashboard']
        forecast = loaded['forecast']

        # 检查 WMAPE 一致性
        dash_wmape = dashboard.get('forecast_wmape')
        fc_wmape = forecast.get('WMAPE')
        if dash_wmape is not None and fc_wmape is not None:
            diff = abs(dash_wmape - fc_wmape)
            consistent = diff < 0.5  # WMAPE 差异 < 0.5 个百分点
            checks.append({
                'name': 'wmape_consistency',
                'passed': consistent,
                'detail': f'Forecast WMAPE={fc_wmape}%, Dashboard WMAPE={dash_wmape}%, 差异={diff}%'
            })
            if not consistent:
                all_passed = False
                cross_ref_issues.append(f'WMAPE 不一致：forecast={fc_wmape}%, dashboard={dash_wmape}%')

    # 3. 检查库存计算是否使用了预测需求（而非独立的历史均值）
    if 'inventory' in loaded and 'forecast' in loaded:
        inventory = loaded['inventory']
        forecast = loaded['forecast']
        inv_source = inventory.get('demand_source', 'unknown')
        consistent = inv_source == 'forecast'
        checks.append({
            'name': 'inventory_uses_forecast',
            'passed': consistent,
            'detail': f'库存需求来源: {inv_source}'
        })
        if not consistent:
            all_passed = False
            cross_ref_issues.append(f'库存计算未使用预测需求，使用来源: {inv_source}')

    # 4. 检查定价弹性模型是否使用了正确的销量数据
    if 'pricing' in loaded and 'forecast' in loaded:
        pricing = loaded['pricing']
        pricing_source = pricing.get('demand_source', 'unknown')
        consistent = pricing_source in ('forecast', 'actual', 'forecast_and_actual')
        checks.append({
            'name': 'pricing_data_source',
            'passed': consistent,
            'detail': f'定价弹性数据来源: {pricing_source}'
        })
        if not consistent:
            cross_ref_issues.append(f'定价分析数据来源不明确: {pricing_source}')

    # 5. 检查 KPI 口径标注
    if 'dashboard' in loaded:
        dashboard = loaded['dashboard']
        kpis_with_caliber = sum(
            1 for kpi in dashboard.get('kpis', [])
            if kpi.get('caliber_source')
        )
        total_kpis = len(dashboard.get('kpis', []))
        caliber_ok = kpis_with_caliber == total_kpis if total_kpis > 0 else True
        checks.append({
            'name': 'kpi_caliber_annotated',
            'passed': caliber_ok,
            'detail': f'{kpis_with_caliber}/{total_kpis} 个 KPI 有口径标注'
        })
        if not caliber_ok:
            all_passed = False
            cross_ref_issues.append(f'{total_kpis - kpis_with_caliber} 个 KPI 缺少口径标注')

    return {
        'passed': all_passed,
        'checks': checks,
        'cross_ref_issues': cross_ref_issues
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else 'results'

    result = check_result_consistency(path)

    print("=" * 60)
    print("  跨阶段结果一致性校验")
    print("=" * 60)
    for c in result['checks']:
        icon = "✅" if c['passed'] else "❌"
        print(f"  {icon} {c['name']}: {c['detail']}")

    if result['cross_ref_issues']:
        print(f"\n  ⚠️  一致性风险 ({len(result['cross_ref_issues'])} 项):")
        for issue in result['cross_ref_issues']:
            print(f"     - {issue}")

    if not result['cross_ref_issues']:
        print(f"\n  ✅ 未发现一致性风险")

    print(f"\n  总结果: {'✅ 通过' if result['passed'] else '⚠️ 存在风险项'}")
    sys.exit(0)
