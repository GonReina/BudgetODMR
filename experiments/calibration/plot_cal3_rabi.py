"""
Analyse cal3_rabi_transient.py: Rabi frequency vs MW power, and the optical
pumping time vs laser power, from the PL around the MW gate edges.

For every setting (laser level x MW power):
  rise  = PL after the MW turns ON, relative to the PL just before, minus the
          same OFF resonance (removes gate pickup / switching transients):
              y(t) = A exp(-t/tau) cos(2 pi f_R t + phi) + B (1 - exp(-t/tau_s)) + C
          f_R = Rabi frequency (generalised, if slightly off resonance), tau =
          nutation damping (T2* and optical pumping), B = the CW ODMR dip.
  fall  = PL after the MW turns OFF, relative to the fully recovered PL, minus
          OFF resonance:  y(t) = D exp(-t/tau_p) + E;  tau_p = optical
          re-polarisation (pumping) time at this laser power.

Then f_R vs MW power: f_R = kappa sqrt(P) (P in mW at the SMCV) -> kappa, written
to rabi_calibration.csv next to the run folder (= <data_dir>/calibration);
plot_cal3_mw_laser_map.py then
labels the MW axis of the map in Rabi frequency too.

Figures (in the run folder): rabi_traces_L<step>.png (traces + fits per laser
level), rabi_summary.png (f_R vs sqrt(P), damping, pumping time vs laser);
rabi_fits.csv, rabi_summary.txt.

Run:  python plot_cal3_rabi.py [run_dir or calibration_dir]
"""

import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from calib_common import CAL_DIR, load_power_table, read_table

T0_US = 0.03          # skip the first samples after the edge (gate / MW switch delay)
RISE_FIT_US = 5.0     # fit window after the MW turns on
TAIL_US = 3.0         # end of the falling-edge trace = the recovered PL level
F_MIN_MHZ, F_MAX_MHZ = 0.3, 40.0
OSC_SIGNIF = 3.0      # oscillation amplitude must exceed 3 sigma to quote f_R


def find_run():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg and os.path.exists(os.path.join(arg, "index.csv")):
        return arg
    runs = sorted(d for d in glob.glob(os.path.join(arg or CAL_DIR, "rabi_*"))
                  if os.path.isdir(d))
    if not runs:
        raise SystemExit("No rabi_* folder: run cal3_rabi_transient.py first.")
    return runs[-1]


def nutation(t, a, tau, f, phi, b, tau_s, c):
    return a * np.exp(-t / tau) * np.cos(2 * np.pi * f * t + phi) + \
        b * (1 - np.exp(-t / tau_s)) + c


def recovery(t, d, tau_p, e):
    return d * np.exp(-t / tau_p) + e


def fit_rise(t, y):
    m = (t >= T0_US) & (t <= RISE_FIT_US) & np.isfinite(y)
    t, y = t[m], y[m]
    if len(t) < 30:
        return None
    b0 = float(np.mean(y[t > 0.6 * t.max()]))
    trend = b0 * (1 - np.exp(-t / 0.5))
    r = (y - trend) * np.hanning(len(t))
    fr = np.fft.rfftfreq(len(t) * 4, t[1] - t[0])
    sp = np.abs(np.fft.rfft(r, len(t) * 4))
    band = np.flatnonzero((fr >= F_MIN_MHZ) & (fr <= F_MAX_MHZ))
    # multi-start: the 3 strongest spectral peaks plus a log grid of frequencies,
    # each with 4 phases (a damped oscillation fit has many local minima)
    peaks = list(fr[band][np.argsort(sp[band])[::-1][:3]]) if band.size else []
    starts = peaks + list(np.geomspace(F_MIN_MHZ * 2, F_MAX_MHZ / 2, 8))
    a0 = 2 * float(np.std(y - trend))
    best = None
    for f0 in starts:
        for phi0 in (0, np.pi / 2, np.pi, 3 * np.pi / 2):
            try:
                p, cov = curve_fit(nutation, t, y, p0=[a0, 0.4, f0, phi0, b0, 0.5, 0.0],
                                   bounds=([0, 0.01, F_MIN_MHZ, -10, -1, 0.01, -1],
                                           [1, 50, F_MAX_MHZ, 10, 1, 50, 1]),
                                   maxfev=5000)
            except Exception:
                continue
            chi = float(np.sum((y - nutation(t, *p)) ** 2))
            if best is None or chi < best[0]:
                best = (chi, p, np.sqrt(np.clip(np.diag(cov), 0, None)))
    if best is None:
        return None
    _, p, e = best
    return dict(p=p, e=e, a=p[0], a_err=e[0], tau=p[1], f=p[2], f_err=e[2], b=p[4],
                # resolved: significant amplitude, frequency known to 15 %, and
                # at least ~half a period before the oscillation has decayed
                seen=bool(p[0] > OSC_SIGNIF * e[0] and e[2] < 0.15 * p[2]
                          and p[1] * p[2] > 0.5))


