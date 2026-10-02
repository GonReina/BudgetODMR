"""
Shared helpers for plot_power_sweep_fm.py and plot_power_sweep_dc.py.

Holds the bits that must behave identically in both: CSV reading (including the
optional per-point standard deviation), edge-safe smoothing, the "raw" per-power
figure that shows the data with NO fit, the noise / SNR estimate and figure, and
the power-broadening line fit.
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


def sweep_noise(sig, std, n_avg):
    """-> (sigma_one_sweep, sigma_averaged, method).

    Preferred: the scatter BETWEEN repeated sweeps, pooled over all frequency
    points as an RMS (sqrt of the mean variance). The RMS, not the median: with
    N = 2 each per-point std is |x1 - x2|/sqrt2, whose median underestimates
    sigma by a third. Points on the resonance count too -- if the line wanders
    between sweeps, that is noise as far as a measurement is concerned.

    Fallback (N = 1 or files without a std column): point-to-point scatter of
    the averaged trace, std(diff)/sqrt2. It only sees fast, white noise and
    misses slow drift, so it is a LOWER bound.
    """
    if n_avg > 1 and np.any(std > 0):
        s1 = float(np.sqrt(np.mean(std ** 2)))
        return s1, s1 / np.sqrt(n_avg), "scatter between repeated sweeps"
    s_avg = float(np.std(np.diff(sig)) / np.sqrt(2))
    return s_avg * np.sqrt(max(n_avg, 1)), s_avg, "point-to-point (lower bound)"


def save_noise_plot(path_out, powers, signal, s1, s_avg, n_avg, unit, title,
                    signal_name, chain_gain_db=0.0):
    """Two-panel 'how big is the noise' figure, meant to be read by anyone.

    (a) signal and noise in the SAME units against MW power;
    (b) noise as a percentage of the signal (100 % = noise as big as the signal).
    chain_gain_db != 0 (amplifier runs) adds a top axis with the typical power
    at the antenna.
    """
    powers, signal = np.asarray(powers), np.asarray(signal)
    s1, s_avg, n_avg = np.asarray(s1), np.asarray(s_avg), np.asarray(n_avg)
    nlab = (f"N = {n_avg.min()}" if n_avg.min() == n_avg.max()
            else f"N = {n_avg.min()}-{n_avg.max()} by power")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.3))
    ax1.semilogy(powers, signal, "o-", ms=4, color="C3", label=signal_name)
    ax1.semilogy(powers, s1, "s--", ms=3, color="0.55", label="noise, one sweep")
    ax1.semilogy(powers, s_avg, "o-", ms=3, color="k",
                 label=f"noise, averaged ({nlab})")
    ax1.set(xlabel="MW power set on the generator [dBm]", ylabel=f"[{unit}]",
            title="(a) Signal and noise, same units")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3, which="both")

    pct1, pct = 100 * s1 / signal, 100 * s_avg / signal
    ax2.semilogy(powers, pct1, "s--", ms=3, color="0.55", label="one sweep")
    ax2.semilogy(powers, pct, "o-", ms=4, color="k", label="averaged")
    ax2.axhline(100, color="C3", lw=1, ls=":")
    ax2.text(powers.min(), 100, " noise = signal", color="C3", va="bottom",
             fontsize=8, bbox=dict(fc="w", ec="none", alpha=0.8, pad=1))
    i = int(np.argmin(pct))
    right = powers[i] > 0.5 * (powers.min() + powers.max())
    ax2.annotate(f"best: {pct[i]:.1f} % (SNR {100/pct[i]:.0f})\nat {powers[i]:+.1f} dBm",
                 (powers[i], pct[i]), xytext=(-20 if right else 20, 45),
                 textcoords="offset points", ha="right" if right else "left",
                 fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8),
                 bbox=dict(fc="w", ec="0.7", alpha=0.9, pad=2))
    ax2.set(xlabel="MW power set on the generator [dBm]",
            ylabel="noise as % of the signal  (= 100 / SNR)",
            title="(b) Noise relative to the signal (lower is better)")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3, which="both")

    if chain_gain_db:
        g = float(chain_gain_db)
        for ax in (ax1, ax2):
            top = ax.secondary_xaxis("top", functions=(lambda x: x + g, lambda x: x - g))
            top.set_xlabel(f"approx. power at the antenna [dBm] (typ. gain {g:+.1f} dB)",
                           fontsize=8)

    fig.suptitle(title, y=1.0)
    fig.tight_layout()
    fig.savefig(path_out, dpi=150)
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
