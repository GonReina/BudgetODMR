"""
Autonomous self-oscillating NV loop -- hardware demo for the funding proposal
("deviations from autonomous behaviour as signals of external perturbations").

The side-of-fringe FM lock is run as a DYNAMICAL SYSTEM: one reading per cycle,

    f_{k+1} = f_k - (G / D_cal) * [ R(f_k) - R_0 ] ,

with the setpoint R_0 on a lobe flank. For effective gain G_eff = G * D_true /
D_cal below 2 the loop is a stable tracker; at G_eff = 2 it undergoes a
period-doubling bifurcation and becomes a self-oscillator (see
proposal/autonomous_nv_sim.py and proposal/autonomous_nv_demo.md). Because
G_eff is proportional to the LOCAL LOBE SLOPE, any perturbation that changes
the slope -- a field gradient across the ensemble, MW or laser power, linewidth
-- moves the oscillation onset. The appearance/disappearance and statistics of
the autonomous oscillation are the sensor signal.

What this script does:
  1. FM sweep + the usual interactive picker: choose the flank working point.
  2. GAIN SCAN: run the loop at each G in GAIN_LIST, recording the frequency
     orbit -> the experimental bifurcation diagram (orbit spread vs G).
  3. STATISTICS RUN: long run at G_STAT (just above threshold) for the
     limit-cycle statistics (period histogram, envelope spectrum,
     two-time correlations -- analysis offline).
Repeat the whole script with a perturbation applied (magnet moved closer for a
gradient, MW power changed, coil driven by the Red Pitaya OUT1) and compare
the measured critical gain G_c -- that comparison IS the demonstration.

Run on the PC:  python odmr_selfosc_fm_pc.py
Outputs in <DATA_DIR>: selfosc_fm_spectrum.csv, selfosc_fm_gainscan.csv,
                       selfosc_fm_stats.csv, selfosc_fm_summary.txt
"""

import os
import time
from datetime import datetime

import numpy as np

from lockin_common import (RedPitayaLockin, SMCV100B, demodulate, frange,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
                           F_START, F_STOP, F_STEP, POWER_DBM,
                           F_MOD, SETTLE_S, FS_HZ, DATA_DIR)
from odmr_sensitivity_fm_pc import (take_spectrum, find_working_point,
                                    pick_working_point, GAMMA)

# --- run settings (local to this script) ---
GAIN_LIST  = (0.6, 1.0, 1.4, 1.8, 2.0, 2.1, 2.2, 2.4, 2.7, 3.0, 3.4)
N_CYC      = 250     # loop cycles per gain value
G_STAT     = 2.3     # gain for the long statistics run (just above onset)
N_STAT     = 4000    # cycles for the statistics run
PICK_BY_HAND  = True
PARK_SETTLE_S = 0.5


def read_R(src, rp, f_mhz):
    src.set_freq_mhz(f_mhz)
    time.sleep(SETTLE_S)
    return demodulate(rp.acquire_in1(), FS_HZ, F_MOD)


