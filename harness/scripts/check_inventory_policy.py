"""🟠 案例专用 — 当前案例：库存分析
切换案例时，请根据新业务需求替换或修订此脚本。

库存策略合理性硬校验脚本
检查推荐的库存策略是否满足服务水平要求，以及是否存在积压或过度库存。
"""

import sys
import json
import os


def check_inventory_policy(policy_path: str) -> dict:
    """校验库存策略合理性。

    Args:
        policy_path: 库存策略结果 JSON 文件路径
            格式: {
                "skus": [
                    {
                        "product_id": "P0001",
                        "abc_class": "A",
                        "xyz_class": "X",
                        "service_level": 0.975,
                        "weeks_of_supply": 6.0,
                        "safety_stock": 120,
                        "rop": 350,
                        "eoq": 200
                    },
                    ...
                ]
            }
    Returns:
        dict: {passed, checks, recommendations}
    """
    checks = []
    all_passed = True

    # 1. 加载策略
    try:
        with open(policy_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {
            'passed': False,
            'checks': [{'name': 'load_policy', 'passed': False, 'detail': str(e)}],
            'recommendations': ['请确认库存策略文件存在且为有效 JSON']
        }

    skus = data.get('skus', [])
    if not skus:
        return {
            'passed': False,
            'checks': [{'name': 'has_data', 'passed': False, 'detail': '策略数据为空'}],
            'recommendations': ['请确认策略文件包含 skus 数据']
        }

    # 2. 按 ABC 类别检查 SL 目标
    sl_targets = {
        'A': 0.97,
        'B': 0.95,
        'C': 0.90
    }

    sl_violations = []
    for sku in skus:
        abc = sku.get('abc_class', 'B')
        actual_sl = sku.get('service_level', 0)
        target = sl_targets.get(abc, 0.95)
        if actual_sl < target:
            sl_violations.append({
                'product_id': sku.get('product_id'),
                'abc_class': abc,
                'actual_sl': actual_sl,
                'target_sl': target
            })

    sl_ok = len(sl_violations) == 0
    checks.append({
        'name': 'service_level_targets',
        'passed': sl_ok,
        'detail': f'{len(sl_violations)} 个 SKU 未达到 SL 目标' if sl_violations else '所有 SKU 满足 SL 目标',
        'violations': sl_violations[:5]  # 只展示前5个
    })
    if not sl_ok:
        all_passed = False

    # 3. 检查 C 类品是否有 > 26 周的积压
    excess_c = [
        s for s in skus
        if s.get('abc_class') == 'C' and s.get('weeks_of_supply', 0) > 26
    ]
    excess_ok = len(excess_c) == 0
    checks.append({
        'name': 'c_class_no_excess',
        'passed': excess_ok,
        'detail': f'{len(excess_c)} 个 C 类 SKU 库存 > 26 周' if excess_c else 'C 类品无过度积压',
        'threshold': 'C类库存周数 ≤ 26'
    })
    if not excess_ok:
        all_passed = False

    # 4. 检查全部 SKU 是否有 > 26 周的积压
    all_excess = [s for s in skus if s.get('weeks_of_supply', 0) > 26]
    excess_ratio = len(all_excess) / len(skus) if skus else 0
    excess_ratio_ok = excess_ratio < 0.05
    checks.append({
        'name': 'excess_ratio',
        'passed': excess_ratio_ok,
        'detail': f'{excess_ratio:.1%} SKU 库存 > 26 周 ({len(all_excess)}/{len(skus)})',
        'threshold': '< 5%'
    })
    if not excess_ratio_ok:
        all_passed = False

    # 5. 检查安全库存非负
    negative_ss = [s for s in skus if s.get('safety_stock', 0) < 0]
    ss_ok = len(negative_ss) == 0
    checks.append({
        'name': 'safety_stock_non_negative',
        'passed': ss_ok,
        'detail': f'{len(negative_ss)} 个 SKU 安全库存为负' if negative_ss else '所有安全库存 ≥ 0',
    })
    if not ss_ok:
        all_passed = False

    # 生成建议
    recommendations = []
    if sl_violations:
        recommendations.append(f'{len(sl_violations)} 个 SKU 服务水平未达标，请调整安全库存或补货策略')
    if excess_c:
        recommendations.append(f'{len(excess_c)} 个 C 类商品库存 > 26 周，建议启动清仓评估')
    if excess_ratio > 0.05:
        recommendations.append(f'{excess_ratio:.1%} 的 SKU 存在积压，建议审查库存策略')

    return {
        'passed': all_passed,
        'checks': checks,
        'recommendations': recommendations
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None

    if path is None:
        print("Usage: python check_inventory_policy.py <policy.json>")
        sys.exit(0)

    result = check_inventory_policy(path)

    print("=" * 50)
    print("  库存策略合理性校验")
    print("=" * 50)
    for c in result['checks']:
        icon = "✅" if c['passed'] else "❌"
        print(f"  {icon} {c['name']}: {c['detail']}")
        if c.get('violations'):
            for v in c['violations']:
                print(f"      - {v}")

    if result['recommendations']:
        print("\n  💡 建议:")
        for r in result['recommendations']:
            print(f"     - {r}")

    print(f"\n  总结果: {'✅ 通过' if result['passed'] else '❌ 未通过'}")
    sys.exit(0)
