"""
LASER RELATIVE INTENSITY NOISE (RIN) -- does balanced detection help us?

Purpose: decide, BEFORE buying a second photodetector, whether the in-band
noise of our detection chain is dominated by

    (a) electronics / dark        -> constant, independent of light level
    (b) photon shot noise         -> grows as sqrt(optical power)
    (c) laser intensity noise     -> grows PROPORTIONALLY to optical power

Only (c) is correlated between two detectors, so only (c) is removed by
balanced / ratiometric detection. If the noise is shot-limited, a second
detector makes things sqrt(2) WORSE and the money should go to collecting
more photons instead.

Method: shine an attenuated sample of the laser on the photodiode (IN1) and
record raw traces at several optical power levels. At each level extract the
noise amplitude spectral density at F_MOD. The three contributions separate
because they scale differently with the DC photodiode voltage V:

    sigma_V(f_mod)^2  =  a^2  +  b^2 * V  +  c^2 * V^2
                         ^^^     ^^^^^^^     ^^^^^^^^
                    electronics    shot     laser RIN       (RIN = c^2, 1/Hz)

A beam-blocked "dark" record measures a directly, so the fit is reduced to the
two remaining terms and is well conditioned.

  ** SAFETY / HARDWARE **
  Attenuate HARD before pointing the beam at the detector: 40 mW on a PDA10A2
  will saturate it and can damage it. Use a weak reflection off a glass slide,
  a diffuse bounce off a white card, or ND filters, and check the DC level
  reported after the first step. The script warns if any record exceeds
  CLIP_WARN_V. No microwaves are used or required.

  Vary the ATTENUATION between steps, never the laser diode current: changing
  the current changes the laser's own noise, which is the quantity we are
  trying to measure.

Usage (on the PC):
    python laser_rin_pc.py             # acquire (interactive) + analyse
    python laser_rin_pc.py analyse     # re-analyse the saved .npz only
    python laser_rin_pc.py selftest    # no hardware: verify the fit on
                                       # synthetic data of known a, b, c

Outputs in <DATA_DIR>: laser_rin.npz, laser_rin.csv, laser_rin.png,
                       laser_rin_summary.txt
"""

import os
import sys
from datetime import datetime

import numpy as np

from lockin_common import (RedPitayaLockin, RP_IP, RP_PORT, RP_GAIN,
                           F_MOD, DATA_DIR)
from odmr_sensitivity_fm_pc import welch_asd

# --- settings ---------------------------------------------------------------
DECIM        = 1024      # fs = 122.07 kHz, 134 ms/record; Nyquist 61 kHz
N_REC        = 10        # records per power level
BAND_FRAC    = 0.10      # average the ASD over f_mod +/- 10 %
CLIP_WARN_V  = 4.0       # warn if the DC level exceeds this (detector range)
MIN_LEVELS   = 4         # minimum number of power levels for a meaningful fit

# Working point of the REAL experiment: the photodiode DC level (volts) seen
# with the laser on and the NV photoluminescence on the detector. Set this to
# your measured value -- the verdict is evaluated at this level.
V_PL_WORKING = 1.0

# Transimpedance gain of the detector in use [V/A], from its datasheet.
# Optional: if set (not None), the fitted shot term is compared with theory.
TRANSIMPEDANCE_V_PER_A = None

FS = 125e6 / DECIM
NPZ = os.path.join(DATA_DIR, "laser_rin.npz")
Q_E = 1.602176634e-19


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------
def record_level(rp, label):
    """N_REC raw records at the current attenuation. Returns (traces, V_dc)."""
    traces = []
    for _ in range(N_REC):
        traces.append(rp.scope.acquire((1,), DECIM, RP_GAIN, fill_timeout_s=5.0))
    traces = np.array(traces)
    v_dc = float(np.mean(traces))
    if np.max(np.abs(traces)) > CLIP_WARN_V:
        print(f"  WARNING: |V| reaches {np.max(np.abs(traces)):.2f} V -- the "
              "detector may be saturating/clipping. Attenuate more.")
    print(f"  [{label}] DC = {v_dc * 1e3:8.2f} mV   "
          f"(pk-pk {np.ptp(traces) * 1e3:.2f} mV)")
    return traces, v_dc


