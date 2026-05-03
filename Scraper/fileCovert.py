import json
import os
import sys

import pandas as pd

SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRAPER_DIR)
DEFAULT_INPUT = os.path.join(SCRAPER_DIR, "sold_listings.jsonl")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "data", "sold_listings.csv.gz")

# Columns to drop before writing — heavy strings or duplicates with no analytical value.
DROP_COLUMNS = {
    "objectID",          # duplicate of id
    "cover_photo_url",   # long image URL, never read
    "listing_url",       # reconstructable from id
    "scraped_at",        # debug field
    "shipping",          # raw nested dict (when not flattened)
}
DROP_PREFIXES = (
    "shipping.",         # all flattened shipping.us.amount, shipping.eu.*, etc.
)


def _filter_columns(df, keep_all=False):
    if keep_all:
        return df
    drop = [c for c in df.columns
            if c in DROP_COLUMNS or c.startswith(DROP_PREFIXES)]
    return df.drop(columns=drop)


def jsonl_to_csv(jsonl_file, csv_file, keep_all=False, gzip=None):
    if not os.path.exists(jsonl_file):
        print(f"Input not found: {jsonl_file}")
        sys.exit(1)

    data = []
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    if not data:
        print(f"Input is empty: {jsonl_file}")
        sys.exit(1)

    df = pd.json_normalize(data)
    before_cols = len(df.columns)
    df = _filter_columns(df, keep_all=keep_all)
    after_cols = len(df.columns)

    os.makedirs(os.path.dirname(csv_file), exist_ok=True)

    if gzip is None:
        gzip = csv_file.endswith(".gz")

    if gzip and not csv_file.endswith(".gz"):
        csv_file += ".gz"

    df.to_csv(csv_file, index=False, encoding="utf-8",
              compression="gzip" if gzip else None)

    size_mb = os.path.getsize(csv_file) / (1024 * 1024)
    dropped = before_cols - after_cols
    print(f"Converted {len(df):,} listings → {csv_file}")
    print(f"  columns: {before_cols} → {after_cols} ({dropped} dropped)"
          f"{' [keep-all]' if keep_all else ''}")
    print(f"  file size: {size_mb:.2f} MB{' (gzipped)' if gzip else ''}")


if __name__ == "__main__":
    args = sys.argv[1:]
    keep_all = "--keep-all" in args
    no_gzip = "--no-gzip" in args
    args = [a for a in args if not a.startswith("--")]

    in_path = args[0] if len(args) > 0 else DEFAULT_INPUT
    out_path = args[1] if len(args) > 1 else DEFAULT_OUTPUT
    if no_gzip and out_path.endswith(".gz"):
        out_path = out_path[:-3]
    jsonl_to_csv(in_path, out_path, keep_all=keep_all,
                 gzip=None if no_gzip is False else False)
