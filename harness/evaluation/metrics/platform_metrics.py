"""ChatBI 平台通用评估指标

适用于所有业务案例，不随案例变化。
评估维度：数据质量、意图解析、结果一致性、输出完整性。
"""

import numpy as np
import pandas as pd
from typing import Optional


# ═══════════════════════════════════════════════════════════
# 数据质量
# ═══════════════════════════════════════════════════════════

def data_completeness(df: pd.DataFrame) -> dict:
    """计算数据完整性——每列的缺失比例。

    Returns:
        dict: {column_name: missing_ratio}，ratio=0表示完整
    """
    missing = df.isnull().sum()
    total = len(df)
    return {col: round(missing[col] / total, 4) for col in df.columns}


def data_uniqueness(df: pd.DataFrame, key_columns: Optional[list] = None) -> dict:
    """检查数据唯一性。

    Args:
        df: 数据DataFrame
        key_columns: 主键列列表，如 ['Store ID', 'Product ID', 'Date']
    Returns:
        dict: {total_rows, unique_rows, duplicate_rows, is_unique}
    """
    if key_columns:
        subset = df[key_columns]
    else:
        subset = df

    total = len(df)
    unique = len(subset.drop_duplicates())
    dupes = total - unique

    return {
        'total_rows': total,
        'unique_rows': unique,
        'duplicate_rows': dupes,
        'is_unique': dupes == 0
    }


def data_range_validity(df: pd.DataFrame, ranges: dict) -> dict:
    """检查各列数值是否在定义范围内。

    Args:
        df: 数据DataFrame
        ranges: {column: (min, max)} 范围定义
    Returns:
        dict: {column: {total, out_of_range, ratio}}
    """
    result = {}
    for col, (lo, hi) in ranges.items():
        if col not in df.columns:
            result[col] = {'error': 'column not found'}
            continue
        series = df[col]
        out = ((series < lo) | (series > hi)).sum()
        result[col] = {
            'total': len(series),
            'out_of_range': int(out),
            'ratio': round(out / len(series), 4),
            'range': (lo, hi)
        }
    return result


# ═══════════════════════════════════════════════════════════
# 意图解析准确性
# ═══════════════════════════════════════════════════════════

def intent_parsing_coverage(intent: dict) -> dict:
    """检查意图解析的完整性——是否所有关键字段都被提取。

    Args:
        intent: intent_parser 输出的结构化意图
    Returns:
        dict: {field: present}
    """
    required_fields = ['analysis_type', 'metrics', 'dimensions', 'output_type']
    return {f: bool(intent.get(f)) for f in required_fields}


def intent_field_match(intent_metrics: list, data_columns: list) -> dict:
    """检查意图中的指标是否都能映射到数据字段。

    Args:
        intent_metrics: intent_parser 输出的指标列表
        data_columns: 实际数据表的列名列表
    Returns:
        dict: {matched, unmatched, match_rate}
    """
    matched = [m for m in intent_metrics if any(
        m.lower() in col.lower() or col.lower() in m.lower()
        for col in data_columns
    )]
    unmatched = [m for m in intent_metrics if m not in matched]
    return {
        'matched': matched,
        'unmatched': unmatched,
        'match_rate': round(len(matched) / max(len(intent_metrics), 1), 2)
    }


# ═══════════════════════════════════════════════════════════
# 跨阶段一致性
# ═══════════════════════════════════════════════════════════

def check_kpi_consistency(kpi_values: dict) -> dict:
    """检查同一KPI在不同阶段的输出是否一致。

    Args:
        kpi_values: {
            'kpi_name': {
                'phase_X': value_from_phase_X,
                'phase_Y': value_from_phase_Y
            }
        }
    Returns:
        dict: {kpi_name: {consistent, max_diff_pct}}
    """
    result = {}
    for kpi_name, phase_values in kpi_values.items():
        vals = list(phase_values.values())
        if len(vals) < 2:
            result[kpi_name] = {'consistent': True, 'note': 'single source'}
            continue
        max_val = max(vals)
        min_val = min(vals)
        if max_val == 0:
            diff_pct = abs(max_val - min_val)
        else:
            diff_pct = round(abs(max_val - min_val) / max_val * 100, 2)

        result[kpi_name] = {
            'consistent': diff_pct < 1.0,
            'max_diff_pct': diff_pct,
            'values': phase_values
        }
    return result


def check_caliber_traceability(report_sections: list, data_spec_path: str) -> dict:
    """检查报告中的指标是否有口径来源标注。

    Args:
        report_sections: 报告各章节内容
        data_spec_path: data_spec.md 路径
    Returns:
        dict: {section: has_caliber_ref}
    """
    # 简化版：检查是否引用了data_spec
    has_ref = "data_spec" in " ".join(report_sections).lower()
    return {
        'has_data_spec_reference': has_ref,
        'sections_checked': len(report_sections)
    }


# ═══════════════════════════════════════════════════════════
# 输出完整性
# ═══════════════════════════════════════════════════════════

def check_output_completeness(outputs: dict) -> dict:
    """检查ChatBI的三类产物是否生成。

    Args:
        outputs: {output_type: file_path_or_none}
    Returns:
        dict: {output_type: generated}
    """
    required = ['dashboard', 'pdf_report', 'data_file']
    return {
        o: bool(outputs.get(o))
        for o in required
    }