def acquire():
    stamp = datetime.now().isoformat(timespec="seconds")
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"LASER RIN measurement: fs = {FS:.0f} Hz, "
          f"{16384 / FS * 1e3:.0f} ms/record, {N_REC} records/level, "
          f"analysing at f_mod = {F_MOD:.0f} Hz")
    print("Attenuate the beam BEFORE it reaches the detector. Vary attenuation "
          "between steps, NOT the diode current.\n")

    rp = RedPitayaLockin(RP_IP, RP_PORT)
    labels, traces, vdcs = [], [], []
    dark = None
    try:
        input("DARK step: block the beam completely, then press Enter... ")
        dark, _ = record_level(rp, "dark")

        print("\nNow step through optical power levels. Aim for 5-8 levels "
              "spanning roughly 0.1x to 2x your working level "
              f"({V_PL_WORKING * 1e3:.0f} mV).")
        while True:
            s = input("\nSet the attenuation, give it a label "
                      "(e.g. 'ND1.0', 'glass', 'iris half'), or 'q' to "
                      "finish: ").strip()
            if s.lower() in ("q", "quit", "done", ""):
                break
            tr, v = record_level(rp, s)
            labels.append(s)
            traces.append(tr)
            vdcs.append(v)
    finally:
        rp.close()

    if not vdcs:
        raise SystemExit("No power levels recorded - nothing to analyse.")
    if len(vdcs) < MIN_LEVELS:
        print(f"\nOnly {len(vdcs)} level(s) recorded; {MIN_LEVELS} or more are "
              "needed to separate the three terms. Saving anyway.")
    np.savez(NPZ, stamp=stamp, fs=FS, f_mod=F_MOD, labels=np.array(labels),
             traces=np.array(traces), v_dc=np.array(vdcs), dark=dark,
             v_pl_working=V_PL_WORKING)
    print(f"\nSaved raw data -> {NPZ}")
    return NPZ


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def asd_of(records, fs, n_seg=6):
    """Power-averaged ASD over several records. Returns (freq, asd)."""
    psds, fr = [], None
    for v in np.atleast_2d(records):
        fr, a = welch_asd(v - np.mean(v), 1.0 / fs, n_seg=n_seg)
        psds.append(a ** 2)
    return fr, np.sqrt(np.mean(psds, axis=0))


def band_median(fr, asd, f0, frac=BAND_FRAC):
    band = (fr >= f0 * (1 - frac)) & (fr <= f0 * (1 + frac))
    if not band.any():
        return float(asd[int(np.argmin(np.abs(fr - f0)))])
    return float(np.median(asd[band]))


def fit_terms(v_dc, sigma, a_dark=None):
    """Fit sigma^2 = a^2 + b^2 V + c^2 V^2 with relative (not absolute)
    residuals, since sigma^2 spans decades. If a_dark is given it is held
    fixed and only the shot and RIN terms are fitted."""
    v_dc, sigma = np.asarray(v_dc, float), np.asarray(sigma, float)
    y = sigma ** 2
    if a_dark is not None:
        y_fit = y - a_dark ** 2
        A = np.column_stack([v_dc, v_dc ** 2])
    else:
        y_fit = y
        A = np.column_stack([np.ones_like(v_dc), v_dc, v_dc ** 2])
    w = 1.0 / np.where(y > 0, y, np.max(y))
    coef, *_ = np.linalg.lstsq(A * w[:, None], y_fit * w, rcond=None)
    if a_dark is not None:
        a2 = a_dark ** 2
        B, C = float(coef[0]), float(coef[1])
    else:
        a2, B, C = float(coef[0]), float(coef[1]), float(coef[2])
    neg = [n for n, val in zip(("electronics", "shot", "RIN"), (a2, B, C))
           if val < 0]
    if neg:
        print(f"  NOTE: fitted {', '.join(neg)} term(s) came out negative "
              "(i.e. consistent with zero) and were clamped to 0.")
    return (max(a2, 0.0) ** 0.5, max(B, 0.0) ** 0.5, max(C, 0.0) ** 0.5)


