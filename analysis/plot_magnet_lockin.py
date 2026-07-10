"""
Analyse a lock-in magnet scan (smcv/odmr_magnet_scan_{am,fm,fm_deriv}_pc.py).

For every magnet position it:
  * plots the ODMR spectrum and marks the resonances (up to 8, from the 4 NV
    orientations),
  * estimates the magnetic-field magnitude three ways:
      - from the TWO most prominent peaks  (axial projection, B = df/2gamma),
      - from all EIGHT peaks               (|B| = sqrt(3/4 sum B_par_i^2), exact for
                                            the 4 tetrahedral NV axes),
      - from a FIT of the 8-line NV Hamiltonian model (needs scipy; am only),
and then plots a waterfall of all positions, |B| vs position (all three estimates),
and the outer splitting vs position.

Set MODE and run on the PC:  python plot_magnet_lockin.py   (numpy+matplotlib; scipy optional)
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
MODE = "fm"                  # "am" | "fm" | "fm_deriv"
N_PEAKS = 8
DO_FIT = True                # fit the NV model (am, needs scipy)

_cfg = load_config()
BASE = _cfg["magnet"]["out_dir"] + "_" + MODE
INDEX = os.path.join(BASE, "magnet_index.csv")
OUT_DIR = os.path.join(BASE, "analysis")
GAMMA = _cfg["analysis"]["gamma_mhz_per_mt"]
SMOOTH = _cfg["analysis"]["smooth_pts"]
MIN_SEP = _cfg["analysis"]["min_sep_mhz"]
FRAC = _cfg["analysis"]["depth_frac"]


def _smooth(y):
    return np.convolve(y, np.ones(SMOOTH) / SMOOTH, mode="same") if SMOOTH > 1 else y


def _refine(x, y, i):
    d = y[i - 1] - 2 * y[i] + y[i + 1]
    return x[i] + 0.5 * (y[i - 1] - y[i + 1]) / d * (x[1] - x[0]) if d else x[i]


def _extrema(x, y, n, min_sep):
    ys = _smooth(y)
    h = ys - np.median(ys)
    idx = [i for i in range(1, len(ys) - 1) if h[i] > 0 and h[i] >= h[i - 1] and h[i] > h[i + 1]]
    if not idx:
        return [], []
    hmax = max(h[i] for i in idx)
    cand = sorted((i for i in idx if h[i] >= FRAC * hmax), key=lambda i: -h[i])
    picks = []
    for i in cand:
        if all(abs(x[i] - x[j]) >= min_sep for j in picks):
            picks.append(i)
        if len(picks) >= n:
            break
    picks.sort()
    return [_refine(x, ys, i) for i in picks], [float(h[i]) for i in picks]


def find_resonances(x, y, mode, n):
    """Return (positions_MHz, amplitudes) of up to n resonance centres, per method."""
    if mode == "am":
        return _extrema(x, y, n, MIN_SEP)
    if mode == "fm_deriv":
        integ = np.cumsum(_smooth(y) - np.median(_smooth(y)))
        return _extrema(x, np.abs(integ - np.median(integ)), n, MIN_SEP)
    if mode == "fm":                                   # |derivative|: cluster lobe pairs
        step = x[1] - x[0]
        lobes, lh = _extrema(x, y, 4 * n, max(2 * step, 0.4))
        if not lobes:
            return [], []
        order = np.argsort(lobes)
        lobes = [lobes[i] for i in order]
        lh = [lh[i] for i in order]
        clusters, cur, curh = [], [lobes[0]], [lh[0]]
        for a, b, hh in zip(lobes, lobes[1:], lh[1:]):
            if b - a > MIN_SEP:
                clusters.append((cur, curh))
                cur, curh = [b], [hh]
            else:
                cur.append(b)
                curh.append(hh)
        clusters.append((cur, curh))
        pos = [sum(c) / len(c) for c, _ in clusters]
        amp = [sum(hh) / len(hh) for _, hh in clusters]
        return pos, amp
    raise ValueError(mode)


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
    print(f"{len(index)} position(s) in {BASE}")

    positions, b2, b8, bfit, outsplit, specs = [], [], [], [], [], []
    fit_curves = {}
    for pos, _u, fname in index:
        x, y = load_spec(fname)
        specs.append((pos, x, y))
        pk, amp = find_resonances(x, y, MODE, N_PEAKS)
        if len(pk) < 2:
            print(f"  pos {pos}: <2 peaks found")
            continue

        # two most prominent (by amplitude) -> axial B
        top2 = sorted(sorted(range(len(pk)), key=lambda i: -amp[i])[:2])
        f_lo, f_hi = pk[top2[0]], pk[top2[1]]
        B2 = nv.field_from_two_peaks(f_lo, f_hi)
        # all peaks -> |B| (exact closed form)
        B8, splits = nv.field_from_eight_peaks(pk)
        # optional model fit (am)
        Bf = np.nan
        fit = None
        if DO_FIT and MODE == "am":
            fit = nv.fit_field(x, y, b_mag_guess_mT=max(B8, 0.05))
            if fit:
                Bf = fit["B_mT"]

        positions.append(pos)
        b2.append(B2)
        b8.append(B8)
        bfit.append(Bf)
        outsplit.append(pk[-1] - pk[0])
        print(f"  pos {pos:>7} {units}: {len(pk)} peaks | B(2pk)={B2:.3f}  "
              f"B(8pk)={B8:.3f}  B(fit)={Bf:.3f} mT")

        # per-position ODMR plot
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(x, y, lw=0.8, color="0.4", label=f"{MODE} spectrum")
        for c in pk:
            ax.axvline(c, color="tab:red", ls="--", lw=0.8)
        for i in top2:
            ax.axvline(pk[i], color="tab:blue", lw=1.4, alpha=0.7)
        if fit is not None and fit.get("fit_curve") is not None:
            ax.plot(x, fit["fit_curve"], lw=1.3, color="tab:green", label="NV fit")
        ax.set_xlabel("Microwave frequency (MHz)")
        ax.set_ylabel(f"lock-in {MODE}")
        ax.set_title(f"{pos} {units}   {len(pk)} peaks | B8={B8:.3f} mT"
                     + (f", Bfit={Bf:.3f}" if not np.isnan(Bf) else ""))
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, f"odmr_pos_{pos:g}{units}.png"), dpi=130)
        plt.close(fig)

    # ---- waterfall ----
    figW, axW = plt.subplots(figsize=(9, 7))
    off = 0.0
    step = 1.1 * max((np.ptp(y) for _, _, y in specs), default=1.0)
    for pos, x, y in specs:
        axW.plot(x, y + off, lw=0.8)
        axW.text(x[0], off, f"{pos:g} {units}", fontsize=8, va="bottom")
        off += step
    axW.set_xlabel("Microwave frequency (MHz)")
    axW.set_ylabel("lock-in signal (offset per position)")
    axW.set_title(f"ODMR vs magnet position ({MODE})")
    axW.grid(True, alpha=0.3)
    figW.tight_layout()
    figW.savefig(os.path.join(OUT_DIR, "waterfall.png"), dpi=140)

    # ---- |B| vs position ----
    figB, axB = plt.subplots(figsize=(8, 5))
    axB.plot(positions, b2, "o-", label="B from 2 most-prominent peaks (axial)")
    axB.plot(positions, b8, "s-", label="|B| from 8 peaks (closed form)")
    if DO_FIT and MODE == "am" and np.any(~np.isnan(bfit)):
        axB.plot(positions, bfit, "^-", label="|B| from NV model fit")
    axB.set_xlabel(f"Magnet position ({units})")
    axB.set_ylabel("Magnetic field (mT)")
    axB.set_title(f"Estimated field vs magnet position ({MODE})")
    axB.legend()
    axB.grid(True, alpha=0.3)
    figB.tight_layout()
    figB.savefig(os.path.join(OUT_DIR, "field_vs_position.png"), dpi=140)

    # ---- outer splitting vs position ----
    figS, axS = plt.subplots(figsize=(8, 5))
    axS.plot(positions, outsplit, "o-", color="tab:purple")
    axS.set_xlabel(f"Magnet position ({units})")
    axS.set_ylabel("Outer peak separation (MHz)")
    axS.set_title(f"Outer splitting vs magnet position ({MODE})")
    axS.grid(True, alpha=0.3)
    figS.tight_layout()
    figS.savefig(os.path.join(OUT_DIR, "splitting_vs_position.png"), dpi=140)

    print(f"Saved per-position + summary plots to {OUT_DIR}")
    plt.show()


if __name__ == "__main__":
    main()
