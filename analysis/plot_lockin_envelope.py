"""
Hilbert-envelope view of each lock-in run.

A single lock-in sweep (odmr_lockin_*_pc.py) is a noisy, fast-fluctuating curve
riding on the ODMR line(s) -- it can look like "wave packets". The analytic-signal
(Hilbert) envelope tracks the slowly-varying amplitude of that fluctuation, which
pulls out the underlying resonance structure without averaging many sweeps.

For each run_XX.csv in the mode's runs folder this saves a plot of the raw signal
plus its Hilbert envelope, and marks the envelope peak(s). It also draws a combined
figure of all the run envelopes so you can see run-to-run consistency.

Uses numpy only (its own FFT-based Hilbert transform -- no scipy needed).

Set MODE and run on the PC:  python plot_lockin_envelope.py
"""

import csv
import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

# expconfig.py + config.json live in the sibling smcv/ folder
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "smcv"))
from expconfig import load_config

# ===== CONFIGURATION =====
MODE = "fm"                 # "am" | "fm" | "fm_deriv"
SMOOTH_ENV_PTS = 5          # extra moving-average smoothing of the envelope (1 = none)
N_PEAKS = 4               # envelope peaks to mark (2 = Zeeman pair)

_cfg = load_config()
RUNS_DIR = os.path.join(_cfg["paths"]["data_dir"], _cfg["lockin"]["runs_subdir"] + "_" + MODE)
OUT_DIR = os.path.join(RUNS_DIR, "run_envelopes")
GAMMA = _cfg["analysis"]["gamma_mhz_per_mt"]
MIN_SEP = _cfg["analysis"]["min_sep_mhz"]


def analytic_envelope(y):
    """|analytic signal| via FFT (numpy-only Hilbert). Envelope of the fluctuation
    about the median, added back to the median for display."""
    base = np.median(y)
    x = y - base
    n = len(x)
    X = np.fft.fft(x)
    h = np.zeros(n)
    if n % 2 == 0:
        h[0] = h[n // 2] = 1.0
        h[1:n // 2] = 2.0
    else:
        h[0] = 1.0
        h[1:(n + 1) // 2] = 2.0
    env = np.abs(np.fft.ifft(X * h))
    if SMOOTH_ENV_PTS > 1:
        env = np.convolve(env, np.ones(SMOOTH_ENV_PTS) / SMOOTH_ENV_PTS, mode="same")
    return base + env


def peaks(x, env, n):
    """n most prominent envelope maxima, separated by MIN_SEP, sorted by frequency."""
    b = np.median(env)
    h = env - b
    idx = [i for i in range(1, len(env) - 1)
           if h[i] > 0 and h[i] >= h[i - 1] and h[i] > h[i + 1]]
    idx.sort(key=lambda i: -h[i])
    picks = []
    for i in idx:
        if all(abs(x[i] - x[j]) >= MIN_SEP for j in picks):
            picks.append(i)
        if len(picks) >= n:
            break
    return sorted(x[i] for i in picks)


def load(path):
    x, y = [], []
    for row in csv.reader(open(path)):
        if not row or row[0].startswith("#") or row[0].startswith("freq"):
            continue
        x.append(float(row[0]))
        y.append(float(row[1]))
    return np.array(x), np.array(y)


def main():
    paths = sorted(glob.glob(os.path.join(RUNS_DIR, "run_*.csv")))
    if not paths:
        raise SystemExit(f"No run_*.csv in {RUNS_DIR} (is MODE right?)")
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"{len(paths)} run(s) in {RUNS_DIR}")

    by_freq = {}
    figA, axA = plt.subplots(figsize=(10, 5))     # combined envelopes
    for p in paths:
        name = os.path.basename(p)
        x, y = load(p)
        for fr, val in zip(x, y):
            by_freq.setdefault(fr, []).append(val)
        env = analytic_envelope(y)
        pk = peaks(x, env, N_PEAKS)
        info = ""
        if len(pk) >= 2:
            split = pk[-1] - pk[0]
            info = f"  split {split:.2f} MHz -> B {split/(2*GAMMA):.3f} mT"
        print(f"  {name}: envelope peaks {[round(v,2) for v in pk]}{info}")

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(x, y, lw=0.6, color="0.7", label="raw run")
        ax.plot(x, env, lw=1.6, color="tab:blue", label="Hilbert envelope")
        for v in pk:
            ax.axvline(v, color="tab:red", ls="--", lw=1)
        ax.set_xlabel("Microwave frequency (MHz)")
        ax.set_ylabel(f"lock-in {MODE}")
        ax.set_title(name + info)
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, name.replace(".csv", "_env.png")), dpi=130)
        plt.close(fig)

        axA.plot(x, env, lw=0.9, alpha=0.5, color="0.6")

    # ---- averaged (median across runs) envelope ----
    afreq = np.array(sorted(by_freq))
    aavg = np.array([np.median(by_freq[fr]) for fr in afreq])
    aenv = analytic_envelope(aavg)
    apk = peaks(afreq, aenv, N_PEAKS)
    ainfo = ""
    if len(apk) >= 2:
        asplit = apk[-1] - apk[0]
        ainfo = f"  outer split {asplit:.2f} MHz -> B {asplit/(2*GAMMA):.3f} mT"
    print(f"  AVERAGE ({len(paths)} runs): envelope peaks {[round(v,2) for v in apk]}{ainfo}")

    axA.plot(afreq, aenv, lw=2.2, color="tab:red", label="average envelope")
    axA.set_xlabel("Microwave frequency (MHz)")
    axA.set_ylabel(f"lock-in {MODE} envelope")
    axA.set_title(f"Hilbert envelopes: {len(paths)} run(s) (grey) + average (red) ({MODE})")
    axA.legend()
    axA.grid(True, alpha=0.3)
    figA.tight_layout()
    figA.savefig(os.path.join(OUT_DIR, "all_envelopes.png"), dpi=140)

    figB, axB = plt.subplots(figsize=(10, 4))
    axB.plot(afreq, aavg, lw=0.7, color="0.7", label=f"median of {len(paths)} runs")
    axB.plot(afreq, aenv, lw=1.8, color="tab:red", label="Hilbert envelope")
    for v in apk:
        axB.axvline(v, color="tab:green", ls="--", lw=1)
    axB.set_xlabel("Microwave frequency (MHz)")
    axB.set_ylabel(f"lock-in {MODE}")
    axB.set_title(f"Averaged spectrum + envelope ({len(paths)} runs){ainfo}")
    axB.legend()
    axB.grid(True, alpha=0.3)
    figB.tight_layout()
    figB.savefig(os.path.join(OUT_DIR, "average_envelope.png"), dpi=140)

    print(f"Saved per-run + combined + average envelope plots to {OUT_DIR}")
    plt.show()


if __name__ == "__main__":
    main()