def analyse(npz_path=None, out_prefix="laser_rin"):
    npz_path = npz_path or NPZ
    if not os.path.exists(npz_path):
        raise SystemExit(f"No data at {npz_path} -- run the acquisition first.")
    d = np.load(npz_path, allow_pickle=True)
    fs, f_mod = float(d["fs"]), float(d["f_mod"])
    labels = [str(x) for x in d["labels"]]
    traces, v_dc = d["traces"], np.asarray(d["v_dc"], float)
    v_pl = float(d["v_pl_working"]) if "v_pl_working" in d else V_PL_WORKING
    dark = d["dark"] if np.ndim(d["dark"]) else None
    if v_dc.size == 0:
        raise SystemExit("The saved file contains no power levels.")

    order = np.argsort(v_dc)
    v_dc = v_dc[order]
    labels = [labels[i] for i in order]
    traces = traces[order]

    spectra, sig = [], []
    for tr in traces:
        fr, asd = asd_of(tr, fs)
        spectra.append((fr, asd))
        sig.append(band_median(fr, asd, f_mod))
    sig = np.array(sig)

    a_dark = None
    if dark is not None:
        fr_d, asd_d = asd_of(dark, fs)
        a_dark = band_median(fr_d, asd_d, f_mod)

    a, b, c = fit_terms(v_dc, sig, a_dark)

    elec, shot, laser = a, b * np.sqrt(v_pl), c * v_pl
    total = float(np.sqrt(elec ** 2 + shot ** 2 + laser ** 2))
    frac = (lambda x: 100 * x ** 2 / total ** 2) if total > 0 else (lambda x: 0.0)
    rin_db = 10 * np.log10(c ** 2) if c > 0 else float("-inf")

    lines = [
        f"LASER RIN / noise decomposition  ({str(d['stamp'])})",
        f"  analysis frequency : {f_mod:.0f} Hz (+/-{100 * BAND_FRAC:.0f} %)",
        f"  power levels       : {len(v_dc)}  "
        f"({v_dc.min() * 1e3:.1f} - {v_dc.max() * 1e3:.1f} mV DC)",
        "  dark (measured)    : "
        + (f"{a_dark * 1e9:.2f} nV/sqrt(Hz)" if a_dark else "not measured"),
        "",
        "  fitted coefficients of sigma^2 = a^2 + b^2 V + c^2 V^2 :",
        f"    a (electronics)  = {a * 1e9:10.2f} nV/sqrt(Hz)",
        f"    b (shot)         = {b * 1e9:10.2f} nV/sqrt(Hz) per sqrt(V)",
        f"    c (laser RIN)    = {c * 1e9:10.2f} nV/sqrt(Hz) per V",
        f"    => RIN(f_mod)    = {c ** 2:.3e} /Hz   ({rin_db:.1f} dB/Hz)",
        "",
        f"  contributions at the working level V_PL = {v_pl * 1e3:.0f} mV:",
        f"    electronics      = {elec * 1e9:10.2f} nV/sqrt(Hz)  "
        f"({frac(elec):5.1f} % of variance)",
        f"    shot noise       = {shot * 1e9:10.2f} nV/sqrt(Hz)  "
        f"({frac(shot):5.1f} %)",
        f"    laser RIN        = {laser * 1e9:10.2f} nV/sqrt(Hz)  "
        f"({frac(laser):5.1f} %)",
        f"    total            = {total * 1e9:10.2f} nV/sqrt(Hz)",
        "",
    ]

    if TRANSIMPEDANCE_V_PER_A:
        b_theory = np.sqrt(2 * Q_E * TRANSIMPEDANCE_V_PER_A)
        lines += [f"  shot cross-check: fitted b = {b * 1e9:.2f}, theory "
                  f"sqrt(2qG) = {b_theory * 1e9:.2f} nV/sqrt(Hz) per sqrt(V) "
                  f"(G = {TRANSIMPEDANCE_V_PER_A:.3g} V/A)", ""]

    floor_balanced = float(np.sqrt(elec ** 2 + 2 * shot ** 2))
    if len(v_dc) < MIN_LEVELS:
        verdict = (f"INCONCLUSIVE: only {len(v_dc)} power levels. Take at "
                   f"least {MIN_LEVELS} spanning a decade and re-run.")
    elif laser > 1.5 * max(shot, elec):
        verdict = ("LASER RIN DOMINATES -> a second photodetector for "
                   "balanced / ratiometric detection is worth buying; it "
                   f"attacks {frac(laser):.0f} % of the variance. Perfect "
                   f"cancellation would leave {floor_balanced * 1e9:.1f} "
                   "nV/sqrt(Hz) (two channels' shot noise + electronics).")
    elif shot > 1.5 * max(laser, elec):
        verdict = ("SHOT-NOISE LIMITED -> do NOT buy the second detector for "
                   "noise cancellation: balancing would add the reference's "
                   "shot noise (sqrt(2) worse). Spend on collecting more "
                   "photons (condenser + large-area detector) instead.")
    elif elec > 1.5 * max(laser, shot):
        verdict = ("ELECTRONICS/ADC LIMITED -> neither balancing nor more "
                   "laser power helps directly. Raise the transimpedance "
                   "gain, AC-couple to remove the DC pedestal, and put more "
                   "light on the detector.")
    else:
        gain = total / floor_balanced if floor_balanced > 0 else float("inf")
        verdict = ("MIXED: no single term dominates at the working level. "
                   f"Balanced detection would give at best {gain:.1f}x in "
                   "this band; decide on cost grounds.")
    lines += ["  VERDICT:", "    " + verdict]

    summary = "\n".join(lines)
    print("\n" + summary)
    with open(os.path.join(DATA_DIR, out_prefix + "_summary.txt"), "w") as f:
        f.write(summary + "\n")

    with open(os.path.join(DATA_DIR, out_prefix + ".csv"), "w") as f:
        f.write(f"# laser RIN measurement, {str(d['stamp'])}, "
                f"f_mod_Hz={f_mod}, fs_Hz={fs}\n")
        f.write("label,V_dc,sigma_at_fmod_V_per_rtHz\n")
        for lb, v, s in zip(labels, v_dc, sig):
            f.write(f"{lb},{v:.6f},{s:.6e}\n")

    _plot(spectra, labels, v_dc, sig, a, b, c, a_dark, f_mod, v_pl, out_prefix)
    return a, b, c


