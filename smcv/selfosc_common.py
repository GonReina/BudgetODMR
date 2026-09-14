"""
Shared helpers for the self-oscillation follow-up measurements
(odmr_selfosc_power_pc.py, odmr_selfosc_cycletime_pc.py,
odmr_selfosc_precision_pc.py). See proposal/workpackage3_report.tex Sec. 5.

Everything here enforces the one rule that makes those measurements meaningful:
the calibration (f*, R0, D_cal) is measured ONCE and then HELD FIXED across
conditions -- if the loop is re-calibrated per condition, G_c = 2 trivially.

Output files use the same format as odmr_selfosc_fm_pc.py, so every run
directory can be analysed / collapsed with analysis/plot_selfosc_fm.py.
"""

import os
import time
from datetime import datetime

import numpy as np

from odmr_selfosc_fm_pc import read_R, alt_amp
from odmr_sensitivity_fm_pc import moving_average, GAMMA


# ---------------------------------------------------------------------------
# G_c estimators (same logic as analysis/plot_selfosc_fm.py)
# ---------------------------------------------------------------------------
def a2_stats(orbits, skip_frac=0.33):
    """orbits: dict gain -> f array. Returns (gains, spread, a2) arrays."""
    gains = np.array(sorted(orbits))
    spread, a2 = [], []
    for g in gains:
        tail = orbits[g][int(len(orbits[g]) * skip_frac):]
        spread.append(float(np.std(tail)))
        a2.append(alt_amp(tail))
    return gains, np.array(spread), np.array(a2)


def gc_crossing(gains, a2):
    """First crossing of a2 above a baseline threshold. Returns (gc, dgc, thr).
    A LOWER bound under noise (amplified fluctuations trigger it early)."""
    base = float(np.median(a2[:3]))
    thr = max(4 * base, 0.05)
    above = a2 > thr
    # require a SUSTAINED crossing (two consecutive points above threshold) so
    # a single noisy a2 excursion cannot trigger the onset; fall back to the
    # single-point crossing if no sustained one exists
    sustained = above[:-1] & above[1:]
    if sustained.any():
        i = int(np.argmax(sustained))
    elif above.any():
        i = int(np.argmax(above))
    else:
        return float("nan"), float("nan"), thr
    if i == 0:
        return float(gains[0]), 0.0, thr
    gc = float(np.interp(thr, [a2[i - 1], a2[i]], [gains[i - 1], gains[i]]))
    return gc, 0.5 * float(gains[i] - gains[i - 1]), thr


def gc_supercritical(gains, a2, thr):
    """Intercept of a2^2 = k (G - G_c) just above onset (nan if <2 points)."""
    idx = np.where(a2 > 2 * thr)[0][:4]
    if len(idx) < 2:
        return float("nan")
    k, c = np.polyfit(gains[idx], a2[idx] ** 2, 1)
    return float(-c / k) if k > 0 else float("nan")


def slope_at_crossing(freqs, R, f_star, R0, smooth=3, half=3):
    """Local slope [V/MHz] where the (smoothed) spectrum crosses R0 nearest to
    f_star -- the slope that governs the loop dynamics (narrow fit window)."""
    freqs, R = np.asarray(freqs, float), np.asarray(R, float)
    Rs = moving_average(R, smooth)
    best = None
    for i in range(2, len(freqs) - 3):
        if (Rs[i] - R0) * (Rs[i + 1] - R0) <= 0:
            d = abs(freqs[i] - f_star)
            if best is None or d < best[0]:
                best = (d, i)
    i = best[1] if best else int(np.argmin(np.abs(freqs - f_star)))
    lo, hi = max(0, i - half), min(len(freqs), i + half + 1)
    slope, _ = np.polyfit(freqs[lo:hi], R[lo:hi], 1)
    return float(slope)


