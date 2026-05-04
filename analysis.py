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


# ───────────────────────── price-point analysis ─────────────────────────

def price_point_analysis(df, bins=20):
    """
    Identify the optimal sold-price points: which buckets see the most volume
    and which sell fastest. Returns a dict ready for plotting / display.
    """
    prices = df["sold_price"].dropna()
    if prices.empty:
        return None

    p1, p99 = prices.quantile([0.01, 0.99])
    trimmed = df[(df["sold_price"] >= p1) & (df["sold_price"] <= p99)].copy()
    if trimmed.empty:
        return None

    edges = np.linspace(trimmed["sold_price"].min(), trimmed["sold_price"].max(), bins + 1)
    trimmed["price_bucket"] = pd.cut(trimmed["sold_price"], bins=edges, include_lowest=True)

    grouped = trimmed.groupby("price_bucket", observed=True).agg(
        count=("sold_price", "count"),
        avg_days_to_sell=("days_to_sell", "mean") if "days_to_sell" in trimmed else ("sold_price", "count"),
    ).reset_index()
    grouped["bucket_mid"] = grouped["price_bucket"].apply(lambda iv: (iv.left + iv.right) / 2).astype(float)

    if grouped["count"].sum() == 0:
        return None

    sweet_idx = int(grouped["count"].idxmax())
    sweet_bucket = grouped.loc[sweet_idx, "price_bucket"]

    if "days_to_sell" in trimmed.columns and trimmed["days_to_sell"].notna().any():
        valid = grouped[grouped["count"] >= max(3, int(grouped["count"].quantile(0.25)))]
        if not valid.empty and valid["avg_days_to_sell"].notna().any():
            fastest_idx = int(valid["avg_days_to_sell"].idxmin())
            fastest_bucket = grouped.loc[fastest_idx, "price_bucket"]
        else:
            fastest_bucket = None
    else:
        fastest_bucket = None

    quartiles = prices.quantile([0.25, 0.5, 0.75])

    return {
        "buckets": grouped,
        "sweet_bucket": sweet_bucket,
        "fastest_bucket": fastest_bucket,
        "median": float(quartiles[0.5]),
        "p25": float(quartiles[0.25]),
        "p75": float(quartiles[0.75]),
        "n": int(len(prices)),
        "trimmed_n": int(len(trimmed)),
    }


# ───────────────────────── keyword / brand trends ─────────────────────────

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "with", "to", "from",
    "by", "at", "is", "as", "this", "that", "it", "its", "be", "are", "was", "were",
    "size", "sz", "fit", "new", "used", "vintage", "rare", "authentic", "real",
    "men", "mens", "women", "womens", "boys", "girls", "kids", "unisex",
    "small", "medium", "large", "xs", "s", "m", "l", "xl", "xxl",
    "black", "white", "grey", "gray", "blue", "red", "green", "brown", "tan", "navy",
    "color", "colour", "style",
}


def _tokenize(text):
    if not isinstance(text, str):
        return []
    out = []
    cur = []
    for ch in text.lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return [t for t in out if len(t) >= 3 and not t.isdigit() and t not in _STOPWORDS]


def keyword_frequency(df, top_n=25):
    """Top tokens from listing titles after stopword filtering."""
    if "title" not in df.columns:
        return pd.DataFrame(columns=["keyword", "count"])
    counts = {}
    for title in df["title"].dropna():
        for tok in _tokenize(title):
            counts[tok] = counts.get(tok, 0) + 1
    series = pd.Series(counts, name="count").sort_values(ascending=False).head(top_n)
    return series.rename_axis("keyword").reset_index()


def brand_popularity(df, top_n=20):
    """Top brands by sold volume + avg price + total revenue."""
    if "designer_names" not in df.columns:
        return pd.DataFrame()
    grouped = (
        df.groupby("designer_names")["sold_price"]
        .agg(count="count", avg_price="mean", total_revenue="sum")
        .reset_index()
        .sort_values("count", ascending=False)
        .head(top_n)
    )
    grouped["avg_price"] = grouped["avg_price"].round(2)
    grouped["total_revenue"] = grouped["total_revenue"].round(2)
    return grouped


def trending_brands(df, recent_days=30, min_count=5, top_n=15):
    """
    Brands whose share of recent (last `recent_days`) sales exceeds their overall
    share most strongly. Returns df sorted by lift descending.
    """
    if "sold_at" not in df.columns or df["sold_at"].notna().sum() == 0:
        return pd.DataFrame()

    cutoff = df["sold_at"].max() - pd.Timedelta(days=recent_days)
    recent = df[df["sold_at"] >= cutoff]
    if recent.empty:
        return pd.DataFrame()

    overall = df["designer_names"].value_counts(normalize=True)
    recent_share = recent["designer_names"].value_counts(normalize=True)
    recent_count = recent["designer_names"].value_counts()

    merged = pd.DataFrame({
        "overall_share": overall,
        "recent_share": recent_share,
        "recent_count": recent_count,
    }).fillna(0)
    merged = merged[merged["recent_count"] >= min_count]
    if merged.empty:
        return pd.DataFrame()

    merged["lift"] = (merged["recent_share"] + 1e-9) / (merged["overall_share"] + 1e-9)
    merged = merged.sort_values("lift", ascending=False).head(top_n).reset_index()
    merged = merged.rename(columns={"index": "designer_names"})
    merged["recent_share"] = (merged["recent_share"] * 100).round(2)
    merged["overall_share"] = (merged["overall_share"] * 100).round(2)
    merged["lift"] = merged["lift"].round(2)
    return merged
