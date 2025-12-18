from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
from pathlib import Path

app = Flask(__name__)
CORS(app)  # 允许前端跨域访问

# 数据目录基础路径
DATA_BASE = Path(__file__).resolve().parent / "data"


def load_csv(folder, name):
    """加载 CSV 文件，并处理 UTF-8 BOM 与列名清理"""
    path = DATA_BASE / folder / name
    if not path.exists():
        return None
    # 兼容带 BOM 的 CSV
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        df = pd.read_csv(path)
    # 列名清理：去掉不可见字符与首尾空格
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df


# —— 新增：分别提供排放、能源、绿化三个数据源 ——
@app.route("/api/emission", methods=["GET"])
def get_emission_total():
    """返回排放相关字段（含 is_imputed_emission 标记与 emission_per_gdp）"""
    df = load_csv("processed", "province_emission.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    province = request.args.get("province")
    year = request.args.get("year", type=int)
    # 尽可能包含可用字段：emission_total、emission_per_gdp、is_imputed_emission
    cols = [c for c in ["province", "year", "emission_total", "emission_per_gdp", "is_imputed_emission"] if c in df.columns]
    df = df[cols]
    if province:
        df = df[df["province"] == province]
    if year is not None:
        df = df[df["year"] == year]
    return df.to_json(orient="records", force_ascii=False)


@app.route("/api/energy", methods=["GET"])
def get_energy_ratio():
    """返回清洁能源比例（province_energy.csv 的 clean_ratio 字段）"""
    df = load_csv("processed", "province_energy.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    province = request.args.get("province")
    year = request.args.get("year", type=int)
    cols = ["province", "year", "clean_ratio"]
    df = df[cols]
    if province:
        df = df[df["province"] == province]
    if year is not None:
        df = df[df["year"] == year]
    return df.to_json(orient="records", force_ascii=False)


@app.route("/api/green", methods=["GET"])
def get_green_rate():
    """返回绿化覆盖率（province_green.csv 的 green_rate 字段）"""
    df = load_csv("processed", "province_green.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    province = request.args.get("province")
    year = request.args.get("year", type=int)
    cols = ["province", "year", "green_rate"]
    # 一些年份可能缺失 green_rate，保留空值以便前端处理
    df = df[cols]
    if province:
        df = df[df["province"] == province]
    if year is not None:
        df = df[df["year"] == year]
    return df.to_json(orient="records", force_ascii=False)


@app.route("/api/province", methods=["GET"])
def get_province_data():
    """返回综合指标表（province_combined.csv）"""
    df = load_csv("processed", "province_combined.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404

    province = request.args.get("province")
    if province:
        df = df[df["province"] == province]

    return df.to_json(orient="records", force_ascii=False)


@app.route("/api/synergy", methods=["GET"])
def get_synergy_index():
    """返回协同指数（province_synergy_index.csv）"""
    df = load_csv("derived", "province_synergy_index.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    return df.to_json(orient="records", force_ascii=False)

# —— 新增：标准化指标（energy_index / eco_index / efficiency_index） ——
@app.route("/api/standardized", methods=["GET"])
def get_standardized_index():
    """返回标准化指标（derived/province_standardized.csv）"""
    df = load_csv("derived", "province_standardized.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    province = request.args.get("province")
    year = request.args.get("year", type=int)
    cols = [c for c in ["province", "year", "energy_index", "eco_index", "efficiency_index"] if c in df.columns]
    df = df[cols]
    if province:
        df = df[df["province"] == province]
    if year is not None:
        df = df[df["year"] == year]
    return df.to_json(orient="records", force_ascii=False)

# —— 新增：变量相关性数据（clean_ratio / green_rate / emission_per_gdp 之间逐年相关） ——
@app.route("/api/relation", methods=["GET"])
def get_variable_relation():
    """返回变量相关性（derived/province_relation.csv）"""
    df = load_csv("derived", "province_relation.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    year = request.args.get("year", type=int)
    cols = [c for c in ["year", "variable_x", "variable_y", "correlation"] if c in df.columns]
    df = df[cols]
    if year is not None:
        df = df[df["year"] == year]
    return df.to_json(orient="records", force_ascii=False)


@app.route("/api/cluster", methods=["GET"])
def get_cluster_result():
    """返回聚类结果（cluster_result.csv）"""
    df = load_csv("derived", "cluster_result.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    return df.to_json(orient="records", force_ascii=False)


@app.route("/api/policy", methods=["GET"])
def get_policy_timeline():
    """返回政策事件时间线"""
    df = load_csv("derived", "policy_timeline.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    # 关键字段规范化
    rename_map = {
        "province": "province",
        "year": "year",
        "policy_name": "policy_name",
        "category": "category",
        "level": "level",
    }
    # 仅保留需要的列，避免意外列影响前端
    cols = [c for c in rename_map.keys() if c in df.columns]
    # 如果第一列名异常（如 BOM 导致），load_csv 已处理；这里再稳妥转换 year 类型
    if "year" in df.columns:
        try:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64").astype(int)
        except Exception:
            pass
    df = df[cols]
    return df.to_json(orient="records", force_ascii=False)


# —— 新增：时序演化分析所需数据 ——
@app.route("/api/temporal/trend", methods=["GET"])
def get_temporal_trend():
    """返回时序趋势数据（province_trend.csv）"""
    df = load_csv("derived", "province_trend.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    return df.to_json(orient="records", force_ascii=False)


@app.route("/api/temporal/delta", methods=["GET"])
def get_temporal_delta():
    """返回时序变化率数据（province_delta.csv）"""
    df = load_csv("derived", "province_delta.csv")
    if df is None:
        return jsonify({"error": "file not found"}), 404
    return df.to_json(orient="records", force_ascii=False)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
