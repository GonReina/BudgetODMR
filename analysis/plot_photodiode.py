"""
Plot a photodiode time series recorded by redpitaya/record_photodiode.py.

Reads the "t_s,pl_mean_v,pl_std_v" CSV (ignoring the '#' header lines) and
shows two views: photoluminescence vs time (with a +/-1 sd band and mean
line), and an FFT of that same trace, so periodic noise (drift, flicker,
mains-related beats) shows up as a distinct peak instead of being buried in
a broadband random-noise floor.

Edit the CONFIGURATION block and run on your PC:  python3 plot_photodiode.py
Requires matplotlib and numpy:  pip install matplotlib numpy
"""

import csv
import os

import matplotlib.pyplot as plt
import numpy as np

# ===== CONFIGURATION =====
# Files live in the repo's data/ folder regardless of where you run this from.
DATA_DIR   = r"D:\data\BudgetODMR\29-06-2026"
INPUT_FILE = os.path.join(DATA_DIR, "photodiode_laser_off.csv")
SAVE_FIG   = os.path.join(DATA_DIR, "photodiode_laser_off.png")   # set to None to skip saving



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

    # FFT of the mean trace. Points are logged roughly every SAMPLE_PERIOD_S
    # but not perfectly evenly spaced, so use the median spacing as the
    # effective sample rate. A narrow peak = periodic/correlated noise; a
    # flat-ish floor = dominated by random noise.
    dt = float(np.median(np.diff(t)))
    fs = 1.0 / dt
    detrended = (np.asarray(mean) - avg) * np.hanning(len(mean))
    spectrum = np.abs(np.fft.rfft(detrended))
    freqs_fft = np.fft.rfftfreq(len(mean), d=dt)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    ax1.fill_between(t, lo, hi, color="tab:blue", alpha=0.2, label="+/-1 sd")
    ax1.plot(t, mean, "-", lw=1.0, color="tab:blue", label="PL mean")
    ax1.axhline(avg, color="tab:red", ls="--", lw=1, label=f"mean = {avg:.4f} V")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Photoluminescence (V)")
    ax1.set_title(f"Photodiode recording ({t[-1]:.0f} s, {len(t)} points, "
                   f"fs~{fs:.2f} Hz)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Skip the DC bin (index 0) -- it's ~0 after removing the mean anyway.
    ax2.semilogy(freqs_fft[1:], spectrum[1:], lw=1.0, color="tab:purple")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Amplitude (a.u., log scale)")
    ax2.set_title("FFT of PL mean -- look for narrow peaks above the noise floor")
    ax2.grid(True, alpha=0.3, which="both")

    fig.tight_layout()

    if SAVE_FIG:
        fig.savefig(SAVE_FIG, dpi=150)
        print(f"Saved {SAVE_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
