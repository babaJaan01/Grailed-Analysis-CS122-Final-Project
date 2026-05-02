import pandas as pd
import json

def jsonl_to_csv(jsonl_file, csv_file):
    data = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    df = pd.json_normalize(data)
    df.to_csv(csv_file, index=False, encoding='utf-8')
    print(f"Converted {len(df)} listings to {csv_file}")

jsonl_to_csv('sold_listings.jsonl', 'sold_listings.csv')