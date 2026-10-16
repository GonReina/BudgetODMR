"""
Analyse odmr_fm_mfli_phase_pc.py: phase-sensitive FM sweep (MFLI) vs DC on/off
sweep (Red Pitaya). Does FM give a better SNR for an ODMR sweep?

  * PHASE: the SMCV FM and the MFLI oscillator share the 10 MHz clock, so the
    ODMR signal lies along one fixed direction in the X/Y plane. That angle is
    found from the mean sweep (principal axis of X, Y after removing the
    off-resonance offset) and X/Y are rotated onto it: X' = signed FM signal
    (the derivative-shaped, dispersive spectrum), Y' = what is left (should be
    noise only). The sign is chosen so that the integral of X' over frequency
    is a DIP, like the DC spectrum. The same angle is fitted to every sweep on
    its own: their spread shows whether the phase stayed put.
  * SNR of one sweep, for each method:
        signal = largest excursion of the mean spectrum from its baseline
                 (FM: max |X'|; DC: dip depth of PL_on/PL_off)
        noise  = median over frequency of the sweep-to-sweep std
    and, because the two sweeps do not take the same time, the FM SNR scaled
    to the duration of one DC sweep: SNR_FM * sqrt(t_DC / t_FM).

Output (in the run folder): fm_mfli.png, fm_mfli_summary.txt

Run:  python plot_fm_mfli.py [run_dir]     (default: newest <data_dir>/fm_mfli_*)
"""

import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from expconfig import load_config


def read_csv(path):
    meta, rows, head = {}, [], None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                k, _, v = line[1:].partition("=")
                meta[k.strip()] = v.strip()
            elif head is None:
                head = line.split(",")
            else:
                rows.append([float(x) for x in line.split(",")])
    a = np.array(rows)
    return meta, {h: a[:, j] for j, h in enumerate(head)}


def by_sweep(c, col):
    """(freqs, array [n_sweeps x n_freqs], seconds per sweep) from long format."""
    sw = c["sweep"].astype(int)
    ids = np.unique(sw)
    freqs = c["freq_MHz"][sw == ids[0]]
    n = min((sw == s).sum() for s in ids)       # a stopped last sweep is cut
    full = [s for s in ids if (sw == s).sum() == n]
    data = np.array([c[col][sw == s][:n] for s in full])
    t_end = np.array([c["t_s"][sw == s][n - 1] for s in full])
    return freqs[:n], data, float(np.diff(np.r_[0.0, t_end]).mean())


def principal_angle(x, y):
    x, y = x - np.median(x), y - np.median(y)
    return 0.5 * np.arctan2(2 * np.mean(x * y), np.mean(x * x) - np.mean(y * y))


def rotate(x, y, th):
    return x * np.cos(th) + y * np.sin(th), -x * np.sin(th) + y * np.cos(th)


def sweep_snr(data, signal):
    noise = float(np.median(data.std(axis=0, ddof=1))) if len(data) > 1 else np.nan
    return signal, noise, signal / noise


