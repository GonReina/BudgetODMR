"""
Plot the results of smcv/odmr_sensitivity_fm_wb_pc.py (wideband FM sensitivity).

Reads from <data_dir> (config.json -> paths.data_dir):
    sensitivity_fm_wb_spectrum.csv     R(f) sweep used for the slope
    sensitivity_fm_wb_timeseries.csv   per-record field series (buf, t_s, B_nT)
    sensitivity_fm_wb_psd.csv          averaged field ASD + MW-off floor

Four panels:
    (a) FM spectrum with the working point,
    (b) one example 1 s field record at the full 238 Hz rate,
    (c) averaged field ASD up to ~119 Hz with the MW-off floor and mains lines,
    (d) per-record RMS vs record index (stability check across the run).

Run on the PC:  python plot_sensitivity_fm_wb.py     (needs numpy + matplotlib)
Saves <data_dir>/sensitivity_fm_wb.png and shows the figure.
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

_cfg = load_config()
DATA_DIR = _cfg["paths"]["data_dir"]
SPEC_CSV = os.path.join(DATA_DIR, "sensitivity_fm_wb_spectrum.csv")
TS_CSV   = os.path.join(DATA_DIR, "sensitivity_fm_wb_timeseries.csv")
PSD_CSV  = os.path.join(DATA_DIR, "sensitivity_fm_wb_psd.csv")
SAVE_FIG = os.path.join(DATA_DIR, "sensitivity_fm_wb.png")   # None to skip


# --------------------------------------------------------------------------
def load_two_col(path):
    a, b = [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or not _is_num(row[0]):
                continue
            a.append(float(row[0]))
            b.append(float(row[1]))
    return np.array(a), np.array(b)


def _is_num(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def load_timeseries(path):
    """Returns (meta, dict buf_index -> field array [nT])."""
    with open(path) as f:
        header = f.readline()
    meta = {}
    for key in ("slope_V_per_MHz", "mode_ratio", "dRdB_V_per_mT", "fs_field_Hz"):
        mt = re.search(rf"{key}=([0-9eE+.-]+)", header)
        if not mt:
            raise SystemExit(f"Header of {path} is missing '{key}'.")
        meta[key] = float(mt.group(1))
    mt = re.search(r"records at\s+([0-9.]+)\s*MHz", header)
    meta["f_star_MHz"] = float(mt.group(1)) if mt else float("nan")

    bufs = {}
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or not _is_num(row[0]):
                continue
            bufs.setdefault(int(row[0]), []).append(float(row[2]))
    return meta, {k: np.array(v) for k, v in bufs.items()}


def load_psd(path):
    fr, asd, asd_fl = [], [], []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or not _is_num(row[0]):
                continue
            fr.append(float(row[0]))
            asd.append(float(row[1]))
            asd_fl.append(float(row[2]))
    return np.array(fr), np.array(asd), np.array(asd_fl)


# --------------------------------------------------------------------------
def main():
    freqs, R = load_two_col(SPEC_CSV)
    meta, bufs = load_timeseries(TS_CSV)
    fr, asd, asd_fl = load_psd(PSD_CSV)
    fs_f = meta["fs_field_Hz"]

    band = (fr >= 20.0) & (fr <= 100.0)
    eta = float(np.median(asd[band])) / np.sqrt(2)
    print(f"{len(bufs)} records, field rate {fs_f:.0f} Hz, "
          f"PSD to {fr[-1]:.0f} Hz")
    print(f"white-region sensitivity: {eta:.1f} nT/sqrt(Hz)")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    # (a) spectrum + working point
    ax = axes[0, 0]
    ax.plot(freqs, 1e3 * R, lw=0.9, color="tab:blue")
    ax.axvline(meta["f_star_MHz"], color="tab:red", ls="--", lw=1.2,
               label=f"f* = {meta['f_star_MHz']:.3f} MHz")
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel("Lock-in R (mV)")
    ax.set_title("(a) FM spectrum and working point")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (b) one example record at full rate
    ax = axes[0, 1]
    k0 = sorted(bufs)[0]
    b = bufs[k0]
    ax.plot(np.arange(len(b)) / fs_f, b, lw=0.6, color="tab:blue")
    ax.set_xlabel("time in record (s)")
    ax.set_ylabel("field (nT)")
    ax.set_title(f"(b) One contiguous record -- {fs_f:.0f} field samples/s")
    ax.grid(True, alpha=0.3)

    # (c) averaged ASD
    ax = axes[1, 0]
    ax.loglog(fr[1:], asd[1:], lw=1.1, color="tab:blue", label="MW on, at f*")
    ax.loglog(fr[1:], asd_fl[1:], lw=1.0, color="tab:gray", alpha=0.8,
              label="MW off (floor)")
    ax.axhline(np.sqrt(2) * eta, color="tab:red", ls="--", lw=1,
               label=rf"$\sqrt{{2}}\,\eta$ = {np.sqrt(2) * eta:.1f} nT/$\sqrt{{Hz}}$")
    for fm in (50, 100, 150):
        if fm < fr[-1]:
            ax.axvline(fm, color="tab:orange", ls=":", lw=0.8)
    ax.plot([], [], ":", color="tab:orange", label="mains harmonics")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel(r"field ASD (nT/$\sqrt{Hz}$)")
    ax.set_title(f"(c) Field noise spectrum up to {fr[-1]:.0f} Hz")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    # (d) per-record RMS (stability across the run)
    ax = axes[1, 1]
    ks = sorted(bufs)
    rms = [float(np.std(bufs[k])) for k in ks]
    ax.plot(ks, rms, "o-", ms=4, color="tab:blue")
    ax.set_xlabel("record #")
    ax.set_ylabel("in-record field RMS (nT)")
    ax.set_title("(d) Stability across records")
    ax.grid(True, alpha=0.3)

    fig.suptitle("Wideband FM sensitivity (contiguous-record demodulation)",
                 y=0.995)
    fig.tight_layout()
    if SAVE_FIG:
        fig.savefig(SAVE_FIG, dpi=150)
        print(f"Saved {SAVE_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
