"""
Analyse/plot the self-oscillation gain scans from smcv/odmr_selfosc_fm_pc.py.

Single-run mode (default, files from config.json -> paths.data_dir):
    selfosc_fm_spectrum.csv, selfosc_fm_gainscan.csv, selfosc_fm_stats.csv
Produces <dir>/selfosc_fm.png:
    (a) measured bifurcation diagram (orbit points vs gain),
    (b) orbit spread + coherent period-2 amplitude vs gain, extracted critical
        gain G_c, and the sub-threshold critical-fluctuation fit
        spread = (sigma_R/|D|) * sqrt( G / (2 - G) ),
    (c) example orbits at low / mid / high gain,
    (d) demodulated cycle spectrum of the statistics run (where an applied AC
        perturbation appears as a mixing sideband).

Multi-run mode (the "collapse" plot for the proposal):
    python plot_selfosc_fm.py <run_dir1> <run_dir2> ...
Each directory holds one run's selfosc_fm_gainscan.csv + selfosc_fm_spectrum.csv
(copy/rename the DATA_DIR files after each perturbation setting). For every run
it extracts G_c and the TRUE lobe slope at f* from that run's spectrum, and
plots G_c against the theory prediction 2*|D_cal|/|D_true| -> all perturbations
should collapse onto the identity line. Saves selfosc_collapse.png in the first
directory.

IMPORTANT experimental note: the collapse only shows a shift if the perturbed
runs are taken with the REFERENCE calibration (same f*, R0, D_cal). If the
hardware script re-picks/re-calibrates each run, D_cal = D_true and G_c = 2
always. For perturbed runs, pick the same point and keep the reference values.

Run on the PC:  python plot_selfosc_fm.py [run_dir ...]   (numpy + matplotlib)
"""

import csv
import os
import re
import sys

import matplotlib.pyplot as plt
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "smcv"))
from expconfig import load_config
from odmr_selfosc_fm_pc import alt_amp
from odmr_sensitivity_fm_pc import moving_average, welch_asd

_cfg = load_config()
DEFAULT_DIR = _cfg["paths"]["data_dir"]


