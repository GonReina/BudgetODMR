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

Output: pl_saturation.csv, pl_saturation.png, pl_saturation_summary.txt,
        odmr_raster.png  (every quick ODMR spectrum as one row of a colour map,
                          sorted by laser power, with the power and PL per row),
        odmr_spectra.png  (all quick ODMR spectra on one set of axes, colour-
                           coded by laser power, legend outside the axes),
        odmr_snr.png      (SNR = contrast / rms fit residual of each spectrum vs
                           laser power, against the shot-noise and fixed-noise
                           scalings; the noise; FWHM / SNR)

Currents above the top of the step-1 table are NOT dropped: with EXTRAPOLATE
their power is extended linearly from the top EXTRAP_PTS calibration points.
They are marked "*" in the labels and tables, open markers in the figure, and
the extrapolated power range is shaded.

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
EXTRAPOLATE = True      # currents above the step-1 table: extend it linearly
EXTRAP_PTS = 3          # ... through its top this many points


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


def extrapolated(path, p_of_i, n_pts=EXTRAP_PTS):
    """P_of_I that continues the step-1 table linearly (fit through its top
    n_pts points) above its highest current; also returns that current and
    the slope (mW/mA)."""
    _, t = read_table(path)
    o = np.argsort(t["current_mA"])
    cur, pw = t["current_mA"][o], t["P_sample_mW"][o]
    k = np.polyfit(cur[-n_pts:], pw[-n_pts:], 1)

    def f(i_ma):
        i_ma = np.asarray(i_ma, float)
        return np.where(i_ma > cur[-1], np.polyval(k, i_ma), p_of_i(i_ma))
    return f, float(cur[-1]), float(k[0])


def load_pl(path, p_of_i):
    meta, c = read_table(path)
    p = p_of_i(c["current_mA"])
    return meta, c, p, c["PL_V"] - c["dark_V"], c["PL_std_V"]


