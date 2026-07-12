"""数据完整性硬校验脚本 —— 不可绕过"""
import pandas as pd
import sys

def check_data_integrity(filepath: str) -> bool:
    """校验原始数据完整性"""
    # TODO: 行数校验、列数校验、列类型校验、缺失值校验、值范围校验、重复行校验
    df = pd.read_csv(filepath)
    assert df.shape == (73100, 15), f"Expected (73100, 15), got {df.shape}"
    assert df.isnull().sum().sum() == 0, "Null values found"
    print("PASS: data integrity check")
    return True

if __name__ == "__main__":
    sys.exit(0 if check_data_integrity(sys.argv[1]) else 1)