# --------------------------------------------------------------------------
def _num(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def load_gainscan(path):
    """Returns (meta, dict gain -> f array [MHz])."""
    with open(path) as f:
        header = f.readline()
    meta = {}
    for key in ("f_star_MHz", "R0_V", "D_V_per_MHz"):
        mt = re.search(rf"{key}=([0-9eE+.-]+)", header)
        if not mt:
            raise SystemExit(f"Header of {path} is missing '{key}'.")
        meta[key] = float(mt.group(1))
    runs = {}
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or not _num(row[0]):
                continue
            runs.setdefault(float(row[0]), []).append(float(row[3]))
    return meta, {g: np.array(v) for g, v in sorted(runs.items())}


def load_two_col(path):
    a, b = [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or not _num(row[0]):
                continue
            a.append(float(row[0]))
            b.append(float(row[1]))
    return np.array(a), np.array(b)


def load_stats(path):
    t, fr = [], []
    with open(path) as f:
        header = f.readline()
    mt = re.search(r"gain=([0-9eE+.-]+)", header)
    g_stat = float(mt.group(1)) if mt else float("nan")
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or not _num(row[0]):
                continue
            t.append(float(row[1]))
            fr.append(float(row[2]))
    return g_stat, np.array(t), np.array(fr)


# --------------------------------------------------------------------------
def analyse_gainscan(gains_f, skip_frac=0.33):
    """Per-gain tail statistics -> (gains, spread, a2, G_c, dG_c)."""
    gains = np.array(sorted(gains_f))
    spread, a2 = [], []
    for g in gains:
        tail = gains_f[g][int(len(gains_f[g]) * skip_frac):]
        spread.append(float(np.std(tail)))
        a2.append(alt_amp(tail))
    spread, a2 = np.array(spread), np.array(a2)

    # G_c: first crossing of the period-2 amplitude above a threshold set by
    # the sub-threshold baseline (4x the median of the lowest three gains)
    base = float(np.median(a2[:3]))
    thr = max(4 * base, 0.05)
    above = a2 > thr
    if not above.any():
        return gains, spread, a2, float("nan"), float("nan"), thr
    i = int(np.argmax(above))
    if i == 0:
        return gains, spread, a2, float(gains[0]), 0.0, thr
    # linear interpolation of the crossing + half grid spacing as uncertainty
    g_c = float(np.interp(thr, [a2[i - 1], a2[i]], [gains[i - 1], gains[i]]))
    dg = 0.5 * float(gains[i] - gains[i - 1])
    return gains, spread, a2, g_c, dg, thr


def supercritical_gc(gains, a2, thr):
    """Refined G_c: fit the supercritical growth law a2^2 = k (G - G_c) to the
    first few points above onset and take the intercept. Needs >= 2 points
    above 2*thr -- EXTEND the gain grid past the shifted onset for perturbed
    runs, or this returns nan. Complements the crossing estimator (which is a
    lower bound under noise: amplified fluctuations trigger it early)."""
    idx = np.where(a2 > 2 * thr)[0][:4]
    if len(idx) < 2:
        return float("nan")
    k, c = np.polyfit(gains[idx], a2[idx] ** 2, 1)
    return float(-c / k) if k > 0 else float("nan")


def fluct_fit(gains, spread, g_c):
    """One-parameter fit of the sub-threshold critical-fluctuation law
    spread = s0 * sqrt(G / (2 - G)) (uses points safely below threshold)."""
    m = gains < min(g_c - 0.15, 1.95) if np.isfinite(g_c) else gains < 1.95
    if m.sum() < 2:
        return None, None
    shape = np.sqrt(gains[m] / (2.0 - gains[m]))
    s0 = float(np.sum(spread[m] * shape) / np.sum(shape ** 2))
    gg = np.linspace(gains[0], 1.98, 200)
    return gg, s0 * np.sqrt(gg / (2.0 - gg))


def true_slope_from_spectrum(spec_path, f_star, R0):
    """Slope that actually governs the loop dynamics: the LOCAL slope at the
    FIXED POINT, i.e. where the (smoothed) spectrum crosses the setpoint R0
    nearest to f_star, fitted over a narrow +/-3-point window (a wide window
    dilutes the slope and would bias the collapse)."""
    freqs, R = load_two_col(spec_path)
    Rs = moving_average(R, 3)
    best = None
    for i in range(2, len(freqs) - 3):
        if (Rs[i] - R0) * (Rs[i + 1] - R0) <= 0:
            d = abs(freqs[i] - f_star)
            if best is None or d < best[0]:
                best = (d, i)
    i = best[1] if best else int(np.argmin(np.abs(freqs - f_star)))
    lo, hi = max(0, i - 3), min(len(freqs), i + 4)
    slope, _ = np.polyfit(freqs[lo:hi], R[lo:hi], 1)
    return float(slope)


# --------------------------------------------------------------------------
def plot_run(run_dir):
    gs_path = os.path.join(run_dir, "selfosc_fm_gainscan.csv")
    meta, runs = load_gainscan(gs_path)
    gains, spread, a2, g_c, dg, thr = analyse_gainscan(runs)
    g_fit = supercritical_gc(gains, a2, thr)
    print(f"[{run_dir}]  G_c = {g_c:.2f} +/- {dg:.2f} (crossing), "
          f"{g_fit:.2f} (supercritical fit)  "
          f"(D_cal = {meta['D_V_per_MHz'] * 1e3:+.3f} mV/MHz)")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    # (a) measured bifurcation diagram
    ax = axes[0, 0]
    for g in gains:
        tail = runs[g][int(len(runs[g]) * 0.33):]
        ax.plot([g] * len(tail), tail, ".", ms=2, color="tab:blue", alpha=0.25)
    if np.isfinite(g_c):
        ax.axvline(g_c, color="tab:red", ls="--", lw=1.2,
                   label=f"$G_c$ = {g_c:.2f} $\\pm$ {dg:.2f}")
        ax.legend(fontsize=8)
    ax.set_xlabel("loop gain G")
    ax.set_ylabel("orbit frequency (MHz)")
    ax.set_title("(a) Measured bifurcation diagram")
    ax.grid(alpha=0.3)

    # (b) spread + period-2 amplitude vs gain
    ax = axes[0, 1]
    ax.semilogy(gains, 1e3 * spread, "s-", color="tab:orange",
                label="orbit spread (incl. critical fluctuations)")
    ax.semilogy(gains, 1e3 * np.maximum(a2, 1e-4), "o-", color="tab:blue",
                label="coherent period-2 amplitude")
    gg, fit = fluct_fit(gains, spread, g_c)
    if gg is not None:
        ax.semilogy(gg, 1e3 * fit, "--", color="tab:orange", alpha=0.7,
                    label=r"$\propto\sqrt{G/(2-G)}$ precursor fit")
    ax.axhline(1e3 * thr, color="tab:blue", ls=":", lw=1, alpha=0.7)
    if np.isfinite(g_c):
        ax.axvline(g_c, color="tab:red", ls="--", lw=1)
    ax.set_xlabel("loop gain G")
    ax.set_ylabel("amplitude (kHz)")
    ax.set_title("(b) Onset and its precursor")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, which="both")

    # (c) example orbits
    ax = axes[1, 0]
    picks = [gains[0], gains[len(gains) // 2], gains[-1]]
    if np.isfinite(g_c):
        picks[1] = float(gains[np.argmin(np.abs(gains - (g_c + 0.15)))])
    for k, g in enumerate(picks):
        y = runs[g][-120:]
        ax.plot(np.arange(len(y)), y - np.mean(y) + k * 1.2, lw=0.8,
                label=f"G = {g:g}")
    ax.set_xlabel("loop cycle")
    ax.set_ylabel("frequency, offset per trace (MHz)")
    ax.set_title("(c) Orbits: lock / limit cycle / deep")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # (d) demodulated cycle spectrum of the statistics run
    ax = axes[1, 1]
    st_path = os.path.join(run_dir, "selfosc_fm_stats.csv")
    if os.path.exists(st_path):
        g_stat, t, fr_ = load_stats(st_path)
        dt = float(np.median(np.diff(t)))
        s = ((-1.0) ** np.arange(len(fr_))) * (fr_ - np.mean(fr_))
        fr_psd, asd = welch_asd(s, dt)
        ax.semilogy(fr_psd[1:], 1e3 * asd[1:], lw=1.0, color="tab:blue")
        ax.set_title(f"(d) Cycle spectrum, G = {g_stat:g} "
                     "(AC signals appear as sidebands)")
        ax.set_xlabel("frequency (Hz)")
        ax.set_ylabel(r"demodulated amplitude (kHz/$\sqrt{Hz}$)")
    else:
        ax.set_title("(d) no selfosc_fm_stats.csv found")
    ax.grid(alpha=0.3, which="both")

    fig.suptitle(f"NV self-oscillation gain scan -- {run_dir}", y=0.995)
    fig.tight_layout()
    out = os.path.join(run_dir, "selfosc_fm.png")
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")
    return meta, g_c, dg, g_fit


def plot_collapse(run_dirs, results):
    """G_c vs the theory prediction 2*|D_cal|/|D_true| across runs."""
    xs, ys, dys, yfits, labels = [], [], [], [], []
    for run_dir, (meta, g_c, dg, g_fit) in zip(run_dirs, results):
        spec = os.path.join(run_dir, "selfosc_fm_spectrum.csv")
        if not (os.path.exists(spec) and np.isfinite(g_c)):
            continue
        d_true = true_slope_from_spectrum(spec, meta["f_star_MHz"],
                                          meta["R0_V"])
        xs.append(2.0 * abs(meta["D_V_per_MHz"]) / abs(d_true))
        ys.append(g_c)
        dys.append(dg)
        yfits.append(g_fit)
        labels.append(os.path.basename(os.path.normpath(run_dir)))
    if len(xs) < 2:
        print("collapse plot: need >= 2 runs with spectra and a finite G_c")
        return
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.errorbar(xs, ys, yerr=dys, fmt="o", ms=7, color="tab:blue", capsize=3,
                label="crossing estimator (lower bound)")
    yf = np.array(yfits)
    mfin = np.isfinite(yf)
    if mfin.any():
        ax.plot(np.array(xs)[mfin], yf[mfin], "o", ms=9, mfc="none",
                color="tab:green", label="supercritical fit")
    for x, y, lb in zip(xs, ys, labels):
        ax.annotate(lb, (x, y), textcoords="offset points", xytext=(6, 4),
                    fontsize=8)
    lim = [0.9 * min(xs + ys), 1.1 * max(xs + ys)]
    ax.plot(lim, lim, "--", color="0.5", label="theory: $G_c = 2\\,D_{cal}/D_{true}$")
    # note: the crossing estimator triggers early under noise (amplified
    # critical fluctuations), so points sit slightly BELOW the identity line;
    # the supercritical fit corrects this when the grid extends past onset
    ax.set_xlabel(r"predicted $2\,|D_{cal}|/|D_{true}|$")
    ax.set_ylabel(r"measured critical gain $G_c$")
    ax.set_title("Onset collapse across perturbations")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(run_dirs[0], "selfosc_collapse.png")
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")


def main():
    run_dirs = sys.argv[1:] if len(sys.argv) > 1 else [DEFAULT_DIR]
    results = [plot_run(d) for d in run_dirs]
    if len(run_dirs) > 1:
        plot_collapse(run_dirs, results)
    plt.show()


if __name__ == "__main__":
    main()
