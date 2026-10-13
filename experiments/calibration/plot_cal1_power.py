"""
Step 1c: analyse the loss budget and the power-vs-current sweeps, and write the
CALIBRATION TABLE current -> power at the sample (the x-axis for steps 2 and 3).

Reads from <data_dir>/calibration/ (newest file of each kind, or set the FILE_*
settings):
    loss_budget_*.csv                           cal1_loss_budget.py
    power_vs_current_before_objective_*.csv     cal1_power_vs_current.py
    power_vs_current_laser_output_*.csv         (optional: path transmission vs current)

What it computes:
  * the transmission of each measured stage (laser -> objective, objective,
    and the fibre if after_fibre was measured) and T_obj = P_after_objective / P_before_objective, averaged over the currents;
  * the 532 nm fraction f532 = (P_bandpass / T_bandpass) / P_open at each
    bandpass position (1.00 = no infrared on the sensor);
  * P_sample(I) = P_before_objective(I) * f532(before_objective) * T_obj,
    averaging the up and down sweeps; the error bar combines the logged
    scatter, half the up/down difference and the T_obj spread;
  * hysteresis (up - down), relative power fluctuation, path-transmission ratio
    (before_objective / laser_output) vs current, TEC temperature vs current, and a linear-extrapolated threshold.

Output: power_calibration.csv  (current_mA,P_sample_mW,P_sample_err_mW,P_before_mW,
                                hysteresis_pct,rel_std_pct,tec_C)
        power_calibration.png, power_calibration_summary.txt

Run:  python plot_cal1_power.py [calibration_dir]
"""

import os

import matplotlib.pyplot as plt
import numpy as np

from calib_common import cal_dir_from_argv, latest, meta_float, read_table

# --- settings ---------------------------------------------------------------
FILE_BUDGET = None     # None -> newest loss_budget_*.csv
FILE_SWEEP = None      # None -> newest power_vs_current_before_objective_*.csv
FILE_LASER = None      # None -> newest power_vs_current_laser_output_*.csv
T_OBJ_OVERRIDE = None  # e.g. 0.62 to force the objective transmission
APPLY_IR_CORRECTION = True
THRESH_FIT_FRAC = 0.5  # fit a line to points above this fraction of the max power

# beam path order; positions not measured are skipped (no fibre fitted yet)
CHAIN = ["laser_output", "after_fibre", "before_objective", "after_objective"]


def stage_ratios(budget):
    """{(position, current): P_open}, {position: f532 list}, per-current ratios."""
    pos, cur, filt, p = (budget["position"], budget["current_mA"],
                         budget["filter"], budget["P_mW"])
    open_p = {(a, round(c, 2)): v for a, c, f, v in zip(pos, cur, filt, p) if f == "none"}
    bp_p = {(a, round(c, 2)): v for a, c, f, v in zip(pos, cur, filt, p) if f == "bp532"}
    return open_p, bp_p


def summarise_budget(budget_path, lines):
    meta, b = read_table(budget_path)
    t_bp = meta_float(meta, "bp_T532", 1.0)
    open_p, bp_p = stage_ratios(b)
    currents = sorted({c for _, c in open_p})
    chain = [p for p in CHAIN if any(k[0] == p for k in open_p)]
    lines += [f"LOSS BUDGET ({os.path.basename(budget_path)})",
              "  current   " + "".join(f"{c:>18s}" for c in chain)]
    for c in currents:
        lines.append(f"  {c:7.2f}   " + "".join(
            f"{open_p.get((pos, c), np.nan):15.4f} mW" for pos in chain))
    ratios = {}
    names = {("laser_output", "after_fibre"): "fibre coupling",
             ("before_objective", "after_objective"): "objective T_obj"}
    stages = [(a, z, names.get((a, z), f"{a} -> {z}"))
              for a, z in zip(chain[:-1], chain[1:])]
    if len(chain) > 2:
        stages.append((chain[0], chain[-1], "total"))
    for a, z, name in stages:
        r = np.array([open_p[(z, c)] / open_p[(a, c)] for c in currents
                      if (a, c) in open_p and (z, c) in open_p and open_p[(a, c)] > 0])
        ratios[name] = r
        if r.size:
            lines.append(f"  {name:34s}: {r.mean():.3f} +/- {r.std():.3f}  "
                         f"(per current: {', '.join(f'{x:.3f}' for x in r)})")
    f532 = {}
    for (pos, c), v in bp_p.items():
        if (pos, c) in open_p and open_p[(pos, c)] > 0:
            f532.setdefault(pos, []).append(v / t_bp / open_p[(pos, c)])
    lines.append(f"  532 nm fraction (bandpass T = {t_bp:.2f}):")
    for pos, fr in f532.items():
        fr = np.array(fr)
        flag = "  <-- INFRARED on the sensor" if abs(fr.mean() - 1) > 0.03 else ""
        lines.append(f"    {pos:18s}: {fr.mean():.3f} +/- {fr.std():.3f}{flag}")
    return ratios, {k: np.array(v) for k, v in f532.items()}, open_p


