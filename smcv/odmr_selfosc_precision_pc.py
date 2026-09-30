"""
Measurement (3) of the WP3 report: ESTIMATOR PRECISION OF THE CRITICAL GAIN
-- repeated identical gain scans give the empirical error bar on G_c, and
hence the quantitative resolution of the threshold observable.

One calibration (f*, R0, D_cal), then N_REPEATS identical fine-grid gain
scans. The scatter of the extracted G_c values is the error bar; via the
identifiability relation dG_c/G_c = beta (Sec. 2.3 of the report), a
fractional linewidth-broadening resolution follows directly:
    beta_min(3 sigma) = 3 * std(G_c) / mean(G_c).

Each repeat is saved in <DATA_DIR>/selfosc_rep_XX/ (standard format, so
analysis/plot_selfosc_fm.py works per repeat). Total time ~55 min with the
defaults at a 0.4 s cycle.

Run on the PC:  python odmr_selfosc_precision_pc.py
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
N_REPEATS    = 5
GAINS        = [0.6, 1.0] + [round(g, 2) for g in np.arange(1.6, 2.65, 0.1)]
N_CYC        = 150
PICK_BY_HAND = True


def main():
    freqs = list(frange(F_START, F_STOP, F_STEP))
    stamp = datetime.now().isoformat(timespec="seconds")
    os.makedirs(DATA_DIR, exist_ok=True)
    f_lo, f_hi = F_START + 0.5, F_STOP - 0.5
    gains = sorted(set(GAINS))

    print(f"G_c precision: {N_REPEATS} repeats of {len(gains)} gains x "
          f"{N_CYC} cycles")
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

        gcs, gfits = [], []
        for rep in range(1, N_REPEATS + 1):
            print(f"\n=== repeat {rep}/{N_REPEATS} ===")
            orbits, rows, dt = scan_gains(src, rp, f_star, R0, D_cal, gains,
                                          N_CYC, f_lo, f_hi,
                                          label=f"[{rep}] ")
            out_dir = os.path.join(DATA_DIR, f"selfosc_rep_{rep:02d}")
            save_run_dir(out_dir, stamp, f_star, R0, D_cal, freqs, R_ref,
                         rows, extra_header=f"repeat={rep}")
            _, _, _, gc, dgc, gfit = report_gc(orbits)
            gcs.append(gc)
            gfits.append(gfit)
            print(f"  -> G_c = {gc:.3f} (crossing), {gfit:.3f} (fit)")

        gcs = np.array(gcs)
        gfits = np.array([g for g in gfits if np.isfinite(g)])
        mu, sd = float(np.mean(gcs)), float(np.std(gcs, ddof=1))
        beta3 = 3 * sd / mu
        lines = [
            f"G_c estimator precision ({stamp}), {N_REPEATS} repeats:",
            "  crossing estimator : "
            + ", ".join(f"{g:.3f}" for g in gcs),
            f"                       mean = {mu:.3f}, std = {sd:.3f}",
        ]
        if len(gfits) >= 2:
            lines.append(f"  supercritical fit  : mean = {np.mean(gfits):.3f}, "
                         f"std = {np.std(gfits, ddof=1):.3f} "
                         f"({len(gfits)} finite)")
        lines += [
            "",
            f"  => fractional-broadening resolution (dGc/Gc = beta):",
            f"     1 sigma: {sd / mu * 100:.1f} %   3 sigma: {beta3 * 100:.1f} %",
            "     (this is the number to quote in Sec. 5.3 of the report)",
        ]
        summary = "\n".join(lines)
        print("\n" + summary)
        with open(os.path.join(DATA_DIR, "selfosc_precision_summary.txt"),
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
