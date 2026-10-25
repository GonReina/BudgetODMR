"""
Analyse cal3_mw_laser_map.py: ODMR contrast vs laser power AND microwave power.

Reads <run>/index.csv (newest <data_dir>/calibration/mw_laser_map_* by default)
and the spectra next to it.

Figures (in the run folder):
  mw_laser_map.png        THE heatmap: dip 1 - PL_on/PL_off (%) (fixed-centre fit,
                          mean over the lines), laser power (y) vs MW power (x);
                          cells where the dip is below 2 sigma are greyed; boxes
                          mark the six cells of mw_laser_map_spectra.png.
  mw_laser_map_spectra.png  six representative spectra on one set of axes, colour
                          coded by map region (blue = low laser, red = high laser;
                          lighter = lower MW), legend outside the axes.
  mw_laser_map_fine.png   the 0.1 MHz fine spectra (low laser, low MW), with the
                          14N hyperfine positions marked.
  mw_spectra_L<N>_<I>mA.png  one figure per laser level: all MW-power spectra
                          overlaid, colour-coded from low MW (dark) to high MW
                          (bright plasma), legend with contrast per power.
  mw_laser_map_more.png   (a) FWHM map  (b) sweeps used  (c) relative sensitivity
                          eta = FWHM / (C sqrt PL), best cell starred
                          (d) drift check: reference contrast at the start and end
                          of each laser level, and the line-centre shift (heating)
  mw_laser_map_cuts.png   per laser level: (a) C vs MW power with the saturation
                          fit C = C_max P/(P + P_sat,MW)  (b) FWHM^2 vs MW power,
                          linear: FWHM^2 = W0^2 + k P  (c) P_sat,MW and C_max vs
                          laser  (d) W0 (zero-MW width) and k vs laser
  mw_laser_map_grid.csv, mw_laser_map_summary.txt

What to look for:
  * C_max falls and P_sat,MW rises with laser power: optical pumping competes
    with the MW drive (more MW power is needed to saturate the spin at higher
    laser power). P_sat,MW roughly proportional to the laser power is the
    textbook behaviour.
  * W0 growing with laser power = OPTICAL broadening; k (the slope of FWHM^2
    with MW power) = MW power broadening. If W0 is flat and the width is set
    by k P, the broadening you saw in step 3 is from the MW, not the laser.
  * the eta map: where to operate.

MW power on the x axis is the SMCV setting; with the amplifier in the chain the
top axis adds the typical chain gain (+44.4 dB), not a measured value.

Laser axis: the map stores the laser CURRENT; it is converted to power at the
sample with <data_dir>/calibration/power_calibration.csv when this runs
(Y_AXIS = "auto"). Redo the loss budget + plot_cal1_power.py, then simply rerun
this plotter.

Run:  python plot_cal3_mw_laser_map.py [run_dir or calibration_dir]
"""

import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from calib_common import (CAL_DIR, DZFS_MHZ_PER_K, load_power_table,
                          read_table)

Y_AXIS = "auto"            # "auto" (power if power_calibration.csv covers every
                           # current, else current), "current", "pl", "power"
HF_SPLIT_MHZ = 2.16        # 14N hyperfine splitting, marked on the fine spectra
CHAIN_GAIN_TYP_DB = 44.4   # ZHL-16W-43-S+ typical 45 dB - 0.6 dB isolator
SIGNIF = 2.0               # dips below SIGNIF sigma are greyed / left out of fits
ETA_SIGNIF = 5.0           # sensitivity map: contrast above 5 sigma ...
ETA_MAX_REL_W = 0.3        # ... and FWHM known to 30 %