def combine_up_down(c):
    """Per current: mean of up/down, error, hysteresis %, rel std %, TEC."""
    out = {}
    for cur in np.unique(np.round(c["current_mA"], 2)):
        m = np.isclose(c["current_mA"], cur, atol=0.005)
        up = m & (c["direction"] == "up")
        dn = m & (c["direction"] == "down")
        p, s = c["P_mW"][m], c["P_std_mW"][m]
        pm = float(np.mean(p))
        err = float(np.sqrt(np.nanmean(s ** 2) / max(1, m.sum())))
        hyst = np.nan
        if up.any() and dn.any():
            pu, pd = float(np.mean(c["P_mW"][up])), float(np.mean(c["P_mW"][dn]))
            hyst = 100 * (pu - pd) / pm if pm else np.nan
            err = float(np.hypot(err, abs(pu - pd) / 2))
        rel = float(100 * np.nanmean(s / p)) if np.all(p > 0) else np.nan
        out[float(cur)] = dict(P=pm, err=err, hyst=hyst, rel=rel,
                               tec=float(np.nanmean(c["tec_C"][m]))
                               if np.isfinite(c["tec_C"][m]).any() else np.nan)
    return out


def main():
    cal_dir = cal_dir_from_argv()
    f_budget = FILE_BUDGET or latest("loss_budget_*.csv", cal_dir)
    f_sweep = FILE_SWEEP or latest("power_vs_current_before_objective_*.csv", cal_dir)
    f_laser = FILE_LASER or latest("power_vs_current_laser_output_*.csv", cal_dir)
    if not f_sweep:
        raise SystemExit(f"No power_vs_current_before_objective_*.csv in {cal_dir}: "
                         "run cal1_power_vs_current.py first.")
    lines = []

    t_obj, t_obj_err, f532_before = 1.0, 0.0, 1.0
    budget_open = {}
    if f_budget:
        ratios, f532, budget_open = summarise_budget(f_budget, lines)
        if ratios.get("objective T_obj", np.array([])).size:
            t_obj = float(ratios["objective T_obj"].mean())
            t_obj_err = float(ratios["objective T_obj"].std())
        if APPLY_IR_CORRECTION and "before_objective" in f532:
            f532_before = float(f532["before_objective"].mean())
    else:
        lines.append("NO LOSS BUDGET FOUND: T_obj = 1 (the table is then power "
                     "BEFORE the objective). Run cal1_loss_budget.py.")
    if T_OBJ_OVERRIDE is not None:
        t_obj, t_obj_err = float(T_OBJ_OVERRIDE), 0.0
        lines.append(f"T_obj overridden: {t_obj:.3f}")

    _, c = read_table(f_sweep)
    per = combine_up_down(c)
    cur = np.array(sorted(per))
    p_before = np.array([per[i]["P"] for i in cur])
    e_before = np.array([per[i]["err"] for i in cur])
    hyst = np.array([per[i]["hyst"] for i in cur])
    rel = np.array([per[i]["rel"] for i in cur])
    tec = np.array([per[i]["tec"] for i in cur])
    k = f532_before * t_obj
    p_sample = p_before * k
    e_sample = np.sqrt((e_before * k) ** 2 + (p_before * f532_before * t_obj_err) ** 2)

    # linear-extrapolated threshold from the upper part of the curve
    sel = p_before >= THRESH_FIT_FRAC * p_before.max()
    i_th, slope_eff = np.nan, np.nan
    if sel.sum() >= 2:
        slope_eff, icpt = np.polyfit(cur[sel], p_before[sel], 1)
        i_th = -icpt / slope_eff

    # path transmission vs current (before_objective / laser_output)
    coup = None
    if f_laser:
        _, cl = read_table(f_laser)
        pl = combine_up_down(cl)
        il = np.array(sorted(pl))
        pll = np.array([pl[i]["P"] for i in il])
        # only above threshold: below it both readings are ~0 and the ratio is noise
        lasing = p_before > 0.05 * p_before.max()
        inside = (cur >= il.min()) & (cur <= il.max()) & lasing
        inside &= np.interp(cur, il, pll) > 0
        if inside.any():
            ratio = p_before[inside] / np.interp(cur[inside], il, pll)
            coup = (cur[inside], ratio)

    with open(os.path.join(cal_dir, "power_calibration.csv"), "w") as f:
        f.write(f"# experiment=power_calibration\n# sweep={os.path.basename(f_sweep)}\n"
                f"# loss_budget={os.path.basename(f_budget) if f_budget else 'none'}\n"
                f"# T_obj={t_obj:.5f}\n# T_obj_err={t_obj_err:.5f}\n"
                f"# f532_before_objective={f532_before:.5f}\n")
        f.write("current_mA,P_sample_mW,P_sample_err_mW,P_before_mW,hysteresis_pct,"
                "rel_std_pct,tec_C\n")
        for row in zip(cur, p_sample, e_sample, p_before, hyst, rel, tec):
            f.write(",".join(f"{v:.6g}" for v in row) + "\n")

    lines += ["", f"POWER vs CURRENT ({os.path.basename(f_sweep)})",
              f"  P_sample = P_before x f532 ({f532_before:.3f}) x T_obj "
              f"({t_obj:.3f} +/- {t_obj_err:.3f})",
              "   I (mA)   P_before (mW)   P_sample (mW)    hyst %   std %   TEC C"]
    for row in zip(cur, p_before, p_sample, e_sample, hyst, rel, tec):
        lines.append("  {:7.2f}   {:12.4f}   {:9.4f}+/-{:<7.4f} {:7.2f} {:7.2f} {:7.2f}"
                     .format(*row))
    lines += [f"  linear-extrapolated threshold: {i_th:.1f} mA "
              f"(slope {slope_eff:.4f} mW/mA above {THRESH_FIT_FRAC:.0%} of max)",
              f"  max |hysteresis|: {np.nanmax(np.abs(hyst)):.2f} %"
              if np.isfinite(hyst).any() else "  (no down sweep: hysteresis not measured)"]
    if coup is not None:
        r = coup[1] / np.mean(coup[1])
        lines.append(f"  path ratio (before_objective / laser_output) vs current: "
                     f"varies by {100 * (r.max() - r.min()):.1f} % peak-to-peak"
                     + ("  <-- transmission depends on current (pointing, clipping"
                        " or coupling)" if r.max() - r.min() > 0.05 else ""))
    summary = "\n".join(lines)
    print(summary)
    with open(os.path.join(cal_dir, "power_calibration_summary.txt"), "w") as f:
        f.write(summary + "\n")

    fig, ax = plt.subplots(2, 3, figsize=(15, 8))
    a = ax[0, 0]
    for d, mk in (("up", "^"), ("down", "v")):
        m = c["direction"] == d
        if m.any():
            a.errorbar(c["current_mA"][m], c["P_mW"][m] * k, yerr=c["P_std_mW"][m] * k,
                       fmt=mk, ms=6, capsize=2, label=f"sweep {d}")
    a.plot(cur, p_sample, "-", color="0.4", lw=1)
    if np.isfinite(i_th):
        a.axvline(i_th, color="tab:red", ls=":", label=f"threshold ~{i_th:.1f} mA")
    a.set(xlabel="laser current (mA)", ylabel="power at the sample (mW)",
          title="(a) calibration: power at the sample")
    a.legend(fontsize=8)
    ax[0, 1].plot(cur, hyst, "o-")
    ax[0, 1].axhline(0, color="k", lw=0.8)
    ax[0, 1].set(xlabel="laser current (mA)", ylabel="(up - down) / mean (%)",
                 title="(b) hysteresis")
    ax[0, 2].plot(cur, rel, "s-", color="tab:purple")
    ax[0, 2].set(xlabel="laser current (mA)", ylabel="logged std / mean (%)",
                 title="(c) power fluctuation over the log")
    if coup is not None:
        ax[1, 0].plot(coup[0], coup[1] / np.mean(coup[1]), "o-", color="tab:green")
        ax[1, 0].set(title="(d) path: before_objective / laser_output")
    else:
        ax[1, 0].text(0.5, 0.5, "no laser_output sweep", ha="center",
                      transform=ax[1, 0].transAxes)
        ax[1, 0].set(title="(d) path transmission vs current")
    ax[1, 0].set(xlabel="laser current (mA)", ylabel="ratio / mean")
    ax[1, 0].ticklabel_format(axis="y", useOffset=False)
    ax[1, 1].plot(cur, tec, "o-", color="tab:orange")
    ax[1, 1].set(xlabel="laser current (mA)", ylabel="TEC temperature (C)",
                 title="(e) TEC temperature")
    a = ax[1, 2]
    if budget_open:
        chain = [p for p in CHAIN if any(k[0] == p for k in budget_open)]
        for c_i in sorted({cc for _, cc in budget_open}):
            a.plot(range(len(chain)), [budget_open.get((p, c_i), np.nan) for p in chain],
                   "o-", label=f"{c_i:.1f} mA")
        a.set_xticks(range(len(chain)), [s.replace("_", "\n") for s in chain], fontsize=8)
        a.set_yscale("log")
        a.legend(fontsize=8)
    a.set(ylabel="power (mW)", title="(f) loss budget")
    for x in ax.flat:
        x.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(cal_dir, "power_calibration.png")
    fig.savefig(out, dpi=150)
    print(f"\nSaved {os.path.join(cal_dir, 'power_calibration.csv')} and {out}")
    plt.show()


if __name__ == "__main__":
    main()
