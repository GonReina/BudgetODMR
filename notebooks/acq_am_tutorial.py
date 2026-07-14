"""
Tutorial data acquisition 4/5: AM LOCK-IN DEMO DATA
(for Part 2 of lockin_odmr_tutorial.ipynb).

With AM modulation on (internal, f_mod from config), this script records:
  1. an AM lock-in SWEEP at ~8 ms/point           -> am_sweep.csv
  2. the frequency of the strongest peak = f_res;
  3. RAW photodiode records ON and OFF resonance at decimation 512
     (fs = 244 kHz, 67 ms/record, several records each) -> am_traces.npz.
     These show, in the time domain and in the PSD, that the photodiode
     output is modulated at 5 kHz ON resonance and flat OFF resonance
     (plus the 2nd harmonic at 10 kHz).

The "DC at 8 ms" companion sweep for the comparison figure comes from
acq_dc_integration_sweep.py (its V_8ms column).

Output: notebooks/tutorial_data/am_sweep.csv, am_traces.npz
Takes ~1 minute after the sweep (~15 s for a 0.25 MHz-step sweep).

Run on the PC:  python acq_am_tutorial.py
"""

import os
import sys
import time
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "smcv"))
from lockin_common import (RedPitayaLockin, SMCV100B, demodulate, frange,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT, RP_GAIN,
                           F_START, F_STOP, F_STEP, POWER_DBM, F_MOD,
                           SETTLE_S, FS_HZ)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "tutorial_data")
DEC_RAW  = 512     # raw records: fs = 244 kHz, 67 ms -> 15 Hz PSD resolution
N_RAW    = 6       # records per point (on / off resonance)
SWEEP_STEP = 0.25  # MHz (coarser than config for speed; the shape suffices)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    freqs = list(frange(F_START, F_STOP, SWEEP_STEP))

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "am")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        # ---- 1) AM lock-in sweep at ~8 ms/point ----
        print(f"AM sweep {F_START}-{F_STOP} MHz / {SWEEP_STEP} "
              f"({len(freqs)} pts)")
        R = []
        for i, fr in enumerate(freqs):
            src.set_freq_mhz(fr)
            time.sleep(SETTLE_S)
            R.append(demodulate(rp.acquire_in1(), FS_HZ, F_MOD))
            if (i + 1) % 40 == 0:
                print(f"  {i + 1}/{len(freqs)}")
        R = np.array(R)
        sweep_path = os.path.join(OUT_DIR, "am_sweep.csv")
        with open(sweep_path, "w") as f:
            f.write(f"# AM lock-in sweep, {stamp}, f_mod_Hz={F_MOD}, "
                    f"power_dBm={POWER_DBM}, t_int_ms~8\n")
            f.write("freq_MHz,lockin_R\n")
            for fr, r in zip(freqs, R):
                f.write(f"{fr:.4f},{r:.8f}\n")
        print(f"  -> {sweep_path}")

        # ---- 2) on / off resonance raw records ----
        f_res = float(freqs[int(np.argmax(R))])
        f_off = float(F_START)
        fs_raw = 125e6 / DEC_RAW
        print(f"raw records at dec {DEC_RAW} (fs = {fs_raw:.0f} Hz): "
              f"ON = {f_res:.2f} MHz, OFF = {f_off:.2f} MHz")
        recs = {}
        for tag, fr in (("on", f_res), ("off", f_off)):
            src.set_freq_mhz(fr)
            time.sleep(0.3)
            recs[tag] = np.array([rp.scope.acquire((1,), DEC_RAW, RP_GAIN)
                                  for _ in range(N_RAW)])
            print(f"  {tag}-resonance: {N_RAW} records")
        traces_path = os.path.join(OUT_DIR, "am_traces.npz")
        np.savez(traces_path, fs=fs_raw, f_mod=F_MOD,
                 f_on=f_res, f_off=f_off, on=recs["on"], off=recs["off"])
        print(f"  -> {traces_path}\nDone.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "am")
        src.close()


if __name__ == "__main__":
    main()