def auto_gain_grid(gc_pred, step=0.1):
    """Gain grid: coarse sub-threshold baseline + fine grid around the
    predicted onset + margin well past it (needed by gc_supercritical)."""
    base = [0.6, 1.0, round(0.7 * gc_pred, 2)]
    fine = list(np.round(np.arange(gc_pred - 0.4, gc_pred + 0.65, step), 2))
    tail = [round(1.3 * gc_pred, 2), round(1.6 * gc_pred, 2)]
    grid = sorted(set(g for g in base + fine + tail if g >= 0.2))
    return grid


# ---------------------------------------------------------------------------
# Scanning with FIXED calibration + plot-compatible output
# ---------------------------------------------------------------------------
def run_loop_delay(src, rp, f0, R0, D, G, n, f_lo, f_hi, extra_delay=0.0):
    """Loop like odmr_selfosc_fm_pc.run_loop, with an optional added per-cycle
    delay (for the cycle-time invariance test)."""
    f = f0
    ts, fs_, rs = [], [], []
    t0 = time.perf_counter()
    for _ in range(n):
        if extra_delay > 0:
            time.sleep(extra_delay)
        R = read_R(src, rp, f)
        f = float(np.clip(f - G * (R - R0) / D, f_lo, f_hi))
        ts.append(time.perf_counter() - t0)
        fs_.append(f)
        rs.append(R)
    return np.array(ts), np.array(fs_), np.array(rs)


def scan_gains(src, rp, f_star, R0, D_cal, gains, n_cyc, f_lo, f_hi,
               park_settle=0.5, extra_delay=0.0, label=""):
    """Gain scan with fixed calibration. Returns (orbits, rows, dt_median)."""
    orbits, rows, dts = {}, [], []
    for G in gains:
        src.set_freq_mhz(f_star)
        time.sleep(park_settle)
        t, fr_, rr = run_loop_delay(src, rp, f_star, R0, D_cal, G, n_cyc,
                                    f_lo, f_hi, extra_delay)
        orbits[G] = fr_
        dts.append(float(np.median(np.diff(t))) if len(t) > 1 else 0.0)
        for k in range(len(t)):
            rows.append((G, k, t[k], fr_[k], rr[k]))
        tail = fr_[n_cyc // 3:]
        print(f"  {label}G = {G:5.2f}: spread {np.std(tail) * 1e3:7.1f} kHz  "
              f"a2 {alt_amp(tail) * 1e3:6.1f} kHz")
    return orbits, rows, float(np.median(dts))


def save_run_dir(out_dir, stamp, f_star, R0, D_cal, freqs, R_spec, rows,
                 extra_header=""):
    """Write selfosc_fm_spectrum.csv + selfosc_fm_gainscan.csv into out_dir,
    in the exact format analysis/plot_selfosc_fm.py expects."""
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "selfosc_fm_spectrum.csv"), "w") as f:
        f.write(f"# FM spectrum, {stamp} {extra_header}\nfreq_MHz,lockin_R\n")
        for fr, r in zip(freqs, R_spec):
            f.write(f"{fr:.5f},{r:.8f}\n")
    with open(os.path.join(out_dir, "selfosc_fm_gainscan.csv"), "w") as f:
        f.write(f"# self-oscillation gain scan, {stamp}, "
                f"f_star_MHz={f_star:.5f}, R0_V={R0:.8e}, "
                f"D_V_per_MHz={D_cal:.8e}, gamma_MHz_per_mT={GAMMA} "
                f"{extra_header}\n")
        f.write("gain,cycle,t_s,f_MHz,R_V\n")
        for G, k, t, fr_, rr in rows:
            f.write(f"{G},{k},{t:.4f},{fr_:.6f},{rr:.8e}\n")


def report_gc(orbits):
    """Convenience: (gains, spread, a2, gc_cross, dgc, gc_fit)."""
    gains, spread, a2 = a2_stats(orbits)
    gc, dgc, thr = gc_crossing(gains, a2)
    gfit = gc_supercritical(gains, a2, thr)
    return gains, spread, a2, gc, dgc, gfit
