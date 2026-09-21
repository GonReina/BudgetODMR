"""
Plot and fit the sweeps from smcv/odmr_power_sweep_dc_pc.py.

Fits ONE OR BOTH resonances simultaneously (set N_LINES). Fitting both beats
masking one out: no data is wasted, the outer wings give a genuine baseline,
overlapping tails are accounted for rather than contaminating the survivor, and
you get two independent Gamma(P) curves plus the splitting for free.

Model, for n lines on a sloping baseline:

        S(f) = b + m*(f - f_mid) - SUM_k A_k / (1 + ((f - f0_k)/hwhm_k)^2)

with FWHM_k = 2 * hwhm_k. This is a TRUE Lorentzian -- the DC measurement has no
modulation and no derivative, which is exactly why it is the reference for the
zero-power intercept.

Then per line:

        Gamma^2 = Gamma_0^2 + a * P_mw          (P_mw linear, mW)

so Gamma^2 against linear power is a straight line: intercept = unbroadened
linewidth, slope set by the Rabi coupling (Omega ~ sqrt(P_mw)).

On extracting Omega
-------------------
Linewidth alone does NOT give the Rabi frequency. The usual CW relation
(Dreau et al., PRB 84, 195204) is

        Gamma = Gamma_0 * sqrt(1 + Omega^2 / (Gamma_0 * Gamma_R))

which has a second unknown, the effective relaxation rate Gamma_R. So this
script reports Gamma_0 and the slope a honestly, plus a "broadening-equivalent"
sqrt(a*P) that becomes a true Rabi frequency only once a is calibrated -- by a
pulsed Rabi measurement, or by using the 2.16 MHz 14N hyperfine splitting as an
absolute ruler. If Gamma_0 comes out below ~2.16 MHz you should be able to
resolve that triplet at low power, which gives you the ruler.

>>> WINDOW WIDTH <<<
A Lorentzian fit needs baseline on both sides -- aim for +/- 3*Gamma_max beyond
the outermost line. The script warns when the window is too tight.

>>> AMPLIFIER COMPRESSION <<<
If the amplifier saturates, the power at the antenna does not follow the power
you set and you are fitting the amplifier, not the NV centres. A curved panel
(b) is the tell.

Run:  python plot_power_sweep_dc.py [data_dir]
"""

import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

from powersweep_common import (read_sweep, power_from_name, smooth,
                               save_raw_plot, broadening_fit)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "smcv"))
from expconfig import load_config

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
N_LINES          = 2       # number of RESONANCES (not hyperfine components)
LINE_CENTERS_MHZ = None    # None -> auto-detect; else e.g. (2864.0, 2884.0)
FIT_LO_MHZ       = None    # None -> use the whole sweep
FIT_HI_MHZ       = None
SUBDIR = "power_sweep_dc"

# 14N hyperfine: fit each resonance as a 1:1:1 triplet at f0-A, f0, f0+A with a
# SHARED width and amplitude. Recovers the TRUE component width even when the
# triplet is unresolved -- a single Lorentzian just returns the envelope.
HYPERFINE    = True
HF_SPLIT_MHZ = None        # None -> FIT the splitting (expect ~2.16 MHz)

RAW_PLOTS = True           # also save a fit-free figure per power
ERRORBAR  = "sem"          # 'sem' (sigma/sqrt(N)) or 'std'

TARGET_FWHM_PREC = 0.02    # want sigma(Gamma)/Gamma <= 2 %
HYPERFINE_MHZ = 2.16
GAMMA_MHZ_PER_MT = 28.024

N_FIXED = 2                # baseline b, slope m
FIT_HF = HYPERFINE and HF_SPLIT_MHZ is None


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
def hf_offsets(p):
    """Frequency offsets of the hyperfine components."""
    if not HYPERFINE:
        return (0.0,)
    a = p[N_FIXED + 3 * N_LINES] if FIT_HF else HF_SPLIT_MHZ
    return (-a, 0.0, a)


def lorentz_dips(f, *p):
    """Sloping baseline minus Lorentzian dips.

    p = [b, m, (amp, f0, hwhm) * N_LINES, (A_hf if fitted)].
    Each resonance contributes 1 or 3 (hyperfine) components of equal amplitude
    and width. FWHM_k = 2 * hwhm_k is the width of a SINGLE component.
    """
    f = np.asarray(f, dtype=float)
    y = p[0] + p[1] * (f - f.mean())
    offs = hf_offsets(p)
    for k in range(N_LINES):
        amp, f0, hw = p[N_FIXED + 3 * k: N_FIXED + 3 * k + 3]
        for o in offs:
            y = y - amp / (1.0 + ((f - f0 - o) / hw) ** 2)
    return y