def template_shift(f, s, f_t, s_t, max_shift=1.5, step=0.005):
    """Frequency shift of spectrum s relative to the template (f_t, s_t): fits
    s ~ a + b * dip_t(f - delta) for every delta on a fine grid (a, b linear)
    and returns the best delta (MHz). Uses the whole line shape, so it stays
    precise when broadened lines merge, where a 2-line fit wanders."""
    n = max(3, len(s_t) // 10)
    dip_t = np.median(np.r_[s_t[:n], s_t[-n:]]) - s_t
    best, best_chi = np.nan, np.inf
    for d in np.arange(-max_shift, max_shift + step / 2, step):
        x = np.interp(f - d, f_t, dip_t, left=0.0, right=0.0)
        X = np.column_stack([np.ones_like(f), x])
        p, *_ = np.linalg.lstsq(X, s, rcond=None)
        chi = float(np.sum((s - X @ p) ** 2))
        if chi < best_chi:
            best, best_chi = d, chi
    return float(best)


def find_run():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg and os.path.exists(os.path.join(arg, "index.csv")):
        return arg
    runs = sorted(d for d in glob.glob(os.path.join(arg or CAL_DIR, "mw_laser_map_*"))
                  if os.path.isdir(d))
    if not runs:
        raise SystemExit("No mw_laser_map_* folder: run cal3_mw_laser_map.py first.")
    return runs[-1]


def sat(p, cmax, psat):
    return cmax * p / (p + psat)


def smooth(s, n=3):
    s = np.asarray(s, float)
    return np.convolve(np.pad(s, n // 2, mode="edge"), np.ones(n) / n, mode="valid")


def pick_regions(C, sig):
    """Six representative cells: lowest / highest laser level x low / middle /
    high MW power. 'Low MW' is the lowest power with a significant dip in that
    row (the lowest power if none is). Returns [(name, (i, j), colour)]."""
    n_l, n_m = C.shape
    if n_l == 0 or n_m == 0:
        return []
    rows = [("low laser", 0, plt.get_cmap("Blues")), ("high laser", n_l - 1,
                                                       plt.get_cmap("Reds"))]
    if n_l == 1:
        rows = rows[:1]
    out = []
    for lname, i, cm in rows:
        ok = np.flatnonzero(sig[i] & np.isfinite(C[i]))
        j_lo = int(ok[0]) if ok.size else 0
        j_hi = n_m - 1
        j_mid = int(round(0.5 * (j_lo + j_hi)))
        for mname, j, shade in (("low MW", j_lo, 0.45), ("mid MW", j_mid, 0.7),
                                ("high MW", j_hi, 0.95)):
            if any(p[1] == (i, j) for p in out):
                continue
            out.append((f"{lname} / {mname}", (i, j), cm(shade)))
    return out


def spectrum_file(run, name):
    _, s = read_table(os.path.join(run, name))
    return s["freq_MHz"], s["signal"]


def main():
    run = find_run()
    meta, t = read_table(os.path.join(run, "index.csv"))
    amp = meta.get("amp_in_chain", "False") == "True"
    role = t["role"]
    grid_rows = (role == "map") | (role == "ref_start")
    steps = np.unique(t["laser_step"][grid_rows])
    cur_of = {s: float(np.nanmean(t["current_mA"][t["laser_step"] == s])) for s in steps}
    steps = np.array(sorted(steps, key=lambda s: cur_of[s]))
    mw = np.unique(t["mw_dBm"][grid_rows])
    shape = (len(steps), len(mw))
    C, E, W, WE, N, PL = (np.full(shape, np.nan) for _ in range(6))
    FILE = np.full(shape, "", dtype=object)
    pl_level = np.full(len(steps), np.nan)
    for r in np.flatnonzero(grid_rows):
        i = int(np.flatnonzero(steps == t["laser_step"][r])[0])
        j = int(np.flatnonzero(mw == t["mw_dBm"][r])[0])
        FILE[i, j] = t["file"][r]
        C[i, j], E[i, j] = t["contrast"][r], t["contrast_err"][r]
        W[i, j], WE[i, j] = t["fwhm_MHz"][r], t["fwhm_err_MHz"][r]
        N[i, j] = t["n_sweeps"][r]
        PL[i, j] = t["PL_off_V"][r] - t["dark_V"][r]
        pl_level[i] = t["PL_V"][r] - t["dark_V"][r]
    cur = np.array([cur_of[s] for s in steps])
    sig = C > SIGNIF * E

    # y axis: the current is converted to power with the step-1 table NOW (at plot
    # time), so a redone loss budget updates the axis without re-measuring
    ylab, yval = "laser current (mA)", cur
    labels = [f"{c:.0f}" for c in cur]
    p_of_i, pmeta = load_power_table(required=False)
    p_sample = p_of_i(cur) if p_of_i is not None else np.full(len(cur), np.nan)
    use_power = Y_AXIS == "power" or (Y_AXIS == "auto" and np.isfinite(p_sample).all())
    if Y_AXIS == "pl":
        ylab, yval = "PL above dark, MW off (mV)", pl_level * 1e3
        labels = [f"{v:.3g}" for v in yval]
    elif use_power and np.isfinite(p_sample).any():
        ylab, yval = "laser power at the sample, mW (current, mA)", p_sample
        labels = [f"{p:.3g}  ({c:.0f})" for p, c in zip(p_sample, cur)]
        t_obj = float(pmeta.get("T_obj", "nan"))
        if t_obj > 1:
            print(f"WARNING: power_calibration.csv has T_obj = {t_obj:.2f} > 1: the "
                  "power axis is wrong until the loss budget is redone.")
    y = np.arange(len(steps))

    def heat(ax, Z, cbar, cmap="viridis", fmt="{:.2f}", grey=None):
        im = ax.pcolormesh(mw, y, Z, cmap=cmap, shading="nearest")
        plt.colorbar(im, ax=ax, label=cbar, pad=0.02)
        for i in range(shape[0]):
            for j in range(shape[1]):
                if np.isfinite(Z[i, j]):
                    dim = grey is not None and not grey[i, j]
                    ax.text(mw[j], i, fmt.format(Z[i, j]), ha="center", va="center",
                            fontsize=6, color="0.6" if dim else "w")
        if grey is not None:
            ax.pcolormesh(mw, y, np.where(grey, np.nan, 1.0), cmap="Greys", vmin=0,
                          vmax=1.4, alpha=0.6, shading="nearest")
        ax.set_yticks(y, labels)
        ax.set(xlabel="MW power, SMCV setting (dBm)", ylabel=ylab)
        if amp:
            top = ax.secondary_xaxis("top", functions=(lambda d: d + CHAIN_GAIN_TYP_DB,
                                                       lambda d: d - CHAIN_GAIN_TYP_DB))
            top.set_xlabel("at the antenna, typical gain (dBm)")

    # ---- representative cells: low / high laser x low / mid / high MW ----
    picks = pick_regions(C, sig)

    # ---- 1: the heatmap ------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 6.5))
    heat(ax, 100 * C, "ODMR dip 1 - PL_on/PL_off (%)", "magma", grey=sig)
    # MW axis in Rabi frequency, if plot_cal3_rabi.py has calibrated it
    rabi_path = os.path.join(os.path.dirname(os.path.abspath(run)), "rabi_calibration.csv")
    if os.path.exists(rabi_path):
        rmeta, _ = read_table(rabi_path)
        kappa = float(rmeta.get("kappa_MHz_per_sqrt_mW", "nan"))
        if np.isfinite(kappa) and kappa > 0:
            rb = ax.secondary_xaxis(-0.13, functions=(
                lambda d: kappa * np.sqrt(10 ** (np.asarray(d) / 10)),
                lambda f: 10 * np.log10(np.clip(np.asarray(f) / kappa, 1e-12, None) ** 2)))
            rb.set_xlabel(f"Rabi frequency (MHz), from {rmeta.get('source', 'rabi run')}")
    dx = float(np.median(np.diff(mw))) if len(mw) > 1 else 3.0
    for name, (i, j), col in picks:
        ax.add_patch(plt.Rectangle((mw[j] - 0.47 * dx, i - 0.47), 0.94 * dx, 0.94,
                                   fill=False, ec=col, lw=2.5))
    ax.set_title(f"ODMR contrast vs laser and MW power ({os.path.basename(run)})\n"
                 f"grey: dip below {SIGNIF:.0f} sigma", fontsize=10, pad=40)
    fig.tight_layout()
    fig.savefig(os.path.join(run, "mw_laser_map.png"), dpi=150)

    # ---- 1b: representative spectra on one set of axes -----------------------
    if picks:
        fig_s, ax_s = plt.subplots(figsize=(11, 6))
        for name, (i, j), col in picks:
            f, s = spectrum_file(run, FILE[i, j])
            laser = (f"{p_sample[i]:.3g} mW ({cur[i]:.0f} mA)" if use_power
                     else f"{cur[i]:.0f} mA")
            lab = (f"{name}: {laser}, {mw[j]:+.1f} dBm, C = {100 * C[i, j]:.2f} %")
            ax_s.plot(f, 100 * (1 - s), ".", ms=3, color=col, alpha=0.7)
            ax_s.plot(f, 100 * (1 - smooth(s)), "-", lw=1.5, color=col, label=lab)
        ax_s.set(xlabel="frequency (MHz)", ylabel="ODMR dip 1 - PL_on/PL_off (%)",
                 title="representative spectra from each region of the map "
                       "(boxes on mw_laser_map.png; lines: 3-point average)")
        ax_s.grid(alpha=0.3)
        ax_s.legend(title="map region: laser, MW (SMCV setting)", loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8,
                    title_fontsize=8, frameon=False)
        fig_s.savefig(os.path.join(run, "mw_laser_map_spectra.png"), dpi=150,
                      bbox_inches="tight")

    # ---- 1c: fine spectra (low laser, low MW) --------------------------------
    fine = np.flatnonzero(role == "fine")
    if fine.size:
        fig_f, ax_f = plt.subplots(figsize=(11, 6))
        cmap_f = plt.get_cmap("plasma")
        for k, r in enumerate(fine[np.argsort(t["current_mA"][fine])]):
            f, s = spectrum_file(run, t["file"][r])
            col = cmap_f(k / max(1, fine.size - 1) * 0.85)
            ax_f.plot(f, 100 * (1 - s), ".", ms=2, color=col, alpha=0.6)
            w_ = t["fwhm_MHz"][r]
            # at the edge of the fit's width grid = not a single Lorentzian (e.g. a
            # resolved hyperfine triplet): no width quoted
            w_txt = (f"FWHM {w_:.2f} MHz" if np.isfinite(w_) and w_ < 11.5
                     else "single-Lorentzian width n/a")
            ax_f.plot(f, 100 * (1 - smooth(s, 5)), "-", lw=1.2, color=col,
                      label=f"{t['current_mA'][r]:.0f} mA, {t['mw_dBm'][r]:+.1f} dBm, "
                            f"{w_txt}, {t['n_sweeps'][r]:.0f} sweeps")
        for cc in (t["f1_MHz"][fine[0]], t["f2_MHz"][fine[0]]):
            if np.isfinite(cc):
                for d in (-HF_SPLIT_MHZ, 0, HF_SPLIT_MHZ):
                    ax_f.axvline(cc + d, color="0.6", ls=":", lw=0.8)
        ax_f.set(xlabel="frequency (MHz)", ylabel="ODMR dip 1 - PL_on/PL_off (%)",
                 title="fine spectra at low laser and MW power (dotted: line centres "
                       f"+/- {HF_SPLIT_MHZ} MHz, the 14N hyperfine positions)")
        ax_f.grid(alpha=0.3)
        ax_f.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8,
                    frameon=False)
        fig_f.savefig(os.path.join(run, "mw_laser_map_fine.png"), dpi=150,
                      bbox_inches="tight")

    # ---- 1d: per-laser-level spectra (all MW powers overlaid) ---------------
    cmap_mw = plt.get_cmap("plasma")
    print("Saving per-level spectra figures...")
    for i in range(len(steps)):
        plot_j = [j for j in range(len(mw)) if FILE[i, j]]
        if not plot_j:
            continue
        fig_l, ax_l = plt.subplots(figsize=(11, 5))
        for k, j in enumerate(plot_j):
            col = cmap_mw(k / max(1, len(plot_j) - 1) * 0.88)
            f, s = spectrum_file(run, FILE[i, j])
            lab = f"{mw[j]:+.1f} dBm"
            if np.isfinite(C[i, j]):
                lab += f"  C={100 * C[i, j]:.2f}%"
            ax_l.plot(f, 100 * (1 - s), ".", ms=2, color=col, alpha=0.45)
            ax_l.plot(f, 100 * (1 - smooth(s)), "-", lw=1.2, color=col, label=lab)
        laser_label = (f"{p_sample[i]:.3g} mW ({cur[i]:.0f} mA)" if use_power
                       else f"{cur[i]:.0f} mA")
        ax_l.set(xlabel="frequency (MHz)", ylabel="ODMR dip 1 - PL_on/PL_off (%)",
                 title=f"ODMR spectra vs MW power — laser {laser_label} "
                       f"({os.path.basename(run)})")
        ax_l.grid(alpha=0.3)
        ax_l.legend(title="MW power (SMCV setting)", loc="upper left",
                    bbox_to_anchor=(1.01, 1.0), fontsize=7, title_fontsize=7,
                    frameon=False)
        out_l = os.path.join(run, f"mw_spectra_L{int(steps[i]):02d}_{cur[i]:.0f}mA.png")
        fig_l.savefig(out_l, dpi=150, bbox_inches="tight")
        plt.close(fig_l)
        print(f"  {os.path.basename(out_l)}")

    # ---- 2: width, sweeps, sensitivity, drift ----------------------------
    # sensitivity only where contrast AND width are well measured (a weak dip's
    # width can collapse onto the edge of the fit grid and fake a "best" cell)
    good_w = (C > ETA_SIGNIF * E) & (WE < ETA_MAX_REL_W * W)
    eta = np.where(good_w & (PL > 0),
                   W / (C * np.sqrt(np.where(PL > 0, PL, np.nan))), np.nan)
    eta = eta / np.nanmin(eta) if np.isfinite(eta).any() else eta
    fig2, ax2 = plt.subplots(2, 2, figsize=(15, 10))
    heat(ax2[0, 0], np.where(sig, W, np.nan), "FWHM (MHz)", "viridis")
    ax2[0, 0].set_title("(a) linewidth (significant dips only)")
    heat(ax2[0, 1], N, "sweeps averaged", "cividis", fmt="{:.0f}")
    ax2[0, 1].set_title("(b) sweeps used by the adaptive averaging")
    heat(ax2[1, 0], eta, "eta / eta_min (lower = better)", "viridis_r")
    best = None
    if np.isfinite(eta).any():
        best = np.unravel_index(np.nanargmin(eta), eta.shape)
        ax2[1, 0].plot(mw[best[1]], best[0], "*", color="red", ms=16, mec="w")
    ax2[1, 0].set_title("(c) relative sensitivity FWHM / (C sqrt PL)")

    # drift: reference contrast start vs end, and the line-centre shift of each
    # reference spectrum against the first one (template fit: heating)
    a = ax2[1, 1]
    c_start, c_end, d_start, d_end = (np.full(len(steps), np.nan) for _ in range(4))
    template = None
    for i, s in enumerate(steps):
        for rl, cc, dd in (("ref_start", c_start, d_start), ("ref_end", c_end, d_end)):
            m = np.flatnonzero((t["laser_step"] == s) & (role == rl))
            if m.size:
                cc[i] = t["contrast"][m[0]]
                f, sg = spectrum_file(run, t["file"][m[0]])
                if template is None:
                    template = (f, sg)
                dd[i] = template_shift(f, sg, *template)
    a.plot(yval, 100 * c_start, "o-", label="reference contrast, start of level")
    a.plot(yval, 100 * c_end, "s--", label="reference contrast, end of level")
    a.set(xlabel=ylab, ylabel="contrast at the reference MW power (%)",
          title="(d) drift check and heating (dip centroid, right axis)")
    a2 = a.twinx()
    d0 = d_start[np.isfinite(d_start)][0] if np.isfinite(d_start).any() else 0
    a2.plot(yval, (d_start - d0) * 1e3, "^:", color="tab:red", label="centre shift, start")
    a2.plot(yval, (d_end - d0) * 1e3, "v:", color="tab:pink", label="centre shift, end")
    a2.set_ylabel("line-centre shift (kHz); -74 kHz = +1 K")
    h1, l1 = a.get_legend_handles_labels()
    h2, l2 = a2.get_legend_handles_labels()
    a.legend(h1 + h2, l1 + l2, fontsize=7)
    a.grid(alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(os.path.join(run, "mw_laser_map_more.png"), dpi=130)

    # ---- 3: cuts and fits ----------------------------------------------
    p_mw = 10 ** (mw / 10)                       # mW at the SMCV (relative scale)
    fig3, ax3 = plt.subplots(2, 2, figsize=(14, 10))
    cmap = plt.get_cmap("viridis")
    cmax, psat, w0, kk, delta_fwhm = (np.full(len(steps), np.nan) for _ in range(5))
    for i in range(len(steps)):
        col = cmap(i / max(1, len(steps) - 1))
        ok = np.isfinite(C[i]) & np.isfinite(E[i])
        ax3[0, 0].errorbar(p_mw[ok], 100 * C[i, ok], yerr=100 * E[i, ok], fmt="o",
                           color=col, ms=4, label=labels[i])
        if ok.sum() >= 3:
            try:
                p, _ = curve_fit(sat, p_mw[ok], C[i, ok], p0=[C[i, ok].max() * 1.2,
                                 np.median(p_mw[ok])], sigma=np.where(E[i, ok] > 0,
                                 E[i, ok], np.nan) if np.all(E[i, ok] > 0) else None,
                                 bounds=([0, 1e-9], [1, 1e3]), maxfev=20000)
                cmax[i], psat[i] = p
                pp = np.logspace(np.log10(p_mw.min()), np.log10(p_mw.max()), 100)
                ax3[0, 0].plot(pp, 100 * sat(pp, *p), "-", color=col, lw=1)
            except Exception:
                pass
        okw = good_w[i] & np.isfinite(W[i])
        ax3[0, 1].errorbar(p_mw[okw], W[i, okw], yerr=WE[i, okw], fmt="o",
                           color=col, ms=4, capsize=2)
        if okw.sum() >= 3:
            k_, b_ = np.polyfit(p_mw[okw], W[i, okw] ** 2, 1)
            kk[i], w0[i] = k_, np.sqrt(b_) if b_ > 0 else np.nan
            if np.isfinite(kk[i]) and np.isfinite(w0[i]):
                delta_fwhm[i] = (np.sqrt(np.clip(kk[i] * float(p_mw[okw].max())
                                                  + w0[i] ** 2, 0, None)) - w0[i])
                pp_fit = np.linspace(0, float(p_mw[okw].max()) * 1.05, 80)
                ax3[0, 1].plot(pp_fit,
                               np.sqrt(np.clip(kk[i] * pp_fit + w0[i] ** 2, 0, None)),
                               "--", color=col, lw=1, alpha=0.8)
    ax3[0, 0].set_xscale("log")
    ax3[0, 0].set(xlabel="MW power at the SMCV (mW)", ylabel="contrast (%)",
                  title="(a) contrast vs MW power; lines: C_max P/(P + P_sat)")
    ax3[0, 0].legend(title=ylab, fontsize=7, title_fontsize=7, loc="upper left",
                     bbox_to_anchor=(1.01, 1), frameon=False)
    ax3[0, 1].set(xlabel="MW power at the SMCV (mW)", ylabel="FWHM (MHz)",
                  title="(b) MW power broadening: FWHM = sqrt(W0^2 + k P) (dashed = fit)")
    ax3[1, 0].plot(yval, 10 * np.log10(psat), "o-", label="P_sat,MW (dBm at SMCV)")
    ax3[1, 0].set(xlabel=ylab, ylabel="P_sat,MW (dBm at the SMCV)",
                  title="(c) MW saturation power and C_max vs laser")
    b2 = ax3[1, 0].twinx()
    b2.plot(yval, 100 * cmax, "s--", color="tab:red", label="C_max")
    b2.set_ylabel("C_max (%)", color="tab:red")
    ax3[1, 1].plot(yval, w0, "o-", label="W0 (zero-MW width)")
    ax3[1, 1].set(xlabel=ylab, ylabel="W0 (MHz)",
                  title="(d) optical (W0) vs MW (k) broadening")
    b3 = ax3[1, 1].twinx()
    b3.plot(yval, kk, "s--", color="tab:orange")
    b3.set_ylabel("k (MHz^2 per mW at the SMCV)", color="tab:orange")
    for a_ in ax3.flat:
        a_.grid(alpha=0.3, which="both")
    fig3.tight_layout()
    fig3.savefig(os.path.join(run, "mw_laser_map_cuts.png"), dpi=130)

    # ---- tables ----------------------------------------------------------
    with open(os.path.join(run, "mw_laser_map_grid.csv"), "w") as f:
        f.write(f"# source={os.path.basename(run)}/index.csv\n"
                "current_mA,P_sample_mW,PL_V,mw_dBm,contrast,contrast_err,fwhm_MHz,"
                "fwhm_err_MHz,n_sweeps,eta_rel\n")
        for i in range(shape[0]):
            for j in range(shape[1]):
                f.write(",".join(f"{v:.6g}" for v in (
                    cur[i], p_sample[i], pl_level[i], mw[j], C[i, j], E[i, j], W[i, j],
                    WE[i, j],
                    N[i, j], eta[i, j])) + "\n")
    lines = [f"MW x LASER MAP ({os.path.basename(run)}): {len(steps)} laser levels x "
             f"{len(mw)} MW powers",
             "   I (mA)  PL (mV)   C_max (%)  P_sat,MW (dBm)  W0 (MHz)  k (MHz^2/mW)  "
             "dFWHM (MHz)  ref drift (%)  centre shift (kHz)"]
    for i in range(len(steps)):
        drift = 100 * (c_end[i] / c_start[i] - 1) if c_start[i] else np.nan
        okw_i = good_w[i] & np.isfinite(W[i])
        med_we_i = float(np.nanmedian(WE[i, okw_i])) if okw_i.any() else np.nan
        broad_flag = (
            "  <-- MW power broadening"
            if np.isfinite(delta_fwhm[i]) and np.isfinite(med_we_i)
            and delta_fwhm[i] > 2 * med_we_i
            else ""
        )
        lines.append(f"  {cur[i]:7.1f}  {pl_level[i] * 1e3:7.2f}  {100 * cmax[i]:9.2f}  "
                     f"{10 * np.log10(psat[i]):14.1f}  {w0[i]:8.2f}  {kk[i]:12.3g}  "
                     f"{delta_fwhm[i]:11.3f}  {drift:13.1f}  "
                     f"{(d_end[i] - d_start[i]) * 1e3:18.0f}{broad_flag}")
    if best is not None:
        lines.append(f"  best sensitivity cell: {cur[best[0]]:.1f} mA, "
                     f"{mw[best[1]]:+.1f} dBm (C = {100 * C[best]:.2f} %, "
                     f"FWHM {W[best]:.2f} MHz)")
    if np.isfinite(d_start).sum() >= 2:
        sh = (np.nanmax(d_start) - np.nanmin(d_start)) / DZFS_MHZ_PER_K
        lines.append(f"  line centre at the reference MW power moves by "
                     f"{abs(sh):.1f} K equivalent across the laser levels")
    summary = "\n".join(lines)
    print(summary)
    with open(os.path.join(run, "mw_laser_map_summary.txt"), "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved figures in {run}")
    plt.show()


if __name__ == "__main__":
    main()