def fit_fall(t, y):
    m = (t >= T0_US) & np.isfinite(y)
    t, y = t[m], y[m]
    if len(t) < 20:
        return None
    try:
        p, cov = curve_fit(recovery, t, y, p0=[y[0] - y[-1], 2.0, y[-1]],
                           bounds=([-1, 0.01, -1], [1, 500, 1]), maxfev=20000)
        e = np.sqrt(np.clip(np.diag(cov), 0, None))
        return dict(p=p, tau_p=p[1], tau_p_err=e[1], d=p[0])
    except Exception:
        return None


def rel(trace, sl):
    base = np.nanmean(trace[sl])
    return trace / base - 1 if base else np.full_like(trace, np.nan)


def main():
    run = find_run()
    _, t = read_table(os.path.join(run, "index.csv"))
    rows = []
    for r in range(len(t["file"])):
        d = np.load(os.path.join(run, t["file"][r]))
        pre = int(d["pre"])
        tr, tf = d["t_rise_us"], d["t_fall_us"]
        tail = slice(-max(5, int(TAIL_US * 1e-6 * float(d["fs"]))), None)
        y_r = rel(d["rise_on"], slice(0, pre)) - rel(d["rise_off"], slice(0, pre))
        y_f = rel(d["fall_on"], tail) - rel(d["fall_off"], tail)
        rows.append(dict(step=int(t["laser_step"][r]), cur=float(t["current_mA"][r]),
                         dbm=float(t["mw_dBm"][r]), tr=tr, tf=tf, yr=y_r, yf=y_f,
                         rise=fit_rise(tr, y_r), fall=fit_fall(tf, y_f),
                         n=int(d["n_rise_on"]), pl=float(t["PL_V"][r])))

    steps = sorted({r["step"] for r in rows})
    lines = [f"RABI / TRANSIENT NUTATION ({os.path.basename(run)})",
             "   I (mA)  MW (dBm)  edges   f_R (MHz)      damping tau (us)  "
             "CW dip B (%)  pumping tau_p (us)"]
    for s in steps:
        rs = sorted((r for r in rows if r["step"] == s), key=lambda r: r["dbm"])
        fig, ax = plt.subplots(1, 2, figsize=(15, 1.3 * len(rs) + 3))
        cmap = plt.get_cmap("viridis")
        off = 0.0
        span = max(np.nanmax(np.abs(r["yr"])) for r in rs) * 1.4 or 0.01
        for k, r in enumerate(rs):
            col = cmap(k / max(1, len(rs) - 1))
            ax[0].plot(r["tr"], 100 * (r["yr"] + off), lw=0.7, color=col)
            fr = r["rise"]
            txt = f"{r['dbm']:+.1f} dBm"
            if fr:
                tt = r["tr"][r["tr"] >= T0_US]
                ax[0].plot(tt, 100 * (nutation(tt, *fr["p"]) + off), "k-", lw=0.8)
                txt += (f": f_R = {fr['f']:.2f} MHz" if fr["seen"] else
                        ": no oscillation resolved")
            ax[0].text(r["tr"][-1], 100 * off, txt, fontsize=7, ha="right", va="bottom")
            ax[1].plot(r["tf"], 100 * (r["yf"] + off), lw=0.7, color=col)
            ff = r["fall"]
            if ff:
                tt = r["tf"][r["tf"] >= T0_US]
                ax[1].plot(tt, 100 * (recovery(tt, *ff["p"]) + off), "k-", lw=0.8)
                ax[1].text(r["tf"][-1], 100 * off, f"{r['dbm']:+.1f} dBm: tau_p = "
                           f"{ff['tau_p']:.2f} us", fontsize=7, ha="right", va="bottom")
            off += span
            lines.append(
                f"  {r['cur']:7.1f}  {r['dbm']:8.1f}  {r['n']:5d}   "
                + (f"{fr['f']:6.2f} +/- {fr['f_err']:.2f}" if fr and fr["seen"]
                   else "     n/a       ")
                + (f"   {fr['tau']:10.3f}       {100 * fr['b']:9.3f}" if fr
                   else "          n/a            n/a")
                + (f"    {ff['tau_p']:10.2f}" if ff else "           n/a"))
        for a_ in ax:
            a_.axvline(0, color="tab:red", lw=0.8, ls=":")
            a_.grid(alpha=0.3)
        ax[0].set(xlabel="time after the MW turns ON (us)",
                  ylabel="PL change, on - off resonance (%), offset per MW power",
                  title=f"nutation at {rs[0]['cur']:.0f} mA (black: fit)")
        ax[1].set(xlabel="time after the MW turns OFF (us)",
                  ylabel="PL change vs recovered level (%), offset",
                  title="optical re-polarisation (black: exponential fit)")
        fig.tight_layout()
        fig.savefig(os.path.join(run, f"rabi_traces_L{s:02d}.png"), dpi=130)

    # ---- f_R vs MW power, pumping time vs laser ----------------------------
    seen = [r for r in rows if r["rise"] and r["rise"]["seen"]]
    kappa = kappa_err = np.nan
    if len(seen) >= 2:
        sq = np.sqrt(10 ** (np.array([r["dbm"] for r in seen]) / 10))
        fR = np.array([r["rise"]["f"] for r in seen])
        w = 1 / np.array([max(r["rise"]["f_err"], 1e-3) for r in seen]) ** 2
        kappa = float(np.sum(w * sq * fR) / np.sum(w * sq ** 2))
        kappa_err = float(np.sqrt(1 / np.sum(w * sq ** 2)))
        lines += ["", f"  f_R = kappa sqrt(P_SMCV):  kappa = {kappa:.1f} +/- "
                      f"{kappa_err:.1f} MHz / sqrt(mW at the SMCV)",
                  "  Rabi frequency at the map MW levels: " + ", ".join(
                      f"{p:+.0f} dBm {kappa * np.sqrt(10 ** (p / 10)):.2f} MHz"
                      for p in (-40, -34, -28, -22, -16.5))]
        # next to the run folder (= <data_dir>/calibration for a normal run)
        cal_out = os.path.join(os.path.dirname(os.path.abspath(run)),
                               "rabi_calibration.csv")
        with open(cal_out, "w") as f:
            f.write(f"# experiment=rabi_calibration\n# source={os.path.basename(run)}\n"
                    f"# kappa_MHz_per_sqrt_mW={kappa:.6g}\n"
                    f"# kappa_err={kappa_err:.6g}\nmw_dBm,rabi_MHz,rabi_err_MHz,"
                    "current_mA\n")
            for r in seen:
                f.write(f"{r['dbm']},{r['rise']['f']:.6g},{r['rise']['f_err']:.6g},"
                        f"{r['cur']}\n")
    else:
        lines += ["", "  fewer than 2 settings with a resolved oscillation: no Rabi "
                      "calibration. Try more MW power, more records, or check that the "
                      "detector bandwidth is >> the expected f_R."]

    fig2, ax2 = plt.subplots(1, 3, figsize=(16, 4.6))
    for s in steps:
        rs = [r for r in rows if r["step"] == s and r["rise"] and r["rise"]["seen"]]
        if rs:
            sq = np.sqrt(10 ** (np.array([r["dbm"] for r in rs]) / 10))
            ax2[0].errorbar(sq, [r["rise"]["f"] for r in rs],
                            yerr=[r["rise"]["f_err"] for r in rs], fmt="o",
                            label=f"{rs[0]['cur']:.0f} mA")
            ax2[1].plot([r["dbm"] for r in rs], [r["rise"]["tau"] for r in rs], "o-",
                        label=f"{rs[0]['cur']:.0f} mA")
    if np.isfinite(kappa):
        xx = np.linspace(0, ax2[0].get_xlim()[1], 50)
        ax2[0].plot(xx, kappa * xx, "k--", label=f"kappa = {kappa:.1f} MHz/sqrt(mW)")
    ax2[0].set(xlabel="sqrt(MW power at the SMCV / mW)", ylabel="f_R (MHz)",
               title="(a) Rabi frequency (expect a line through 0)")
    ax2[1].set(xlabel="MW power, SMCV (dBm)", ylabel="nutation damping tau (us)",
               title="(b) damping: T2* and optical pumping")
    tp = [(r["cur"], r["pl"], r["fall"]["tau_p"], r["fall"]["tau_p_err"])
          for r in rows if r["fall"]]
    if tp:
        cur = np.array([x[0] for x in tp])
        p_of_i, _ = load_power_table(required=False)
        xs = p_of_i(cur) if p_of_i is not None else cur
        xl = ("laser power at the sample (mW)" if p_of_i is not None and
              np.isfinite(xs).all() else "laser current (mA)")
        if xl.startswith("laser current"):
            xs = cur
        ax2[2].errorbar(xs, [1 / x[2] for x in tp],
                        yerr=[x[3] / x[2] ** 2 for x in tp], fmt="o")
        ax2[2].set(xlabel=xl, ylabel="pumping rate 1/tau_p (1/us)",
                   title="(c) optical pumping rate (expect ~ linear in laser power)")
    for a_ in ax2:
        a_.grid(alpha=0.3)
        if a_.get_legend_handles_labels()[0]:
            a_.legend(fontsize=8)
    fig2.tight_layout()
    fig2.savefig(os.path.join(run, "rabi_summary.png"), dpi=130)

    with open(os.path.join(run, "rabi_fits.csv"), "w") as f:
        f.write("current_mA,mw_dBm,f_R_MHz,f_R_err_MHz,osc_resolved,tau_us,cw_dip,"
                "tau_pump_us,tau_pump_err_us\n")
        for r in rows:
            fr, ff = r["rise"], r["fall"]
            f.write(",".join(str(v) for v in (
                r["cur"], r["dbm"], fr["f"] if fr else "", fr["f_err"] if fr else "",
                fr["seen"] if fr else "", fr["tau"] if fr else "",
                fr["b"] if fr else "", ff["tau_p"] if ff else "",
                ff["tau_p_err"] if ff else "")) + "\n")
    summary = "\n".join(lines)
    print(summary)
    with open(os.path.join(run, "rabi_summary.txt"), "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved figures in {run}")
    plt.show()


if __name__ == "__main__":
    main()
