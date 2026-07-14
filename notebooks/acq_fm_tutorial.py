"""
Tutorial data acquisition 5/5: FM LOCK-IN DEMO DATA
(for Part 3 of lockin_odmr_tutorial.ipynb).

Real FREQUENCY modulation (SMCV internal), virtual phase-free demodulation.
Records:
  1. an FM lock-in SWEEP at ~8 ms/point -> fm_sweep.csv (the two-lobe shape);
  2. from the sweep, three park points: OFF resonance, on a lobe SLOPE
     (steepest flank) and at the NULL (line centre);
  3. RAW photodiode records at each (decimation 512, fs = 244 kHz)
     -> fm_traces.npz. These show the rocking intuition experimentally:
     no tone off resonance, a 5 kHz tone on the slope, and a doubled
     (10 kHz) wiggle at the centre.

Output: notebooks/tutorial_data/fm_sweep.csv, fm_traces.npz
Takes ~1 minute after the sweep.

Run on the PC:  python acq_fm_tutorial.py
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
DEC_RAW    = 512
N_RAW      = 6
SWEEP_STEP = 0.25   # MHz
SMOOTH     = 3


def moving_average(y, n=SMOOTH):
    return np.convolve(y, np.ones(n) / n, mode="same") if n > 1 else y


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    freqs = np.array(list(frange(F_START, F_STOP, SWEEP_STEP)))

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "fm")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        # ---- 1) FM lock-in sweep ----
        print(f"FM sweep {F_START}-{F_STOP} MHz / {SWEEP_STEP} "
              f"({len(freqs)} pts)")
        R = []
        for i, fr in enumerate(freqs):
            src.set_freq_mhz(fr)
            time.sleep(SETTLE_S)
            R.append(demodulate(rp.acquire_in1(), FS_HZ, F_MOD))
            if (i + 1) % 40 == 0:
                print(f"  {i + 1}/{len(freqs)}")
        R = np.array(R)
        sweep_path = os.path.join(OUT_DIR, "fm_sweep.csv")
        with open(sweep_path, "w") as f:
            f.write(f"# FM lock-in sweep, {stamp}, f_mod_Hz={F_MOD}, "
                    f"power_dBm={POWER_DBM}, t_int_ms~8\n")
            f.write("freq_MHz,lockin_R\n")
            for fr, r in zip(freqs, R):
                f.write(f"{fr:.4f},{r:.8f}\n")
        print(f"  -> {sweep_path}")

        # ---- 2) pick off / slope / null from the sweep ----
        Rs = moving_average(R)
        i_pk = int(np.argmax(Rs))                       # strongest lobe
        grad = np.gradient(Rs, freqs)
        i_sl = int(np.argmax(np.abs(grad)))             # steepest flank
        # null: local minimum within +/-3 MHz of the strongest lobe
        win = (np.abs(freqs - freqs[i_pk]) < 3.0) & (Rs < 0.5 * Rs[i_pk])
        i_nu = int(np.where(win)[0][np.argmin(Rs[win])]) if win.any() else i_pk
        points = {"off": float(F_START),
                  "slope": float(freqs[i_sl]),
                  "null": float(freqs[i_nu])}
        print("park points: " +
              ", ".join(f"{k} = {v:.2f} MHz" for k, v in points.items()))

        # ---- 3) raw records at each point ----
        fs_raw = 125e6 / DEC_RAW
        out = {"fs": fs_raw, "f_mod": F_MOD}
        for tag, fr in points.items():
            src.set_freq_mhz(fr)
            time.sleep(0.3)
            out[tag] = np.array([rp.scope.acquire((1,), DEC_RAW, RP_GAIN)
                                 for _ in range(N_RAW)])
            out[f"f_{tag}"] = fr
            print(f"  {tag}: {N_RAW} records at {fr:.2f} MHz")
        traces_path = os.path.join(OUT_DIR, "fm_traces.npz")
        np.savez(traces_path, **out)
        print(f"  -> {traces_path}\nDone.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
