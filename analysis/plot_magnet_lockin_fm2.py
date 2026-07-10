"""
Magnet-scan field estimate from the TWO central peaks (FM lock-in).

Pipeline per position:
  1. take the Hilbert ENVELOPE of the noisy FM signal (clean, all-positive),
  2. FIT the 8-line NV Hamiltonian model to that envelope (seeded from the 8 most
     prominent envelope peaks),
  3. take the peak positions FROM THE FIT (the fitted model lines, not the noisy
     signal), and pick the nearest fitted peak below and above 2870 MHz -- the two
     closest to the central dip -- to estimate

         splitting  = f_high - f_low
         |B|_axial  = splitting / (2 * gamma)          gamma = 28.024 MHz/mT

It checks the pair is roughly symmetric about 2870 and warns if not. Two field
estimates are reported: the central-pair axial B, and the full-fit |B|.

Per position it saves a plot (raw, envelope, NV fit, chosen pair); then it plots
field and splitting vs magnet position. Needs scipy for the fit (falls back to
envelope peaks without it). Set MODE (default "fm") and run:
    python plot_magnet_lockin_fm2.py         (numpy + matplotlib; scipy for the fit)
"""

import csv
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "smcv"))
from expconfig import load_config
import nv_odmr_sim as nv

# ===== CONFIGURATION =====
MODE = "fm"                  # data folder: <magnet.out_dir>_<MODE>
PEAK_MIN_FRAC = 0.20         # a peak must be >= this fraction of the tallest peak
SYMM_TOL_FRAC = 0.35         # warn if the pair's two half-splits differ by more than this
DO_FIT = True                # fit the NV 8-line model to the Hilbert ENVELOPE (needs scipy)
SMOOTH_ENV_PTS = 5           # smoothing applied to the envelope before fitting
_cfg = load_config()
BASE = _cfg["magnet"]["out_dir"] + "_" + MODE
INDEX = os.path.join(BASE, "magnet_index.csv")
OUT_DIR = os.path.join(BASE, "analysis_fm2")
GAMMA = _cfg["analysis"]["gamma_mhz_per_mt"]
D_CENTRE = _cfg["analysis"]["d_center_mhz"]
SMOOTH = _cfg["analysis"]["smooth_pts"]
MIN_SEP = _cfg["analysis"]["min_sep_mhz"]


def _smooth(y):
    return np.convolve(y, np.ones(SMOOTH) / SMOOTH, mode="same") if SMOOTH > 1 else y


def hilbert_envelope(y):
    """|analytic signal| via FFT (numpy Hilbert). The FM lock-in signal fluctuates
    fast; its envelope is a clean, all-POSITIVE curve peaking at the resonance
    centres -- which is exactly what the positive-Lorentzian NV model_am fits."""
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


def find_peaks_simple(x, y):
    """Simple find-peaks: local maxima above PEAK_MIN_FRAC of the tallest, separated
    by MIN_SEP, parabolic-refined. Returns (positions, heights) sorted by frequency."""
    ys = _smooth(y)
    base = np.median(ys)
    h = ys - base
    cand = [i for i in range(1, len(ys) - 1)
            if h[i] > 0 and h[i] >= h[i - 1] and h[i] > h[i + 1]]
    if not cand:
        return [], []
    hmax = max(h[i] for i in cand)
    cand = sorted((i for i in cand if h[i] >= PEAK_MIN_FRAC * hmax), key=lambda i: -h[i])
    picks = []
    for i in cand:
        if all(abs(x[i] - x[j]) >= MIN_SEP for j in picks):
            picks.append(i)
    picks.sort()
    out_f, out_h = [], []
    for i in picks:
        d = ys[i - 1] - 2 * ys[i] + ys[i + 1]
        xf = x[i] + 0.5 * (ys[i - 1] - ys[i + 1]) / d * (x[1] - x[0]) if d else x[i]
        out_f.append(float(xf))
        out_h.append(float(h[i]))
    return out_f, out_h


