"""
Plot an ODMR spectrum recorded by odmr_redpitaya.py.

Reads the "freq_MHz,pl_volts" CSV (ignoring the '#' header lines) and plots
photoluminescence vs microwave frequency, marking the deepest dip (the NV
resonance). Edit INPUT_FILE below and run:  python3 plot_odmr.py

Typically run on your PC after copying the CSV over:
    scp root@rp-XXXXXXXX.local:/root/odmr_spectrum.csv .
Requires matplotlib:  pip install matplotlib
"""

import csv
import os

import matplotlib.pyplot as plt

# ===== CONFIGURATION =====
# Files live in the repo's data/ folder regardless of where you run this from.
DATA_DIR   = r"D:\data\BudgetODMR\23-06-2026\data\odmr_runs4"# set to None to skip saving


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
    freqs, pl = load_spectrum(INPUT_FILE)
    if not freqs:
        raise SystemExit(f"No data points found in {INPUT_FILE}")

    # Deepest dip = ODMR resonance (PL drops on resonance).
    i_dip = min(range(len(pl)), key=lambda i: pl[i])
    f_dip = freqs[i_dip]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(freqs, pl, "-", lw=1.2, color="tab:blue")
    ax.axvline(f_dip, color="tab:red", ls="--", lw=1,
               label=f"dip @ {f_dip:.2f} MHz")

    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel("Photoluminescence (V)")
    ax.set_title("NV centre ODMR spectrum")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if SAVE_FIG:
        fig.savefig(SAVE_FIG, dpi=150)
        print(f"Saved {SAVE_FIG}")
    plt.show()


if __name__ == "__main__":
    for i in range(1, 6):
        INPUT_FILE = os.path.join(DATA_DIR, f"run_0{i}.csv")
        SAVE_FIG   = os.path.join(DATA_DIR, f"run_0{i}.png")   
        if i > 9:
            INPUT_FILE = os.path.join(DATA_DIR, f"run_{i}.csv")
            SAVE_FIG   = os.path.join(DATA_DIR, f"run_{i}.png")
        main()