def main():
    cal_dir = cal_dir_from_argv()
    f_cal = os.path.join(cal_dir, "power_calibration.csv")
    p_of_i, pmeta = load_power_table(f_cal)
    i_cal_max, p_cal_max, slope_x = np.inf, np.inf, np.nan
    if EXTRAPOLATE:
        p_of_i, i_cal_max, slope_x = extrapolated(f_cal, p_of_i)
        p_cal_max = float(p_of_i(i_cal_max))
    f_nv = FILE_NV or latest("pl_vs_current_nv_*.csv", cal_dir)
    f_bg = FILE_BG or latest("pl_vs_current_background_*.csv", cal_dir)
    f_nd = FILE_ND or latest("nd_check_*.csv", cal_dir)
    if not f_nv:
        raise SystemExit(f"No pl_vs_current_nv_*.csv in {cal_dir}: run "
                         "cal3_pl_vs_power.py with MODE = 'nv'.")
    meta, c, P, pl, pl_err = load_pl(f_nv, p_of_i)
    extrap = c["current_mA"] > i_cal_max
    if np.isnan(P).any():
        print(f"WARNING: {np.isnan(P).sum()} current(s) outside the step-1 "
              "calibration range are dropped: "
              + ", ".join(f"{i:.0f}" for i in c["current_mA"][np.isnan(P)]) + " mA "
              "(extend the cal1 sweep, or set EXTRAPOLATE = True).")
    ok = np.isfinite(P)
    lines = [f"PL vs POWER ({os.path.basename(f_nv)}; T_obj = "
             f"{pmeta.get('T_obj', '?')})"]
    if extrap.any():
        lines.append(f"  * EXTRAPOLATED power for {extrap.sum()} current(s) above "
                     f"{i_cal_max:.0f} mA ({p_cal_max:.1f} mW): linear through the top "
                     f"{EXTRAP_PTS} step-1 points, {slope_x:.3f} mW/mA -> "
                     f"{np.nanmax(P):.1f} mW at {c['current_mA'].max():.0f} mA. "
                     "Fits using them are only as good as that guess.")
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
    lin = None
    if p_full is not None:
        lines.append(f"  free fit:  A = {p_full[0] * 1e3:.3f} +/- {e_full[0] * 1e3:.3f} mV, "
                     f"P_sat = {p_full[1]:.3f} +/- {e_full[1]:.3f} mW, "
                     f"b = {p_full[2] * 1e3:.4f} +/- {e_full[2] * 1e3:.4f} mV/mW")
        if p_full[1] > 2 * pn.max():
            lin = np.polyfit(pn, yn, 1)
            slope = lin[0]
            lines.append(f"  NO SATURATION in {pn.min():.1f}-{pn.max():.1f} mW: P_sat runs "
                         "off to the bound, so A, P_sat and their errors mean nothing. "
                         f"PL is ~linear here ({slope * 1e3:.3f} mV/mW; PL/P = "
                         f"{yn[0] / pn[0] * 1e3:.2f} -> {yn[-1] / pn[-1] * 1e3:.2f} mV/mW). "
                         "Saturation needs more power than this range.")
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
    C, Ce, W, We, D, De, N, spectra = ([] for _ in range(8))
    raster = []     # (row index in the table, freq, signal) for the raster plot
    for j, fname in enumerate(c["odmr_file"] if "odmr_file" in c else []):
        fp = os.path.join(cal_dir, str(fname)) if isinstance(fname, str) and fname else None
        res = None
        if fp and os.path.exists(fp):
            _, s = read_table(fp)
            res = fit_odmr(s["freq_MHz"], s["signal"], n_lines)
            spectra.append((s["freq_MHz"], s["signal"], res))
            raster.append((j, s["freq_MHz"], s["signal"]))
        if res:
            ln = res["lines"]
            C.append(np.mean([x["contrast"] for x in ln]))
            Ce.append(np.sqrt(np.sum([x["contrast_err"] ** 2 for x in ln])) / len(ln))
            W.append(np.mean([x["fwhm"] for x in ln]))
            We.append(np.sqrt(np.sum([x["fwhm_err"] ** 2 for x in ln])) / len(ln))
            D.append(np.mean([x["f0"] for x in ln]))
            De.append(np.sqrt(np.sum([x["f0_err"] ** 2 for x in ln])) / len(ln))
            # noise of PL_on/PL_off: rms of the fit residual
            N.append(float(np.std(s["signal"] - res["model"](s["freq_MHz"]), ddof=1)))
        else:
            for lst in (C, Ce, W, We, D, De, N):
                lst.append(np.nan)
    has_odmr = len(C) == len(P) and np.isfinite(C).any()
    eta = np.full(len(P), np.nan)
    snr = np.full(len(P), np.nan)
    if has_odmr:
        C, Ce, W, We, D, De, N = map(np.array, (C, Ce, W, We, D, De, N))
        snr = C / N
        good = ok & np.isfinite(C) & (C > 0) & (pl > 0)
        eta[good] = W[good] / (C[good] * np.sqrt(pl[good]))
        eta /= np.nanmin(eta)
        jb = int(np.nanargmin(eta))
        lines += ["", "ODMR vs POWER (contrast & FWHM = mean over the lines)",
                  "   P (mW)   PL (mV)   C (%)   FWHM (MHz)   D (MHz)   eta (rel)"]
        for row, x in zip(zip(P, pl * 1e3, 100 * C, W, D, eta), extrap):
            lines.append("  {:7.3f}  {:8.3f}  {:6.2f}  {:10.3f}  {:9.3f}  {:8.2f}".format(*row)
                         + ("  *" if x else ""))
        lines.append(f"  best sensitivity (min FWHM / (C sqrt PL)) at P = {P[jb]:.3f} mW "
                     f"({c['current_mA'][jb]:.2f} mA)" + (" *" if extrap[jb] else ""))
        lines += ["", "ODMR SNR (per spectrum: C / rms of the fit residual; same sweep "
                  "settings at every current)",
                  "   P (mW)   noise (%)   noise (uV)    SNR   FWHM/SNR (kHz)"]
        for row, x in zip(zip(P, 100 * N, N * pl * 1e6, snr, 1e3 * W / snr), extrap):
            lines.append("  {:7.3f}  {:9.3f}  {:10.1f}  {:7.1f}  {:12.1f}".format(*row)
                         + ("  *" if x else ""))
        js = int(np.nanargmax(np.where(ok, snr, np.nan)))
        jf = int(np.nanargmin(np.where(ok, W / snr, np.nan)))
        lines.append(f"  highest SNR {snr[js]:.1f} at P = {P[js]:.3f} mW "
                     f"({c['current_mA'][js]:.2f} mA)" + (" *" if extrap[js] else ""))
        lines.append(f"  lowest FWHM/SNR {1e3 * W[jf] / snr[jf]:.1f} kHz at P = "
                     f"{P[jf]:.3f} mW ({c['current_mA'][jf]:.2f} mA)"
                     + (" *" if extrap[jf] else ""))
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
                "fwhm_MHz,fwhm_err_MHz,centre_MHz,centre_err_MHz,eta_rel,noise_rel,snr,"
                "P_extrapolated\n")
        nan = np.full(len(P), np.nan)
        cols = [c["current_mA"], P, pl, pl_err] + ([C, Ce, W, We, D, De] if has_odmr
                                                   else [nan] * 6) + [eta]
        cols += [N if has_odmr else nan, snr, extrap]
        for row in zip(*cols):
            f.write(",".join(f"{v:.6g}" for v in row) + "\n")

    # ---- figure ----------------------------------------------------------
    fig, ax = plt.subplots(2, 3, figsize=(15, 8.5))
    pp = np.linspace(0, np.nanmax(P) * 1.1, 200)
    a = ax[0, 0]
    a.errorbar(P[~extrap], pl[~extrap] * 1e3, yerr=pl_err[~extrap] * 1e3, fmt="o",
               color="tab:blue", label="on diamond")
    if extrap.any():
        a.errorbar(P[extrap], pl[extrap] * 1e3, yerr=pl_err[extrap] * 1e3, fmt="o",
                   mfc="none", color="tab:blue", label="on diamond (P extrapolated)")
    if lin is not None:      # degenerate saturation fit: show the straight line
        a.plot(pp, np.polyval(lin, pp) * 1e3, "-", label=f"linear, "
               f"{lin[0] * 1e3:.2f} mV/mW (no saturation found)")
    elif p_full is not None:
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
        if extrap.any() and a_ is not ax[1, 2]:
            a_.axvspan(p_cal_max, a_.get_xlim()[1], color="0.85", alpha=0.5, lw=0)
    if extrap.any():
        ax[0, 0].text(p_cal_max, 0.02, " P extrapolated", transform=ax[0, 0]
                      .get_xaxis_transform(), fontsize=7, color="0.3")
    fig.tight_layout()
    out = os.path.join(cal_dir, "pl_saturation.png")
    fig.savefig(out, dpi=150)

    out_r = plot_odmr_raster(raster, c, P, pl, extrap,
                             os.path.join(cal_dir, "odmr_raster.png"),
                             os.path.basename(f_nv))
    out_s = plot_odmr_overlay(raster, spectra, c, P, extrap,
                              os.path.join(cal_dir, "odmr_spectra.png"),
                              os.path.basename(f_nv))
    if out_s:
        out_r = f"{out_r}, {out_s}"
    if has_odmr:
        out_n = plot_snr(P, pl, C, Ce, W, N, snr, ok, extrap, p_cal_max,
                         os.path.join(cal_dir, "odmr_snr.png"), os.path.basename(f_nv))
        out_r = f"{out_r}, {out_n}"

    summary = "\n".join(lines)
    print(summary)
    with open(os.path.join(cal_dir, "pl_saturation_summary.txt"), "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved {out}" + (f" and {out_r}" if out_r else ""))
    plt.show()


