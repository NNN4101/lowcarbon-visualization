"""
verify_data_quality.py
版本：v2.0（适配 process_all_v4_fixed.py）
功能：
 - 检查 processed / derived / meta 各文件完整性与一致性；
 - 验证时间区间、字段、数据逻辑；
 - 检测预测值区间合理性；
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path

# ===== 路径配置 =====
BASE = Path(r"D:\coding\project\lowcarbon_visualization\backend\data")
PROC = BASE / "processed"
DER  = BASE / "derived"
META = BASE / "meta"

# ===== 工具函数 =====
def safe_read(path):
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def check_exists():
    print("\n📁【文件存在性检查】")
    required = [
        ("province_emission.csv", PROC, ["province","year","emission_total","emission_per_gdp","is_imputed_emission"]),
        ("province_energy.csv", PROC, ["clean_ratio","fossil_ratio"]),
        ("province_green.csv", PROC, ["green_rate","forest_area"]),
        ("province_combined.csv", PROC, ["clean_ratio","green_rate","emission_per_gdp"]),
        ("province_standardized.csv", DER, ["energy_index","eco_index","efficiency_index"]),
        ("province_synergy_index.csv", DER, ["synergy_score"]),
        ("province_relation.csv", DER, ["correlation"]),
        ("province_trend.csv", DER, ["clean_ratio","green_rate","emission_per_gdp"]),
        ("province_delta.csv", DER, ["Δenergy","Δgreen","Δemission"]),
        ("policy_timeline.csv", DER, ["policy_name","category","level"]),
        ("cluster_result.csv", DER, ["cluster_type"]),
        ("cluster_summary.csv", DER, ["mean_energy","mean_eco","mean_efficiency"]),
        ("model_output.csv", DER, ["predicted_emission_per_gdp","scenario_name"]),
        ("data_sources.json", META, []),
        ("variable_dict.json", META, []),
    ]

    missing = False
    for name, folder, fields in required:
        path = folder / name
        if not path.exists():
            print(f"{name:<30} ❌ 缺失")
            missing = True
        else:
            df = safe_read(path)
            if len(fields) > 0:
                if all(f in df.columns for f in fields):
                    print(f"{name:<30} ✅")
                else:
                    print(f"{name:<30} ⚠️ 字段不全 {set(fields)-set(df.columns)}")
                    missing = True
            else:
                print(f"{name:<30} ✅")
    return not missing


def check_time_ranges():
    print("\n📆【时间区间检查】")
    checks = [
        ("province_emission.csv", PROC, (2003,2022)),
        ("province_energy.csv", PROC, (2003,2022)),
        ("province_green.csv", PROC, (2005,2023)),
        ("province_combined.csv", PROC, (2005,2022)),
    ]
    for name, folder, (start, end) in checks:
        df = safe_read(folder / name)
        if df.empty or "year" not in df.columns: continue
        years = df["year"].dropna().astype(int)
        if years.min() <= start and years.max() >= end:
            print(f"{name:<30} ✅ {years.min()}–{years.max()}")
        else:
            print(f"{name:<30} ⚠️ 年份区间异常 {years.min()}–{years.max()}")


def check_province_coverage():
    print("\n🗺️【省份覆盖检查】")
    df = safe_read(PROC / "province_combined.csv")
    if not df.empty:
        provinces = df["province"].nunique()
        mark = "✅" if provinces >= 31 else "⚠️ 不足"
        print(f"共 {provinces} 个省份（{mark}）")
    else:
        print("❌ 无法读取 province_combined.csv")


def check_logic_consistency():
    print("\n🧩【逻辑一致性检查】")

    # (1) fossil+clean≈1
    energy = safe_read(PROC / "province_energy.csv")
    if not energy.empty:
        energy["sum"] = energy["clean_ratio"] + energy["fossil_ratio"]
        ok = (abs(energy["sum"]-1) < 0.01).mean()*100
        print(f"clean+fossil≈1 正确率 {ok:.1f}% {'✅' if ok>95 else '⚠️'}")

    # (2) Z-score 均值≈0
    std = safe_read(DER / "province_standardized.csv")
    if not std.empty:
        zs = {c: round(std[c].mean(),3) for c in ["energy_index","eco_index","efficiency_index"]}
        print(f"Z-score 均值 {zs} {'✅' if all(abs(v)<0.05 for v in zs.values()) else '⚠️'}")

    # (3) 协同相关方向
    rel = safe_read(DER / "province_relation.csv")
    if not rel.empty:
        sub = rel.query("year==2022")
        corr = sub.pivot(index="variable_x",columns="variable_y",values="correlation")
        if all(x in corr.columns for x in ["clean_ratio","green_rate","emission_per_gdp"]):
            c1, c2, c3 = corr.loc["clean_ratio","emission_per_gdp"], corr.loc["green_rate","emission_per_gdp"], corr.loc["clean_ratio","green_rate"]
            mark = "✅ 合理" if (c1<0 and c2<0 and c3>0) else "⚠️ 异常"
            print(f"协同相关: clean={c3:.2f}, green={c2:.2f}, emission={c1:.2f} → {mark}")

    # (4) 预测值合理性
    pred = safe_read(DER / "model_output.csv")
    if not pred.empty:
        minv, maxv = pred["predicted_emission_per_gdp"].min(), pred["predicted_emission_per_gdp"].max()
        if 0.02 <= minv and maxv <= 0.5:
            print(f"预测值范围 {minv:.3f}–{maxv:.3f} ✅ 合理")
        else:
            print(f"⚠️ 预测值异常 {minv:.3f}–{maxv:.3f}")


def generate_report():
    import sys
    from io import StringIO
    backup_stdout = sys.stdout
    sys.stdout = report = StringIO()

    check_exists()
    check_time_ranges()
    check_province_coverage()
    check_logic_consistency()

    sys.stdout = backup_stdout
    text = report.getvalue()
    (BASE / "verify_report_v2.txt").write_text(text, encoding="utf-8")
    print(text)
    print("✅ 验证报告已生成：verify_report_v2.txt")

if __name__ == "__main__":
    generate_report()
