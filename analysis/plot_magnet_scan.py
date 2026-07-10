"""
Plot the magnet-distance ODMR scan produced by odmr_magnet_scan.py.

Reads magnet_index.csv (idx,position,units,filename,timestamp) and each pos_*.csv
spectrum, finds the two NV resonance dips in every spectrum, and makes three
figures:

  1. Waterfall of all spectra (offset by position) with the two dips marked --
     you should see the pair separate as the magnet gets closer.
  2. Dip separation (MHz) vs magnet position.
  3. Estimated axial magnetic field vs magnet position.

Physics of the field estimate
------------------------------
The NV ground state has a zero-field splitting D ~= 2870 MHz. An axial magnetic
field B_par (the component ALONG the NV symmetry axis) Zeeman-splits the two
ms=+/-1 lines symmetrically:  f+/- = D +/- gamma * B_par, so the measured
splitting is  df = 2 * gamma * B_par  with gamma = 28.024 MHz/mT. Hence

    B_par [mT] = df [MHz] / (2 * 28.024) = df / 56.05

IMPORTANT: this is the field PROJECTED onto the NV axis of the family you're
seeing, not necessarily the total |B|. The true |B| >= B_par, equal only if the
magnet field is aligned with that NV axis. Getting the full vector |B| requires
resolving splittings from several of the four NV orientations (up to 8 dips).
The ~2.16 MHz 14N hyperfine triplet is a separate, fixed sub-structure that does
NOT move with the magnet and is only visible at sub-MHz resolution / high SNR --
it is not what produces the position-dependent separation here.

Edit CONFIGURATION and run on the PC:  python plot_magnet_scan.py
Requires matplotlib + numpy.
"""

import csv
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

# expconfig.py + config.json live in the sibling smcv/ folder; put it on the path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "smcv"))
from expconfig import load_config

# ===== CONFIGURATION (from config.json) =====
_cfg = load_config()
OUT_DIR    = _cfg["magnet"]["out_dir"]
INDEX_FILE = os.path.join(OUT_DIR, "magnet_index.csv")
SAVE_DIR   = OUT_DIR                     # where PNGs are written (None to skip saving)

_a = _cfg["analysis"]
GAMMA_MHZ_PER_MT = _a["gamma_mhz_per_mt"]   # NV electron gyromagnetic ratio
D_CENTER_MHZ     = _a["d_center_mhz"]        # zero-field splitting (used only as a hint)

# dip-finder tuning
SMOOTH_PTS   = _a["smooth_pts"]    # moving-average window before finding minima
MIN_SEP_MHZ  = _a["min_sep_mhz"]   # two dips must be at least this far apart
DEPTH_FRAC   = _a["depth_frac"]    # a dip must be >= this fraction of the deepest dip's depth


def load_index(path):
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append((float(row["position"]), row["units"], row["filename"]))
    return rows


def load_spectrum(path):
    freq, sig = [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0].startswith("freq"):
                continue
            freq.append(float(row[0]))
            sig.append(float(row[1]))
    return np.array(freq), np.array(sig)


def _refine(x, y, i):
    """Parabolic sub-sample interpolation of an extremum at index i."""
    if 0 < i < len(y) - 1:
        denom = y[i - 1] - 2 * y[i] + y[i + 1]
        if denom != 0:
            delta = 0.5 * (y[i - 1] - y[i + 1]) / denom
            return x[i] + delta * (x[1] - x[0])
    return x[i]


