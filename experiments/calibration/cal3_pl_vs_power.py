"""
Step 3: PL vs LASER POWER at the sample, with a quick CW ODMR at each power.

Three runs, chosen with MODE:

  "nv"          focus in the diamond. At each current: PL (MW off), then a
                quick CW ODMR sweep (MW on/off ratio) -> contrast C, linewidth,
                and the line centres (D = mean of the two lines: heating shifts
                it by about -74 kHz/K).
  "background"  the SAME currents with the focus moved OFF the diamond (glass,
                filter and immersion fluorescence, 532 nm leaking through the
                550 nm long-pass). This is the linear b*P term of the fit.
  "nd_check"    detector linearity: at the highest power, PL without, with,
                and again without a known ND filter in front of the APD. If
                the PL ratio differs from the ND transmission, the DETECTOR is
                saturating, not the NV centres. Use the ND transmission at the
                PL wavelengths (~650-750 nm): absorptive ND filters are not
                flat, so 10^-OD is only approximate.

Keep the APD gain, pinhole, filters and alignment FIXED for all three runs.
The x-axis comes from step 1 (power_calibration.csv); plot_cal3_pl_saturation.py
fits PL = A*P/(P + P_sat) + b*P.

Signal path: APD (or PDA10A2) -> Red Pitaya IN1; SMCV100B -> amplifier ->
antenna. The MW level goes through SMCV100B.set_power_dbm(), which enforces
the config.json mw_chain limit.

Output: <data_dir>/calibration/
          pl_vs_current_<MODE>_<stamp>.csv
              step,current_mA,PL_V,PL_std_V,dark_V,tec_C,odmr_file
          pl_vs_current_<MODE>_<stamp>/odmr_XX.csv   (freq_MHz,signal = PL_on/PL_off)
          nd_check_<stamp>.csv                        (MODE "nd_check")
Next:   plot_cal3_pl_saturation.py

Run on the PC:  python cal3_pl_vs_power.py
"""

import os
import sys
import time

import numpy as np

from calib_common import (Stop, TableWriter, ask_current, ask_float, ask_tec,
                          ask_yes, cal_path, fit_odmr, pause, stamp, wait_stable)

_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from odmr_smcv100b_pc import (POWER_DBM, RP_IP, RP_PORT, SMCV_IP, SMCV_PORT,
                              F_START_MHZ, F_STOP_MHZ, RedPitayaADC, SMCV100B,
                              frange, integrate)

# --- settings ---------------------------------------------------------------
MODE = "nv"                 # "nv", "background" or "nd_check"
CURRENTS_MA = [132.0, 134.0, 136.0, 138.0, 140.0, 142.0, 144.0, 147.0]
I_MAX_MA = 150.0            # never ask for more (set to your LDC200C limit)
PL_READS = 20               # PL = mean of 20 integrations (config integration_ms each)
SETTLE_MIN_S, SETTLE_MAX_S, SETTLE_TOL = 20.0, 240.0, 0.005

DO_ODMR = True              # quick CW ODMR at every current (MODE "nv" only)
ODMR_F_START, ODMR_F_STOP = F_START_MHZ, F_STOP_MHZ    # config.json sweep window
ODMR_STEP_MHZ = 0.5         # coarser than a full sweep: this is the quick check
ODMR_SWEEPS = 1
MW_POWER_DBM = POWER_DBM    # config.json sweep.power_dbm; KEEP IT FIXED for the run
MW_SETTLE_S = 0.02
N_LINES = 2                 # resonances in the window (1 at zero field)


def pl_reading(adc, n=PL_READS):
    v = np.array([integrate(adc) for _ in range(n)])
    return float(v.mean()), float(v.std(ddof=1))


def odmr_sweep(src, adc, freqs):
    """MW on/off ratio per point, averaged over ODMR_SWEEPS."""
    acc = np.zeros(len(freqs))
    for s in range(ODMR_SWEEPS):
        for i, f in enumerate(freqs):
            src.set_freq_mhz(f)
            src.output(True)
            time.sleep(MW_SETTLE_S)
            on = integrate(adc)
            src.output(False)
            time.sleep(MW_SETTLE_S)
            off = integrate(adc)
            acc[i] += on / off if off else np.nan
            print(f"\r  ODMR sweep {s + 1}/{ODMR_SWEEPS}: {i + 1}/{len(freqs)} "
                  f"({f:.1f} MHz)", end="", flush=True)
    print()
    return acc / ODMR_SWEEPS


def measure_dark(adc):
    pause("  DARK: block the LASER (APD stays on, same gain)")
    d, ds = pl_reading(adc)
    print(f"  dark = {d * 1e3:.3f} +/- {ds * 1e3:.3f} mV")
    pause("  Unblock the laser")
    return d