def main():
    if len(sys.argv) > 1:
        run_dir = sys.argv[1]
    else:
        runs = [r for r in sorted(glob.glob(os.path.join(
            load_config()["paths"]["data_dir"], "fm_mfli_*"))) if os.path.isdir(r)]
        if not runs:
            raise SystemExit("No fm_mfli_* folder: run odmr_fm_mfli_phase_pc.py first.")
        run_dir = runs[-1]

    meta, c = read_csv(os.path.join(run_dir, "fm_sweeps.csv"))
    f, X, t_fm = by_sweep(c, "X_V")
    _, Y, _ = by_sweep(c, "Y_V")
    th = principal_angle(X.mean(0), Y.mean(0))
    Xr, Yr = rotate(X, Y, th)
    Xr = Xr - np.median(Xr.mean(0))
    Yr = Yr - np.median(Yr.mean(0))
    df = np.gradient(f)
    if np.abs(np.min(np.cumsum(Xr.mean(0) * df))) < np.abs(np.max(np.cumsum(Xr.mean(0) * df))):
        th += np.pi                         # integral of X' must be a dip
        Xr, Yr = -Xr, -Yr
    th_sweeps = np.array([principal_angle(x, y) for x, y in zip(X, Y)])
    spread = np.degrees(np.ptp(np.angle(np.exp(2j * (th_sweeps - th))) / 2))
    fm_sig, fm_noise, fm_snr = sweep_snr(Xr, float(np.abs(Xr.mean(0)).max()))
    y_rms = float(np.sqrt(np.mean(Yr.mean(0) ** 2)))

    pick = np.hypot(float(meta.get("pickup_X_V", "nan")), float(meta.get("pickup_Y_V", "nan")))
    lines = [f"FM (MFLI) vs DC ({os.path.basename(run_dir)}, {meta.get('power_dBm')} dBm)",
             f"  f_mod {float(meta['f_mod_Hz']):.0f} Hz, deviation "
             f"{float(meta['deviation_Hz']) / 1e3:.0f} kHz, TC {float(meta['time_constant_s']) * 1e3:.0f} ms, "
             f"{float(meta['t_int_s']) * 1e3:.0f} ms per point, {len(X)} sweeps",
             f"  MFLI clock: {'external 10 MHz (shared with the SMCV)' if meta.get('ext_clock') == '1' else 'INTERNAL -> phase not locked'}",
             f"  signal phase {np.degrees(th):.1f} deg; per-sweep spread {spread:.1f} deg"
             + ("  <-- phase NOT stable" if spread > 10 else ""),
             f"  pickup off resonance: {pick * 1e6:.2f} uV vs FM signal "
             f"{fm_sig * 1e6:.2f} uV" + ("  <-- pickup comparable to the signal"
                                         if pick > 0.1 * fm_sig else ""),
             f"  residual in Y' (should be ~noise): {y_rms * 1e6:.2f} uV rms", "",
             "  per sweep         signal          noise     SNR   time/sweep",
             f"  FM X' (MFLI)  {fm_sig * 1e6:9.2f} uV  {fm_noise * 1e6:9.3f} uV  {fm_snr:6.1f}"
             f"   {t_fm:6.1f} s"]

    dc_path = os.path.join(run_dir, "dc_sweeps.csv")
    D = None
    if os.path.exists(dc_path):
        _, cd = read_csv(dc_path)
        fd, D, t_dc = by_sweep(cd, "ratio")
        base = float(np.median(D.mean(0)))
        dc_sig, dc_noise, dc_snr = sweep_snr(D, base - float(D.mean(0).min()))
        fm_eq = fm_snr * np.sqrt(t_dc / t_fm)
        lines += [f"  DC on/off     {100 * dc_sig:9.3f} %   {100 * dc_noise:9.4f} %   "
                  f"{dc_snr:6.1f}   {t_dc:6.1f} s",
                  "",
                  f"  FM SNR scaled to one DC sweep's time: {fm_eq:.1f} = "
                  f"{fm_eq / dc_snr:.2f} x DC -> FM "
                  + ("GIVES a better SNR." if fm_eq > dc_snr else "does NOT give a better SNR.")]
    else:
        lines.append("  (no dc_sweeps.csv: DO_DC was off)")

    fig, ax = plt.subplots(1, 3, figsize=(17, 4.8))
    a = ax[0]
    m, s = Xr.mean(0) * 1e6, Xr.std(0, ddof=1) * 1e6 if len(Xr) > 1 else 0
    a.fill_between(f, m - s, m + s, alpha=0.3, color="tab:blue")
    a.plot(f, m, "-", color="tab:blue", label="X' (signed FM signal)")
    a.plot(f, Yr.mean(0) * 1e6, "-", color="tab:gray", lw=0.8, label="Y' (residual)")
    a.axhline(0, color="k", lw=0.6)
    a.set(xlabel="MW frequency (MHz)", ylabel="demodulated (uV)",
          title=f"FM, phase-sensitive (SNR/sweep {fm_snr:.0f})")
    a.legend(fontsize=8)
    a = ax[1]
    if D is not None:
        m, s = D.mean(0), D.std(0, ddof=1) if len(D) > 1 else 0
        a.fill_between(fd, m - s, m + s, alpha=0.3, color="tab:red")
        a.plot(fd, m, "-", color="tab:red")
        a.set(title=f"DC on/off (SNR/sweep {dc_snr:.0f})")
    a.set(xlabel="MW frequency (MHz)", ylabel="PL_on / PL_off")
    a = ax[2]
    integ = np.cumsum(Xr.mean(0) * df)
    integ -= np.interp(f, [f[0], f[-1]], [integ[0], integ[-1]])   # baseline: the ends
    a.plot(f, integ / np.abs(integ).max(), "-", color="tab:blue",
           label="integral of X' (FM)")
    if D is not None:
        k = max(1, len(fd) // 10)
        dd = D.mean(0) - np.mean(np.r_[D.mean(0)[:k], D.mean(0)[-k:]])
        a.plot(fd, dd / np.abs(dd).max(), "-", color="tab:red", label="DC dip")
    a.set(xlabel="MW frequency (MHz)", ylabel="normalised",
          title="check: integrated FM vs DC line shape")
    a.legend(fontsize=8)
    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(run_dir, "fm_mfli.png")
    fig.savefig(out, dpi=140)

    summary = "\n".join(lines)
    print(summary)
    with open(os.path.join(run_dir, "fm_mfli_summary.txt"), "w") as fh:
        fh.write(summary + "\n")
    print(f"\nSaved {out}")
    plt.show()


if __name__ == "__main__":
    main()