def central_pair(peaks, heights, centre):
    """The nearest peak below and nearest above `centre` (the two closest to the
    central dip). Returns (f_lo, f_hi, warnings) or (None, None, [...])."""
    below = [(f, hh) for f, hh in zip(peaks, heights) if f < centre]
    above = [(f, hh) for f, hh in zip(peaks, heights) if f > centre]
    warn = []
    if not below or not above:
        return None, None, ["no peaks on both sides of centre"]
    f_lo, h_lo = max(below, key=lambda t: t[0])       # closest below
    f_hi, h_hi = min(above, key=lambda t: t[0])       # closest above
    # symmetry check
    d_lo, d_hi = centre - f_lo, f_hi - centre
    if abs(d_lo - d_hi) > SYMM_TOL_FRAC * (0.5 * (d_lo + d_hi)):
        warn.append(f"pair not symmetric about {centre:.0f} "
                    f"({d_lo:.2f} vs {d_hi:.2f} MHz)")
    # prominence check: are these among the two tallest peaks?
    order = sorted(range(len(peaks)), key=lambda i: -heights[i])[:2]
    tall = {round(peaks[i], 3) for i in order}
    if round(f_lo, 3) not in tall or round(f_hi, 3) not in tall:
        warn.append("central pair is not the two most prominent peaks")
    return f_lo, f_hi, warn


def load_index():
    rows = []
    with open(INDEX) as f:
        for r in csv.DictReader(f):
            rows.append((float(r["position"]), r["units"], r["filename"]))
    rows.sort(key=lambda t: t[0])
    return rows


def load_spec(fname):
    x, y = [], []
    for r in csv.reader(open(os.path.join(BASE, fname))):
        if not r or r[0].startswith("#") or r[0].startswith("freq"):
            continue
        x.append(float(r[0]))
        y.append(float(r[1]))
    return np.array(x), np.array(y)


