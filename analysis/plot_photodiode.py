"""
Plot a photodiode time series recorded by redpitaya/record_photodiode.py.

Reads the "t_s,pl_mean_v,pl_std_v" CSV (ignoring the '#' header lines) and
plots photoluminescence vs time, with a shaded +/-1 standard-deviation band.
A dashed line marks the overall mean so drift is easy to see.

Edit the CONFIGURATION block and run on your PC:  python3 plot_photodiode.py
Requires matplotlib:  pip install matplotlib
"""

import csv
import os

import matplotlib.pyplot as plt

# ===== CONFIGURATION =====
# Files live in the repo's data/ folder regardless of where you run this from.
DATA_DIR   = r"D:\data"
INPUT_FILE = os.path.join(DATA_DIR, "photodiode_laser_on.csv")
SAVE_FIG   = os.path.join(DATA_DIR, "photodiode_laser_on.png")   # set to None to skip saving


def load_series(path):
    t, mean, std = [], [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0].startswith("t_s"):
                continue
            t.append(float(row[0]))
            mean.append(float(row[1]))
            std.append(float(row[2]) if len(row) > 2 else 0.0)
    return t, mean, std


def main():
    t, mean, std = load_series(INPUT_FILE)
    if not t:
        raise SystemExit(f"No data points found in {INPUT_FILE}")

    avg = sum(mean) / len(mean)
    lo = [m - s for m, s in zip(mean, std)]
    hi = [m + s for m, s in zip(mean, std)]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(t, lo, hi, color="tab:blue", alpha=0.2, label="+/-1 sd")
    ax.plot(t, mean, "-", lw=1.0, color="tab:blue", label="PL mean")
    ax.axhline(avg, color="tab:red", ls="--", lw=1, label=f"mean = {avg:.4f} V")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Photoluminescence (V)")
    ax.set_title(f"Photodiode recording ({t[-1]:.0f} s, {len(t)} points)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if SAVE_FIG:
        fig.savefig(SAVE_FIG, dpi=150)
        print(f"Saved {SAVE_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
