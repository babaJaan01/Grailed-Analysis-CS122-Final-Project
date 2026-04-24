import sys
import tkinter as tk
from tkinter import messagebox

from data_loader import load_data, DATA_PATH
from gui import AnalysisPage


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DATA_PATH

    try:
        df = load_data(path)
    except FileNotFoundError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Data Not Found",
            f"Could not find data file:\n{path}\n\n"
            "Place sold_listings.csv in the data/ folder and try again.",
        )
        return

    root = tk.Tk()
    root.title("Grailed Sales Analysis")
    root.geometry("1000x680")
    root.minsize(800, 560)

    page = AnalysisPage(root, df)
    page.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
