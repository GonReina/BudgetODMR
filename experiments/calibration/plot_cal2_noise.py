"""
Step 2d: analyse the laser-noise measurements.

Reads from <data_dir>/calibration/ (newest of each; any may be missing):
    noise_floors_*.npz             cal2_noise_floors.py
    rin_vs_current_*.npz           cal2_rin_vs_current.py
    noise_vs_photocurrent_*.npz    cal2_noise_vs_photocurrent.py
    power_calibration.csv          step 1 (optional: power at the sample axis)

Figure (noise_cal2.png):
  (a) noise ASD spectra: terminated input, blocked beam, and every current.
  (b) RIN(f) = S_V(f) / V_DC^2 spectra per current (dB/Hz): quiet bands.
  (c) RIN vs current at the candidate modulation frequencies (median over
      f +/- BAND_FRAC). Dashed: the blocked-beam floor expressed as RIN at the
      same DC level -- RIN below that cannot be measured at this light level.
  (d) Stage 0c: noise at the candidate frequencies vs DC photocurrent, log-log,
      with reference slopes 0 (electronics), 1/2 (shot), 1 (laser), the floors,
      and the fitted a^2 + b^2 V + c^2 V^2 decomposition (as laser_rin_pc.py).

Set TRANSIMPEDANCE_V_PER_A (PDA10A2 datasheet, for your load: Hi-Z or 50 ohm)
to plot against photocurrent and draw the absolute shot-noise line
sqrt(2 q G V); without it the x-axis is the DC voltage.

Output: rin_vs_current.csv, noise_vs_photocurrent.csv, noise_cal2.png,
        noise_cal2_summary.txt

Run:  python plot_cal2_noise.py [calibration_dir]
"""

import os

import matplotlib.pyplot as plt
import numpy as np

from calib_common import F_MOD, cal_dir_from_argv, latest, load_power_table
from laser_rin_pc import asd_of, fit_terms

# --- settings ---------------------------------------------------------------
F_CANDIDATES_HZ = sorted({1000.0, 2000.0, 5000.0, 10000.0, F_MOD})
BAND_FRAC = 0.05            # median of the ASD over f +/- 5 %
TRANSIMPEDANCE_V_PER_A = None
Q_E = 1.602176634e-19


def band(fr, asd, f0):
    m = (fr >= f0 * (1 - BAND_FRAC)) & (fr <= f0 * (1 + BAND_FRAC))
    return float(np.median(asd[m])) if m.any() else float(asd[np.argmin(abs(fr - f0))])


def db(x):
    return 10 * np.log10(np.where(x > 0, x, np.nan))


def load(pattern, cal_dir):
    p = latest(pattern, cal_dir)
    return (np.load(p, allow_pickle=True), p) if p else (None, None)