def power_label(P, c, extrap, j):
    return ((f"{P[j]:.2f} mW" if np.isfinite(P[j]) else "? mW")
            + ("*" if extrap[j] else "") + f"  ({c['current_mA'][j]:.0f} mA)")


def raster_rows(raster, c, P, extrap):
    """Sort the spectra by laser power (lowest first) onto one frequency grid:
    rows (table indices), freq, image of the dip depth in %, colour limit, labels."""
    key = [P[j] if np.isfinite(P[j]) else c["current_mA"][j] / 1e6 for j, _, _ in raster]
    raster = [raster[k] for k in np.argsort(key)]
    rows = [j for j, _, _ in raster]
    fr = raster[0][1]
    img = np.array([100 * (1 - np.interp(fr, f, s, left=np.nan, right=np.nan))
                    for _, f, s in raster])
    lim = np.nanpercentile(np.abs(img), 99) if np.isfinite(img).any() else 1.0
    labels = [power_label(P, c, extrap, j) for j in rows]
    return rows, fr, img, lim, labels


def plot_odmr_overlay(raster, spectra, c, P, extrap, out, title):
    """All quick ODMR spectra on ONE set of axes (as panel (f)), colour-coded by
    laser power, with the fits, and a legend of the laser power OUTSIDE the axes."""
    if not raster:
        return None
    key = [P[j] if np.isfinite(P[j]) else c["current_mA"][j] / 1e6 for j, _, _ in raster]
    order = np.argsort(key)
    cmap = plt.get_cmap("viridis")
    fig, ax = plt.subplots(figsize=(11, 6))
    for k, i in enumerate(order[::-1]):              # highest power first in the legend
        j, fr, s = raster[i]
        res = spectra[i][2]
        col = cmap(1 - k / max(1, len(order) - 1))
        lab = power_label(P, c, extrap, j)
        ax.plot(fr, s, ".", ms=3, color=col, label=lab)
        if res:
            ax.plot(fr, res["model"](fr), "-", lw=1, color=col)
    ax.set(xlabel="frequency (MHz)", ylabel="PL_on / PL_off",
           title=f"quick ODMR spectra vs laser power ({title}; lines: fits)")
    ax.grid(alpha=0.3)
    ax.legend(title="laser power at the sample\n(current; * extrapolated)", loc="upper left",
              bbox_to_anchor=(1.01, 1.0), fontsize=7, title_fontsize=8,
              frameon=False, markerscale=3)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    return out


