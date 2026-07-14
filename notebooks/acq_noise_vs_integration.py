"""
Tutorial data acquisition 3/5: NOISE VS INTEGRATION TIME, DC AND LOCK-IN
(for the "why not integrate longer" plot of Part 1 and the noise-rejection
plot of Part 2 of lockin_odmr_tutorial.ipynb).

Parks the MW OFF RESONANCE (sweep start frequency) with AM modulation ENABLED,
so the photodiode sees realistic operating conditions but carries no 5 kHz
tone. Captures N contiguous 1.07 s records (decimation 8192, fs = 15.3 kHz).
The notebook then slices each record into chunks of varying length T and
computes, for each T,
    * the scatter of plain chunk MEANS        -> DC noise vs T,
    * the scatter of chunk LOCK-IN readings R -> lock-in noise vs T,
which is the experimental version of the simulated noise-rejection figure.

Output: notebooks/tutorial_data/noise_vs_T.npz  (keys: fs, f_mod, v [N x 16384])
Takes ~1-2 minutes.

Run on the PC:  python acq_noise_vs_integration.py
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "smcv"))
from lockin_common import (RedPitayaLockin, SMCV100B,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT, RP_GAIN,
                           F_START, POWER_DBM, F_MOD)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "tutorial_data")
DEC       = 8192      # fs = 15.26 kHz, 1.07 s per contiguous record
N_RECORDS = 20


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    fs = 125e6 / DEC
    print(f"Noise vs integration time: {N_RECORDS} records of "
          f"{16384 / fs:.2f} s at fs = {fs:.0f} Hz, parked OFF resonance "
          f"({F_START} MHz), AM modulation on, f_mod = {F_MOD:.0f} Hz")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "am")
    src.set_freq_mhz(F_START)          # far from resonance: no tone
    src.output(True)
    time.sleep(0.5)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        traces = []
        t0 = time.perf_counter()
        for k in range(N_RECORDS):
            traces.append(rp.scope.acquire((1,), DEC, RP_GAIN,
                                           fill_timeout_s=8.0))
            print(f"  record {k + 1}/{N_RECORDS} "
                  f"({(time.perf_counter() - t0) / (k + 1):.1f} s each)")
        path = os.path.join(OUT_DIR, "noise_vs_T.npz")
        np.savez(path, fs=fs, f_mod=F_MOD, v=np.array(traces))
        print(f"\nDone -> {path}")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "am")
        src.close()


if __name__ == "__main__":
    main()
