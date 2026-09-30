"""
Measurement (1) of the WP3 report: MW-POWER DEPENDENCE OF THE CRITICAL GAIN
-- the slope-ratio collapse, the strongest figure the study can produce.

Protocol (Sec. 5.1 of proposal/workpackage3_report.tex):
  1. Calibrate ONCE at the reference power (FM sweep + flank picker):
     f*, R0, D_cal. These are then HELD FIXED for every condition.
  2. For each MW power in POWER_LIST:
       a. take an FM spectrum at that power  -> D_true at the R = R0 crossing;
       b. predict G_c = 2 |D_cal/D_true| and build a gain grid that extends
          well past it (the supercritical estimator needs points above onset);
       c. run the gain scan with the REFERENCE calibration;
       d. save into <DATA_DIR>/selfosc_power_<P>dBm/ in the standard format.
  3. Print the collapse table: measured G_c vs predicted 2 D_cal/D_true.

Analyse / plot with:
    python analysis/plot_selfosc_fm.py <dir_ref> <dir_P2> <dir_P3> ...
(which also produces the collapse figure).

Safety/validity checks: a power is skipped if the lobe peak falls below the
reference setpoint R0 (no fixed point on the flank -> the loop has nothing to
lock to). Total time ~15 min for three powers at 250 cycles/gain.

Run on the PC:  python odmr_selfosc_power_pc.py
"""

import os
import time
from datetime import datetime

import numpy as np

from lockin_common import (RedPitayaLockin, SMCV100B, frange,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
                           F_START, F_STOP, F_STEP, POWER_DBM, F_MOD, DATA_DIR)
from odmr_sensitivity_fm_pc import (take_spectrum, find_working_point,
                                    pick_working_point, moving_average)
from selfosc_common import (auto_gain_grid, report_gc, save_run_dir,
                            scan_gains, slope_at_crossing)

# --- settings ---
POWER_LIST   = (POWER_DBM, POWER_DBM - 3.0, POWER_DBM - 6.0)  # first = reference
N_CYC        = 250
PICK_BY_HAND = True


def main():
    freqs = list(frange(F_START, F_STOP, F_STEP))
    stamp = datetime.now().isoformat(timespec="seconds")
    os.makedirs(DATA_DIR, exist_ok=True)
    f_lo, f_hi = F_START + 0.5, F_STOP - 0.5

    print(f"G_c vs MW power: {POWER_LIST} dBm (reference = {POWER_LIST[0]})")
    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_LIST[0])
    setup_smcv_modulation(src, "fm")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        # ---- reference calibration (ONCE) ----
        print(f"\nReference calibration at {POWER_LIST[0]:+.1f} dBm")
        R_ref = take_spectrum(src, rp, freqs)
        f_auto, s_auto, snr = find_working_point(freqs, R_ref)
        if PICK_BY_HAND:
            f_star, D_cal, _ = pick_working_point(freqs, R_ref, f_auto, s_auto)
        else:
            f_star, D_cal = f_auto, s_auto
        R0 = float(np.interp(f_star, freqs, R_ref))
        print(f"  f* = {f_star:.3f} MHz, R0 = {R0 * 1e3:.3f} mV, "
              f"D_cal = {D_cal * 1e3:+.4f} mV/MHz (SNR ~ {snr:.0f})")

        results = []
        for P in POWER_LIST:
            tag = f"selfosc_power_{P:+.0f}dBm".replace("+", "p").replace("-", "m")
            out_dir = os.path.join(DATA_DIR, tag)
            print(f"\n=== MW power {P:+.1f} dBm ===")
            src.s.write(f":SOURce:POWer:LEVel:IMMediate:AMPLitude {P:.2f}")
            src.s.query("*OPC?")
            time.sleep(1.0)

            R_spec = take_spectrum(src, rp, freqs)
            peak = float(np.max(moving_average(R_spec, 3)))
            if peak < R0:
                print(f"  SKIPPED: lobe peak {peak * 1e3:.3f} mV < setpoint "
                      f"R0 {R0 * 1e3:.3f} mV -- no fixed point on the flank. "
                      "Use a smaller power step or a lower setpoint.")
                continue
            D_true = slope_at_crossing(freqs, R_spec, f_star, R0)
            gc_pred = 2.0 * abs(D_cal / D_true)
            gains = auto_gain_grid(gc_pred)
            print(f"  D_true = {D_true * 1e3:+.4f} mV/MHz -> predicted "
                  f"G_c = {gc_pred:.2f}; scanning {len(gains)} gains "
                  f"{gains[0]}..{gains[-1]}")

            orbits, rows, dt = scan_gains(src, rp, f_star, R0, D_cal, gains,
                                          N_CYC, f_lo, f_hi)
            save_run_dir(out_dir, stamp, f_star, R0, D_cal, freqs, R_spec,
                         rows, extra_header=f"power_dBm={P}")
            _, _, _, gc, dgc, gfit = report_gc(orbits)
            results.append((P, D_true, gc_pred, gc, dgc, gfit, out_dir))
            print(f"  -> G_c = {gc:.2f} +/- {dgc:.2f} (crossing), "
                  f"{gfit:.2f} (fit)   [predicted {gc_pred:.2f}]")

        # ---- collapse summary ----
        lines = [f"G_c vs MW power ({stamp}), reference calibration at "
                 f"{POWER_LIST[0]:+.1f} dBm:",
                 f"  f* = {f_star:.3f} MHz, R0 = {R0 * 1e3:.3f} mV, "
                 f"D_cal = {D_cal * 1e3:+.4f} mV/MHz", "",
                 "  P[dBm]   D_true[mV/MHz]   predicted   crossing      fit"]
        for P, Dt, gp, gc, dgc, gf, _ in results:
            lines.append(f"  {P:+6.1f}   {Dt * 1e3:+12.4f}   {gp:9.2f}   "
                         f"{gc:.2f}+/-{dgc:.2f}   {gf:6.2f}")
        lines += ["", "  Collapse plot: python analysis/plot_selfosc_fm.py "
                  + " ".join(r[6] for r in results)]
        summary = "\n".join(lines)
        print("\n" + summary)
        with open(os.path.join(DATA_DIR, "selfosc_power_summary.txt"), "w") as f:
            f.write(summary + "\n")

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
