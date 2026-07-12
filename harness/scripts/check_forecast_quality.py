"""🟠 案例专用 — 当前案例：库存分析
切换案例时，请根据新业务需求替换或修订此脚本。

预测质量硬校验脚本
检查预测模型是否显著优于内置基线，以及是否存在系统性偏差。
"""

import sys
import json
import os


def check_forecast_quality(results_path: str, baseline_wmape: float = None) -> dict:
    """校验预测模型质量。

    Args:
        results_path: 预测结果 JSON 文件路径，格式为 evaluate_forecast() 的输出
        baseline_wmape: 内置基线 WMAPE，若未提供则从数据集中估算
    Returns:
        dict: {passed, checks, recommendations}
    """
    checks = []
    all_passed = True

    # 1. 加载结果
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {
            'passed': False,
            'checks': [{'name': 'load_results', 'passed': False, 'detail': str(e)}],
            'recommendations': ['请确认预测结果文件存在且为有效 JSON']
        }

    # 如果 results 是单个模型，转为列表
    if isinstance(results, dict):
        models = [results]
    else:
        models = results

    # 2. 检查是否有模型优于内置基线
    if baseline_wmape is not None:
        better_than_baseline = any(
            m.get('WMAPE', float('inf')) < baseline_wmape
            for m in models
        )
        checks.append({
            'name': 'better_than_baseline',
            'passed': better_than_baseline,
            'detail': f'基线 WMAPE={baseline_wmape}%, 模型 WMAPE={[m.get("WMAPE") for m in models]}',
            'threshold': f'WMAPE < {baseline_wmape}%'
        })
        if not better_than_baseline:
            all_passed = False
    else:
        checks.append({
            'name': 'better_than_baseline',
            'passed': None,
            'detail': '未提供基线 WMAPE，跳过对比检查。请从数据集的 Demand Forecast 字段计算基线 WMAPE。'
        })

    # 3. 检查 Bias 是否在 ±5% 以内
    for m in models:
        bias = m.get('Bias', 0)
        bias_ok = abs(bias) <= 5.0
        checks.append({
            'name': f'bias_check_{m.get("model", "unknown")}',
            'passed': bias_ok,
            'detail': f'{m.get("model")}: Bias={bias}%',
            'threshold': '|Bias| ≤ 5%'
        })
        if not bias_ok:
            all_passed = False

    # 4. 检查是否至少对比了 3 种模型
    model_count = len(models)
    enough_models = model_count >= 3
    checks.append({
        'name': 'model_count',
        'passed': enough_models,
        'detail': f'共 {model_count} 个模型',
        'threshold': '≥ 3 个模型'
    })
    if not enough_models:
        all_passed = False

    # 生成建议
    recommendations = []
    if not enough_models:
        recommendations.append(f'当前仅 {model_count} 个模型，建议至少对比 3 种方法（如 ARIMA + XGBoost + Prophet）')
    for m in models:
        if m.get('Bias', 0) > 5:
            recommendations.append(f'{m.get("model")} 存在正向偏差（高估），有库存积压风险')
        elif m.get('Bias', 0) < -5:
            recommendations.append(f'{m.get("model")} 存在负向偏差（低估），有缺货风险')

    return {
        'passed': all_passed,
        'checks': checks,
        'recommendations': recommendations
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    baseline = float(sys.argv[2]) if len(sys.argv) > 2 else None

    if path is None:
        print("Usage: python check_forecast_quality.py <results.json> [baseline_wmape]")
        sys.exit(0)

    result = check_forecast_quality(path, baseline)

    print("=" * 50)
    print("  预测质量校验")
    print("=" * 50)
    for c in result['checks']:
        icon = "✅" if c['passed'] else ("⚠️" if c['passed'] is None else "❌")
        print(f"  {icon} {c['name']}: {c['detail']}")

    if result['recommendations']:
        print("\n  💡 建议:")
        for r in result['recommendations']:
            print(f"     - {r}")

    print(f"\n  总结果: {'✅ 通过' if result['passed'] else '❌ 未通过'}")

    # 始终 exit(0) — 校验结果由 reviewer 判断，脚本不阻塞
    sys.exit(0)