def find_two_dips(x, y):
    """Return (f_low, f_high, separation_MHz). separation=0 if only one dip."""
    ys = y
    if SMOOTH_PTS > 1:
        k = np.ones(SMOOTH_PTS) / SMOOTH_PTS
        ys = np.convolve(y, k, mode="same")
    depth = np.median(ys) - ys                      # positive at a dip
    # local maxima of depth = local minima of signal
    mins = [i for i in range(1, len(ys) - 1)
            if depth[i] > 0 and depth[i] >= depth[i - 1] and depth[i] > depth[i + 1]]
    if not mins:
        return None
    dmax = max(depth[i] for i in mins)
    cand = sorted((i for i in mins if depth[i] >= DEPTH_FRAC * dmax),
                  key=lambda i: -depth[i])
    f1 = _refine(x, ys, cand[0])
    second = next((i for i in cand[1:] if abs(x[i] - x[cand[0]]) >= MIN_SEP_MHZ), None)
    if second is None:
        return (f1, f1, 0.0)
    f2 = _refine(x, ys, second)
    lo, hi = sorted((f1, f2))
    return (lo, hi, hi - lo)


def main():
    index = load_index(INDEX_FILE)
    if not index:
        raise SystemExit(f"No positions found in {INDEX_FILE}")
    index.sort(key=lambda r: r[0])                  # by position
    units = index[0][1]

    positions, seps, bfields, spectra = [], [], [], []
    for pos, _u, fname in index:
        x, y = load_spectrum(os.path.join(OUT_DIR, fname))
        res = find_two_dips(x, y)
        spectra.append((pos, x, y, res))
        if res is None:
            print(f"  pos {pos}: no dip found")
            continue
        lo, hi, sep = res
        b = sep / (2 * GAMMA_MHZ_PER_MT)
        positions.append(pos)
        seps.append(sep)
        bfields.append(b)
        print(f"  pos {pos:>8} {units}:  dips {lo:.2f} & {hi:.2f} MHz  "
              f"-> split {sep:.2f} MHz  -> B_axial {b:.3f} mT")

    # ---- Figure 1: waterfall of spectra ----
    fig1, ax1 = plt.subplots(figsize=(9, 7))
    offs = 0.0
    step = 0.08                                     # vertical offset between traces
    for pos, x, y, res in spectra:
        yb = y / np.median(y) + offs                # normalize then offset
        ax1.plot(x, yb, lw=1.0)
        ax1.text(x[0], offs + 1.0, f"{pos:g} {units}", fontsize=8, va="bottom")
        if res is not None and res[2] > 0:
            lo, hi, _ = res
            for fdip in (lo, hi):
                j = int(np.argmin(np.abs(x - fdip)))
                ax1.plot(fdip, y[j] / np.median(y) + offs, "v", color="tab:red", ms=6)
        offs += step
    ax1.set_xlabel("Microwave frequency (MHz)")
    ax1.set_ylabel("Normalized signal (offset per position)")
    ax1.set_title("ODMR spectra vs magnet position (dips marked)")
    ax1.grid(True, alpha=0.3)
    fig1.tight_layout()

    # ---- Figure 2: dip separation vs position ----
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ax2.plot(positions, seps, "o-", color="tab:blue")
    ax2.set_xlabel(f"Magnet position ({units})")
    ax2.set_ylabel("Dip separation (MHz)")
    ax2.set_title("NV dip separation vs magnet position")
    ax2.grid(True, alpha=0.3)
    fig2.tight_layout()

    # ---- Figure 3: axial B field vs position ----
    fig3, ax3 = plt.subplots(figsize=(8, 5))
    ax3.plot(positions, bfields, "s-", color="tab:green")
    ax3.set_xlabel(f"Magnet position ({units})")
    ax3.set_ylabel("Axial magnetic field B$_\\parallel$ (mT)")
    ax3.set_title("Estimated axial field from Zeeman splitting  (B = df / 2$\\gamma$)")
    ax3.grid(True, alpha=0.3)
    fig3.tight_layout()

    if SAVE_DIR:
        fig1.savefig(os.path.join(SAVE_DIR, "magnet_waterfall.png"), dpi=150)
        fig2.savefig(os.path.join(SAVE_DIR, "magnet_separation.png"), dpi=150)
        fig3.savefig(os.path.join(SAVE_DIR, "magnet_bfield.png"), dpi=150)
        print(f"Saved 3 figures to {SAVE_DIR}")

    plt.show()


if __name__ == "__main__":
    main()
