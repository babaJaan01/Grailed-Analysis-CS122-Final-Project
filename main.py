import sys
import tkinter as tk
from tkinter import messagebox

from data_loader import load_raw, DATA_PATH
from gui import App


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DATA_PATH

    try:
        raw_df = load_raw(path)
    except FileNotFoundError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Data Not Found",
            f"Could not find data file:\n{path}\n\n"
            "Place sold_listings.csv in the data/ folder and try again.",
        )
        return

    app = App(raw_df)
    app.mainloop()


if __name__ == "__main__":
    main()
