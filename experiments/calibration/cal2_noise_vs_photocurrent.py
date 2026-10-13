"""
Step 2c (Stage 0c): NOISE vs PHOTOCURRENT at the chosen laser current.

Keep the laser current FIXED (the quiet current picked from step 2b) and vary
ONLY the attenuation. plot_cal2_noise.py plots the noise at the candidate
modulation frequencies against the DC photocurrent on log-log axes:

    slope 0    electronics noise (constant)
    slope 1/2  shot noise        (sqrt of the photocurrent)
    slope 1    laser noise       (proportional to the photocurrent)

and fits sigma^2 = a^2 + b^2 V + c^2 V^2 (same decomposition as
laser_rin_pc.py). Aim for 6-10 levels spanning at least a decade, up to
just below clipping. Same detector position, DECIMATION and IN1 jumper as
step 2b; run cal2_noise_floors.py first.

Output: <data_dir>/calibration/noise_vs_photocurrent_<stamp>.npz
        (fs, current_mA, tec_C, v_dc, label, traces [n_level x N_REC x 16384])
Next:   plot_cal2_noise.py

Run on the PC:  python cal2_noise_vs_photocurrent.py
"""

import numpy as np

from calib_common import (Photodiode, Stop, ask, ask_current, ask_tec, cal_path,
                          live_dc_monitor, pause, stamp, wait_stable)

# --- settings ---------------------------------------------------------------
CURRENT_MA = 140.0         # the quiet current from step 2b
I_MAX_MA = 150.0
DECIMATION = 1024
GAIN = None                # None -> config.json redpitaya.input_gain
N_REC = 10
SETTLE_MIN_S, SETTLE_MAX_S, SETTLE_TOL = 30.0, 300.0, 0.005


def main():
    path = cal_path(f"noise_vs_photocurrent_{stamp()}.npz")
    pd = Photodiode(DECIMATION, GAIN)
    vdc_l, lab_l, tr_l = [], [], []
    cur, tec = float("nan"), float("nan")

    def save():
        np.savez(path, fs=pd.fs, decimation=DECIMATION, gain=pd.gain,
                 current_mA=cur, tec_C=tec, v_dc=np.array(vdc_l),
                 label=np.array(lab_l), traces=np.array(tr_l))

    try:
        cur = ask_current(CURRENT_MA, I_MAX_MA)
        if cur is None:
            raise Stop
        pause("Detector in the step 2b position, strongest attenuation you plan "
              "to use")
        wait_stable(pd.dc, 0.0, 10.0, SETTLE_TOL, SETTLE_MIN_S, SETTLE_MAX_S,
                    unit="mV", scale=1e3)
        tec = ask_tec()
        print("\nNow change ONLY the attenuation between levels (never the current).")
        while True:
            print("-" * 72)
            v = live_dc_monitor(pd)
            label = ask(f"  label for this level at {v * 1e3:.1f} mV "
                        "(e.g. 'ND2.0'; blank = finish)", "")
            if not label:
                break
            tr = pd.records(N_REC)
            vdc_l.append(float(tr.mean()))
            lab_l.append(label)
            tr_l.append(tr)
            print(f"  [{label}] DC {vdc_l[-1] * 1e3:.2f} mV, rms {tr.std() * 1e3:.3f} mV"
                  f"  ({len(vdc_l)} level(s))")
            save()
    except (Stop, KeyboardInterrupt):
        print("\nStopped.")
    finally:
        pd.close()
    if vdc_l:
        save()
        print(f"\n{len(vdc_l)} level(s) -> {path}\nNext: plot_cal2_noise.py")


if __name__ == "__main__":
    main()