def _plot(spectra, labels, v_dc, sig, a, b, c, a_dark, f_mod, v_pl, prefix):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not available - figure skipped)")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    for (fr, asd), lb, v in zip(spectra, labels, v_dc):
        ax1.loglog(fr[1:], asd[1:] * 1e9, lw=0.8,
                   label=f"{lb} ({v * 1e3:.0f} mV)")
    ax1.axvline(f_mod, color="tab:red", ls="--", lw=1)
    ax1.set(xlabel="frequency (Hz)", ylabel=r"ASD (nV/$\sqrt{Hz}$)",
            title=f"(a) Photodiode noise spectra vs optical power "
                  f"(dashed: {f_mod:.0f} Hz)")
    ax1.legend(fontsize=6)
    ax1.grid(alpha=0.3, which="both")

    vv = np.logspace(np.log10(max(v_dc.min(), 1e-4) / 3),
                     np.log10(max(v_dc.max(), v_pl) * 2), 200)
    ax2.loglog(v_dc * 1e3, sig * 1e9, "o", ms=7, color="tab:blue",
               label="measured", zorder=5)
    ax2.loglog(vv * 1e3, np.full_like(vv, a) * 1e9, ":", color="0.5",
               label="electronics (const)")
    ax2.loglog(vv * 1e3, b * np.sqrt(vv) * 1e9, "--", color="tab:green",
               label=r"shot ($\propto\sqrt{V}$)")
    ax2.loglog(vv * 1e3, c * vv * 1e9, "-.", color="tab:orange",
               label=r"laser RIN ($\propto V$)")
    ax2.loglog(vv * 1e3, np.sqrt(a ** 2 + b ** 2 * vv + c ** 2 * vv ** 2) * 1e9,
               "-", color="tab:red", lw=1.6, label="total (fit)")
    ax2.axvline(v_pl * 1e3, color="k", ls="--", lw=1, alpha=0.6)
    if a_dark:
        ax2.axhline(a_dark * 1e9, color="0.5", lw=0.8, alpha=0.6)
    ax2.set(xlabel="photodiode DC level (mV)",
            ylabel=rf"ASD at {f_mod:.0f} Hz (nV/$\sqrt{{Hz}}$)",
            title="(b) Noise vs optical power (dashed line: working level)")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3, which="both")

    fig.tight_layout()
    out = os.path.join(DATA_DIR, prefix + ".png")
    fig.savefig(out, dpi=150)
    print(f"Saved figure -> {out}")
    try:
        plt.show()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Self-test: no hardware needed, verifies the fit recovers known coefficients
