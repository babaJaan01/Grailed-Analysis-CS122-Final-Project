import numpy as np
import pandas as pd
from scipy import stats


def summary_stats(df):
    prices = df["sold_price"].dropna().to_numpy()
    if len(prices) == 0:
        return {}
    return {
        "count": int(len(prices)),
        "mean": float(np.mean(prices)),
        "median": float(np.median(prices)),
        "std": float(np.std(prices, ddof=1)),
        "min": float(np.min(prices)),
        "max": float(np.max(prices)),
        "skewness": float(stats.skew(prices)),
        "kurtosis": float(stats.kurtosis(prices)),
    }


def category_analysis(df):
    result = (
        df.groupby("top_category")["sold_price"]
        .agg(count="count", avg_price="mean", total_revenue="sum")
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )
    result["avg_price"] = result["avg_price"].round(2)
    result["total_revenue"] = result["total_revenue"].round(2)
    return result


def brand_analysis(df, top_n=10):
    result = (
        df.groupby("designer_names")["sold_price"]
        .agg(count="count", avg_price="mean", total_revenue="sum")
        .reset_index()
        .sort_values("count", ascending=False)
        .head(top_n)
    )
    result["avg_price"] = result["avg_price"].round(2)
    result["total_revenue"] = result["total_revenue"].round(2)
    return result


def price_drop_analysis(df):
    dropped = df[df["had_price_drop"]]
    not_dropped = df[~df["had_price_drop"]]

    result = {
        "total_listings": len(df),
        "listings_with_drop": int(df["had_price_drop"].sum()),
        "avg_discount_rate": float(df["discount_rate"].mean()),
        "avg_discount_rate_dropped": float(dropped["discount_rate"].mean()) if len(dropped) else 0.0,
        "avg_sold_price_dropped": float(dropped["sold_price"].mean()) if len(dropped) else 0.0,
        "avg_sold_price_not_dropped": float(not_dropped["sold_price"].mean()) if len(not_dropped) else 0.0,
        "pearson_r": None,
        "pearson_p": None,
    }

    valid = df[["num_price_drops", "sold_price"]].dropna()
    if len(valid) >= 3:
        r, p = stats.pearsonr(valid["num_price_drops"], valid["sold_price"])
        result["pearson_r"] = round(float(r), 4)
        result["pearson_p"] = round(float(p), 4)

    return result


def location_analysis(df):
    result = (
        df.groupby("location")["sold_price"]
        .agg(count="count", avg_price="mean", total_revenue="sum")
        .reset_index()
        .sort_values("count", ascending=False)
    )
    result["avg_price"] = result["avg_price"].round(2)
    result["total_revenue"] = result["total_revenue"].round(2)
    return result