def alt_amp(u, blk=32):
    """Coherent period-2 amplitude: block-median of |mean of (-1)^k (u - <u>)|.
    Amplified NOISE below the bifurcation averages to ~0; the deterministic
    limit cycle does not -- this is the clean oscillation discriminator."""
    u = np.asarray(u, float) - np.mean(u)
    s = ((-1.0) ** np.arange(len(u))) * u
    nb = max(1, len(s) // blk)
    return float(np.median([abs(np.mean(s[i * blk:(i + 1) * blk]))
                            for i in range(nb)]))


def run_loop(src, rp, f0, R0, D, G, n, label=""):
    """Iterate the autonomous loop; returns (t, f, R) arrays."""
    lo, hi = F_START + 0.5, F_STOP - 0.5
    f = f0
    ts, fs_, rs = [], [], []
    t0 = time.perf_counter()
    for k in range(n):
        R = read_R(src, rp, f)
        f = float(np.clip(f - G * (R - R0) / D, lo, hi))
        ts.append(time.perf_counter() - t0)
        fs_.append(f)
        rs.append(R)
        if label and (k + 1) % 200 == 0:
            print(f"  {label}: {k + 1}/{n}")
    return np.array(ts), np.array(fs_), np.array(rs)


def main():
    freqs = list(frange(F_START, F_STOP, F_STEP))
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")

    print(f"SELF-OSCILLATION run: gains {GAIN_LIST}, {N_CYC} cycles each; "
          f"stats at G={G_STAT} x {N_STAT}")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "fm")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        # ---- working point (flank) ----
        print("\nStep 1/3: FM spectrum + working point")
        R = take_spectrum(src, rp, freqs)
        with open(os.path.join(DATA_DIR, "selfosc_fm_spectrum.csv"), "w") as f:
            f.write(f"# FM spectrum for self-oscillation run, {stamp}\n"
                    "freq_MHz,lockin_R\n")
            for fr, r in zip(freqs, R):
                f.write(f"{fr:.5f},{r:.8f}\n")
        f_auto, slope_auto, snr = find_working_point(freqs, R)
        if PICK_BY_HAND:
            f_star, slope, _ = pick_working_point(freqs, R, f_auto, slope_auto)
        else:
            f_star, slope = f_auto, slope_auto
        R0 = float(np.interp(f_star, freqs, R))
        print(f"  flank at {f_star:.3f} MHz, R0 = {R0 * 1e3:.3f} mV, "
              f"D = {slope * 1e3:+.3f} mV/MHz (SNR ~ {snr:.0f})")

        # ---- gain scan: the experimental bifurcation diagram ----
        print("\nStep 2/3: gain scan")
        gs_path = os.path.join(DATA_DIR, "selfosc_fm_gainscan.csv")
        spreads = []
        with open(gs_path, "w") as f:
            f.write(f"# self-oscillation gain scan, {stamp}, "
                    f"f_star_MHz={f_star:.5f}, R0_V={R0:.8e}, "
                    f"D_V_per_MHz={slope:.8e}, gamma_MHz_per_mT={GAMMA}\n")
            f.write("gain,cycle,t_s,f_MHz,R_V\n")
            for G in GAIN_LIST:
                src.set_freq_mhz(f_star)
                time.sleep(PARK_SETTLE_S)
                t, fr_, rr = run_loop(src, rp, f_star, R0, slope, G, N_CYC)
                for k in range(len(t)):
                    f.write(f"{G},{k},{t[k]:.4f},{fr_[k]:.6f},{rr[k]:.8e}\n")
                tail = fr_[N_CYC // 3:]                      # skip transient
                spread, a2 = float(np.std(tail)), alt_amp(tail)
                spreads.append((spread, a2))
                print(f"  G = {G:4.1f}: spread {spread * 1e3:7.1f} kHz  "
                      f"period-2 amp {a2 * 1e3:7.1f} kHz")

        # experimental critical gain: first G where the coherent period-2
        # amplitude JUMPS above twice the sub-threshold trend
        a2s = np.array([s[1] for s in spreads])
        base = max(a2s[0], 1e-6)
        jump = [g for g, a in zip(GAIN_LIST, a2s) if a > 4 * base and a > 0.05]
        g_c = jump[0] if jump else float("nan")

        # ---- statistics run ----
        print(f"\nStep 3/3: statistics run at G = {G_STAT}")
        src.set_freq_mhz(f_star)
        time.sleep(PARK_SETTLE_S)
        t, fr_, rr = run_loop(src, rp, f_star, R0, slope, G_STAT, N_STAT,
                              label="stats")
        with open(os.path.join(DATA_DIR, "selfosc_fm_stats.csv"), "w") as f:
            f.write(f"# self-oscillation statistics, {stamp}, gain={G_STAT}, "
                    f"f_star_MHz={f_star:.5f}, R0_V={R0:.8e}, "
                    f"D_V_per_MHz={slope:.8e}\n")
            f.write("cycle,t_s,f_MHz,R_V\n")
            for k in range(len(t)):
                f.write(f"{k},{t[k]:.4f},{fr_[k]:.6f},{rr[k]:.8e}\n")

        dt = float(np.median(np.diff(t)))
        lines = [
            f"Self-oscillation summary ({stamp})",
            f"  working point   : {f_star:.3f} MHz, R0 = {R0 * 1e3:.3f} mV, "
            f"D = {slope * 1e3:+.3f} mV/MHz",
            f"  cycle time      : {dt * 1e3:.0f} ms ({1 / dt:.1f} cycles/s)",
            "  gain scan (G: spread / period-2 amplitude):",
        ] + [
            f"    G = {g:4.1f}: {s * 1e3:7.1f} kHz / {a * 1e3:7.1f} kHz"
            for g, (s, a) in zip(GAIN_LIST, spreads)
        ] + [
            f"  critical gain   : G_c ~ {g_c}"
            "   (theory: 2 x D_cal/D_true; repeat with a perturbation",
            "                    applied and compare G_c -- that shift is the "
            "sensor signal.",
            "                    The smooth growth of the spread BELOW G_c is "
            "the critical-",
            "                    fluctuation precursor -- also perturbation-"
            "dependent.)",
            f"  stats run       : G = {G_STAT}, {N_STAT} cycles, period-2 amp "
            f"{alt_amp(fr_[N_STAT // 4:]) * 1e3:.1f} kHz",
        ]
        summary = "\n".join(lines)
        print("\n" + summary)
        with open(os.path.join(DATA_DIR, "selfosc_fm_summary.txt"), "w") as f:
            f.write(summary + "\n")

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