def main():
    if not os.path.exists(INDEX):
        raise SystemExit(f"No magnet_index.csv in {BASE} (is MODE right / scan done?)")
    os.makedirs(OUT_DIR, exist_ok=True)
    index = load_index()
    units = index[0][1]
    print(f"{len(index)} position(s) in {BASE}; centre = {D_CENTRE:.0f} MHz")

    positions, splits, fields, bfit = [], [], [], []
    for pos, _u, fname in index:
        x, y = load_spec(fname)
        env = hilbert_envelope(y)                      # clean, all-positive
        env_pk, env_hh = find_peaks_simple(x, env)     # only used to SEED the fit
        if len(env_pk) < 2:
            print(f"  pos {pos}: <2 envelope peaks")
            continue

        # NV 8-line model fit to the ENVELOPE (all-positive Lorentzian peaks).
        # Seed the guess from the 8 MOST-PROMINENT envelope peaks so stray noise
        # peaks can't corrupt the closed-form starting estimate.
        Bf, fit = np.nan, None
        if DO_FIT:
            top8 = sorted(env_pk[i] for i in sorted(range(len(env_pk)),
                                                    key=lambda i: -env_hh[i])[:8])
            g8, _ = nv.field_from_eight_peaks(top8)
            fit = nv.fit_field(x, env, b_mag_guess_mT=max(g8, 0.05))
            if fit:
                Bf = fit["B_mT"]

        # PEAKS now come from the NV FIT (the clean fitted model lines), not the
        # noisy envelope. Fall back to envelope peaks only if the fit is missing.
        if fit is not None:
            pk = sorted(fit["peaks_MHz"])
            hh = list(np.interp(pk, x, fit["fit_curve"]))
        else:
            pk, hh = env_pk, env_hh

        # central pair (nearest below / above 2870) from the fitted peaks
        f_lo, f_hi, warn = central_pair(pk, hh, D_CENTRE)
        if f_lo is not None:
            split = f_hi - f_lo
            B = split / (2 * GAMMA)
        else:
            split, B = np.nan, np.nan

        positions.append(pos)
        splits.append(split)
        fields.append(B)
        bfit.append(Bf)
        wtxt = ("  [!] " + "; ".join(warn)) if warn else ""
        print(f"  pos {pos:>7} {units}: pair B={B:.3f}  fit |B|={Bf:.3f} mT{wtxt}")

        # per-position plot: raw, envelope, and NV fit to the envelope
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(x, y, lw=0.6, color="0.75", label=f"{MODE} raw")
        ax.plot(x, env, lw=1.4, color="tab:blue", label="Hilbert envelope")
        if fit is not None and fit.get("fit_curve") is not None:
            ax.plot(x, fit["fit_curve"], lw=1.3, color="tab:green", label="NV fit to envelope")
            for c in fit["peaks_MHz"]:
                ax.axvline(c, color="tab:green", ls=":", lw=0.6)
        ax.axvline(D_CENTRE, color="tab:orange", ls=":", lw=1)
        if f_lo is not None:
            ax.axvline(f_lo, color="tab:red", lw=1.4)
            ax.axvline(f_hi, color="tab:red", lw=1.4, label="central pair")
        ax.set_xlabel("Microwave frequency (MHz)")
        ax.set_ylabel(f"lock-in {MODE}")
        ttl = f"{pos} {units}"
        if not np.isnan(B):
            ttl += f"   pair B={B:.3f}"
        if not np.isnan(Bf):
            ttl += f"   fit |B|={Bf:.3f} mT"
        ax.set_title(ttl)
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, f"pair_pos_{pos:g}{units}.png"), dpi=130)
        plt.close(fig)

    if not positions:
        raise SystemExit("No valid positions found.")

    figS, axS = plt.subplots(figsize=(8, 5))
    axS.plot(positions, splits, "o-", color="tab:purple")
    axS.set_xlabel(f"Magnet position ({units})")
    axS.set_ylabel("Central-pair splitting (MHz)")
    axS.set_title(f"Central-pair splitting vs position ({MODE})")
    axS.grid(True, alpha=0.3)
    figS.tight_layout()
    figS.savefig(os.path.join(OUT_DIR, "central_splitting_vs_position.png"), dpi=140)

    figB, axB = plt.subplots(figsize=(8, 5))
    # PRIMARY readout: |B| from the NV Hamiltonian fit (recovers the true magnitude).
    if DO_FIT and np.any(~np.isnan(bfit)):
        axB.plot(positions, bfit, "^-", color="tab:blue", lw=2.0, ms=8,
                 label="|B| from NV fit (primary)")
    # SECONDARY cross-check: axial B from the innermost fitted pair (tracks only the
    # smallest projection, so expect it to sit below |B|).
    axB.plot(positions, fields, "s--", color="tab:green", lw=1.0, alpha=0.7,
             label="central-pair axial B (cross-check)")
    axB.set_xlabel(f"Magnet position ({units})")
    axB.set_ylabel("Magnetic field (mT)")
    axB.set_title(f"Field vs magnet position ({MODE})  -  |B| from NV fit")
    axB.legend()
    axB.grid(True, alpha=0.3)
    figB.tight_layout()
    figB.savefig(os.path.join(OUT_DIR, "central_field_vs_position.png"), dpi=140)

    # dedicated fit-|B| figure (clean, fit result only)
    if DO_FIT and np.any(~np.isnan(bfit)):
        figF, axF = plt.subplots(figsize=(8, 5))
        axF.plot(positions, bfit, "^-", color="tab:blue", lw=2.0, ms=8)
        axF.set_xlabel(f"Magnet position ({units})")
        axF.set_ylabel("|B| (mT)")
        axF.set_title(f"|B| from NV Hamiltonian fit vs magnet position ({MODE})")
        axF.grid(True, alpha=0.3)
        figF.tight_layout()
        figF.savefig(os.path.join(OUT_DIR, "fit_field_vs_position.png"), dpi=140)

    print(f"Saved per-position + summary plots to {OUT_DIR}")
    plt.show()


if __name__ == "__main__":
    main()
