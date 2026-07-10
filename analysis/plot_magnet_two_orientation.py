"""
Magnet-scan field analysis with the TWO-orientation NV Hamiltonian, fitting two
models to every magnet position and comparing them:

  * SIMPLE  model  -- splitting due to the field only (Zeeman): fit_field_axes.
                      Parameters (|B|, theta, phi, D, linewidth, amp, baseline).
  * COMPLEX model  -- additionally accounts for the 14N hyperfine triplet (a_hf ~
                      2.16 MHz, each line splits into three -- a KNOWN constant) and
                      transverse strain E: fit_field_axes_ext.

Strain caveat: with only two orientations at low field, strain E and the transverse
field split the lines the same way, so a free per-position E is NOT identifiable (it
just trades off against |B|). Strain is a property of the diamond spot -- constant
across a magnet scan -- so measure it once from a near-zero-field spectrum (where the
split is 2E) and set E_FIXED_MHZ; the complex model then holds E fixed and differs
from the simple model by the (identifiable) hyperfine structure plus that fixed strain.
Set FIT_STRAIN=True only if you accept the |B|/E trade-off.

For each position it:
  1. loads the FM spectrum and takes the Hilbert ENVELOPE (clean, all-positive),
  2. fits both models (restricted to AXES, two <111> orientations),
  3. reports |B| from each model, plus E and the linewidths,
  4. saves a per-position plot (raw, envelope, simple fit, complex fit).
Then it plots |B| vs position for both models, E vs position, and linewidth vs
position.

Interpretation: with only two orientations |B| is weakly constrained (the field
sets the line positions but the magnitude is soft), and at low field E and the
transverse field trade off -- so compare the two models rather than trusting either
|B| blindly. The COMPLEX model is worth it when the lines are narrow enough to show
strain asymmetry or resolved hyperfine structure; otherwise the SIMPLE model is the
cleaner readout.

Run on the PC:  python plot_magnet_two_orientation.py   (numpy + matplotlib; scipy for the fits)
"""

import csv
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "smcv"))
from expconfig import load_config
import nv_odmr_sim as nv

# ===== CONFIGURATION =====
MODE = "fm"                  # data folder: <magnet.out_dir>_<MODE>
AXES = (0, 1, 2)                # which NV orientations to fit (two-orientation model)
A_HF_MHZ = 2.16              # 14N hyperfine spacing for the complex model (0 disables it)
DO_COMPLEX = True            # also fit the strain + hyperfine model
E_FIXED_MHZ = 0.0            # strain E held fixed for the complex model (measure at ~B=0)
FIT_STRAIN = False           # let E float per position (NOT identifiable vs B -- see note)
SMOOTH_ENV_PTS = 5           # envelope smoothing before fitting

_cfg = load_config()
BASE = _cfg["magnet"]["out_dir"] + "_" + MODE
INDEX = os.path.join(BASE, "magnet_index.csv")
OUT_DIR = os.path.join(BASE, "analysis_two_orientation")
GAMMA = _cfg["analysis"]["gamma_mhz_per_mt"]
D_CENTRE = _cfg["analysis"]["d_center_mhz"]
MIN_SEP = _cfg["analysis"]["min_sep_mhz"]


