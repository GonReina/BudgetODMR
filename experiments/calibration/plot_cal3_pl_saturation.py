"""
Step 3b: PL SATURATION, contrast, linewidth, sensitivity and heating vs the
laser power at the sample.

Reads from <data_dir>/calibration/ (newest of each):
    power_calibration.csv               step 1 (REQUIRED: the x-axis)
    pl_vs_current_nv_*.csv (+ ODMR)     cal3_pl_vs_power.py MODE "nv"
    pl_vs_current_background_*.csv      MODE "background" (optional)
    nd_check_*.csv                      MODE "nd_check"   (optional)

Analysis (P = power at the sample, PL with the dark level subtracted):
  * fit  PL = A*P/(P + P_sat) + b*P  to the on-diamond PL;
  * fit the off-diamond background as b_bg*P + c, and fit A*P/(P + P_sat) to
    PL - background (the NV part alone); b from the free fit should match b_bg;
  * from each quick ODMR: contrast C, linewidth FWHM (mean over the lines);
  * relative sensitivity eta ~ FWHM / (C * sqrt(PL)) (lower is better),
    normalised to its best point: this, not PL alone, picks the operating power;
    a FWHM that grows with P means optical power broadening;
  * heating: D = mean of the line centres vs P; the zero-field splitting moves
    by -74 kHz/K, so a drift with power means the diamond heats up.
  * detector linearity from the ND check.

Output: pl_saturation.csv, pl_saturation.png, pl_saturation_summary.txt

Run:  python plot_cal3_pl_saturation.py [calibration_dir]
"""

import os

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from calib_common import (DZFS_MHZ_PER_K, cal_dir_from_argv, fit_odmr, latest,
                          load_power_table, meta_float, read_table)

# --- settings ---------------------------------------------------------------
FILE_NV = None          # None -> newest pl_vs_current_nv_*.csv
FILE_BG = None          # None -> newest pl_vs_current_background_*.csv
FILE_ND = None          # None -> newest nd_check_*.csv
N_LINES = None          # None -> from the file (cal3 setting)


def sat_lin(p, a, psat, b):
    return a * p / (p + psat) + b * p


def sat(p, a, psat):
    return a * p / (p + psat)


def fit(fun, x, y, err, p0, bounds):
    sig = err if np.all(np.isfinite(err)) and np.all(err > 0) else None
    try:
        p, cov = curve_fit(fun, x, y, p0=p0, sigma=sig, absolute_sigma=sig is not None,
                           bounds=bounds, maxfev=20000)
        return p, np.sqrt(np.clip(np.diag(cov), 0, None))
    except Exception as e:
        print(f"  fit failed: {e}")
        return None, None


def load_pl(path, p_of_i):
    meta, c = read_table(path)
    p = p_of_i(c["current_mA"])
    return meta, c, p, c["PL_V"] - c["dark_V"], c["PL_std_V"]


