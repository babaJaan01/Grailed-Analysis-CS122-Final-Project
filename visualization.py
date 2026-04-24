import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

_PALETTE = "Blues_d"


def plot_bar(df, x_col, y_col, ax, title=""):
    data = df[[x_col, y_col]].dropna().sort_values(y_col, ascending=True).tail(15)
    ax.barh(data[x_col].astype(str), data[y_col], color=sns.color_palette(_PALETTE, len(data)))
    ax.set_xlabel(y_col.replace("_", " ").title())
    ax.set_ylabel(x_col.replace("_", " ").title())
    ax.set_title(title or f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}")
    ax.tick_params(axis="y", labelsize=8)


def plot_histogram(df, col, ax):
    data = df[col].dropna()
    sns.histplot(data, ax=ax, kde=True, color=sns.color_palette(_PALETTE, 1)[0])
    ax.set_xlabel(col.replace("_", " ").title())
    ax.set_ylabel("Count")
    ax.set_title(f"Distribution of {col.replace('_', ' ').title()}")


def plot_scatter(df, x_col, y_col, ax):
    data = df[[x_col, y_col, "top_category"]].dropna()
    categories = data["top_category"].unique()
    palette = sns.color_palette("tab10", len(categories))
    for i, cat in enumerate(categories):
        subset = data[data["top_category"] == cat]
        ax.scatter(subset[x_col], subset[y_col], label=cat, color=palette[i], alpha=0.7, s=40)
    ax.set_xlabel(x_col.replace("_", " ").title())
    ax.set_ylabel(y_col.replace("_", " ").title())
    ax.set_title(f"{y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}")
    ax.legend(fontsize=7, loc="upper left")


def plot_box(df, group_col, value_col, ax):
    data = df[[group_col, value_col]].dropna()
    order = (
        data.groupby(group_col)[value_col]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )
    sns.boxplot(data=data, x=group_col, y=value_col, order=order, ax=ax, palette=_PALETTE)
    ax.set_xlabel(group_col.replace("_", " ").title())
    ax.set_ylabel(value_col.replace("_", " ").title())
    ax.set_title(f"{value_col.replace('_', ' ').title()} by {group_col.replace('_', ' ').title()}")
    ax.tick_params(axis="x", rotation=30, labelsize=8)


def plot_pie(df, col, ax):
    counts = df[col].dropna().value_counts()
    if len(counts) > 8:
        top = counts.iloc[:8]
        other = pd.Series({"Other": counts.iloc[8:].sum()})
        counts = pd.concat([top, other])
    ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%", startangle=140,
           colors=sns.color_palette("pastel", len(counts)))
    ax.set_title(f"Distribution by {col.replace('_', ' ').title()}")


def plot_heatmap(df, ax):
    numeric_cols = ["price", "sold_price", "discount_rate", "num_price_drops",
                    "days_to_sell", "seller_rating"]
    available = [c for c in numeric_cols if c in df.columns]
    corr = df[available].corr()
    sns.heatmap(
        corr, ax=ax, annot=True, fmt=".2f", cmap="coolwarm",
        linewidths=0.5, annot_kws={"size": 8},
    )
    ax.set_title("Correlation Heatmap")
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.tick_params(axis="y", rotation=0, labelsize=8)


def plot_line(df, ax):
    data = df[["sold_at", "sold_price"]].dropna().copy()
    data["week"] = data["sold_at"].dt.to_period("W").apply(lambda p: p.start_time)
    weekly = data.groupby("week")["sold_price"].agg(count="count", avg_price="mean").reset_index()
    ax.plot(weekly["week"], weekly["count"], marker="o", color=sns.color_palette(_PALETTE, 1)[0])
    ax.set_xlabel("Week")
    ax.set_ylabel("Sales Count")
    ax.set_title("Weekly Sales Volume")
    ax.tick_params(axis="x", rotation=30, labelsize=8)
