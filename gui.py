import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg") #idk why this is needed tbh
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from analysis import (
    category_analysis,
    brand_analysis,
    price_drop_analysis,
    location_analysis,
    summary_stats,
)
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
CATEGORY_OPTS = ["top_category", "designer_names", "location", "condition", "color", "department"]
METRIC_OPTS = ["sold_price", "discount_rate", "days_to_sell", "price"]

_CATEGORY_LABELS = {
    "top_category": "Category",
    "designer_names": "Brand / Designer",
    "location": "Location",
    "condition": "Condition",
    "color": "Color",
    "department": "Department",
}

_METRIC_LABELS = {
    "sold_price": "Sold Price ($)",
    "discount_rate": "Discount Rate (%)",
    "days_to_sell": "Days to Sell",
    "price": "Original Price ($)",
}


class AnalysisPage(tk.Frame):
    def __init__(self, parent, df, **kwargs):
        super().__init__(parent, **kwargs)
        self.df = df
        self._build_ui()

    def _build_ui(self):

        # ── Header ──────────────────────────────────────────────────────────
        header = tk.Label(
            self, text="Grailed Sales Analysis",
            font=("Helvetica", 16, "bold"), bg="#1a1a2e", fg="white",
            pady=10,
        )
        header.pack(fill=tk.X)

        # ── Filter bar ──────────────────────────────────────────────────────
        filter_frame = tk.Frame(self, pady=8, padx=10)
        filter_frame.pack(fill=tk.X)

        # Row 1 — dropdowns + generate
        row1 = tk.Frame(filter_frame)
        row1.pack(fill=tk.X, pady=(0, 4))

        tk.Label(row1, text="Graph Type:").pack(side=tk.LEFT, padx=(0, 4))
        self.graph_var = tk.StringVar(value=GRAPH_TYPES[0])
        graph_menu = ttk.OptionMenu(row1, self.graph_var, GRAPH_TYPES[0], *GRAPH_TYPES)
        graph_menu.config(width=11)
        graph_menu.pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(row1, text="Category:").pack(side=tk.LEFT, padx=(0, 4))
        self.category_var = tk.StringVar(value=CATEGORY_OPTS[0])
        cat_menu = ttk.OptionMenu(
            row1, self.category_var, CATEGORY_OPTS[0],
            *CATEGORY_OPTS,
            command=lambda _: self._update_cat_label(),
        )
        cat_menu.config(width=16)
        cat_menu.pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(row1, text="Metric:").pack(side=tk.LEFT, padx=(0, 4))
        self.metric_var = tk.StringVar(value=METRIC_OPTS[0])
        metric_menu = ttk.OptionMenu(row1, self.metric_var, METRIC_OPTS[0], *METRIC_OPTS)
        metric_menu.config(width=14)
        metric_menu.pack(side=tk.LEFT, padx=(0, 20))

        self.generate_btn = ttk.Button(row1, text="Generate Plot", command=self._generate)
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 4))

        # Row 2 — sample size slider + reset
        row2 = tk.Frame(filter_frame)
        row2.pack(fill=tk.X)

        max_rows = max(len(self.df), 1)
        tk.Label(row2, text="Sample Size:").pack(side=tk.LEFT, padx=(0, 4))
        self.sample_var = tk.IntVar(value=min(max_rows, 100))
        self.sample_slider = tk.Scale(
            row2, variable=self.sample_var,
            from_=10, to=max_rows,
            orient=tk.HORIZONTAL, length=200,
        )
        self.sample_slider.pack(side=tk.LEFT, padx=(0, 14))

        reset_btn = ttk.Button(row2, text="Reset", command=self._reset)
        reset_btn.pack(side=tk.LEFT)

        # ── Canvas ──────────────────────────────────────────────────────────
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 4))

        self.fig, self.ax = plt.subplots(figsize=(9, 4.5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._draw_placeholder()

        # ── Stats bar ───────────────────────────────────────────────────────
        stats_frame = tk.Frame(self, bg="#1a1a2e", pady=6)
        stats_frame.pack(fill=tk.X)

        self.stats_var = tk.StringVar(value="Load a plot to see summary statistics.")
        stats_lbl = tk.Label(
            stats_frame, textvariable=self.stats_var,
            bg="#1a1a2e", fg="#e0e0e0", font=("Helvetica", 9),
        )
        stats_lbl.pack()

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _update_cat_label(self):
        pass  # reserved for future label updates

    def _get_sample(self):
        n = min(self.sample_var.get(), len(self.df))
        return self.df.sample(n=n, random_state=42) if n < len(self.df) else self.df.copy()

    def _draw_placeholder(self):
        self.ax.clear()
        self.ax.text(
            0.5, 0.5, "Select options above and click Generate Plot",
            ha="center", va="center", fontsize=12, color="#888",
            transform=self.ax.transAxes,
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def _update_stats(self, df):
        st = summary_stats(df)
        if not st:
            self.stats_var.set("No data.")
            return
        self.stats_var.set(
            f"n = {st['count']}   |   "
            f"Mean: ${st['mean']:.2f}   |   "
            f"Median: ${st['median']:.2f}   |   "
            f"Std Dev: ${st['std']:.2f}   |   "
            f"Min: ${st['min']:.0f}   Max: ${st['max']:.0f}   |   "
            f"Skewness: {st['skewness']:.2f}"
        )

    def _generate(self):
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
        self.sample_var.set(min(len(self.df), 100))
        self.stats_var.set("Load a plot to see summary statistics.")
        self._draw_placeholder()