def run_nd_check(adc):
    path = cal_path(f"nd_check_{stamp()}.csv")
    out = TableWriter(path, ["current_mA", "T_nd", "PL_open1_V", "PL_nd_V",
                             "PL_open2_V", "dark_V", "ratio", "ratio_over_T"],
                      meta=dict(experiment="nd_check"))
    try:
        cur = ask_current(max(CURRENTS_MA), I_MAX_MA)
        if cur is None:
            raise Stop
        wait_stable(lambda: integrate(adc), 0.0, 10.0, SETTLE_TOL, SETTLE_MIN_S,
                    SETTLE_MAX_S, unit="mV", scale=1e3)
        dark = measure_dark(adc)
        od = ask_float("  ND filter OD", 1.0)
        t_nd = ask_float("  its transmission at the PL wavelengths (~700 nm)",
                         round(10 ** -od, 4))
        o1, _ = pl_reading(adc)
        pause("  Put the ND filter in front of the APD")
        nd, _ = pl_reading(adc)
        pause("  Remove the ND filter")
        o2, _ = pl_reading(adc)
        ratio = (nd - dark) / (0.5 * (o1 + o2) - dark)
        print(f"\n  open {o1 * 1e3:.3f} / {o2 * 1e3:.3f} mV, with ND {nd * 1e3:.3f} mV"
              f" (dark {dark * 1e3:.3f})")
        print(f"  PL ratio = {ratio:.4f}  vs  T_nd = {t_nd:.4f}  ->  "
              f"ratio / T = {ratio / t_nd:.3f}")
        if ratio / t_nd > 1.05:
            print("  ratio > T: the open reading is COMPRESSED -> the detector "
                  "saturates at this power. Lower the APD gain or attenuate.")
        else:
            print("  consistent with a linear detector (within 5 %).")
        out.row(cur, t_nd, o1, nd, o2, dark, ratio, ratio / t_nd)
    finally:
        out.close()
    print(f"Saved {path}")


def run_sweep(adc, src):
    tag = f"pl_vs_current_{MODE}_{stamp()}"
    spec_dir = cal_path(tag)
    os.makedirs(spec_dir, exist_ok=True)
    freqs = list(frange(ODMR_F_START, ODMR_F_STOP, ODMR_STEP_MHZ))
    do_odmr = DO_ODMR and MODE == "nv" and src is not None
    out = TableWriter(cal_path(tag + ".csv"),
                      ["step", "current_mA", "PL_V", "PL_std_V", "dark_V", "tec_C",
                       "odmr_file"],
                      meta=dict(experiment="pl_vs_current", mode=MODE,
                                mw_power_dBm=MW_POWER_DBM if do_odmr else "none",
                                n_lines=N_LINES))
    print(f"\nPL vs CURRENT ({MODE}) -> {out.path}")
    if do_odmr:
        print(f"  quick ODMR: {ODMR_F_START}-{ODMR_F_STOP} MHz / {ODMR_STEP_MHZ} "
              f"({len(freqs)} pts) at {MW_POWER_DBM:+.1f} dBm")
    if MODE == "background":
        pause("Move the focus OFF the diamond (same depth into the substrate / "
              "glass), everything else unchanged")
    try:
        dark = measure_dark(adc)
        for step, planned in enumerate(CURRENTS_MA):
            cur = ask_current(planned, I_MAX_MA)
            if cur is None:
                continue
            wait_stable(lambda: integrate(adc), 0.0, 10.0, SETTLE_TOL, SETTLE_MIN_S,
                        SETTLE_MAX_S, unit="mV", scale=1e3)
            tec = ask_tec()
            pl, pls = pl_reading(adc)
            print(f"  PL = {(pl - dark) * 1e3:.3f} mV above dark (+/- {pls * 1e3:.3f})")
            fname = ""
            if do_odmr:
                sig = odmr_sweep(src, adc, freqs)
                fname = f"odmr_{step:02d}.csv"
                with open(os.path.join(spec_dir, fname), "w") as f:
                    f.write(f"# experiment=pl_vs_current_odmr\n# current_mA={cur}\n"
                            f"# mw_power_dBm={MW_POWER_DBM}\n# PL_V={pl}\n"
                            "# signal=PL_on/PL_off\nfreq_MHz,signal\n")
                    for fr, s in zip(freqs, sig):
                        f.write(f"{fr:.4f},{s:.7f}\n")
                fit = fit_odmr(freqs, sig, N_LINES)
                if fit:
                    for ln in fit["lines"]:
                        print(f"    line {ln['f0']:.2f} MHz: C = {100 * ln['contrast']:.2f} %"
                              f", FWHM = {ln['fwhm']:.2f} MHz")
                    print(f"    centre (mean of lines) = "
                          f"{np.mean([ln['f0'] for ln in fit['lines']]):.3f} MHz")
                else:
                    print("    (ODMR fit failed -- check the spectrum/N_LINES)")
            out.row(step, cur, pl, pls, dark, tec,
                    os.path.join(os.path.basename(spec_dir), fname) if fname else "")
        if ask_yes("\nMeasure the dark level again (drift check)?"):
            d2 = measure_dark(adc)
            print(f"  dark drift: {(d2 - dark) * 1e3:+.3f} mV")
    except (Stop, KeyboardInterrupt):
        print("\nStopped -- steps so far are saved.")
    finally:
        out.close()
    print(f"\nSaved {out.path}")
    if MODE == "nv":
        print("Next: MODE = 'background', then MODE = 'nd_check', then "
              "plot_cal3_pl_saturation.py")


def main():
    if max(CURRENTS_MA) > I_MAX_MA:
        raise SystemExit(f"CURRENTS_MA goes above I_MAX_MA = {I_MAX_MA} mA.")
    if MODE not in ("nv", "background", "nd_check"):
        raise SystemExit(f"MODE must be 'nv', 'background' or 'nd_check', not {MODE!r}")
    adc = RedPitayaADC(RP_IP, RP_PORT)
    src = None
    try:
        if MODE == "nv" and DO_ODMR:
            src = SMCV100B(SMCV_IP, SMCV_PORT)
            src.configure(MW_POWER_DBM)
            src.output(False)
        if MODE == "nd_check":
            run_nd_check(adc)
        else:
            run_sweep(adc, src)
    except Stop:
        print("Stopped.")
    finally:
        adc.close()
        if src is not None:
            src.close()


if __name__ == "__main__":
    main()
