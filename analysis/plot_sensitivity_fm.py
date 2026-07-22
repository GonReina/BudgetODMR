"""
Plot the results of smcv/odmr_sensitivity_fm_pc.py.

Reads from <data_dir> (config.json -> paths.data_dir):
    sensitivity_fm_spectrum.csv     R(f) used for the slope calibration
    sensitivity_fm_timeseries.csv   parked time series (MW on + MW-off floor);
                                    its header carries f*, slope and dR/dB

and produces a single four-panel figure:
    (a) FM spectrum with the working point f* and the fitted slope,
    (b) the parked time series converted to field units (nT), floor in grey,
    (c) noise spectrum (ASD) of the field reading -- shows WHERE the noise lives,
    (d) Allan deviation vs averaging time, with a 1/sqrt(tau) guide and the
        MW-off detection floor.

All numbers (sigma, eta, Allan) are recomputed from the raw time series with the
SAME functions the measurement script uses (imported from it), so this plot always
agrees with sensitivity_fm_summary.txt.

Run on the PC:  python plot_sensitivity_fm.py     (needs numpy + matplotlib)
Saves <data_dir>/sensitivity_fm.png and shows the figure.
"""

import csv
import os
import re
import sys

import matplotlib.pyplot as plt
import numpy as np

# expconfig.py + config.json + the measurement script live in the sibling smcv/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "smcv"))
from expconfig import load_config
from odmr_sensitivity_fm_pc import (analyse, moving_average, welch_asd,
                                    demodulate, F_MOD,
                                    SMOOTH_PTS, FIT_HALF_PTS)

_cfg = load_config()
DATA_DIR = _cfg["paths"]["data_dir"]
SPEC_CSV = os.path.join(DATA_DIR, "sensitivity_fm_spectrum.csv")
TS_CSV   = os.path.join(DATA_DIR, "sensitivity_fm_timeseries.csv")
SAVE_FIG = os.path.join(DATA_DIR, "sensitivity_fm.png")   # None to skip


# --------------------------------------------------------------------------
def load_spectrum(path):
    freqs, R = [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0].startswith("freq"):
                continue
            freqs.append(float(row[0]))
            R.append(float(row[1]))
    return np.array(freqs), np.array(R)


def load_timeseries(path):
    """Returns (f_star, slope, dRdB, t_on, R_on, t_off, R_off).
    f*/slope/dRdB are parsed from the '#' header written by the measurement."""
    with open(path) as f:
        header = f.readline()
    def grab(pattern):
        mt = re.search(pattern, header)
        if not mt:
            raise SystemExit(f"Header of {path} is missing '{pattern}' -- "
                             "was it written by odmr_sensitivity_fm_pc.py?")
        return float(mt.group(1))
    f_star = grab(r"parked at\s+([0-9.]+)\s*MHz")
    slope  = grab(r"slope_V_per_MHz=([0-9eE+.-]+)")
    dRdB   = grab(r"dRdB_V_per_mT=([0-9eE+.-]+)")

    t_on, r_on, t_off, r_off = [], [], [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0].startswith("t_s"):
                continue
            t, r, on = float(row[0]), float(row[1]), int(row[2])
            (t_on if on else t_off).append(t)
            (r_on if on else r_off).append(r)
    return (f_star, slope, dRdB, np.array(t_on), np.array(r_on),
            np.array(t_off), np.array(r_off))


