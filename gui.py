import threading
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import seaborn as sns

from analysis import (
    summary_stats,
    price_point_analysis,
    keyword_frequency,
    brand_popularity,
    trending_brands,
)
from data_loader import clean_data
from visualization import (
    plot_bar,
    plot_histogram,
    plot_scatter,
    plot_box,
    plot_pie,
    plot_heatmap,
    plot_line,
)

GRAPH_TYPES = ["Bar", "Histogram", "Scatter", "Box", "Pie", "Heatmap", "Line"]
CATEGORY_OPTS = ["top_category", "designer_names", "location", "condition", "color", "department", "size"]
METRIC_OPTS = ["sold_price", "discount_rate", "days_to_sell", "price", "sold_shipping_price"]

_CATEGORY_LABELS = {
    "top_category": "Category",
    "designer_names": "Brand / Designer",
    "location": "Location",
    "condition": "Condition",
    "color": "Color",
    "department": "Department",
    "size": "Size",
}
_METRIC_LABELS = {
    "sold_price": "Sold Price ($)",
    "discount_rate": "Discount Rate (%)",
    "days_to_sell": "Days to Sell",
    "price": "Original Price ($)",
    "sold_shipping_price": "Shipping Price ($)",
}


# ═══════════════════════════ Clean Data page ═══════════════════════════

