"""
Tutorial data acquisition 2/5: DC ODMR SWEEP AT SEVERAL INTEGRATION TIMES
(for Part 1 of lockin_odmr_tutorial.ipynb).

One CW sweep (no modulation, no MW on/off reference). At every frequency ONE
Red Pitaya buffer is captured at decimation 1024 (fs = 122 kHz, 134 ms), and
the mean photodiode voltage is computed over the first T of the SAME buffer
for each T in T_LIST -- so the four integration times share identical noise
and the comparison is exact. The 8 ms column doubles as the "DC at 8 ms"
reference for the AM/FM comparisons.

Output: notebooks/tutorial_data/dc_integration_sweep.csv
        (freq_MHz, V_2ms, V_8ms, V_20ms, V_100ms)
Takes ~2 minutes for the config sweep range.

Run on the PC:  python acq_dc_integration_sweep.py
"""

import os
import sys
import time
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "smcv"))
from lockin_common import (RedPitayaLockin, SMCV100B, frange,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT, RP_GAIN,
                           F_START, F_STOP, F_STEP, POWER_DBM, SETTLE_S)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "tutorial_data")
DEC    = 1024                          # fs = 122 kHz, buffer = 134 ms
T_LIST = (0.002, 0.008, 0.020, 0.100)  # integration times [s]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    freqs = list(frange(F_START, F_STOP, F_STEP))
    fs = 125e6 / DEC
    n_samp = [int(round(T * fs)) for T in T_LIST]
    stamp = datetime.now().isoformat(timespec="seconds")
    print(f"DC sweep {F_START}-{F_STOP} MHz ({len(freqs)} pts), "
          f"T = {[f'{1e3*T:.0f}' for T in T_LIST]} ms from one buffer/point")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    path = os.path.join(OUT_DIR, "dc_integration_sweep.csv")
    try:
        with open(path, "w") as f:
            f.write(f"# DC ODMR, one dec-{DEC} buffer per point, {stamp}, "
                    f"power_dBm={POWER_DBM}, fs_Hz={fs:.1f}\n")
            f.write("freq_MHz," +
                    ",".join(f"V_{1e3*T:.0f}ms" for T in T_LIST) + "\n")
            t0 = time.perf_counter()
            for i, fr in enumerate(freqs):
                src.set_freq_mhz(fr)
                time.sleep(SETTLE_S)
                v = rp.scope.acquire((1,), DEC, RP_GAIN)
                means = [np.mean(v[:n]) for n in n_samp]
                f.write(f"{fr:.4f}," +
                        ",".join(f"{m:.7f}" for m in means) + "\n")
                if (i + 1) % 25 == 0:
                    print(f"  {i + 1}/{len(freqs)} "
                          f"({(time.perf_counter() - t0) / (i + 1):.2f} s/pt)")
        print(f"\nDone -> {path}")
    finally:
        rp.close()
        src.close()


if __name__ == "__main__":
    main()
