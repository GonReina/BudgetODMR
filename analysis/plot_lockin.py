"""
Analyse the lock-in ODMR data from smcv/odmr_lockin_{am,fm,fm_deriv}_pc.py.

Each of those scripts writes, under <data_dir>:
    odmr_lockin_runs_<mode>/run_XX.csv   per sweep: freq_MHz,signal
    odmr_lockin_<mode>_average.csv       running average
where <mode> is am | fm | fm_deriv. This script averages the per-run files
(median across runs, robust to a bad sweep), plots the averaged lineshape, and
finds the resonance centre(s) -- but the CENTRE means something different for each
method, so the finder is chosen by mode:

  am        -> line is a PEAK in the lock-in magnitude; centre = peak.
  fm        -> line is the |derivative| (two lobes, NULL at centre); centre =
               midpoint between the two lobes of each resonance.
  fm_deriv  -> line is the SIGNED derivative (dispersive, ZERO-CROSSING at centre);
               we integrate it back to an absorption line and take its extremum.

If two centres are found (e.g. a Zeeman-split pair) it reports the splitting and
the implied axial field B = df / (2*gamma).

Set MODE and run on the PC:  python plot_lockin.py     (needs numpy + matplotlib)
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
N_RESONANCES = 4            # how many resonance centres to look for (2 = Zeeman pair)
PLOT_RUNS = True            # also save a plot of each individual run_XX.csv

_cfg = load_config()
DATA_DIR = _cfg["paths"]["data_dir"]
RUNS_DIR = os.path.join(DATA_DIR, _cfg["lockin"]["runs_subdir"] + "_" + MODE)
SAVE_FIG = os.path.join(DATA_DIR, f"odmr_lockin_{MODE}.png")   # None to skip

_a = _cfg["analysis"]
GAMMA_MHZ_PER_MT = _a["gamma_mhz_per_mt"]
SMOOTH_PTS  = _a["smooth_pts"]
MIN_SEP_MHZ = _a["min_sep_mhz"]
DEPTH_FRAC  = _a["depth_frac"]


# --------------------------------------------------------------------------
def median(vals):
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def load_runs(runs_dir):
    paths = sorted(glob.glob(os.path.join(runs_dir, "run_*.csv")))
    if not paths:
        raise SystemExit(f"No run_*.csv in {runs_dir} (is MODE right?)")
    by_freq = {}
    runs = []
    for p in paths:
        xf, yf = [], []
        with open(p) as f:
            for row in csv.reader(f):
                if not row or row[0].startswith("#") or row[0].startswith("freq"):
                    continue
                fr, val = float(row[0]), float(row[1])
                by_freq.setdefault(fr, []).append(val)
                xf.append(fr)
                yf.append(val)
        runs.append((os.path.basename(p), np.array(xf), np.array(yf)))
    freqs = np.array(sorted(by_freq))
    sig = np.array([median(by_freq[fr]) for fr in freqs])
    std = np.array([float(np.std(by_freq[fr])) for fr in freqs])
    print(f"Averaged {len(paths)} run(s), {len(freqs)} points, from {runs_dir}")
    return freqs, sig, std, runs


def plot_run(name, x, y, out_png):
    """Save a plot of one individual run (raw lock-in signal vs frequency)."""
    ctr = find_centres(x, y, MODE, N_RESONANCES)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(x, y, "-", lw=0.9, color="tab:gray")
    for c in ctr:
        ax.axvline(c, color="tab:red", ls="--", lw=1)
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel(f"lock-in {MODE}")
    ax.set_title(name + (f"   split {ctr[-1]-ctr[0]:.2f} MHz" if len(ctr) >= 2 else ""))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def smooth(y):
    if SMOOTH_PTS > 1:
        return np.convolve(y, np.ones(SMOOTH_PTS) / SMOOTH_PTS, mode="same")
    return y


def _refine(x, y, i):
    if 0 < i < len(y) - 1:
        d = y[i - 1] - 2 * y[i] + y[i + 1]
        if d != 0:
            return x[i] + 0.5 * (y[i - 1] - y[i + 1]) / d * (x[1] - x[0])
    return x[i]


def find_extrema(x, y, n, kind="max", min_sep=None):
    """Up to n most prominent maxima ('max') or minima ('min'), separated by
    min_sep (default MIN_SEP_MHZ), parabolic-refined. Returns sorted x positions."""
    if min_sep is None:
        min_sep = MIN_SEP_MHZ
    ys = smooth(y)
    base = median(ys)
    h = (ys - base) if kind == "max" else (base - ys)      # positive at the feature
    ext = [i for i in range(1, len(ys) - 1)
           if h[i] > 0 and h[i] >= h[i - 1] and h[i] > h[i + 1]]
    if not ext:
        return []
    hmax = max(h[i] for i in ext)
    cand = sorted((i for i in ext if h[i] >= DEPTH_FRAC * hmax), key=lambda i: -h[i])
    picks = []
    for i in cand:
        if all(abs(x[i] - x[j]) >= min_sep for j in picks):
            picks.append(i)
        if len(picks) >= n:
            break
    return sorted(_refine(x, ys, i) for i in picks)


def find_centres(x, y, mode, n):
    """Method-aware resonance-centre finder."""
    if mode == "am":
        return find_extrema(x, y, n, "max")                # peak(s)
    if mode == "fm_deriv":
        integ = np.cumsum(smooth(y) - median(smooth(y)))   # integrate derivative -> line
        return find_extrema(x, np.abs(integ - median(integ)), n, "max")
    if mode == "fm":
        # |derivative|: each resonance = two closely-spaced lobes. Find all lobes
        # with a SMALL separation, then cluster lobes into resonances (gaps larger
        # than MIN_SEP_MHZ separate resonances); each cluster centre = its mean.
        step = x[1] - x[0]
        lobes = find_extrema(x, y, 4 * n, "max", min_sep=max(2 * step, 0.4))
        if not lobes:
            return []
        clusters, cur = [], [lobes[0]]
        for a, b in zip(lobes, lobes[1:]):
            if b - a > MIN_SEP_MHZ:
                clusters.append(cur)
                cur = [b]
            else:
                cur.append(b)
        clusters.append(cur)
        centres = sorted(sum(c) / len(c) for c in clusters if c)
        # if more clusters than expected, keep the n widest-support ones
        if len(centres) > n:
            clusters.sort(key=len, reverse=True)
            centres = sorted(sum(c) / len(c) for c in clusters[:n])
        return centres
    raise ValueError(mode)


def main():
    freqs, sig, std, runs = load_runs(RUNS_DIR)
    centres = find_centres(freqs, sig, MODE, N_RESONANCES)

    if PLOT_RUNS:
        rdir = os.path.join(RUNS_DIR, "run_plots")
        os.makedirs(rdir, exist_ok=True)
        for name, x, y in runs:
            plot_run(name, x, y, os.path.join(rdir, name.replace(".csv", ".png")))
        print(f"Saved {len(runs)} per-run plot(s) to {rdir}")

    label = {"am": "peak", "fm": "null (lobe midpoint)",
             "fm_deriv": "zero-crossing"}[MODE]
    print(f"MODE={MODE}: found {len(centres)} centre(s) [{label}]:")
    for c in centres:
        print(f"  {c:.3f} MHz")
    if len(centres) >= 2:
        split = centres[-1] - centres[0]
        b = split / (2 * GAMMA_MHZ_PER_MT)
        print(f"  -> splitting {split:.3f} MHz  ->  B_axial {b:.4f} mT")

    fig, ax = plt.subplots(figsize=(9, 5))
    lo, hi = sig - std, sig + std
    ax.fill_between(freqs, lo, hi, color="tab:blue", alpha=0.15, label="+/-1 sd")
    ax.plot(freqs, sig, "-", lw=1.2, color="tab:blue", label=f"lock-in {MODE}")
    if MODE == "fm_deriv":
        ax.axhline(np.median(sig), color="0.6", lw=0.8, ls=":")
    for c in centres:
        ax.axvline(c, color="tab:red", ls="--", lw=1)
    if centres:
        ax.plot([], [], color="tab:red", ls="--", lw=1, label=f"centre ({label})")
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel(f"Lock-in signal ({'R' if MODE != 'fm_deriv' else 'X, signed'})")
    ax.set_title(f"Lock-in ODMR ({MODE})"
                 + (f"  -  split {centres[-1]-centres[0]:.2f} MHz" if len(centres) >= 2 else ""))
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if SAVE_FIG:
        fig.savefig(SAVE_FIG, dpi=150)
        print(f"Saved {SAVE_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
