import ast
import os

import numpy as np
import pandas as pd

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sold_listings.csv")

_LIST_COLS = ["price_drops", "designers", "traits", "styles", "badges"]


def _safe_eval(val):
    if pd.isna(val) or val == "":
        return []
    if isinstance(val, list):
        return val
    try:
        result = ast.literal_eval(str(val))
        return result if isinstance(result, list) else []
    except (ValueError, SyntaxError):
        return []


def load_data(path=DATA_PATH):
    df = pd.read_csv(path, low_memory=False)

    for col in _LIST_COLS:
        if col in df.columns:
            df[col] = df[col].apply(_safe_eval)

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["sold_price"] = pd.to_numeric(df["sold_price"], errors="coerce")
    df["seller_rating"] = pd.to_numeric(df["seller_rating"], errors="coerce")

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["sold_at"] = pd.to_datetime(df["sold_at"], errors="coerce", utc=True)

    df["num_price_drops"] = df["price_drops"].apply(len)
    df["had_price_drop"] = df["num_price_drops"] > 0

    with np.errstate(divide="ignore", invalid="ignore"):
        raw_rate = (df["price"] - df["sold_price"]) / df["price"] * 100
    df["discount_rate"] = raw_rate.clip(lower=0, upper=100).fillna(0)

    df["days_to_sell"] = (
        (df["sold_at"] - df["created_at"]).dt.total_seconds() / 86400
    ).clip(lower=0)

    df["top_category"] = (
        df["category_path"]
        .fillna("")
        .str.split(".")
        .str[0]
        .replace("", "unknown")
    )

    df = df.dropna(subset=["sold_price"])
    df = df.reset_index(drop=True)
    return df
