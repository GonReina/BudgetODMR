"""
Measurement (2) of the WP3 report: CYCLE-TIME INVARIANCE OF THE CRITICAL GAIN
-- a null test of the memoryless-map model.

The map f_{k+1} = f_k - (G/D_cal)[R(f_k) - R0] contains no time scale, so
G_c must be independent of the loop cycle duration. This script measures G_c
with deliberately added per-cycle delays. Interpretation:
  * flat G_c vs cycle time  -> the memoryless-map assumption is validated;
  * G_c deviating at SHORT cycle times -> unsettled instrument transients
    (MW source switching, detector response) act as an effective slope
    change, and the turnover calibrates the settling time.
Either outcome is a publishable panel.

Calibration (f*, R0, D_cal) is done once and held fixed; each condition's
gain scan uses the same fine grid around G = 2 and is saved in
<DATA_DIR>/selfosc_dt_<ms>ms/ in the standard format (analysable with
analysis/plot_selfosc_fm.py). Total time: dominated by the largest delay
(~35 min for the default list at 200 cycles/gain).

Run on the PC:  python odmr_selfosc_cycletime_pc.py
"""

import os
import time
from datetime import datetime

import numpy as np

from lockin_common import (RedPitayaLockin, SMCV100B, frange,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
                           F_START, F_STOP, F_STEP, POWER_DBM, DATA_DIR)
from odmr_sensitivity_fm_pc import (take_spectrum, find_working_point,
                                    pick_working_point)
from selfosc_common import report_gc, save_run_dir, scan_gains

# --- settings ---
EXTRA_DELAYS = (0.0, 0.15, 0.4, 0.8)          # added seconds per cycle
GAINS        = [round(g, 2) for g in np.arange(1.5, 2.75, 0.1)] + [0.6, 1.0]
N_CYC        = 200
PICK_BY_HAND = True


def main():
    freqs = list(frange(F_START, F_STOP, F_STEP))
    stamp = datetime.now().isoformat(timespec="seconds")
    os.makedirs(DATA_DIR, exist_ok=True)
    f_lo, f_hi = F_START + 0.5, F_STOP - 0.5
    gains = sorted(set(GAINS))

    print(f"G_c vs cycle time: extra delays {EXTRA_DELAYS} s, "
          f"{len(gains)} gains x {N_CYC} cycles")
    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "fm")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        # ---- calibration (ONCE) ----
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
        for dly in EXTRA_DELAYS:
            print(f"\n=== extra delay {dly * 1e3:.0f} ms/cycle ===")
            orbits, rows, dt = scan_gains(src, rp, f_star, R0, D_cal, gains,
                                          N_CYC, f_lo, f_hi, extra_delay=dly)
            out_dir = os.path.join(DATA_DIR, f"selfosc_dt_{dt * 1e3:.0f}ms")
            save_run_dir(out_dir, stamp, f_star, R0, D_cal, freqs, R_ref,
                         rows, extra_header=f"extra_delay_s={dly} "
                                            f"cycle_dt_s={dt:.4f}")
            _, _, _, gc, dgc, gfit = report_gc(orbits)
            results.append((dly, dt, gc, dgc, gfit, out_dir))
            print(f"  cycle {dt * 1e3:.0f} ms -> G_c = {gc:.2f} +/- {dgc:.2f} "
                  f"(crossing), {gfit:.2f} (fit)")

        lines = [f"G_c vs cycle time ({stamp}); theory: flat (no time scale "
                 "in the map). Deviation at short cycles = settling.", "",
                 "  extra[ms]   cycle[ms]   crossing      fit"]
        for dly, dt, gc, dgc, gf, _ in results:
            lines.append(f"  {dly * 1e3:9.0f}   {dt * 1e3:9.0f}   "
                         f"{gc:.2f}+/-{dgc:.2f}   {gf:6.2f}")
        summary = "\n".join(lines)
        print("\n" + summary)
        with open(os.path.join(DATA_DIR, "selfosc_cycletime_summary.txt"),
                  "w") as f:
            f.write(summary + "\n")

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