def find_lines_dc(fr, sig, n_lines):
    """The n most prominent dips -> (centres, rough FWHMs)."""
    sm = smooth(sig)
    step = fr[1] - fr[0]
    span = sm.max() - sm.min()
    pk, props = find_peaks(-sm, prominence=0.05 * span,
                           distance=max(1, int(round(1.0 / step))))
    if pk.size < n_lines:
        raise RuntimeError(f"found {pk.size} dips, need {n_lines}")
    keep = np.sort(pk[np.argsort(props["prominences"])[::-1][:n_lines]])
    centers = [float(fr[i]) for i in keep]
    # crude width: prominence-based half-depth crossing
    widths = []
    base = float(np.percentile(sm, 90))
    for i in keep:
        half = 0.5 * (base + sm[i])
        lo = i
        while lo > 0 and sm[lo] < half:
            lo -= 1
        hi = i
        while hi < len(sm) - 1 and sm[hi] < half:
            hi += 1
        widths.append(max((fr[hi] - fr[lo]), 4 * step))
    return centers, widths


def build_mask(fr):
    m = np.ones(fr.shape, dtype=bool)
    if FIT_LO_MHZ is not None:
        m &= fr >= FIT_LO_MHZ
    if FIT_HI_MHZ is not None:
        m &= fr <= FIT_HI_MHZ
    return m


def fit_one(fr, sig, centers_hint, widths_hint):
    """Fit the n-line Lorentzian-dip model (multi-start over width scale)."""
    mask = build_mask(fr)
    if mask.sum() < 8 * N_LINES:
        raise RuntimeError("too few points inside the fit window")
    x, y = fr[mask], sig[mask]

    b0 = float(np.percentile(y, 90))
    amp0 = max(b0 - float(np.min(y)), 1e-12)
    span = x[-1] - x[0]

    lo = [-np.inf, -np.inf]
    hi = [np.inf, np.inf]
    for _ in range(N_LINES):
        lo += [0.0, x.min(), 1e-4]
        hi += [np.inf, x.max(), span]
    if FIT_HF:
        lo += [1.0]
        hi += [4.0]

    best = None
    for w_scale in (0.5, 1.0, 2.0):
        p0 = [b0, 0.0]
        for f0h, wh in zip(centers_hint, widths_hint):
            p0 += [amp0, float(np.clip(f0h, x.min(), x.max())),
                   float(np.clip(wh * w_scale / 2, 1e-3, 0.5 * span))]
        if FIT_HF:
            p0 += [HYPERFINE_MHZ]
        try:
            popt, pcov = curve_fit(lorentz_dips, x, y, p0=p0, bounds=(lo, hi),
                                   maxfev=60000)
        except Exception:
            continue
        chi = float(np.sum((y - lorentz_dips(x, *popt)) ** 2))
        if best is None or chi < best[0]:
            best = (chi, popt, pcov)

    if best is None:
        raise RuntimeError("all fit seeds failed to converge")
    _, popt, pcov = best
    perr = np.sqrt(np.diag(pcov))

    idx = np.argsort([popt[N_FIXED + 3 * k + 1] for k in range(N_LINES)])
    lines = []
    for k in idx:
        amp, f0, hw = popt[N_FIXED + 3 * k: N_FIXED + 3 * k + 3]
        lines.append(dict(amp=amp, f0=f0, g=2 * hw,
                          gerr=2 * perr[N_FIXED + 3 * k + 2],
                          contrast=amp / popt[0] * 100 if popt[0] else np.nan))
    a_hf = (popt[N_FIXED + 3 * N_LINES] if FIT_HF
            else (HF_SPLIT_MHZ if HYPERFINE else np.nan))
    return dict(b=popt[0], m=popt[1], lines=lines, popt=popt, mask=mask,
                a_hf=a_hf)