# --------------------------------------------------------------------------
def main():
    freqs, R = load_spectrum(SPEC_CSV)
    f_star, slope, dRdB, t, r, t_fl, r_fl = load_timeseries(TS_CSV)
    res = analyse(t, r, dRdB, t_fl, r_fl)
    b_nT = (r - np.mean(r)) / dRdB * 1e6
    floor_nT = res.get("floor_sigma_nT")

    print(f"Working point {f_star:.3f} MHz, dR/dB = {dRdB * 1e3:.4f} mV/mT")
    print(f"sigma = {res['sigma_nT']:.1f} nT/reading, "
          f"eta = {res['eta_int_nT_rtHz']:.1f} nT/sqrt(Hz) (intrinsic), "
          f"{res['eta_wall_nT_rtHz']:.1f} nT/sqrt(Hz) (wall-clock)")
    print(f"Allan minimum {res['adev_best_nT']:.1f} nT at tau = {res['tau_best_s']:.2f} s")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    # (a) spectrum + working point + fitted slope
    ax = axes[0, 0]
    ax.plot(freqs, 1e3 * R, "-", lw=1.0, color="tab:blue", label="lock-in R")
    if SMOOTH_PTS > 1:
        ax.plot(freqs, 1e3 * moving_average(R, SMOOTH_PTS), lw=1.0,
                color="tab:cyan", alpha=0.7, label=f"smoothed ({SMOOTH_PTS} pts)")
    step = freqs[1] - freqs[0]
    df = FIT_HALF_PTS * step
    r_star = float(np.interp(f_star, freqs, R))
    fx = np.array([f_star - df, f_star + df])
    ax.plot(fx, 1e3 * (r_star + slope * (fx - f_star)), "-", color="tab:red",
            lw=2, label=f"slope {slope * 1e3:+.2f} mV/MHz")
    ax.axvline(f_star, color="tab:red", ls="--", lw=1)
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel("Lock-in R (mV)")
    ax.set_title(f"(a) FM spectrum -- working point {f_star:.3f} MHz")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (b) parked time series in field units
    ax = axes[0, 1]
    ax.plot(t, b_nT, lw=0.6, color="tab:blue", label="MW on, at f*")
    if len(r_fl):
        ax.plot(t_fl, (r_fl - np.mean(r_fl)) / dRdB * 1e6, lw=0.6,
                color="tab:gray", alpha=0.8, label="MW off (floor)")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("equivalent field (nT)")
    ax.set_title(f"(b) Parked at f* -- {res['dt_s'] * 1e3:.0f} ms/reading, "
                 f"duty {100 * res['duty']:.0f} %")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (c) noise spectrum of the field reading (band: 0 ... 1/(2 dt), ~10 Hz)
    ax = axes[1, 0]
    fr, asd = welch_asd(b_nT, res["dt_s"])
    ax.loglog(fr[1:], asd[1:], lw=1.0, color="tab:blue", label="MW on, at f*")
    if len(r_fl) >= 64:
        fr2, asd2 = welch_asd((r_fl - np.mean(r_fl)) / dRdB * 1e6, res["dt_s"])
        ax.loglog(fr2[1:], asd2[1:], lw=1.0, color="tab:gray", alpha=0.8,
                  label="MW off (floor)")
    white = np.sqrt(2) * res["eta_wall_nT_rtHz"]   # ASD of white noise = sqrt(2)*eta
    ax.axhline(white, color="tab:red", ls="--", lw=1,
               label=rf"$\sqrt{{2}}\,\eta$ = {white:.1f} nT/$\sqrt{{Hz}}$")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel(r"field ASD (nT/$\sqrt{Hz}$)")
    ax.set_title("(c) Noise spectrum: flat = white, rise at low f = drift/1-f")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    # (d) demodulation in action: one raw buffer + sliding-window tone amplitude
    ax = axes[1, 1]
    raw_path = os.path.join(DATA_DIR, "sensitivity_fm_rawbuf.npz")
    if not os.path.exists(raw_path):
        ax.text(0.5, 0.5, "no sensitivity_fm_rawbuf.npz --\n"
                "re-run odmr_sensitivity_fm_pc.py\n(newer version saves raw buffers)",
                ha="center", va="center", transform=ax.transAxes, fontsize=9)
        ax.set_title("(d) Raw signal during one measurement interval")
    else:
        d_ = np.load(raw_path)
        fs_raw, v = float(d_["fs"]), d_["v"][0]
        fmod_ = float(d_["f_mod"]) if "f_mod" in d_ else F_MOD
        tt_raw = np.arange(len(v)) / fs_raw
        ax.plot(1e3 * tt_raw, 1e3 * (v - np.mean(v)), lw=0.3, color="0.7",
                label="raw photodiode (mean removed)")
        block = max(64, int(round(1e-3 * fs_raw)))       # 1 ms demod window
        hop = max(1, block // 4)
        tt_d, RR = [], []
        for s0 in range(0, len(v) - block + 1, hop):
            tt_d.append((s0 + block / 2) / fs_raw)
            RR.append(demodulate(v[s0:s0 + block], fs_raw, fmod_))
        ax2 = ax.twinx()
        ax2.plot(1e3 * np.array(tt_d), 1e3 * np.array(RR), color="tab:green",
                 lw=1.6, label="demodulated R(t), 1 ms window")
        ax2.axhline(1e3 * float(np.mean(RR)), color="tab:green", ls=":", lw=1)
        ax2.set_ylabel("demodulated R (mV)", color="tab:green")
        ax2.tick_params(axis="y", labelcolor="tab:green")
        ax2.set_ylim(bottom=0)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="lower right")
        ax.set_title("(d) One measurement interval: raw signal + demodulation")
    ax.set_xlabel("time in buffer (ms)")
    ax.set_ylabel("photodiode - mean (mV)")
    ax.grid(True, alpha=0.3)
    print(f"Allan minimum {res['adev_best_nT']:.1f} nT at "
          f"tau = {res['tau_best_s']:.2f} s "
          f"(Allan plot removed from the figure; values remain in the summary)")

    fig.suptitle("FM lock-in ODMR sensitivity", y=0.995)
    fig.tight_layout()
    if SAVE_FIG:
        fig.savefig(SAVE_FIG, dpi=150)
        print(f"Saved {SAVE_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