def main():
    cal_dir = cal_dir_from_argv()
    floors, f_floor = load("noise_floors_*.npz", cal_dir)
    rin, f_rin = load("rin_vs_current_*.npz", cal_dir)
    vph, f_vph = load("noise_vs_photocurrent_*.npz", cal_dir)
    if rin is None and vph is None:
        raise SystemExit(f"No rin_vs_current_*.npz or noise_vs_photocurrent_*.npz in "
                         f"{cal_dir}: run the cal2 scripts first.")
    p_of_i, _ = load_power_table(os.path.join(cal_dir, "power_calibration.csv"),
                                 required=False)
    lines = []
    fl = {}
    if floors is not None:
        fs = float(floors["fs"])
        for name in ("terminated", "blocked"):
            fr, a = asd_of(floors[name], fs)
            fl[name] = (fr, a, {f: band(fr, a, f) for f in F_CANDIDATES_HZ})
        lines += [f"FLOORS ({os.path.basename(f_floor)}, IN1 {floors['gain']})",
                  "   f (Hz)    terminated (nV/rtHz)   blocked beam (nV/rtHz)"]
        for f in F_CANDIDATES_HZ:
            lines.append(f"  {f:7.0f}   {fl['terminated'][2][f] * 1e9:14.1f}   "
                         f"{fl['blocked'][2][f] * 1e9:18.1f}")
        lines.append("")
    else:
        lines.append("NO FLOORS: run cal2_noise_floors.py (needed to read the "
                     "plots below).\n")

    fig, ax = plt.subplots(2, 2, figsize=(14, 9))
    for name, st in (("terminated", ":"), ("blocked", "--")):
        if name in fl:
            ax[0, 0].loglog(fl[name][0][1:], fl[name][1][1:] * 1e9, st, color="k",
                            lw=1, label=f"{name} floor")

    # ---- RIN vs current --------------------------------------------------
    if rin is not None:
        fs = float(rin["fs"])
        cur, vdc = np.asarray(rin["current_mA"]), np.asarray(rin["v_dc"])
        cmap = plt.get_cmap("viridis")
        rin_at = {f: [] for f in F_CANDIDATES_HZ}
        for k, (c, v, tr) in enumerate(zip(cur, vdc, rin["traces"])):
            fr, a = asd_of(tr, fs)
            col = cmap(k / max(1, len(cur) - 1))
            ax[0, 0].loglog(fr[1:], a[1:] * 1e9, color=col, lw=0.7, label=f"{c:.1f} mA")
            ax[0, 1].semilogx(fr[1:], db(a[1:] ** 2 / v ** 2), color=col, lw=0.7,
                              label=f"{c:.1f} mA")
            for f in F_CANDIDATES_HZ:
                rin_at[f].append(band(fr, a, f) ** 2 / v ** 2)
        if "blocked" in fl:
            v_ref = float(np.mean(vdc))
            ax[0, 1].semilogx(fl["blocked"][0][1:],
                              db(fl["blocked"][1][1:] ** 2 / v_ref ** 2), "--",
                              color="k", lw=1, label="blocked floor as RIN")
        x_p = p_of_i(cur) if p_of_i else np.full_like(cur, np.nan)
        hdr = "current_mA,P_sample_mW,V_dc,tec_C," + ",".join(
            f"RIN_dB_{f:.0f}Hz,excess_RIN_dB_{f:.0f}Hz" for f in F_CANDIDATES_HZ)
        rows = []
        lines += [f"RIN vs CURRENT ({os.path.basename(f_rin)}, target "
                  f"{float(rin['v_target']) * 1e3:.0f} mV)",
                  "   I (mA)  P_samp (mW)  V_dc (mV) " + "".join(
                      f"{f:>9.0f} Hz" for f in F_CANDIDATES_HZ) + "   [RIN dB/Hz]"]
        for j, c in enumerate(cur):
            vals = [rin_at[f][j] for f in F_CANDIDATES_HZ]
            exc = [r - (fl["blocked"][2][f] ** 2 / vdc[j] ** 2 if "blocked" in fl else 0)
                   for r, f in zip(vals, F_CANDIDATES_HZ)]
            rows.append([c, x_p[j], vdc[j], float(rin["tec_C"][j])] +
                        [x for pair in zip(db(np.array(vals)), db(np.array(exc)))
                         for x in pair])
            lines.append(f"  {c:7.2f}  {x_p[j]:10.4f}  {vdc[j] * 1e3:9.1f} " +
                         "".join(f"{x:12.1f}" for x in db(np.array(vals))))
        for f in F_CANDIDATES_HZ:
            r = np.array(rin_at[f])
            ax[1, 0].plot(cur, db(r), "o-", label=f"{f:.0f} Hz")
            j = int(np.nanargmin(r))
            lines.append(f"  quietest at {f:6.0f} Hz: {cur[j]:.2f} mA "
                         f"({db(r[j]):.1f} dB/Hz; noisiest {db(np.nanmax(r)):.1f})")
            if "blocked" in fl:
                ax[1, 0].plot(cur, db(fl["blocked"][2][f] ** 2 / vdc ** 2), ":",
                              color=ax[1, 0].lines[-1].get_color(), lw=1)
        lines.append("")
        with open(os.path.join(cal_dir, "rin_vs_current.csv"), "w") as fcsv:
            fcsv.write(f"# source={os.path.basename(f_rin)}\n# band_frac={BAND_FRAC}\n"
                       + hdr + "\n")
            for row in rows:
                fcsv.write(",".join(f"{v:.6g}" for v in row) + "\n")
        if p_of_i and np.isfinite(x_p).any():
            top = ax[1, 0].twiny()
            top.set_xlim(ax[1, 0].get_xlim())
            top.set_xticks(cur[np.isfinite(x_p)])
            top.set_xticklabels([f"{p:.2g}" for p in x_p[np.isfinite(x_p)]],
                                fontsize=7, rotation=60)
            top.set_xlabel("power at the sample (mW)")
    ax[1, 0].set(xlabel="laser current (mA)", ylabel="RIN (dB/Hz)",
                 title="(c) RIN vs current (dotted: blocked-beam floor)")

    # ---- noise vs photocurrent (Stage 0c) --------------------------------
    if vph is not None and len(vph["v_dc"]):
        fs = float(vph["fs"])
        v = np.asarray(vph["v_dc"], float)
        order = np.argsort(v)
        v, tr_all = v[order], vph["traces"][order]
        g = TRANSIMPEDANCE_V_PER_A
        x = v / g * 1e6 if g else v * 1e3
        xlab = "DC photocurrent (uA)" if g else "photodiode DC level (mV)"
        sig = {f: [] for f in F_CANDIDATES_HZ}
        for tr in tr_all:
            fr, a = asd_of(tr, fs)
            for f in F_CANDIDATES_HZ:
                sig[f].append(band(fr, a, f))
        lines += [f"NOISE vs PHOTOCURRENT ({os.path.basename(f_vph)}, "
                  f"{float(vph['current_mA']):.2f} mA, {len(v)} levels)",
                  "   f (Hz)   log-log slope   a (nV/rtHz)  b (nV/rtHz/rtV)  "
                  "c (nV/rtHz/V)  RIN (dB/Hz)   dominant at the top level"]
        with open(os.path.join(cal_dir, "noise_vs_photocurrent.csv"), "w") as fcsv:
            fcsv.write(f"# source={os.path.basename(f_vph)}\n"
                       f"# current_mA={float(vph['current_mA'])}\n"
                       "label,V_dc," + ",".join(f"asd_{f:.0f}Hz_V_per_rtHz"
                                                for f in F_CANDIDATES_HZ) + "\n")
            for j, lab in enumerate(np.asarray(vph["label"])[order]):
                fcsv.write(f"{lab},{v[j]:.6g}," + ",".join(
                    f"{sig[f][j]:.6g}" for f in F_CANDIDATES_HZ) + "\n")
        for f in F_CANDIDATES_HZ:
            s = np.array(sig[f])
            pos = (v > 0) & (s > 0)
            slope = np.polyfit(np.log(v[pos]), np.log(s[pos]), 1)[0] if pos.sum() > 1 \
                else np.nan
            a_dark = fl["blocked"][2][f] if "blocked" in fl else None
            a, b, c = fit_terms(v, s, a_dark)
            vt = v.max()
            terms = {"electronics": a, "shot": b * np.sqrt(vt), "laser": c * vt}
            lines.append(f"  {f:7.0f}   {slope:10.2f}   {a * 1e9:11.1f}  {b * 1e9:13.1f}  "
                         f"{c * 1e9:13.1f}  {db(c ** 2):10.1f}   "
                         f"{max(terms, key=terms.get)}")
            ax[1, 1].loglog(x, s * 1e9, "o-", label=f"{f:.0f} Hz (slope {slope:.2f})")
        xx = np.logspace(np.log10(x.min()), np.log10(x.max()), 50)
        y0 = np.median([sig[f][0] for f in F_CANDIDATES_HZ]) * 1e9
        for p, st, name in ((0, ":", "slope 0"), (0.5, "--", "slope 1/2"),
                            (1, "-.", "slope 1")):
            ax[1, 1].loglog(xx, y0 * (xx / x.min()) ** p, st, color="0.5", lw=1,
                            label=name)
        if g:
            ax[1, 1].loglog(x, np.sqrt(2 * Q_E * g * v) * 1e9, "-", color="tab:green",
                            lw=2, alpha=0.5, label="shot noise sqrt(2qGV)")
        for name, st in (("terminated", ":"), ("blocked", "--")):
            if name in fl:
                ax[1, 1].axhline(fl[name][2][F_CANDIDATES_HZ[0]] * 1e9, color="k",
                                 ls=st, lw=0.8)
        ax[1, 1].set(xlabel=xlab)
        lines.append("  slope 0 = electronics, 1/2 = shot, 1 = laser noise")
    ax[1, 1].set(ylabel="noise ASD (nV/rtHz)",
                 title="(d) noise vs photocurrent (black: floors)")

    for f in F_CANDIDATES_HZ:
        for a_ in (ax[0, 0], ax[0, 1]):
            a_.axvline(f, color="tab:red", lw=0.6, alpha=0.5)
    ax[0, 0].set(xlabel="frequency (Hz)", ylabel="ASD (nV/rtHz)",
                 title="(a) noise spectra (red: candidate f_mod)")
    ax[0, 1].set(xlabel="frequency (Hz)", ylabel="RIN (dB/Hz)",
                 title="(b) RIN spectra at constant DC level")
    for a_ in ax.flat:
        a_.grid(alpha=0.3, which="both")
        if a_.lines:
            a_.legend(fontsize=6)
    fig.tight_layout()
    out = os.path.join(cal_dir, "noise_cal2.png")
    fig.savefig(out, dpi=150)

    summary = "\n".join(lines)
    print(summary)
    with open(os.path.join(cal_dir, "noise_cal2_summary.txt"), "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved {out}")
    plt.show()


if __name__ == "__main__":
    main()
