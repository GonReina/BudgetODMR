"""
Plot the results of smcv/odmr_selfosc_precision_pc.py (repeated gain scans).

By default finds all <data_dir>/selfosc_rep_* directories (config.json ->
paths.data_dir); alternatively pass directories explicitly:

    python plot_selfosc_precision.py [rep_dir1 rep_dir2 ...]

Produces <data_dir>/selfosc_precision.png with two panels:
  (a) the coherent period-2 amplitude a2 versus gain for every repeat,
      overlaid, with each repeat's extracted G_c marked -- shows visually how
      reproducible the onset is;
  (b) G_c per repeat for both estimators (crossing = lower bound, filled;
      supercritical fit, open), with the mean +/- 1 sigma band.

Also prints the fractional-broadening resolution derived from the scatter
(dGc/Gc = beta, Sec. 2.3 of the WP3 report): beta_min(1s) and beta_min(3s).

Run on the PC:  python plot_selfosc_precision.py     (numpy + matplotlib)
"""

import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "smcv"))
from expconfig import load_config
from plot_selfosc_fm import load_gainscan, analyse_gainscan, supercritical_gc

_cfg = load_config()
DATA_DIR = _cfg["paths"]["data_dir"]


def main():
    if len(sys.argv) > 1:
        rep_dirs = sys.argv[1:]
    else:
        rep_dirs = sorted(glob.glob(os.path.join(DATA_DIR, "selfosc_rep_*")))
    if not rep_dirs:
        raise SystemExit(f"No selfosc_rep_* directories in {DATA_DIR} -- "
                         "run smcv/odmr_selfosc_precision_pc.py first.")

    results = []          # (name, gains, a2, thr, gc, dgc, gfit)
    for d in rep_dirs:
        meta, runs = load_gainscan(os.path.join(d, "selfosc_fm_gainscan.csv"))
        gains, spread, a2, gc, dgc, thr = analyse_gainscan(runs)
        gfit = supercritical_gc(gains, a2, thr)
        results.append((os.path.basename(os.path.normpath(d)),
                        gains, a2, thr, gc, dgc, gfit))
        print(f"[{d}] G_c = {gc:.3f} +/- {dgc:.3f} (crossing), "
              f"{gfit:.3f} (fit)")

    gcs = np.array([r[4] for r in results])
    gfits = np.array([r[6] for r in results])
    gfits = gfits[np.isfinite(gfits)]
    mu, sd = float(np.mean(gcs)), float(np.std(gcs, ddof=1))
    print(f"\ncrossing: mean = {mu:.3f}, std = {sd:.3f}  "
          f"-> beta resolution {sd / mu * 100:.1f} % (1s), "
          f"{3 * sd / mu * 100:.1f} % (3s)")
    if len(gfits) >= 2:
        print(f"fit     : mean = {np.mean(gfits):.3f}, "
              f"std = {np.std(gfits, ddof=1):.3f} ({len(gfits)} finite)")

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    # (a) overlaid a2 curves with per-repeat G_c markers
    for k, (name, gains, a2, thr, gc, dgc, gfit) in enumerate(results):
        c = f"C{k % 10}"
        ax.semilogy(gains, 1e3 * np.maximum(a2, 1e-4), "o-", ms=3, lw=1.0,
                    color=c, alpha=0.8, label=name)
        if np.isfinite(gc):
            ax.axvline(gc, color=c, ls="--", lw=0.8, alpha=0.6)
    ax.axhline(1e3 * results[0][3], color="0.5", ls=":", lw=1,
               label="onset threshold")
    ax.set_xlabel("loop gain G")
    ax.set_ylabel("period-2 amplitude $a_2$ (kHz)")
    ax.set_title("(a) Onset reproducibility across repeats")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, which="both")

    # (b) G_c per repeat + mean band
    x = np.arange(1, len(results) + 1)
    dgcs = np.array([r[5] for r in results])
    ax2.errorbar(x, gcs, yerr=dgcs, fmt="o", ms=7, capsize=3,
                 color="tab:blue", label="crossing (lower bound)")
    gfit_all = np.array([r[6] for r in results])
    mfin = np.isfinite(gfit_all)
    if mfin.any():
        ax2.plot(x[mfin], gfit_all[mfin], "o", ms=9, mfc="none",
                 color="tab:green", label="supercritical fit")
    ax2.axhspan(mu - sd, mu + sd, color="tab:blue", alpha=0.15,
                label=rf"crossing mean $\pm 1\sigma$")
    ax2.axhline(mu, color="tab:blue", ls="--", lw=1)
    ax2.set_xticks(x)
    ax2.set_xlabel("repeat #")
    ax2.set_ylabel("critical gain $G_c$")
    ax2.set_title(rf"(b) $G_c$ = {mu:.3f} $\pm$ {sd:.3f}  "
                  rf"($\beta$ resolution: {sd / mu * 100:.1f}% at $1\sigma$)")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    fig.suptitle("Critical-gain estimator precision (repeated scans)", y=1.0)
    fig.tight_layout()
    out = os.path.join(os.path.dirname(os.path.normpath(rep_dirs[0])) or ".",
                       "selfosc_precision.png")
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")
    plt.show()


if __name__ == "__main__":
    main()
