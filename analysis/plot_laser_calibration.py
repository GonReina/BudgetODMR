"""
Plot the photodiode-vs-laser-current data from
redpitaya/pd_vs_laser_current.py.

Reads the CSV
    timestamp,ldc_current_mA,pl_mean_v,pl_std_v,n_samples,integ_s
and makes TWO separate figures:

  Figure 1 -- PL (detector output) vs laser current, with a shaded +/-1 sd band.
              This is the detector response curve; a clean setup is roughly
              linear until the detector or ADC starts to saturate (curve flattens).

  Figure 2 -- noise as a PERCENTAGE of signal (100 * sd / PL) vs laser current.
              Relative noise usually falls as the signal grows, then can rise
              again if the detector saturates/clips. Tells you the best operating
              current for the lowest fractional noise.

Edit CONFIGURATION and run on your PC:  python3 plot_laser_calibration.py
Requires matplotlib:  pip install matplotlib
"""

import csv
import os

import matplotlib.pyplot as plt

# ===== CONFIGURATION =====
DATA_DIR   = r"C:\Users\qute\Downloads\rsattempt\29-06-2026"
INPUT_FILE = os.path.join(DATA_DIR, "laser_power_calibration.csv")
SAVE_FIG_PL  = os.path.join(DATA_DIR, "laser_calibration_pl.png")       # None to skip
SAVE_FIG_PCT = os.path.join(DATA_DIR, "laser_calibration_stdpct.png")   # None to skip


def load(path):
    cur, pl, std = [], [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0].startswith("timestamp"):
                continue
            cur.append(float(row[1]))
            pl.append(float(row[2]))
            std.append(float(row[3]))
    return cur, pl, std


def main():
    cur, pl, std = load(INPUT_FILE)
    if not cur:
        raise SystemExit(f"No data points found in {INPUT_FILE}")

    # sort by current so lines/bands draw left-to-right
    order = sorted(range(len(cur)), key=lambda i: cur[i])
    cur = [cur[i] for i in order]
    pl  = [pl[i]  for i in order]
    std = [std[i] for i in order]
    std_pct = [100.0 * s / m if m else 0.0 for s, m in zip(std, pl)]

    # ---- Figure 1: PL vs current, shaded +/-1 sd ----
    lo = [m - s for m, s in zip(pl, std)]
    hi = [m + s for m, s in zip(pl, std)]
    fig1, ax1 = plt.subplots(figsize=(9, 5))
    ax1.fill_between(cur, lo, hi, color="tab:blue", alpha=0.2, label="+/-1 sd")
    ax1.plot(cur, pl, "o-", lw=1.2, ms=4, color="tab:blue", label="PL mean")
    ax1.set_xlabel("Laser diode current (mA)")
    ax1.set_ylabel("Detector output (V)")
    ax1.set_title(f"Photodiode response vs laser current ({len(cur)} points)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    fig1.tight_layout()
    if SAVE_FIG_PL:
        fig1.savefig(SAVE_FIG_PL, dpi=150)
        print(f"Saved {SAVE_FIG_PL}")

    # ---- Figure 2: relative noise (sd as % of PL) vs current ----
    fig2, ax2 = plt.subplots(figsize=(9, 5))
    ax2.plot(cur, std_pct, "s-", lw=1.2, ms=4, color="tab:red")
    ax2.set_xlabel("Laser diode current (mA)")
    ax2.set_ylabel("Noise (sd) as % of signal")
    ax2.set_title("Relative photodiode noise vs laser current")
    ax2.grid(True, alpha=0.3)
    fig2.tight_layout()
    if SAVE_FIG_PCT:
        fig2.savefig(SAVE_FIG_PCT, dpi=150)
        print(f"Saved {SAVE_FIG_PCT}")

    plt.show()


if __name__ == "__main__":
    main()
