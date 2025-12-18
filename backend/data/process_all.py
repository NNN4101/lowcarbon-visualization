"""
process_all_v4_final_fixed.py
版本：v4.4
更新说明：
- 替换 ElasticNet 为 LinearRegression，解决预测值恒定问题；
- 保留标准化、插值与均值填充；
- 输出结构严格符合系统方案要求；
- 保留日志输出与容错逻辑。
"""

import os, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# ===== 路径配置 =====
BASE = Path(r"D:\coding\project\lowcarbon_visualization\backend\data")
RAW = BASE / "province_raw"
PROC = BASE / "processed"
DER  = BASE / "derived"
META = BASE / "meta"

YEARS_COMBINED = range(2005, 2023)
YEARS_EMI_EN   = range(2003, 2023)
YEARS_GREEN    = range(2005, 2024)

def ensure_dirs():
    for d in [PROC, DER, META]:
        d.mkdir(parents=True, exist_ok=True)

def normalize_province(s):
    if not isinstance(s, str): return s
    s = s.strip().replace("省","").replace("市","")
    rep = {
        "内蒙古自治区":"内蒙古","广西壮族自治区":"广西","西藏自治区":"西藏",
        "宁夏回族自治区":"宁夏","新疆维吾尔自治区":"新疆","黑龙江省":"黑龙江",
        "北京市":"北京","天津市":"天津","上海市":"上海","重庆市":"重庆"
    }
    for k,v in rep.items(): s=s.replace(k,v)
    return s

def load_csv(name):
    p = RAW / name
    df = pd.read_csv(p)
    if "province" in df.columns:
        df["province"] = df["province"].map(normalize_province)
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df

def fossil_from_clean(df):
    df["fossil_ratio"] = 1 - df["clean_ratio"]
    df["fossil_ratio"] = df["fossil_ratio"].clip(0,1)
    return df

def zscore_by_year(df, cols):
    out = df.copy()
    for c in cols:
        out[c+"_z"] = out.groupby("year")[c].transform(lambda x: (x-x.mean())/x.std(ddof=0))
    return out