def plot_snr(P, pl, C, Ce, W, N, snr, ok, extrap, p_cal_max, out, title):
    """SNR of each quick ODMR spectrum vs laser power: (a) SNR = C / noise, with
    how it would scale if the noise were shot-limited (C sqrt PL) or a fixed
    detector noise (C PL), both matched to the measured median; (b) the noise
    as a fraction of the PL and in volts; (c) FWHM / SNR, the frequency
    resolution of one spectrum (lower = better)."""
    m = ok & np.isfinite(snr)
    o = np.argsort(P)
    o = o[m[o]]
    fig, ax = plt.subplots(1, 3, figsize=(16, 5))

    def pts(a_, y, yerr=None, **kw):
        for sel, mfc in ((~extrap[o], None), (extrap[o], "none")):
            if sel.any():
                a_.errorbar(P[o][sel], y[o][sel], yerr=None if yerr is None
                            else yerr[o][sel], fmt="o", mfc=mfc, capsize=2, **kw)
        a_.plot(P[o], y[o], "-", lw=0.8, alpha=0.5, color=kw.get("color"))

    a = ax[0]
    pts(a, snr, Ce / N, color="tab:blue")
    for model, ls, lab in ((C * np.sqrt(pl), "--", "shot-noise limited ~ C sqrt(PL)"),
                           (C * pl, ":", "fixed detector noise ~ C PL")):
        k = np.nanmedian(snr[m] / model[m])
        a.plot(P[o], k * model[o], ls, color="0.4", label=lab)
    js = o[int(np.nanargmax(snr[o]))]
    a.axvline(P[js], color="tab:blue", ls=":", lw=1,
              label=f"max SNR {snr[js]:.0f} at {P[js]:.1f} mW")
    a.set(ylabel="SNR = contrast / rms residual", title="(a) ODMR SNR per spectrum")
    a.legend(fontsize=7)

    a = ax[1]
    pts(a, 100 * N, color="tab:purple")
    a.set(ylabel="noise of PL_on/PL_off (%)", title="(b) noise")
    a.tick_params(axis="y", colors="tab:purple")
    t = a.twinx()
    t.plot(P[o], N[o] * pl[o] * 1e6, "s--", ms=4, color="tab:gray")
    t.set_ylabel("noise x PL (uV)  [constant = detector-limited]", color="tab:gray")

    a = ax[2]
    pts(a, 1e3 * W / snr, color="tab:green")
    jf = o[int(np.nanargmin((W / snr)[o]))]
    a.axvline(P[jf], color="tab:green", ls=":", lw=1,
              label=f"min {1e3 * W[jf] / snr[jf]:.0f} kHz at {P[jf]:.1f} mW")
    a.set(ylabel="FWHM / SNR (kHz)", title="(c) frequency resolution (lower = better)")
    a.legend(fontsize=7)

    for a_ in ax:
        a_.set_xlabel("power at the sample (mW)")
        a_.grid(alpha=0.3)
        if extrap.any():
            a_.axvspan(p_cal_max, a_.get_xlim()[1], color="0.85", alpha=0.5, lw=0)
    if extrap.any():
        ax[0].text(p_cal_max, 0.02, " P extrapolated (open markers)",
                   transform=ax[0].get_xaxis_transform(), fontsize=7, color="0.3")
    fig.suptitle(f"ODMR SNR vs laser power ({title}; one sweep per spectrum, "
                 "same settings at every power)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    return out


def plot_odmr_raster(raster, c, P, pl, extrap, out, title):
    """One row per laser power (sorted by power, lowest at the bottom): the ODMR
    dip depth 1 - PL_on/PL_off on a common frequency grid; beside it the laser
    power at the sample (and the typed-in monitor) and the PL for each row."""
    if not raster:
        return None
    rows, fr, img, lim, labels = raster_rows(raster, c, P, extrap)
    y = np.arange(len(rows))

    fig, ax = plt.subplots(1, 3, figsize=(14, max(4.0, 0.3 * len(rows) + 2)),
                           sharey=True, gridspec_kw=dict(width_ratios=[4, 1, 1]))
    im = ax[0].pcolormesh(fr, y, img, cmap="magma", vmin=0, vmax=lim, shading="nearest")
    fig.colorbar(im, ax=ax[0], pad=0.01, label="ODMR dip 1 - PL_on/PL_off (%)")
    ax[0].set(xlabel="frequency (MHz)",
              ylabel="laser power at the sample (current; * extrapolated)",
              title=f"ODMR spectra vs laser power ({title})")
    ax[0].set_yticks(y, labels, fontsize=7)

    ax[1].barh(y, [P[j] for j in rows], color="tab:green", alpha=0.6,
               label="step-1 calibration")
    ex = [k for k, j in enumerate(rows) if extrap[j]]
    if ex:
        ax[1].barh(ex, [P[rows[k]] for k in ex], color="none", edgecolor="tab:green",
                   hatch="//", label="extrapolated")
    if "P_mon_mW" in c and np.isfinite(c["P_mon_mW"]).any():
        ax[1].plot([c["P_mon_mW"][j] for j in rows], y, "k|", ms=10,
                   label="monitor (typed in)")
    ax[1].set(xlabel="power (mW)", title="laser power")
    ax[1].legend(fontsize=7, loc="lower right")
    ax[2].barh(y, [pl[j] * 1e3 for j in rows], color="tab:blue", alpha=0.6)
    ax[2].set(xlabel="PL - dark (mV)", title="PL")
    for a_ in ax[1:]:
        a_.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    return out


if __name__ == "__main__":
    main()
