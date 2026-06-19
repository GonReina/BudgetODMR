"""
Average the repeated ODMR sweeps produced by redpitaya/odmr_repeat_sweeps.py.

Reads every run_*.csv in RUNS_DIR, groups the photoluminescence values by
frequency, and writes the per-frequency mean (and standard deviation across
runs, plus the number of runs contributing) to a single averaged CSV. It also
plots the averaged spectrum with a +/-1 sd band and marks the deepest dip
(the NV resonance).

Averaging N independent sweeps lowers the random noise by ~sqrt(N), making a
shallow ODMR dip easier to see. Edit the CONFIGURATION block and run on your
PC:  python3 average_sweeps.py
Requires matplotlib:  pip install matplotlib
"""

import csv
import glob
import math
import os

import matplotlib.pyplot as plt

# ===== CONFIGURATION =====
# Files live in the repo's data/ folder regardless of where you run this from.
DATA_DIR   = r"D:\data"
RUNS_DIR   = os.path.join(DATA_DIR, "odmr_runs")     # where odmr_repeat_sweeps.py output landed
RUNS_GLOB  = "run_*.csv"
OUTPUT_CSV = os.path.join(DATA_DIR, "odmr_average.csv")
SAVE_FIG   = os.path.join(DATA_DIR, "odmr_average.png")   # set to None to skip saving


def load_spectrum(path):
    freqs, pl = [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0].startswith("freq"):
                continue
            freqs.append(float(row[0]))
            pl.append(float(row[1]))
    return freqs, pl


def main():
    paths = sorted(glob.glob(os.path.join(RUNS_DIR, RUNS_GLOB)))
    if not paths:
        raise SystemExit(f"No '{RUNS_GLOB}' files found in {RUNS_DIR}")
    print(f"Averaging {len(paths)} run(s) from {RUNS_DIR}/")

    # Group PL values by frequency so runs of differing length still combine.
    by_freq = {}
    for p in paths:
        freqs, pl = load_spectrum(p)
        for fr, v in zip(freqs, pl):
            by_freq.setdefault(fr, []).append(v)
        print(f"  {os.path.basename(p)}: {len(freqs)} points")

    freqs = sorted(by_freq)
    means, stds, counts = [], [], []
    for fr in freqs:
        vals = by_freq[fr]
        m = sum(vals) / len(vals)
        var = sum((v - m) ** 2 for v in vals) / len(vals)
        means.append(m)
        stds.append(math.sqrt(var))
        counts.append(len(vals))

    n_min, n_max = min(counts), max(counts)
    if n_min != n_max:
        print(f"  note: runs cover different frequencies "
              f"({n_min}-{n_max} runs per point)")

    with open(OUTPUT_CSV, "w") as f:
        f.write(f"# averaged ODMR spectrum from {len(paths)} runs in {RUNS_DIR}\n")
        f.write("freq_MHz,pl_mean_v,pl_std_v,n_runs\n")
        for fr, m, s, c in zip(freqs, means, stds, counts):
            f.write(f"{fr:.4f},{m:.6f},{s:.6f},{c}\n")
    print(f"Wrote {OUTPUT_CSV}")

    # Deepest dip = ODMR resonance.
    i_dip = min(range(len(means)), key=lambda i: means[i])
    f_dip = freqs[i_dip]

    lo = [m - s for m, s in zip(means, stds)]
    hi = [m + s for m, s in zip(means, stds)]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.fill_between(freqs, lo, hi, color="tab:blue", alpha=0.2, label="+/-1 sd across runs")
    ax.plot(freqs, means, "-", lw=1.2, color="tab:blue", label=f"mean of {len(paths)} runs")
    ax.axvline(f_dip, color="tab:red", ls="--", lw=1, label=f"dip @ {f_dip:.2f} MHz")

    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel("Photoluminescence (V)")
    ax.set_title(f"NV centre ODMR spectrum (averaged, {len(paths)} runs)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if SAVE_FIG:
        fig.savefig(SAVE_FIG, dpi=150)
        print(f"Saved {SAVE_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