def main():
    ensure_dirs()
    print("🚀 数据处理开始...")
    emission = load_csv("emission_raw.csv")
    energy   = load_csv("energy_raw.csv")
    green    = load_csv("green_raw.csv")
    gdp      = load_csv("gdp_raw.csv")
    pop      = load_csv("population_raw.csv")
    policy   = load_csv("policy_events.csv")

    for df in [emission,energy,green,gdp,pop]:
        for c in df.columns:
            if c not in ["province","year"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")

    energy = fossil_from_clean(energy)

    # --- 排放外推 ---
    merged = (
        energy[["province","year","total_energy_consumption_std_coal_mt","fossil_ratio"]]
        .merge(emission,on=["province","year"],how="left")
    )
    out_rows=[]
    for p,g in merged.groupby("province"):
        g=g.dropna(subset=["emission_total_mt","total_energy_consumption_std_coal_mt"])
        if len(g)<8: continue
        X=g[["total_energy_consumption_std_coal_mt","fossil_ratio"]].prod(axis=1).values.reshape(-1,1)
        y=g["emission_total_mt"].values
        m=LinearRegression().fit(X,y)
        for yv in [2020,2021,2022]:
            row=energy.query("province==@p and year==@yv")
            if not row.empty:
                driver=(row["total_energy_consumption_std_coal_mt"]*row["fossil_ratio"]).values
                pred=m.predict(driver.reshape(-1,1))
                out_rows.append([p,yv,float(pred[0]),1])
    extra=pd.DataFrame(out_rows,columns=["province","year","emission_total_mt","is_imputed_emission"])
    emission["is_imputed_emission"]=0
    emission=pd.concat([emission,extra],ignore_index=True)

    merged=(emission.merge(gdp,on=["province","year"],how="left")
                    .merge(pop,on=["province","year"],how="left"))
    merged["emission_per_gdp"]=merged["emission_total_mt"]/merged["gdp_billion_cny"]
    merged["per_capita_t"]=(merged["emission_total_mt"]*1e6)/(merged["population_million"]*1e6)
    emi=merged.loc[:,["province","year","emission_total_mt","emission_per_gdp","per_capita_t","is_imputed_emission"]].copy()
    emi.rename(columns={"emission_total_mt":"emission_total"}, inplace=True)
    emi.to_csv(PROC/"province_emission.csv",index=False,encoding="utf-8-sig")

    energy.loc[:,["province","year","clean_ratio","fossil_ratio","total_energy_consumption_std_coal_mt"]].to_csv(
        PROC/"province_energy.csv",index=False,encoding="utf-8-sig")
    green.rename(columns={"forest_area_km2":"forest_area"},inplace=True)
    green.loc[:,["province","year","green_rate","forest_area"]].to_csv(
        PROC/"province_green.csv",index=False,encoding="utf-8-sig")

    comb=(emi.merge(energy,on=["province","year"],how="left")
             .merge(green,on=["province","year"],how="left"))
    comb=comb[(comb["year"]>=2005)&(comb["year"]<=2022)]
    comb.loc[:,["province","year","emission_per_gdp","clean_ratio","green_rate"]].to_csv(
        PROC/"province_combined.csv",index=False,encoding="utf-8-sig")

    # --- Z-score + 协同指数 ---
    std=zscore_by_year(comb,["clean_ratio","green_rate","emission_per_gdp"])
    std["energy_index"]=std["clean_ratio_z"]
    std["eco_index"]=std["green_rate_z"]
    std["efficiency_index"]=-std["emission_per_gdp_z"]
    std["synergy_score"]=0.4*std["energy_index"]+0.3*std["eco_index"]+0.3*std["efficiency_index"]
    std[["province","year","energy_index","eco_index","efficiency_index"]].to_csv(
        DER/"province_standardized.csv",index=False,encoding="utf-8-sig")
    std[["province","year","synergy_score"]].to_csv(
        DER/"province_synergy_index.csv",index=False,encoding="utf-8-sig")

    # --- 相关矩阵 ---
    rels=[]
    for y,g in comb.groupby("year"):
        corr=g[["clean_ratio","green_rate","emission_per_gdp"]].corr()
        for a in corr.columns:
            for b in corr.columns:
                rels.append({"year":int(y),"variable_x":a,"variable_y":b,"correlation":float(corr.loc[a,b])})
    pd.DataFrame(rels).to_csv(DER/"province_relation.csv",index=False,encoding="utf-8-sig")

    trend=comb[["province","year","clean_ratio","green_rate","emission_per_gdp"]].copy()
    trend.to_csv(DER/"province_trend.csv",index=False,encoding="utf-8-sig")

    delta=trend.sort_values(["province","year"]).copy()
    delta["Δenergy"]=delta.groupby("province")["clean_ratio"].diff()
    delta["Δgreen"]=delta.groupby("province")["green_rate"].diff()
    delta["Δemission"]=delta.groupby("province")["emission_per_gdp"].diff()
    delta.to_csv(DER/"province_delta.csv",index=False,encoding="utf-8-sig")

    keep=[c for c in ["province","year","policy_name","category","level"] if c in policy.columns]
    policy[keep].drop_duplicates().to_csv(DER/"policy_timeline.csv",index=False,encoding="utf-8-sig")

    # --- 聚类 ---
    latest=std.query("year==2022")[["province","energy_index","eco_index","efficiency_index","synergy_score"]].dropna()
    km=KMeans(n_clusters=4,n_init=10,random_state=42).fit(latest[["energy_index","eco_index","efficiency_index"]])
    latest["cluster_type"]=km.labels_
    latest.to_csv(DER/"cluster_result.csv",index=False,encoding="utf-8-sig")
    (latest.groupby("cluster_type")[["energy_index","eco_index","efficiency_index","synergy_score"]]
           .mean().reset_index()
           .rename(columns={"energy_index":"mean_energy","eco_index":"mean_eco","efficiency_index":"mean_efficiency"}))\
           .to_csv(DER/"cluster_summary.csv",index=False,encoding="utf-8-sig")

    # --- 预测模型（LinearRegression 改进版） ---
    trend["clean_ratio"] = trend.groupby("province")["clean_ratio"].transform(lambda x: x.interpolate(limit=3))
    trend["green_rate"]  = trend.groupby("province")["green_rate"].transform(lambda x: x.interpolate(limit=3))
    trend.fillna(trend.mean(numeric_only=True), inplace=True)

    train = trend.dropna(subset=["emission_per_gdp"])
    X, y = train[["clean_ratio","green_rate"]].values, train["emission_per_gdp"].values
    scaler = StandardScaler().fit(X)
    model = LinearRegression().fit(scaler.transform(X), y)

    last22 = trend.query("year==2022")[["province","clean_ratio","green_rate"]].dropna()
    rows = []
    for _, r in last22.iterrows():
        for year in range(2023, 2031):
            for scen, dc, dg in [("baseline", 0, 0), ("clean_plus5pp", 0.05, 0), ("green_plus2pp", 0.02, 0.02)]:
                clean = np.clip(r.clean_ratio + dc, 0, 1)
                green = np.clip(r.green_rate + dg, 0, 1)
                try:
                    pred = float(model.predict(scaler.transform([[clean, green]]))[0])
                    rows.append([r.province, year, scen, clean, green, pred])
                except Exception as e:
                    print(f"⚠️ 跳过 {r.province}-{year} ({scen}) 原因: {e}")
                    continue

    pd.DataFrame(rows, columns=["province","year","scenario_name","clean_ratio","green_rate","predicted_emission_per_gdp"])\
        .to_csv(DER/"model_output.csv", index=False, encoding="utf-8-sig")

    # --- Meta 信息 ---
    META.mkdir(exist_ok=True)
    src_info={
        "CEADs":"省级CO₂排放（2003–2019）+ 模型外推2020–2022",
        "国家能源年鉴":"能源结构与清洁能源比例",
        "住建部/统计局":"城市绿化数据",
        "统计年鉴":"GDP与人口",
        "note":"所有比例已归一化至0–1，字段含义详见 variable_dict.json"
    }
    (META/"data_sources.json").write_text(json.dumps(src_info,ensure_ascii=False,indent=2),encoding="utf-8")
    var_dict={
        "province":"省份","year":"年份","clean_ratio":"清洁能源占比","green_rate":"建成区绿化覆盖率",
        "emission_per_gdp":"单位GDP排放","energy_index":"能源标准化","eco_index":"绿化标准化",
        "efficiency_index":"效率标准化(-z)","synergy_score":"协同指数","cluster_type":"聚类类型",
        "Δenergy":"清洁能源年变动","Δgreen":"绿化率年变动","Δemission":"排放强度年变动",
        "predicted_emission_per_gdp":"模型预测值"
    }
    (META/"variable_dict.json").write_text(json.dumps(var_dict,ensure_ascii=False,indent=2),encoding="utf-8")

    print("✅ 所有文件已生成，符合方案要求。")

if __name__ == "__main__":
    main()
