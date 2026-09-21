"""
Shared helpers for plot_power_sweep_fm.py and plot_power_sweep_dc.py.

Holds the bits that must behave identically in both: CSV reading (including the
optional per-point standard deviation), edge-safe smoothing, the "raw" per-power
figure that shows the data with NO fit, and the power-broadening line fit.
"""

import os

import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
def read_sweep(path):
    """-> (freq, signal, std, meta).

    std is the per-point scatter across the N_AVG sweeps, written by the
    acquisition scripts as a third column. Files written before that column
    existed still load; std comes back as zeros.
    """
    fr, sig, std, meta = [], [], [], {}
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                for tok in line[1:].split():
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        meta[k] = v
                continue
            if line.startswith("freq"):
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue
            fr.append(float(parts[0]))
            sig.append(float(parts[1]))
            std.append(float(parts[2]) if len(parts) > 2 else 0.0)
    return np.array(fr), np.array(sig), np.array(std), meta


def power_from_name(path):
    return float(os.path.basename(path).replace("sweep_", "").replace("dBm.csv", ""))


def smooth(y, k=None):
    """Boxcar smoothing with EDGE padding.

    np.convolve(mode='same') zero-pads, which makes the smoothed trace plunge at
    both ends whenever the data carries a DC offset -- and PL_on/PL_off sits near
    1.0. That fake excursion then dominates peak-prominence thresholds and the
    line finder sees nothing at all.
    """
    y = np.asarray(y, dtype=float)
    k = k or max(3, len(y) // 60)
    if k < 2 or len(y) < 2 * k:
        return y
    pad = k // 2
    yp = np.pad(y, pad, mode="edge")
    return np.convolve(yp, np.ones(k) / k, mode="same")[pad:pad + len(y)]


def save_raw_plot(path_out, fr, sig, std, power_dbm, n_avg, ylabel,
                  errorbar="sem", title_extra=""):
    """Per-power figure of the AVERAGED data with NO fit.

    Shows the mean with error bars and nothing else. Deliberately fit-free: this
    is the plot to look at when deciding whether a feature (an unresolved
    hyperfine triplet, say) is really in the data, before any model has had a
    chance to impose structure on it.

    errorbar: 'sem' -> sigma/sqrt(N), the error on the plotted mean (default,
              and the statistically correct bar for a mean)
              'std' -> the raw per-sweep scatter sigma
    """
    fig, ax = plt.subplots(figsize=(8, 4.4))

    have_err = np.any(std > 0)
    if have_err:
        err = std / np.sqrt(max(n_avg, 1)) if errorbar == "sem" else std
        lbl = (rf"mean $\pm$ s.e.m. ($\sigma/\sqrt{{{n_avg}}}$)"
               if errorbar == "sem" else rf"mean $\pm\ \sigma$ (N={n_avg})")
        ax.errorbar(fr, sig, yerr=err, fmt="o", ms=2.5, lw=0, elinewidth=0.7,
                    capsize=0, color="C0", ecolor="0.65", label=lbl)
    else:
        ax.plot(fr, sig, "o", ms=2.5, color="C0",
                label="mean (no scatter: N_AVG = 1)")

    ax.axhline(float(np.median(sig)), color="0.5", ls=":", lw=0.8)

    ax.set(xlabel="MW frequency [MHz]", ylabel=ylabel,
           title=f"{power_dbm:+.1f} dBm -- averaged data, no fit{title_extra}")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path_out, dpi=140)
    plt.close(fig)


def broadening_fit(powers, g, gerr):
    """Weighted straight-line fit of Gamma^2 = Gamma_0^2 + a * P_mw."""
    p_mw = 10 ** (np.asarray(powers) / 10.0)
    g = np.asarray(g)
    gerr = np.asarray(gerr)
    w = 1.0 / np.maximum(2 * g * gerr, 1e-9) ** 2
    A = np.column_stack([np.ones_like(p_mw), p_mw])
    coef, *_ = np.linalg.lstsq(A * np.sqrt(w)[:, None], g ** 2 * np.sqrt(w),
                               rcond=None)
    return float(np.sqrt(max(coef[0], 0.0))), float(coef[1]), p_mw