# ---------------------------------------------------------------------------
def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else load_config()["paths"]["data_dir"]
    in_dir = os.path.join(data_dir, SUBDIR)
    fig_dir = os.path.join(in_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    # Sort by the PARSED power: filenames carrying negative powers do not sort
    # lexicographically ("-1.50" would come before "-15.00").
    files = sorted(glob.glob(os.path.join(in_dir, "sweep_*dBm.csv")),
                   key=power_from_name)
    if not files:
        raise SystemExit(f"No sweep_*dBm.csv in {in_dir} -- "
                         f"run smcv/odmr_power_sweep_dc_pc.py first.")
    print(f"{len(files)} sweeps in {in_dir}, fitting {N_LINES} resonance(s)")

    # Seed the line positions ONCE. Try the LOWEST powers first: the lines are
    # narrowest there and therefore best separated. At high power two lines can
    # merge into a single broad feature that no peak-finder will split.
    if LINE_CENTERS_MHZ is not None:
        centers0 = list(LINE_CENTERS_MHZ)[:N_LINES]
        widths0 = [5.0] * N_LINES
        print("  seed centres (from LINE_CENTERS_MHZ): "
              + ", ".join(f"{c:.2f} MHz" for c in centers0))
    else:
        centers0 = widths0 = None
        for cand in files:
            try:
                frc, sigc, _, _ = read_sweep(cand)
                centers0, widths0 = find_lines_dc(frc, sigc, N_LINES)
                print(f"  seed centres (from {os.path.basename(cand)}): "
                      + ", ".join(f"{c:.2f} MHz" for c in centers0))
                break
            except Exception:
                continue
        if centers0 is None:
            raise SystemExit(
                f"Could not auto-detect {N_LINES} resonance(s) in any sweep. "
                f"Set LINE_CENTERS_MHZ explicitly, or lower N_LINES.")

    rows = []
    hf_vals = []
    for path in files:
        p = power_from_name(path)
        fr, sig, std, meta = read_sweep(path)
        n_avg = int(float(meta.get("n_avg", 1)))

        if RAW_PLOTS:
            save_raw_plot(os.path.join(fig_dir, f"raw_{p:05.2f}dBm.png"),
                          fr, sig, std, p, n_avg, "PL$_{on}$/PL$_{off}$",
                          errorbar=ERRORBAR)

        try:
            res = fit_one(fr, sig, centers0, widths0)
        except Exception as e:
            print(f"  {p:+5.1f} dBm  FIT FAILED ({e})")
            continue
        if FIT_HF and np.isfinite(res["a_hf"]):
            hf_vals.append(res["a_hf"])

        row = dict(p=p, n_avg=n_avg, popt=res["popt"], mask=res["mask"],
                   path=path)
        parts, worst = [], 0.0
        for j, l in enumerate(res["lines"], start=1):
            prec = l["gerr"] / l["g"] if l["g"] else np.nan
            worst = max(worst, prec if prec == prec else 0.0)
            row[f"f{j}"] = l["f0"]; row[f"g{j}"] = l["g"]
            row[f"e{j}"] = l["gerr"]; row[f"pr{j}"] = prec
            row[f"c{j}"] = l["contrast"]
            parts.append(f"L{j}: f0={l['f0']:8.2f} G={l['g']:6.3f}"
                         f"+/-{l['gerr']:5.3f} ({100*prec:4.1f}%) "
                         f"C={l['contrast']:4.2f}%")
        row["n_need"] = n_avg * (worst / TARGET_FWHM_PREC) ** 2
        if N_LINES == 2:
            row["split"] = row["f2"] - row["f1"]
        rows.append(row)

        gmax = max(row[f"g{j}"] for j in range(1, N_LINES + 1))
        edge = min(min(row[f"f{j}"] - fr.min(), fr.max() - row[f"f{j}"])
                   for j in range(1, N_LINES + 1))
        flag = "  [WINDOW TOO NARROW]" if edge < 3 * gmax else ""
        print(f"  {p:+5.1f} dBm  " + "  ".join(parts) + flag)

    if len(rows) < 3:
        raise SystemExit("Fewer than 3 successful fits -- nothing to trend.")

    powers = np.array([r["p"] for r in rows])

    for r in rows:
        fr, sig, _, _ = read_sweep(r["path"])
        fig, ax = plt.subplots(figsize=(7.5, 4))
        ax.plot(fr, sig, ".", ms=3, color="0.6", label="data")
        xf = np.linspace(fr[r["mask"]].min(), fr[r["mask"]].max(), 1200)
        ax.plot(xf, lorentz_dips(xf, *r["popt"]), "-", lw=1.6, color="C3",
                label="fit")
        for j, col in zip(range(1, N_LINES + 1), ("C2", "C0")):
            ax.axvline(r[f"f{j}"], color=col, ls="--", lw=1,
                       label=f"L{j}: {r[f'f{j}']:.2f} MHz, "
                             f"$\\Gamma$={r[f'g{j}']:.2f} MHz")
        ax.set(xlabel="MW frequency [MHz]", ylabel="PL$_{on}$/PL$_{off}$",
               title=f"DC ODMR, {r['p']:+.1f} dBm")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(os.path.join(fig_dir, f"sweep_{r['p']:05.2f}dBm.png"), dpi=140)
        plt.close(fig)

    print(f"\nGamma^2 = Gamma_0^2 + a * P_mw")
    fits = {}
    for j in range(1, N_LINES + 1):
        g = np.array([r[f"g{j}"] for r in rows])
        ge = np.array([r[f"e{j}"] for r in rows])
        g0, a, p_mw = broadening_fit(powers, g, ge)
        fits[j] = dict(g0=g0, a=a, g=g, ge=ge, p_mw=p_mw)
        om = np.sqrt(max(a, 0) * p_mw[-1])
        print(f"  line {j}: Gamma_0 = {g0:.3f} MHz   a = {a:.4g} MHz^2/mW   "
              f"equiv. Omega at {powers[-1]:+.1f} dBm = {om:.2f} MHz")
        if g0 < HYPERFINE_MHZ:
            print(f"    Gamma_0 < {HYPERFINE_MHZ} MHz -- the 14N triplet should be "
                  f"resolvable at low power; use it as an absolute ruler.")
    if HYPERFINE:
        if FIT_HF and hf_vals:
            hv = np.array(hf_vals)
            print(f"\n14N HYPERFINE: A = {np.mean(hv):.3f} +/- {np.std(hv):.3f} MHz "
                  f"(literature {HYPERFINE_MHZ} MHz)")
            off = abs(np.mean(hv) - HYPERFINE_MHZ) / HYPERFINE_MHZ
            if off < 0.10:
                print("  -> agrees with the literature value. That is a real "
                      "detection AND an absolute calibration of your frequency "
                      "axis; use it as the ruler for the Rabi conversion.")
            else:
                print(f"  -> {100*off:.0f} % off the literature value. The triplet "
                      f"is probably unresolved, so A is unconstrained. Compare "
                      f"against a run with HYPERFINE = False.")
        else:
            print(f"\n14N HYPERFINE: A pinned at {HF_SPLIT_MHZ} MHz")
        print("  Widths above are per COMPONENT, not the triplet envelope.")

    if N_LINES == 2:
        da = abs(fits[1]["a"] - fits[2]["a"]) / max(abs(fits[1]["a"]), 1e-12)
        print(f"  consistency: |dGamma_0| = "
              f"{abs(fits[1]['g0']-fits[2]['g0']):.3f} MHz, slopes differ by "
              f"{100*da:.0f} %")
        if da > 0.25:
            print("    -> the two transitions are NOT broadening together. "
                  "Suspect different NV orientations or B1 inhomogeneity.")

        split = np.array([r["split"] for r in rows])
        b_mt = split / (2 * GAMMA_MHZ_PER_MT)
        print(f"\nSPLITTING: {np.mean(split):.3f} +/- {np.std(split):.3f} MHz "
              f"-> B_NV = {np.mean(b_mt):.4f} mT")
        drift = float(np.ptp(split))
        print(f"  drift across the power scan: {drift:.3f} MHz "
              f"({drift/(2*GAMMA_MHZ_PER_MT)*1e3:.1f} uT)")
        if drift > 0.05 * np.mean(split):
            print("  -> the splitting moved during the run. Magnet or temperature "
                  "drift; re-run faster or interleave powers.")

    nn = np.array([r["n_need"] for r in rows])
    prs = np.array([max(r[f"pr{j}"] for j in range(1, N_LINES + 1)) for r in rows])
    print(f"\nAVERAGING ADVISOR (target sigma(Gamma)/Gamma <= "
          f"{100*TARGET_FWHM_PREC:.0f} %)")
    print(f"  achieved (worst line): best {100*np.nanmin(prs):.1f} %, "
          f"worst {100*np.nanmax(prs):.1f} %")
    print(f"  N_AVG needed: median {int(np.ceil(np.nanmedian(nn)))}, "
          f"worst-case {int(np.ceil(np.nanmax(nn)))}")

    ncol = 4 if N_LINES == 2 else 3
    fig, axes = plt.subplots(1, ncol, figsize=(4.8 * ncol, 4.2))
    ax1, ax2, ax3 = axes[0], axes[1], axes[2]
    pg = np.linspace(powers.min(), powers.max(), 300)
    for j, col in zip(range(1, N_LINES + 1), ("C0", "C1")):
        d = fits[j]
        ax1.errorbar(powers, d["g"], yerr=d["ge"], fmt="o", ms=4, capsize=2,
                     color=col, label=f"line {j}")
        ax1.plot(pg, np.sqrt(d["g0"] ** 2 + d["a"] * 10 ** (pg / 10.0)), "-",
                 lw=1.3, color=col, alpha=0.7)
        ax2.errorbar(d["p_mw"], d["g"] ** 2, yerr=2 * d["g"] * d["ge"], fmt="o",
                     ms=4, capsize=2, color=col,
                     label=f"L{j}: $\\Gamma_0$={d['g0']:.2f}, a={d['a']:.3g}")
        ax2.plot(d["p_mw"], d["g0"] ** 2 + d["a"] * d["p_mw"], "-", lw=1.3,
                 color=col, alpha=0.7)
        ax3.plot(powers, [r[f"c{j}"] for r in rows], "o-", ms=4, lw=1, color=col,
                 label=f"line {j}")
    ax1.axhline(HYPERFINE_MHZ, color="C2", ls="--", lw=1,
                label=f"$^{{14}}$N {HYPERFINE_MHZ} MHz")
    ax1.set(xlabel="MW power [dBm]", ylabel="FWHM [MHz]",
            title="(a) Power broadening")
    ax1.legend(fontsize=7); ax1.grid(alpha=0.3)
    ax2.set(xlabel="MW power [mW, linear]", ylabel=r"FWHM$^2$ [MHz$^2$]",
            title="(b) Linearity check")
    ax2.legend(fontsize=7); ax2.grid(alpha=0.3)
    ax3.set(xlabel="MW power [dBm]", ylabel="contrast [%]",
            title="(c) Contrast vs power")
    ax3.legend(fontsize=7); ax3.grid(alpha=0.3)

    if N_LINES == 2:
        ax4 = axes[3]
        ax4.plot(powers, split, "o-", ms=4, lw=1, color="C6")
        ax4.axhline(float(np.mean(split)), color="0.5", ls=":", lw=1,
                    label=f"mean {np.mean(split):.2f} MHz "
                          f"({np.mean(b_mt):.3f} mT)")
        ax4.set(xlabel="MW power [dBm]", ylabel="splitting [MHz]",
                title="(d) Splitting / field stability")
        ax4.legend(fontsize=8); ax4.grid(alpha=0.3)

    fig.suptitle("DC (unmodulated) ODMR power broadening", y=1.0)
    fig.tight_layout()
    out = os.path.join(in_dir, "power_broadening_dc.png")
    fig.savefig(out, dpi=150)
    print(f"\nSaved {out}\nPer-sweep figures in {fig_dir}")

    with open(os.path.join(in_dir, "fwhm_vs_power_dc.csv"), "w") as f:
        f.write("# DC ODMR power broadening\n")
        for j in range(1, N_LINES + 1):
            f.write(f"# line{j}: Gamma_0_MHz={fits[j]['g0']:.5f} "
                    f"a_MHz2_per_mW={fits[j]['a']:.6g}\n")
        cols = "power_dBm,power_mW"
        for j in range(1, N_LINES + 1):
            cols += (f",f0_{j}_MHz,fwhm_{j}_MHz,fwhm_err_{j}_MHz,"
                     f"contrast_{j}_pct")
        cols += ",splitting_MHz" if N_LINES == 2 else ""
        f.write(cols + ",n_avg_used,n_avg_needed\n")
        for r in rows:
            line = f"{r['p']:.2f},{10**(r['p']/10):.5f}"
            for j in range(1, N_LINES + 1):
                line += (f",{r[f'f{j}']:.5f},{r[f'g{j}']:.5f},"
                         f"{r[f'e{j}']:.5f},{r[f'c{j}']:.4f}")
            if N_LINES == 2:
                line += f",{r['split']:.5f}"
            line += f",{r['n_avg']},{r['n_need']:.1f}"
            f.write(line + "\n")

    print("\nIf panel (b) is NOT a straight line, suspect amplifier compression "
          "before suspecting the physics.")


if __name__ == "__main__":
    main()
