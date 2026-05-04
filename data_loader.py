import ast
import os

import numpy as np
import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_GZ_PATH = os.path.join(_DATA_DIR, "sold_listings.csv.gz")
_CSV_PATH = os.path.join(_DATA_DIR, "sold_listings.csv")
DATA_PATH = _GZ_PATH if os.path.exists(_GZ_PATH) else _CSV_PATH

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


def load_raw(path=DATA_PATH):
    """Load CSV with minimal coercion. Cleaning + feature engineering happens in clean_data()."""
    df = pd.read_csv(path, low_memory=False)

    for col in _LIST_COLS:
        if col in df.columns:
            df[col] = df[col].apply(_safe_eval)

    for col in ("price", "sold_price", "seller_rating"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ("created_at", "sold_at"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    return df


def clean_data(df, log=None):
    """
    Clean and feature-engineer the raw dataframe. Returns a new dataframe.
    `log` is an optional callable(str) for progress output.
    """
    def _log(msg):
        if log:
            log(msg)

    df = df.copy()
    initial = len(df)
    _log(f"Starting with {initial:,} rows")

    if "id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["id"], keep="first")
        removed = before - len(df)
        if removed:
            _log(f"Removed {removed:,} duplicate listings (by id)")

    if "sold_price" in df.columns:
        before = len(df)
        df = df[df["sold_price"].notna() & (df["sold_price"] > 0)]
        removed = before - len(df)
        if removed:
            _log(f"Removed {removed:,} rows with missing/zero sold_price")

        before = len(df)
        df = df[df["sold_price"] <= 50000]
        removed = before - len(df)
        if removed:
            _log(f"Removed {removed:,} extreme outliers (sold_price > $50,000)")

    if "title" in df.columns:
        before = len(df)
        df = df[df["title"].notna() & (df["title"].astype(str).str.strip() != "")]
        removed = before - len(df)
        if removed:
            _log(f"Removed {removed:,} rows missing title")

    if "designer_names" in df.columns:
        df["designer_names"] = (
            df["designer_names"].fillna("Unknown").astype(str).str.strip()
        )
        df.loc[df["designer_names"] == "", "designer_names"] = "Unknown"
        _log("Normalized designer_names")

    if "location" in df.columns:
        df["location"] = df["location"].fillna("Unknown").astype(str).str.strip()

    if "condition" in df.columns:
        df["condition"] = df["condition"].fillna("unknown").astype(str).str.strip().str.lower()

    if "size" in df.columns:
        df["size"] = df["size"].fillna("unknown").astype(str).str.strip().str.lower()

    if "price_drops" in df.columns:
        df["num_price_drops"] = df["price_drops"].apply(len)
        df["had_price_drop"] = df["num_price_drops"] > 0
        _log("Computed price-drop features")

    if "price" in df.columns and "sold_price" in df.columns:
        with np.errstate(divide="ignore", invalid="ignore"):
            raw_rate = (df["price"] - df["sold_price"]) / df["price"] * 100
        df["discount_rate"] = raw_rate.clip(lower=0, upper=100).fillna(0)
        _log("Computed discount_rate")

    if "sold_at" in df.columns and "created_at" in df.columns:
        df["days_to_sell"] = (
            (df["sold_at"] - df["created_at"]).dt.total_seconds() / 86400
        ).clip(lower=0)
        _log("Computed days_to_sell")

    if "category_path" in df.columns:
        df["top_category"] = (
            df["category_path"].fillna("").astype(str).str.split(".").str[0].replace("", "unknown")
        )
        _log("Derived top_category from category_path")

    df = df.reset_index(drop=True)
    final = len(df)
    pct = (final / initial * 100) if initial else 0
    _log(f"Done. Final: {final:,} rows ({pct:.1f}% retained)")
    return df


def load_data(path=DATA_PATH):
    """Backward-compatible: load + clean in one call (no progress logging)."""
    return clean_data(load_raw(path))