class CleanPage(tk.Frame):
    """Gates the rest of the app. Runs cleaning on the raw df, then unlocks tabs."""

    def __init__(self, parent, controller, raw_df):
        super().__init__(parent)
        self.controller = controller
        self.raw_df = raw_df
        self._busy = False
        self._build_ui()

    def _build_ui(self):
        header = tk.Label(
            self, text="Step 1 — Clean the Data",
            font=("Helvetica", 18, "bold"), bg="#1a1a2e", fg="white", pady=12,
        )
        header.pack(fill=tk.X)

        intro = tk.Label(
            self,
            text=(
                "Before any analysis can run, the raw dataset must be cleaned and prepared.\n"
                "This drops duplicates, removes invalid prices, normalizes brand names,\n"
                "and computes derived fields (discount rate, days-to-sell, top category)."
            ),
            font=("Helvetica", 11), justify="center", pady=10, padx=20,
        )
        intro.pack()

        info = tk.Label(
            self, text=f"Loaded raw dataset: {len(self.raw_df):,} rows",
            font=("Helvetica", 10, "italic"), fg="#555",
        )
        info.pack(pady=(0, 10))

        self.clean_btn = ttk.Button(self, text="🧹  Clean Data", command=self._on_clean)
        self.clean_btn.pack(pady=8, ipadx=20, ipady=4)

        self.status_var = tk.StringVar(value="Idle.")
        tk.Label(self, textvariable=self.status_var, font=("Helvetica", 10, "bold"),
                 fg="#1a1a2e").pack(pady=(4, 6))

        log_frame = tk.Frame(self, padx=20, pady=4)
        log_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(log_frame, text="Cleaning Log", font=("Helvetica", 10, "bold")).pack(anchor="w")

        self.log_text = tk.Text(log_frame, height=14, wrap="word", state="disabled",
                                bg="#0f0f1a", fg="#d0d0d0", font=("Menlo", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _append_log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")
        self.log_text.update_idletasks()

    def _on_clean(self):
        if self._busy:
            return
        self._busy = True
        self.clean_btn.configure(state="disabled")
        self.status_var.set("Cleaning…")
        self._append_log("─" * 50)

        def worker():
            try:
                cleaned = clean_data(
                    self.raw_df,
                    log=lambda m: self.after(0, self._append_log, m),
                )
                self.after(0, self._on_done, cleaned, None)
            except Exception as e:
                self.after(0, self._on_done, None, e)

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, cleaned_df, error):
        self._busy = False
        if error is not None:
            self.status_var.set("Cleaning failed.")
            self.clean_btn.configure(state="normal")
            messagebox.showerror("Cleaning Error", str(error))
            return
        self.status_var.set(f"Done. {len(cleaned_df):,} rows ready for analysis.")
        self._append_log(">>> Unlocking other tabs…")
        self.controller.on_clean_complete(cleaned_df)


# ═══════════════════════════ Price Analysis page ═══════════════════════════

class PriceAnalysisPage(tk.Frame):
    """Find optimal sold-price points across the dataset (or a filter)."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.df = None
        self._build_ui()

    def _build_ui(self):
        header = tk.Label(self, text="Optimal Price Points",
                          font=("Helvetica", 16, "bold"),
                          bg="#1a1a2e", fg="white", pady=10)
        header.pack(fill=tk.X)

        bar = tk.Frame(self, padx=10, pady=8)
        bar.pack(fill=tk.X)

        tk.Label(bar, text="Category:").pack(side=tk.LEFT, padx=(0, 4))
        self.cat_var = tk.StringVar(value="All")
        self.cat_menu = ttk.OptionMenu(bar, self.cat_var, "All", "All")
        self.cat_menu.config(width=18)
        self.cat_menu.pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(bar, text="Brand contains:").pack(side=tk.LEFT, padx=(0, 4))
        self.brand_var = tk.StringVar()
        tk.Entry(bar, textvariable=self.brand_var, width=20).pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(bar, text="Bins:").pack(side=tk.LEFT, padx=(0, 4))
        self.bins_var = tk.IntVar(value=20)
        ttk.Spinbox(bar, from_=5, to=50, textvariable=self.bins_var, width=4).pack(side=tk.LEFT, padx=(0, 14))

        ttk.Button(bar, text="Analyze", command=self._analyze).pack(side=tk.LEFT)

        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 4))
        self.fig, (self.ax_top, self.ax_bot) = plt.subplots(2, 1, figsize=(9, 5.5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._placeholder("Click Analyze to compute optimal price points.")

        stats_frame = tk.Frame(self, bg="#1a1a2e", pady=6)
        stats_frame.pack(fill=tk.X)
        self.stats_var = tk.StringVar(value="")
        tk.Label(stats_frame, textvariable=self.stats_var,
                 bg="#1a1a2e", fg="#e0e0e0", font=("Helvetica", 10)).pack()

    def set_df(self, df):
        self.df = df
        cats = ["All"] + sorted(df["top_category"].dropna().unique().tolist()) \
            if "top_category" in df.columns else ["All"]
        menu = self.cat_menu["menu"]
        menu.delete(0, "end")
        for c in cats:
            menu.add_command(label=c, command=lambda v=c: self.cat_var.set(v))
        self.cat_var.set("All")

    def _placeholder(self, text):
        for ax in (self.ax_top, self.ax_bot):
            ax.clear()
            ax.set_xticks([])
            ax.set_yticks([])
        self.ax_top.text(0.5, 0.5, text, ha="center", va="center",
                         fontsize=12, color="#888", transform=self.ax_top.transAxes)
        self.canvas.draw()

    def _filter(self):
        df = self.df
        if df is None:
            return None
        if self.cat_var.get() != "All" and "top_category" in df.columns:
            df = df[df["top_category"] == self.cat_var.get()]
        brand = self.brand_var.get().strip().lower()
        if brand and "designer_names" in df.columns:
            df = df[df["designer_names"].str.lower().str.contains(brand, na=False)]
        return df

    def _analyze(self):
        if self.df is None:
            return
        sub = self._filter()
        if sub is None or sub.empty:
            self._placeholder("No rows match the current filter.")
            self.stats_var.set("")
            return

        result = price_point_analysis(sub, bins=self.bins_var.get())
        if not result:
            self._placeholder("Not enough data to analyze.")
            self.stats_var.set("")
            return

        buckets = result["buckets"]
        self.ax_top.clear()
        self.ax_bot.clear()

        # Top: volume per price bucket
        bar_colors = ["#4a90e2"] * len(buckets)
        sweet_idx = buckets["count"].idxmax()
        bar_colors[buckets.index.get_loc(sweet_idx)] = "#e94e77"
        self.ax_top.bar(buckets["bucket_mid"], buckets["count"],
                        width=(buckets["bucket_mid"].diff().median() or 1) * 0.9,
                        color=bar_colors, edgecolor="white", linewidth=0.5)
        self.ax_top.set_title("Sold-Listing Volume by Price Bucket  "
                              "(red = highest-volume / 'sweet spot')")
        self.ax_top.set_xlabel("Sold Price ($)")
        self.ax_top.set_ylabel("Count")

        # Bottom: avg days_to_sell per bucket
        if "avg_days_to_sell" in buckets.columns and buckets["avg_days_to_sell"].notna().any():
            colors = ["#7fbf7f"] * len(buckets)
            if result["fastest_bucket"] is not None:
                fast_idx = buckets.index[buckets["price_bucket"] == result["fastest_bucket"]]
                if len(fast_idx):
                    colors[buckets.index.get_loc(fast_idx[0])] = "#e94e77"
            self.ax_bot.bar(buckets["bucket_mid"], buckets["avg_days_to_sell"],
                            width=(buckets["bucket_mid"].diff().median() or 1) * 0.9,
                            color=colors, edgecolor="white", linewidth=0.5)
            self.ax_bot.set_title("Avg Days-to-Sell by Price Bucket  (red = fastest)")
            self.ax_bot.set_xlabel("Sold Price ($)")
            self.ax_bot.set_ylabel("Days")
        else:
            self.ax_bot.text(0.5, 0.5, "days_to_sell not available",
                             ha="center", va="center", color="#888",
                             transform=self.ax_bot.transAxes)
            self.ax_bot.set_xticks([])
            self.ax_bot.set_yticks([])

        self.fig.tight_layout()
        self.canvas.draw()

        sweet = result["sweet_bucket"]
        fastest = result["fastest_bucket"]
        msg = (f"n = {result['n']:,}   |   "
               f"P25 ${result['p25']:.0f}   Median ${result['median']:.0f}   P75 ${result['p75']:.0f}   |   "
               f"Sweet spot: ${sweet.left:.0f}–${sweet.right:.0f}")
        if fastest is not None:
            msg += f"   |   Fastest-selling: ${fastest.left:.0f}–${fastest.right:.0f}"
        self.stats_var.set(msg)


# ═══════════════════════════ Keyword Analysis page ═══════════════════════════

class KeywordAnalysisPage(tk.Frame):
    """Brand popularity, trending brands, and title-keyword frequency."""

    VIEWS = ["Top Brands by Volume", "Trending Brands (last 30d)", "Top Title Keywords"]

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.df = None
        self._build_ui()

    def _build_ui(self):
        header = tk.Label(self, text="Keyword & Brand Trends",
                          font=("Helvetica", 16, "bold"),
                          bg="#1a1a2e", fg="white", pady=10)
        header.pack(fill=tk.X)

        bar = tk.Frame(self, padx=10, pady=8)
        bar.pack(fill=tk.X)

        tk.Label(bar, text="View:").pack(side=tk.LEFT, padx=(0, 4))
        self.view_var = tk.StringVar(value=self.VIEWS[0])
        ttk.OptionMenu(bar, self.view_var, self.VIEWS[0], *self.VIEWS).pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(bar, text="Top N:").pack(side=tk.LEFT, padx=(0, 4))
        self.n_var = tk.IntVar(value=20)
        ttk.Spinbox(bar, from_=5, to=50, textvariable=self.n_var, width=4).pack(side=tk.LEFT, padx=(0, 14))

        ttk.Button(bar, text="Analyze", command=self._analyze).pack(side=tk.LEFT)

        body = tk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 4))

        canvas_frame = tk.Frame(body)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.fig, self.ax = plt.subplots(figsize=(7, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        table_frame = tk.Frame(body, width=320)
        table_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))
        table_frame.pack_propagate(False)
        tk.Label(table_frame, text="Details", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.tree = ttk.Treeview(table_frame, show="headings", height=18)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self._placeholder("Pick a view and click Analyze.")

        self.status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.status_var, bg="#1a1a2e", fg="#e0e0e0",
                 font=("Helvetica", 10), pady=6).pack(fill=tk.X)

    def set_df(self, df):
        self.df = df

    def _placeholder(self, text):
        self.ax.clear()
        self.ax.text(0.5, 0.5, text, ha="center", va="center",
                     fontsize=12, color="#888", transform=self.ax.transAxes)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def _set_table(self, df):
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        self.tree.delete(*self.tree.get_children())
        cols = list(df.columns)
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=max(80, 320 // max(1, len(cols))), anchor="w")
        for _, row in df.iterrows():
            self.tree.insert("", tk.END, values=[row[c] for c in cols])

    def _analyze(self):
        if self.df is None:
            return
        view = self.view_var.get()
        n = self.n_var.get()
        self.ax.clear()

        try:
            if view == "Top Brands by Volume":
                data = brand_popularity(self.df, top_n=n)
                if data.empty:
                    self._placeholder("No brand data available.")
                    return
                d = data.sort_values("count", ascending=True)
                self.ax.barh(d["designer_names"].astype(str), d["count"],
                             color=sns.color_palette("Blues_d", len(d)))
                self.ax.set_title(f"Top {n} Brands by Sold Volume")
                self.ax.set_xlabel("Listings Sold")
                self.ax.tick_params(axis="y", labelsize=8)
                self._set_table(data[["designer_names", "count", "avg_price", "total_revenue"]])
                self.status_var.set(f"Top {len(data)} brands by sold-listing count.")

            elif view == "Trending Brands (last 30d)":
                data = trending_brands(self.df, recent_days=30, min_count=3, top_n=n)
                if data.empty:
                    self._placeholder("Not enough recent data to compute trends.")
                    self.status_var.set("")
                    return
                d = data.sort_values("lift", ascending=True)
                self.ax.barh(d["designer_names"].astype(str), d["lift"],
                             color=sns.color_palette("flare", len(d)))
                self.ax.axvline(1.0, color="#888", linestyle="--", linewidth=1)
                self.ax.set_title("Trending Brands — Recent vs Overall Share (lift)")
                self.ax.set_xlabel("Lift (>1 = over-represented recently)")
                self.ax.tick_params(axis="y", labelsize=8)
                self._set_table(data[["designer_names", "recent_count", "lift",
                                      "recent_share", "overall_share"]])
                self.status_var.set(f"Top {len(data)} trending brands (last 30 days).")

            elif view == "Top Title Keywords":
                data = keyword_frequency(self.df, top_n=n)
                if data.empty:
                    self._placeholder("No title text available.")
                    return
                d = data.sort_values("count", ascending=True)
                self.ax.barh(d["keyword"].astype(str), d["count"],
                             color=sns.color_palette("crest", len(d)))
                self.ax.set_title(f"Top {n} Keywords in Listing Titles")
                self.ax.set_xlabel("Frequency")
                self.ax.tick_params(axis="y", labelsize=8)
                self._set_table(data)
                self.status_var.set(f"Top {len(data)} keywords across all listing titles.")

            self.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            messagebox.showerror("Analysis Error", str(e))
            self._placeholder("Error — see dialog.")


# ═══════════════════════════ Custom Charts page (existing) ═══════════════════════════

class AnalysisPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.df = None
        self._build_ui()

    def _build_ui(self):
        header = tk.Label(self, text="Custom Charts",
                          font=("Helvetica", 16, "bold"),
                          bg="#1a1a2e", fg="white", pady=10)
        header.pack(fill=tk.X)

        filter_frame = tk.Frame(self, pady=8, padx=10)
        filter_frame.pack(fill=tk.X)

        row1 = tk.Frame(filter_frame)
        row1.pack(fill=tk.X, pady=(0, 4))

        tk.Label(row1, text="Graph Type:").pack(side=tk.LEFT, padx=(0, 4))
        self.graph_var = tk.StringVar(value=GRAPH_TYPES[0])
        ttk.OptionMenu(row1, self.graph_var, GRAPH_TYPES[0], *GRAPH_TYPES).pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(row1, text="Category:").pack(side=tk.LEFT, padx=(0, 4))
        self.category_var = tk.StringVar(value=CATEGORY_OPTS[0])
        ttk.OptionMenu(row1, self.category_var, CATEGORY_OPTS[0], *CATEGORY_OPTS).pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(row1, text="Metric:").pack(side=tk.LEFT, padx=(0, 4))
        self.metric_var = tk.StringVar(value=METRIC_OPTS[0])
        ttk.OptionMenu(row1, self.metric_var, METRIC_OPTS[0], *METRIC_OPTS).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Button(row1, text="Generate Plot", command=self._generate).pack(side=tk.LEFT, padx=(0, 4))

        row2 = tk.Frame(filter_frame)
        row2.pack(fill=tk.X)
        tk.Label(row2, text="Sample Size:").pack(side=tk.LEFT, padx=(0, 4))
        self.sample_var = tk.IntVar(value=100)
        self.sample_slider = tk.Scale(row2, variable=self.sample_var, from_=10, to=100,
                                      orient=tk.HORIZONTAL, length=200)
        self.sample_slider.pack(side=tk.LEFT, padx=(0, 14))
        ttk.Button(row2, text="Reset", command=self._reset).pack(side=tk.LEFT)

        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 4))
        self.fig, self.ax = plt.subplots(figsize=(9, 4.5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._draw_placeholder()

        stats_frame = tk.Frame(self, bg="#1a1a2e", pady=6)
        stats_frame.pack(fill=tk.X)
        self.stats_var = tk.StringVar(value="Load a plot to see summary statistics.")
        tk.Label(stats_frame, textvariable=self.stats_var,
                 bg="#1a1a2e", fg="#e0e0e0", font=("Helvetica", 9)).pack()

    def set_df(self, df):
        self.df = df
        max_rows = max(len(df), 10)
        self.sample_slider.configure(from_=10, to=max_rows)
        self.sample_var.set(min(max_rows, 200))

    def _get_sample(self):
        n = min(self.sample_var.get(), len(self.df))
        return self.df.sample(n=n, random_state=42) if n < len(self.df) else self.df.copy()

    def _draw_placeholder(self):
        self.ax.clear()
        self.ax.text(0.5, 0.5, "Select options above and click Generate Plot",
                     ha="center", va="center", fontsize=12, color="#888",
                     transform=self.ax.transAxes)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def _update_stats(self, df):
        st = summary_stats(df)
        if not st:
            self.stats_var.set("No data.")
            return
        self.stats_var.set(
            f"n = {st['count']}   |   Mean: ${st['mean']:.2f}   |   "
            f"Median: ${st['median']:.2f}   |   Std Dev: ${st['std']:.2f}   |   "
            f"Min: ${st['min']:.0f}   Max: ${st['max']:.0f}   |   "
            f"Skewness: {st['skewness']:.2f}"
        )

    def _generate(self):
        if self.df is None:
            return
        graph = self.graph_var.get()
        cat_col = self.category_var.get()
        metric_col = self.metric_var.get()
        sample = self._get_sample()
        self.ax.clear()
        try:
            if graph == "Bar":
                agg = sample.groupby(cat_col)[metric_col].mean().reset_index()
                plot_bar(agg, cat_col, metric_col, self.ax,
                         title=f"Avg {_METRIC_LABELS[metric_col]} by {_CATEGORY_LABELS[cat_col]}")
            elif graph == "Histogram":
                plot_histogram(sample, metric_col, self.ax)
            elif graph == "Scatter":
                plot_scatter(sample, "price", metric_col, self.ax)
            elif graph == "Box":
                plot_box(sample, cat_col, metric_col, self.ax)
            elif graph == "Pie":
                plot_pie(sample, cat_col, self.ax)
            elif graph == "Heatmap":
                plot_heatmap(sample, self.ax)
            elif graph == "Line":
                plot_line(sample, self.ax)
            self.fig.tight_layout()
            self.canvas.draw()
            self._update_stats(sample)
        except Exception as exc:
            messagebox.showerror("Plot Error", str(exc))
            self._draw_placeholder()

    def _reset(self):
        self.graph_var.set(GRAPH_TYPES[0])
        self.category_var.set(CATEGORY_OPTS[0])
        self.metric_var.set(METRIC_OPTS[0])
        if self.df is not None:
            self.sample_var.set(min(len(self.df), 200))
        self.stats_var.set("Load a plot to see summary statistics.")
        self._draw_placeholder()


# ═══════════════════════════ App controller ═══════════════════════════

class App(tk.Tk):
    """Top-level Notebook controller. Cleaning gates the analysis tabs."""

    LOCKED_INDICES = (1, 2, 3)

    def __init__(self, raw_df):
        super().__init__()
        self.title("Grailed Sales Analysis")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.clean_page = CleanPage(self.notebook, controller=self, raw_df=raw_df)
        self.price_page = PriceAnalysisPage(self.notebook, controller=self)
        self.keyword_page = KeywordAnalysisPage(self.notebook, controller=self)
        self.charts_page = AnalysisPage(self.notebook, controller=self)

        self.notebook.add(self.clean_page, text="1. Clean Data")
        self.notebook.add(self.price_page, text="2. Price Analysis")
        self.notebook.add(self.keyword_page, text="3. Keyword Analysis")
        self.notebook.add(self.charts_page, text="4. Custom Charts")

        for i in self.LOCKED_INDICES:
            self.notebook.tab(i, state="disabled")

    def on_clean_complete(self, cleaned_df):
        self.price_page.set_df(cleaned_df)
        self.keyword_page.set_df(cleaned_df)
        self.charts_page.set_df(cleaned_df)
        for i in self.LOCKED_INDICES:
            self.notebook.tab(i, state="normal")
        self.notebook.select(1)
