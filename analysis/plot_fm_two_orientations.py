"""
Fit the NV spin-1 Hamiltonian for only TWO NV orientations (4 lines) to an FM
lock-in dataset.

Why two orientations: for some field directions / crystal cuts only two of the
four NV orientations are resolved (the other two overlap or are too weak). This
fits the Hamiltonian restricted to two <111> axes instead of the full eight.

Pipeline:
  1. load an FM spectrum -- either a single CSV (DATA_FILE) or the median-average
     of the run_*.csv files in the FM runs folder,
  2. take the Hilbert ENVELOPE -> clean, all-positive curve peaking at resonances,
  3. seed |B| from the widest envelope pair, then fit the 2-orientation Hamiltonian
     (|B|, theta, phi, D, linewidth, amplitude, baseline) to the envelope,
  4. report |B|, the two axial projections and the four line positions; plot
     raw + envelope + fit + fitted lines.

Two orientations constrain |B| less tightly than the full 8-line fit -- use
plot_magnet_lockin_fm2.py when all four orientations are visible.

Run on the PC:  python plot_fm_two_orientations.py   (numpy + matplotlib; scipy for the fit)
"""

import csv
import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "smcv"))
from expconfig import load_config
import nv_odmr_sim as nv

# ===== CONFIGURATION =====
MODE = "fm"                  # data folder / label
AXES = (0, 1, 2)                # which two of the four NV_AXES (0..3) to fit
DATA_FILE = None             # a single freq,signal CSV; None -> average the FM runs
SMOOTH_ENV_PTS = 5           # moving-average smoothing of the envelope before fitting

_cfg = load_config()
DATA_DIR = _cfg["paths"]["data_dir"]
RUNS_DIR = os.path.join(DATA_DIR, _cfg["lockin"]["runs_subdir"] + "_" + MODE)
OUT_DIR = os.path.join(DATA_DIR, "fm_two_orientation_fit")
GAMMA = _cfg["analysis"]["gamma_mhz_per_mt"]
D_CENTRE = _cfg["analysis"]["d_center_mhz"]
MIN_SEP = _cfg["analysis"]["min_sep_mhz"]


def hilbert_envelope(y):
    """|analytic signal| via numpy FFT (no scipy). The fast-fluctuating FM lock-in
    signal has a slowly-varying, all-positive envelope that peaks at the resonance
    centres -- exactly what the positive-Lorentzian NV model fits."""
    base = np.median(y)
    x = np.asarray(y, float) - base
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
    return env


def find_peaks_simple(x, y, n=4):
    """Up to n most-prominent local maxima above the median, separated by MIN_SEP,
    sorted by frequency. Used only to SEED the field guess."""
    b = np.median(y)
    h = np.asarray(y, float) - b
    cand = [i for i in range(1, len(y) - 1)
            if h[i] > 0 and h[i] >= h[i - 1] and h[i] > h[i + 1]]
    cand.sort(key=lambda i: -h[i])
    picks = []
    for i in cand:
        if all(abs(x[i] - x[j]) >= MIN_SEP for j in picks):
            picks.append(i)
        if len(picks) >= n:
            break
    picks.sort()
    return [float(x[i]) for i in picks]


def _read_csv(path):
    x, y = [], []
    for row in csv.reader(open(path)):
        if not row or row[0].startswith("#") or row[0].startswith("freq"):
            continue
        x.append(float(row[0]))
        y.append(float(row[1]))
    return np.array(x), np.array(y)


def load_dataset():
    """Return (freq_MHz, signal). Single file if DATA_FILE is set, else the
    median across all run_*.csv in the FM runs folder."""
    if DATA_FILE:
        print(f"Loading single dataset: {DATA_FILE}")
        return _read_csv(DATA_FILE)
    paths = sorted(glob.glob(os.path.join(RUNS_DIR, "run_*.csv")))
    if not paths:
        raise SystemExit(f"No run_*.csv in {RUNS_DIR} and DATA_FILE not set.")
    by_freq = {}
    for p in paths:
        x, y = _read_csv(p)
        for fr, val in zip(x, y):
            by_freq.setdefault(fr, []).append(val)
    fr = np.array(sorted(by_freq))
    sig = np.array([np.median(by_freq[v]) for v in fr])
    print(f"Averaged {len(paths)} run(s), {len(fr)} points, from {RUNS_DIR}")
    return fr, sig


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    x, y = load_dataset()
    env = hilbert_envelope(y)

    # seed |B| from the widest envelope pair (axial-projection lower bound)
    seed_pk = find_peaks_simple(x, env, n=4)
    if len(seed_pk) >= 2:
        b_guess = max((seed_pk[-1] - seed_pk[0]) / (2 * GAMMA), 0.05)
    else:
        b_guess = 0.3
    print(f"Seed peaks {[round(v, 2) for v in seed_pk]} -> |B| guess {b_guess:.3f} mT")

    fit = nv.fit_field_axes(x, env, axes_idx=AXES, b_mag_guess_mT=b_guess,
                            D=D_CENTRE)
    if fit is None:
        raise SystemExit("scipy is required for the fit (pip install scipy).")

    axial = fit["axial_projections_mT"]
    print(f"\nTwo-orientation Hamiltonian fit (NV axes {AXES}):")
    print(f"  |B|            = {fit['B_mT']:.4f} mT")
    print(f"  axial B (ax {AXES[0]}) = {axial[0]:+.4f} mT")
    print(f"  axial B (ax {AXES[1]}) = {axial[1]:+.4f} mT")
    print(f"  D              = {fit['D_MHz']:.2f} MHz")
    print(f"  linewidth FWHM = {fit['fwhm_MHz']:.2f} MHz")
    print(f"  line positions = {[round(v, 2) for v in fit['peaks_MHz']]} MHz")
    print(f"  fit converged  = {fit['success']}")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(x, y, lw=0.6, color="0.75", label=f"{MODE} raw")
    ax.plot(x, env, lw=1.4, color="tab:blue", label="Hilbert envelope")
    ax.plot(x, fit["fit_curve"], lw=1.6, color="tab:green",
            label=f"2-orientation NV fit (axes {AXES})")
    for c in fit["peaks_MHz"]:
        ax.axvline(c, color="tab:green", ls=":", lw=0.8)
    ax.axvline(D_CENTRE, color="tab:orange", ls=":", lw=1, label=f"D={D_CENTRE:.0f}")
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel(f"lock-in {MODE}")
    ax.set_title(f"Two-orientation NV fit   |B|={fit['B_mT']:.3f} mT   "
                 f"axial {axial[0]:+.3f} / {axial[1]:+.3f} mT")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "fm_two_orientation_fit.png")
    fig.savefig(out, dpi=140)
    print(f"\nSaved {out}")
    plt.show()


if __name__ == "__main__":
    main()