# ---------------------------------------------------------------------------
def selftest():
    """Synthesise records whose noise follows a known (a, b, c) and check that
    the analysis recovers them and reaches the right verdict in all three
    regimes. White noise of per-sample std s has one-sided ASD s*sqrt(2/fs),
    so s = A*sqrt(fs/2) produces a target ASD A."""
    os.makedirs(DATA_DIR, exist_ok=True)
    rng = np.random.default_rng(0)
    levels = np.array([0.05, 0.1, 0.2, 0.5, 1.0, 2.0])
    cases = {"RIN-dominated":         (2e-9, 10e-9, 2000e-9),
             "shot-dominated":        (2e-9, 2000e-9, 10e-9),
             "electronics-dominated": (2000e-9, 10e-9, 10e-9)}
    path = os.path.join(DATA_DIR, "laser_rin_selftest.npz")
    ok = True
    for name, (a, b, c) in cases.items():
        tr = []
        for V in levels:
            A = np.sqrt(a ** 2 + b ** 2 * V + c ** 2 * V ** 2)
            tr.append(V + rng.normal(0, A * np.sqrt(FS / 2), (4, 16384)))
        dark = rng.normal(0, a * np.sqrt(FS / 2), (4, 16384))
        np.savez(path, stamp="selftest-" + name, fs=FS, f_mod=F_MOD,
                 labels=np.array([f"L{i}" for i in range(len(levels))]),
                 traces=np.array(tr), v_dc=levels.copy(), dark=dark,
                 v_pl_working=1.0)
        print("=" * 72)
        print(f"SELFTEST [{name}]  true a, b, c = "
              f"{a * 1e9:.0f}, {b * 1e9:.0f}, {c * 1e9:.0f} nV")
        fa, fb, fc = analyse(path, out_prefix="laser_rin_selftest")
        for nm, tv, fv in (("a", a, fa), ("b", b, fb), ("c", c, fc)):
            if tv > 100e-9 and not 0.7 < fv / max(tv, 1e-30) < 1.4:
                print(f"  FAIL: {nm} recovered {fv * 1e9:.1f} nV, "
                      f"true {tv * 1e9:.1f} nV")
                ok = False
    print("=" * 72)
    print("SELFTEST " + ("PASSED - the analysis is trustworthy."
                         if ok else "FAILED - do not trust the fit yet."))
    print("(selftest wrote laser_rin_selftest.* ; your real run writes "
          "laser_rin.* and is untouched)")
    return ok


if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "acquire"
    if mode.startswith("analys"):
        analyse()
    elif mode.startswith("self"):
        selftest()
    else:
        analyse(acquire())