def hilbert_envelope(y):
    """|analytic signal| via numpy FFT (no scipy). The fast-fluctuating FM lock-in
    signal has a slow, all-positive envelope peaking at the resonance centres."""
    base = np.median(y)
    x = np.asarray(y, float) - base
    n = len(x)
    X = np.fft.fft(x)
    h = np.zeros(n)
    if n % 2 == 0:
        h[0] = h[n // 2] = 1.0
        h[1:n // 2] = 2.0
    else:
        h[0] = 1.0
        h[1:(n + 1) // 2] = 2.0
    env = np.abs(np.fft.ifft(X * h))
    if SMOOTH_ENV_PTS > 1:
        env = np.convolve(env, np.ones(SMOOTH_ENV_PTS) / SMOOTH_ENV_PTS, mode="same")
    return env


def seed_b(x, env):
    """|B| seed from the widest pair of envelope peaks (axial-projection lower bound)."""
    b = np.median(env)
    h = env - b
    cand = [i for i in range(1, len(env) - 1)
            if h[i] > 0 and h[i] >= h[i - 1] and h[i] > h[i + 1]]
    cand.sort(key=lambda i: -h[i])
    picks = []
    for i in cand:
        if all(abs(x[i] - x[j]) >= MIN_SEP for j in picks):
            picks.append(i)
        if len(picks) >= 4:
            break
    picks.sort()
    if len(picks) >= 2:
        return max((x[picks[-1]] - x[picks[0]]) / (2 * GAMMA), 0.05)
    return 0.3


def load_index():
    rows = []
    with open(INDEX) as f:
        for r in csv.DictReader(f):
            rows.append((float(r["position"]), r["units"], r["filename"]))
    rows.sort(key=lambda t: t[0])
    return rows


def load_spec(fname):
    x, y = [], []
    for r in csv.reader(open(os.path.join(BASE, fname))):
        if not r or r[0].startswith("#") or r[0].startswith("freq"):
            continue
        x.append(float(r[0]))
        y.append(float(r[1]))
    return np.array(x), np.array(y)


def main():
    if not os.path.exists(INDEX):
        raise SystemExit(f"No magnet_index.csv in {BASE} (is MODE right / scan done?)")
    os.makedirs(OUT_DIR, exist_ok=True)
    index = load_index()
    units = index[0][1]
    print(f"{len(index)} position(s) in {BASE}; axes {AXES}; centre {D_CENTRE:.0f} MHz")

    positions, b_simple, b_complex = [], [], []
    e_vals, fw_simple, fw_complex = [], [], []
    for pos, _u, fname in index:
        x, y = load_spec(fname)
        env = hilbert_envelope(y)
        bg = seed_b(x, env)

        fs = nv.fit_field_axes(x, env, axes_idx=AXES, b_mag_guess_mT=bg, D=D_CENTRE)
        if fs is None:
            raise SystemExit("scipy is required for the fits (pip install scipy).")
        fc = nv.fit_field_axes_ext(x, env, axes_idx=AXES, b_mag_guess_mT=bg,
                                   D=D_CENTRE, a_hf=A_HF_MHZ, E=E_FIXED_MHZ,
                                   fit_E=FIT_STRAIN) if DO_COMPLEX else None

        Bs = fs["B_mT"]
        Bc = fc["B_mT"] if fc else np.nan
        E = fc["E_MHz"] if fc else np.nan
        positions.append(pos)
        b_simple.append(Bs)
        b_complex.append(Bc)
        e_vals.append(E)
        fw_simple.append(fs["fwhm_MHz"])
        fw_complex.append(fc["fwhm_MHz"] if fc else np.nan)
        msg = f"  pos {pos:>7} {units}: |B|_simple={Bs:.3f}"
        if fc:
            msg += f"  |B|_complex={Bc:.3f}  E={E:.2f} MHz"
        print(msg + " mT")

        # per-position plot
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(x, y, lw=0.6, color="0.8", label=f"{MODE} raw")
        ax.plot(x, env, lw=1.3, color="tab:blue", label="Hilbert envelope")
        ax.plot(x, fs["fit_curve"], lw=1.5, color="tab:green",
                label=f"simple (Zeeman)  |B|={Bs:.3f} mT")
        if fc:
            ax.plot(x, fc["fit_curve"], lw=1.5, color="tab:red", ls="--",
                    label=f"complex (E+HF)  |B|={Bc:.3f} mT, E={E:.2f}")
        ax.axvline(D_CENTRE, color="tab:orange", ls=":", lw=1)
        ax.set_xlabel("Microwave frequency (MHz)")
        ax.set_ylabel(f"lock-in {MODE}")
        ax.set_title(f"{pos} {units}   two-orientation fit (axes {AXES})")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, f"twofit_pos_{pos:g}{units}.png"), dpi=130)
        plt.close(fig)

    if not positions:
        raise SystemExit("No valid positions found.")

    # ---- |B| vs position ----
    figB, axB = plt.subplots(figsize=(8, 5))
    axB.plot(positions, b_simple, "o-", color="tab:green", label="|B| simple (Zeeman)")
    if DO_COMPLEX and np.any(~np.isnan(b_complex)):
        axB.plot(positions, b_complex, "s--", color="tab:red",
                 label="|B| complex (E + hyperfine)")
    axB.set_xlabel(f"Magnet position ({units})")
    axB.set_ylabel("Field magnitude |B| (mT)")
    axB.set_title(f"Two-orientation |B| vs magnet position ({MODE})")
    axB.legend()
    axB.grid(True, alpha=0.3)
    figB.tight_layout()
    figB.savefig(os.path.join(OUT_DIR, "field_vs_position.png"), dpi=140)

    # ---- E vs position (only meaningful if E was actually fitted) ----
    if DO_COMPLEX and FIT_STRAIN and np.any(~np.isnan(e_vals)):
        figE, axE = plt.subplots(figsize=(8, 5))
        axE.plot(positions, e_vals, "^-", color="tab:purple")
        axE.set_xlabel(f"Magnet position ({units})")
        axE.set_ylabel("Strain / E parameter (MHz)")
        axE.set_title(f"Fitted strain E vs magnet position ({MODE})")
        axE.grid(True, alpha=0.3)
        figE.tight_layout()
        figE.savefig(os.path.join(OUT_DIR, "strain_vs_position.png"), dpi=140)

    # ---- linewidth vs position ----
    figW, axW = plt.subplots(figsize=(8, 5))
    axW.plot(positions, fw_simple, "o-", color="tab:green", label="FWHM simple")
    if DO_COMPLEX and np.any(~np.isnan(fw_complex)):
        axW.plot(positions, fw_complex, "s--", color="tab:red", label="FWHM complex")
    axW.set_xlabel(f"Magnet position ({units})")
    axW.set_ylabel("Fitted linewidth FWHM (MHz)")
    axW.set_title(f"Linewidth vs magnet position ({MODE})")
    axW.legend()
    axW.grid(True, alpha=0.3)
    figW.tight_layout()
    figW.savefig(os.path.join(OUT_DIR, "linewidth_vs_position.png"), dpi=140)

    print(f"\nSaved per-position + summary plots to {OUT_DIR}")
    plt.show()


if __name__ == "__main__":
    main()
