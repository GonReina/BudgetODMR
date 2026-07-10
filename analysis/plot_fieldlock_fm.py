"""
Plot the results of smcv/odmr_fieldlock_fm_pc.py (closed-loop FM magnetometer).

Reads from <data_dir> (config.json -> paths.data_dir):
    fieldlock_fm_spectrum.csv     R(f) used to choose the null
    fieldlock_fm_timeseries.csv   t, f0, error, B (header carries f_ref, delta,
                                  D, gain, gamma)

Four panels:
    (a) FM spectrum with the locked null and the two sampling points f0 +/- delta,
    (b) the measured field B(t) (and the tracked line position on a twin axis),
    (c) noise spectrum (ASD) of B -- where the closed-loop noise lives,
    (d) Allan deviation of B with a 1/sqrt(tau) guide.

Run on the PC:  python plot_fieldlock_fm.py     (needs numpy + matplotlib)
Saves <data_dir>/fieldlock_fm.png and shows the figure.
"""

import csv
import os
import re
import sys

import matplotlib.pyplot as plt
import numpy as np

# expconfig.py + config.json + the measurement scripts live in the sibling smcv/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "smcv"))
from expconfig import load_config
from odmr_sensitivity_fm_pc import allan_deviation, moving_average, welch_asd, SMOOTH_PTS

_cfg = load_config()
DATA_DIR = _cfg["paths"]["data_dir"]
SPEC_CSV = os.path.join(DATA_DIR, "fieldlock_fm_spectrum.csv")
TS_CSV   = os.path.join(DATA_DIR, "fieldlock_fm_timeseries.csv")
SAVE_FIG = os.path.join(DATA_DIR, "fieldlock_fm.png")   # None to skip


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
    """Returns (meta dict, t, f0, err, B). Meta parsed from the '#' header."""
    with open(path) as f:
        header = f.readline()
    meta = {}
    for key in ("f_ref_MHz", "delta_MHz", "D_V_per_MHz", "gain",
                "gamma_MHz_per_mT"):
        mt = re.search(rf"{key}=([0-9eE+.-]+)", header)
        if not mt:
            raise SystemExit(f"Header of {path} is missing '{key}' -- was it "
                             "written by odmr_fieldlock_fm_pc.py?")
        meta[key] = float(mt.group(1))

    t, f0, err, b = [], [], [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0].startswith("t_s"):
                continue
            t.append(float(row[0]))
            f0.append(float(row[1]))
            err.append(float(row[2]))
            b.append(float(row[3]))
    return meta, np.array(t), np.array(f0), np.array(err), np.array(b)


# --------------------------------------------------------------------------
def main():
    freqs, R = load_spectrum(SPEC_CSV)
    meta, t, f0, err, b_nT = load_timeseries(TS_CSV)
    f_ref, delta = meta["f_ref_MHz"], meta["delta_MHz"]
    dt = float(np.median(np.diff(t)))
    sigma = float(np.std(b_nT - np.mean(b_nT)))
    eta = sigma * np.sqrt(dt)
    taus, adev = allan_deviation(b_nT, dt)
    i_best = int(np.argmin(adev))

    print(f"Locked null {f_ref:.4f} MHz, delta = {delta:.3f} MHz, "
          f"D = {meta['D_V_per_MHz'] * 1e3:+.4f} mV/MHz, gain = {meta['gain']}")
    print(f"sigma = {sigma:.1f} nT/cycle ({dt * 1e3:.0f} ms), "
          f"eta = {eta:.1f} nT/sqrt(Hz) (closed loop, wall-clock)")
    print(f"Allan minimum {adev[i_best]:.1f} nT at tau = {taus[i_best]:.2f} s")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    # (a) spectrum + locked null + sampling points
    ax = axes[0, 0]
    ax.plot(freqs, 1e3 * R, lw=0.8, color="0.65", label="lock-in R (raw)")
    ax.plot(freqs, 1e3 * moving_average(R, SMOOTH_PTS), lw=1.2,
            color="tab:blue", label=f"smoothed ({SMOOTH_PTS} pts)")
    ax.axvline(f_ref, color="tab:red", ls="--", lw=1.2, label="locked null")
    for s in (-1, 1):
        fs_ = f_ref + s * delta
        ax.plot(fs_, 1e3 * float(np.interp(fs_, freqs, R)), "v", ms=9,
                color="tab:red")
    ax.plot([], [], "v", color="tab:red", label=r"sampling $f_0 \pm \delta$")
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel("Lock-in R (mV)")
    ax.set_title(f"(a) Spectrum -- locked at {f_ref:.3f} MHz")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (b) field vs time (twin axis: tracked line position)
    ax = axes[0, 1]
    ax.plot(t, b_nT, lw=0.6, color="tab:blue")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("field B (nT, rel. to lock start)")
    ax2 = ax.twinx()
    ax2.plot(t, 1e3 * (f0 - f_ref), lw=0.5, color="tab:orange", alpha=0.6)
    ax2.set_ylabel("integrator f0 - f_ref (kHz)", color="tab:orange")
    ax2.tick_params(axis="y", labelcolor="tab:orange")
    ax.set_title(f"(b) Closed-loop field -- {dt * 1e3:.0f} ms/cycle")
    ax.grid(True, alpha=0.3)

    # (c) noise spectrum of B
    ax = axes[1, 0]
    fr, asd = welch_asd(b_nT, dt)
    ax.loglog(fr[1:], asd[1:], lw=1.0, color="tab:blue", label="closed loop B")
    err_nT = err / meta["D_V_per_MHz"] / meta["gamma_MHz_per_mT"] * 1e6
    fr2, asd2 = welch_asd(err_nT, dt)
    ax.loglog(fr2[1:], asd2[1:], lw=1.0, color="tab:gray", alpha=0.8,
              label="in-loop residual e/D")
    ax.axhline(np.sqrt(2) * eta, color="tab:red", ls="--", lw=1,
               label=rf"$\sqrt{{2}}\,\eta$ = {np.sqrt(2) * eta:.1f} nT/$\sqrt{{Hz}}$")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel(r"field ASD (nT/$\sqrt{Hz}$)")
    ax.set_title("(c) Noise spectrum of the field reading")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    # (d) Allan deviation
    ax = axes[1, 1]
    ax.loglog(taus, adev, "o-", color="tab:blue", label="Allan deviation")
    ax.loglog(taus, adev[0] * np.sqrt(taus[0] / taus), "--", color="0.5",
              label=r"white noise ($\propto 1/\sqrt{\tau}$)")
    ax.plot(taus[i_best], adev[i_best], "*", ms=14, color="tab:red",
            label=f"best: {adev[i_best]:.1f} nT @ {taus[i_best]:.1f} s")
    ax.set_xlabel("averaging time tau (s)")
    ax.set_ylabel("Allan deviation (nT)")
    ax.set_title(f"(d) Sensitivity: {eta:.1f} nT/$\\sqrt{{Hz}}$ (closed loop)")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    fig.suptitle("FM ODMR field lock (closed loop)", y=0.995)
    fig.tight_layout()
    if SAVE_FIG:
        fig.savefig(SAVE_FIG, dpi=150)
        print(f"Saved {SAVE_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
