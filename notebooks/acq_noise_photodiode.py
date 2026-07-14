"""
Tutorial data acquisition 1/5: RAW PHOTODIODE NOISE (for the "know your enemy"
section of lockin_odmr_tutorial.ipynb).

Records raw photodiode traces from Red Pitaya IN1 with the LASER ON and the
MICROWAVES OFF, at three decimations so the notebook can stitch a noise PSD
covering ~0.1 Hz ... 1 MHz:

    decimation    64  -> fs = 1.95 MHz, 8.4 ms/buffer   (white floor, hf)
    decimation  8192  -> fs = 15.3 kHz, 1.07 s/buffer   (mains 50/150 Hz)
    decimation 65536  -> fs = 1.91 kHz, 8.6 s/buffer    (1/f and drift)

Output: notebooks/tutorial_data/noise_dec{N}.npz with keys 'fs' and 'v'
(array n_buffers x 16384, volts). Takes ~2 minutes (dominated by the slow
buffers).

Run on the PC:  python acq_noise_photodiode.py
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "smcv"))
from lockin_common import (RedPitayaLockin, SMCV100B,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT, RP_GAIN)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "tutorial_data")
PLAN = ((64, 16), (8192, 8), (65536, 4))     # (decimation, n_buffers)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # make sure the MW output is off (noise of laser + detection chain only)
    try:
        src = SMCV100B(SMCV_IP, SMCV_PORT)
        src.output(False)
        src.s.close()
        print("SMCV output switched OFF.")
    except Exception as e:
        print(f"(couldn't reach the SMCV: {e} -- make sure MW is off.)")

    rp = RedPitayaLockin(RP_IP, RP_PORT)
    try:
        for dec, n in PLAN:
            fs = 125e6 / dec
            dur = 16384 / fs
            print(f"decimation {dec}: fs = {fs:.0f} Hz, {dur:.2f} s/buffer, "
                  f"{n} buffers...")
            traces = []
            t0 = time.perf_counter()
            for k in range(n):
                traces.append(rp.scope.acquire((1,), dec, RP_GAIN,
                                               fill_timeout_s=3 * dur + 5))
                print(f"  buffer {k + 1}/{n} "
                      f"({(time.perf_counter() - t0) / (k + 1):.1f} s each)")
            path = os.path.join(OUT_DIR, f"noise_dec{dec}.npz")
            np.savez(path, fs=fs, v=np.array(traces))
            print(f"  -> {path}")
        print("\nDone. Re-run the noise cells of the tutorial notebook.")
    finally:
        rp.close()


if __name__ == "__main__":
    main()