def main():
    cal_dir = cal_dir_from_argv()
    p_of_i, pmeta = load_power_table(os.path.join(cal_dir, "power_calibration.csv"))
    f_nv = FILE_NV or latest("pl_vs_current_nv_*.csv", cal_dir)
    f_bg = FILE_BG or latest("pl_vs_current_background_*.csv", cal_dir)
    f_nd = FILE_ND or latest("nd_check_*.csv", cal_dir)
    if not f_nv:
        raise SystemExit(f"No pl_vs_current_nv_*.csv in {cal_dir}: run "
                         "cal3_pl_vs_power.py with MODE = 'nv'.")
    meta, c, P, pl, pl_err = load_pl(f_nv, p_of_i)
    if np.isnan(P).any():
        print(f"WARNING: {np.isnan(P).sum()} current(s) outside the step-1 "
              "calibration range are dropped.")
    ok = np.isfinite(P)
    lines = [f"PL vs POWER ({os.path.basename(f_nv)}; T_obj = "
             f"{pmeta.get('T_obj', '?')})"]
    if "P_mon_mW" in c and np.isfinite(c["P_mon_mW"]).any():
        # power monitor (pick-off): does the laser reproduce the step-1 power?
        rel = c["P_mon_mW"] / P
        rel = rel / np.nanmedian(rel)
        lines.append("  power monitor / step-1 power (normalised to the median): "
                     + ", ".join(f"{i:.0f} mA {r:.3f}"
                                 for i, r in zip(c["current_mA"], rel)))
        if np.nanmax(np.abs(rel - 1)) > 0.03:
            lines.append("  WARNING: the laser power differs from step 1 by > 3 % at "
                         "some currents: the power axis is off there.")

    # ---- saturation fits -------------------------------------------------
    pn, yn, en = P[ok], pl[ok], pl_err[ok]
    p_full, e_full = fit(sat_lin, pn, yn, en,
                         [1.5 * yn.max(), np.median(pn), 0.0],
                         ([0, 1e-9, -np.inf], [np.inf, np.inf, np.inf]))
    if p_full is not None:
        lines.append(f"  free fit:  A = {p_full[0] * 1e3:.3f} +/- {e_full[0] * 1e3:.3f} mV, "
                     f"P_sat = {p_full[1]:.3f} +/- {e_full[1]:.3f} mW, "
                     f"b = {p_full[2] * 1e3:.4f} +/- {e_full[2] * 1e3:.4f} mV/mW")
    bg = None
    if f_bg:
        _, cb, Pb, plb, plb_err = load_pl(f_bg, p_of_i)
        okb = np.isfinite(Pb)
        if okb.sum() >= 2:
            (b_bg, c_bg) = np.polyfit(Pb[okb], plb[okb], 1)
            bg = (Pb[okb], plb[okb], b_bg, c_bg)
            lines.append(f"  background ({os.path.basename(f_bg)}): b_bg = "
                         f"{b_bg * 1e3:.4f} mV/mW, offset {c_bg * 1e3:.3f} mV")
            nv_part = yn - (b_bg * pn + c_bg)
            p_nv, e_nv = fit(sat, pn, nv_part, en, [1.5 * nv_part.max(), np.median(pn)],
                             ([0, 1e-9], [np.inf, np.inf]))
            if p_nv is not None:
                lines.append(f"  NV part (PL - background): A = {p_nv[0] * 1e3:.3f} mV, "
                             f"P_sat = {p_nv[1]:.3f} +/- {e_nv[1]:.3f} mW")
            frac = (b_bg * pn + c_bg) / yn
            lines.append(f"  background fraction of the PL: {100 * frac.min():.1f} - "
                         f"{100 * frac.max():.1f} %")
    else:
        lines.append("  no background run: b is only constrained by the free fit "
                     "(run MODE = 'background').")

    # ---- ODMR: contrast, width, centre -----------------------------------
    n_lines = N_LINES or int(meta_float(meta, "n_lines", 2))
    C, Ce, W, We, D, De, spectra = ([] for _ in range(7))
    for fname in c["odmr_file"] if "odmr_file" in c else []:
        fp = os.path.join(cal_dir, str(fname)) if isinstance(fname, str) and fname else None
        res = None
        if fp and os.path.exists(fp):
            _, s = read_table(fp)
            res = fit_odmr(s["freq_MHz"], s["signal"], n_lines)
            spectra.append((s["freq_MHz"], s["signal"], res))
        if res:
            ln = res["lines"]
            C.append(np.mean([x["contrast"] for x in ln]))
            Ce.append(np.sqrt(np.sum([x["contrast_err"] ** 2 for x in ln])) / len(ln))
            W.append(np.mean([x["fwhm"] for x in ln]))
            We.append(np.sqrt(np.sum([x["fwhm_err"] ** 2 for x in ln])) / len(ln))
            D.append(np.mean([x["f0"] for x in ln]))
            De.append(np.sqrt(np.sum([x["f0_err"] ** 2 for x in ln])) / len(ln))
        else:
            for lst in (C, Ce, W, We, D, De):
                lst.append(np.nan)
    has_odmr = len(C) == len(P) and np.isfinite(C).any()
    eta = np.full(len(P), np.nan)
    if has_odmr:
        C, Ce, W, We, D, De = map(np.array, (C, Ce, W, We, D, De))
        good = ok & np.isfinite(C) & (C > 0) & (pl > 0)
        eta[good] = W[good] / (C[good] * np.sqrt(pl[good]))
        eta /= np.nanmin(eta)
        jb = int(np.nanargmin(eta))
        lines += ["", "ODMR vs POWER (contrast & FWHM = mean over the lines)",
                  "   P (mW)   PL (mV)   C (%)   FWHM (MHz)   D (MHz)   eta (rel)"]
        for row in zip(P, pl * 1e3, 100 * C, W, D, eta):
            lines.append("  {:7.3f}  {:8.3f}  {:6.2f}  {:10.3f}  {:9.3f}  {:8.2f}".format(*row))
        lines.append(f"  best sensitivity (min FWHM / (C sqrt PL)) at P = {P[jb]:.3f} mW "
                     f"({c['current_mA'][jb]:.2f} mA)")
        gw = good & np.isfinite(W)
        if gw.sum() >= 2:
            sw = np.polyfit(P[gw], W[gw], 1)[0]
            lines.append(f"  FWHM slope: {sw * 1e3:.1f} kHz/mW"
                         + ("  <-- optical power broadening" if sw * np.ptp(P[gw])
                            > 2 * np.nanmedian(We[gw]) else ""))
        gd = good & np.isfinite(D)
        if gd.sum() >= 2:
            sd, _ = np.polyfit(P[gd], D[gd], 1)
            lines.append(f"  centre drift: {sd * 1e3:+.1f} kHz/mW = "
                         f"{sd / DZFS_MHZ_PER_K:+.2f} K/mW "
                         f"({np.ptp(P[gd]) * sd / DZFS_MHZ_PER_K:+.2f} K over the sweep)")
    else:
        lines.append("  no ODMR spectra (DO_ODMR off, or fits failed).")
    if "P_mon_end_mW" in c and np.isfinite(c["P_mon_end_mW"]).any():
        drift = 100 * (c["P_mon_end_mW"] / c["P_mon_mW"] - 1)
        lines.append(f"  laser drift during each ODMR sweep (monitor): "
                     f"{np.nanmin(drift):+.2f} to {np.nanmax(drift):+.2f} %")

    if f_nd:
        _, nd = read_table(f_nd)
        lines.append("")
        for r, t in zip(nd["ratio"], nd["T_nd"]):
            lines.append(f"ND CHECK: PL ratio {r:.4f} vs T_nd {t:.4f} -> ratio/T = "
                         f"{r / t:.3f}" + ("  <-- DETECTOR SATURATES at the top power"
                                           if r / t > 1.05 else "  (linear)"))
    else:
        lines.append("\nNo ND check: run MODE = 'nd_check' to rule out detector "
                     "saturation.")

    with open(os.path.join(cal_dir, "pl_saturation.csv"), "w") as f:
        f.write(f"# source={os.path.basename(f_nv)}\n")
        f.write("current_mA,P_sample_mW,PL_V,PL_err_V,contrast,contrast_err,"
                "fwhm_MHz,fwhm_err_MHz,centre_MHz,centre_err_MHz,eta_rel\n")
        nan = np.full(len(P), np.nan)
        cols = [c["current_mA"], P, pl, pl_err] + ([C, Ce, W, We, D, De] if has_odmr
                                                   else [nan] * 6) + [eta]
        for row in zip(*cols):
            f.write(",".join(f"{v:.6g}" for v in row) + "\n")

    # ---- figure ----------------------------------------------------------
    fig, ax = plt.subplots(2, 3, figsize=(15, 8.5))
    pp = np.linspace(0, np.nanmax(P) * 1.1, 200)
    a = ax[0, 0]
    a.errorbar(P, pl * 1e3, yerr=pl_err * 1e3, fmt="o", label="on diamond")
    if p_full is not None:
        a.plot(pp, sat_lin(pp, *p_full) * 1e3, "-", label=f"A P/(P+P_sat) + bP, "
               f"P_sat={p_full[1]:.2f} mW")
        a.plot(pp, sat(pp, *p_full[:2]) * 1e3, ":", color="0.4", label="saturating part")
    if bg is not None:
        a.plot(bg[0], bg[1] * 1e3, "s", color="tab:gray", label="off diamond")
        a.plot(pp, (bg[2] * pp + bg[3]) * 1e3, "--", color="tab:gray")
    a.set(xlabel="power at the sample (mW)", ylabel="PL - dark (mV)",
          title="(a) PL saturation")
    a.legend(fontsize=7)
    if has_odmr:
        ax[0, 1].errorbar(P, 100 * C, yerr=100 * Ce, fmt="o-")
        ax[0, 1].set(ylabel="contrast C (%)")
        ax[0, 2].errorbar(P, W, yerr=We, fmt="o-", color="tab:orange")
        ax[0, 2].set(ylabel="FWHM (MHz)")
        ax[1, 0].plot(P, eta, "o-", color="tab:green")
        ax[1, 0].axvline(P[int(np.nanargmin(eta))], color="tab:green", ls=":")
        ax[1, 0].set(ylabel="FWHM / (C sqrt PL), relative")
        d0 = D[np.nanargmin(P)] if np.isfinite(D).any() else 0
        ax[1, 1].errorbar(P, (D - d0) * 1e3, yerr=De * 1e3, fmt="o-", color="tab:red")
        ax[1, 1].set(ylabel="centre shift (kHz)")
        tw = ax[1, 1].secondary_yaxis("right", functions=(
            lambda k: k / (DZFS_MHZ_PER_K * 1e3), lambda t: t * DZFS_MHZ_PER_K * 1e3))
        tw.set_ylabel("temperature change (K)")
        cmap = plt.get_cmap("viridis")
        for k, (fr, s, res) in enumerate(spectra):
            col = cmap(k / max(1, len(spectra) - 1))
            ax[1, 2].plot(fr, s, ".", ms=2, color=col)
            if res:
                ax[1, 2].plot(fr, res["model"](fr), "-", lw=0.8, color=col)
        ax[1, 2].set(xlabel="frequency (MHz)", ylabel="PL_on / PL_off")
    for a_, t in zip((ax[0, 1], ax[0, 2], ax[1, 0], ax[1, 1], ax[1, 2]),
                     ("(b) ODMR contrast", "(c) linewidth (power broadening?)",
                      "(d) relative sensitivity (lower = better)",
                      "(e) heating: line-centre shift", "(f) quick ODMR spectra")):
        a_.set_title(t)
        if a_ is not ax[1, 2]:
            a_.set_xlabel("power at the sample (mW)")
    for a_ in ax.flat:
        a_.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(cal_dir, "pl_saturation.png")
    fig.savefig(out, dpi=150)

    summary = "\n".join(lines)
    print(summary)
    with open(os.path.join(cal_dir, "pl_saturation_summary.txt"), "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved {out}")
    plt.show()


if __name__ == "__main__":
    main()
