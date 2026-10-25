"""
DC ODMR vs DIAMOND POSITION: an N_SWEEPS-sweep average, then you take the
diamond out, rotate it, put it back, and the next position is measured. Repeat
as often as you like; type q at the prompt to finish.

Same measurement as odmr_smcv100b_pc.py (MW on/off ratio, config.json range,
power, settle and integration). The MW output is OFF while you handle the
diamond.

Output: <data_dir>/positions_<stamp>/pos_<k>_<label>.csv, one per position:
          freq_MHz,signal,std,sweep_1,...,sweep_N
          (signal = mean of the sweeps, std = their standard deviation;
           # key=value metadata: label, n_sweeps, power, ...)
        The file is rewritten after every sweep, so a stopped position keeps
        the sweeps it has.
Next:   plot_odmr_positions.py

Run on the PC:  python odmr_positions_pc.py
"""

import os
import re
import sys
from datetime import datetime

import numpy as np

_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from expconfig import load_config
from odmr_smcv100b_pc import (F_START_MHZ, F_STEP_MHZ, F_STOP_MHZ, POWER_DBM, RP_IP,
                              RP_PORT, SMCV_IP, SMCV_PORT, SMCV100B, RedPitayaADC,
                              frange, measure_point)

# --- settings ---------------------------------------------------------------
N_SWEEPS = 2
DATA_DIR = load_config()["paths"]["data_dir"]


def save(path, freqs, sweeps, label, k):
    a = np.array(sweeps)
    with open(path, "w") as f:
        f.write(f"# experiment=odmr_positions\n# position={k}\n# label={label}\n"
                f"# n_sweeps={len(a)}\n# power_dBm={POWER_DBM}\n"
                f"# signal=PL_on/PL_off\n"
                f"# saved={datetime.now().isoformat(timespec='seconds')}\n")
        f.write("freq_MHz,signal,std," + ",".join(f"sweep_{i + 1}" for i in range(len(a)))
                + "\n")
        std = a.std(axis=0, ddof=1) if len(a) > 1 else np.zeros(len(freqs))
        for j, fr in enumerate(freqs):
            f.write(f"{fr:.4f},{a[:, j].mean():.7f},{std[j]:.7f},"
                    + ",".join(f"{v:.7f}" for v in a[:, j]) + "\n")


def main():
    run_dir = os.path.join(DATA_DIR, f"positions_{datetime.now():%Y%m%d_%H%M%S}")
    os.makedirs(run_dir, exist_ok=True)
    freqs = list(frange(F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ))
    print(f"DC ODMR vs position -> {run_dir}\n  {F_START_MHZ}-{F_STOP_MHZ} MHz / "
          f"{F_STEP_MHZ} ({len(freqs)} pts), {N_SWEEPS} sweeps per position, "
          f"{POWER_DBM:+.1f} dBm")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    adc = RedPitayaADC(RP_IP, RP_PORT)
    src.configure(POWER_DBM)
    k = 0
    try:
        while True:
            k += 1
            src.output(False)
            ans = input(f"\nPosition {k}: mount the diamond (rotated), refocus. Label "
                        f"[pos{k}], q = finish: ").strip()
            if ans.lower() in ("q", "quit"):
                break
            label = ans or f"pos{k}"
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
            path = os.path.join(run_dir, f"pos_{k:02d}_{safe}.csv")
            src.output(True)
            sweeps = []
            for s in range(N_SWEEPS):
                row = []
                for i, fr in enumerate(freqs):
                    row.append(measure_point(src, adc, fr))
                    print(f"\r  sweep {s + 1}/{N_SWEEPS}: {i + 1}/{len(freqs)} "
                          f"({fr:.2f} MHz)", end="", flush=True)
                sweeps.append(row)
                save(path, freqs, sweeps, label, k)
            print(f"\n  -> {os.path.basename(path)}")
    except KeyboardInterrupt:
        print("\nStopped. Completed sweeps are saved.")
    finally:
        src.close()
        adc.close()
    print(f"\nDone -> {run_dir}\nNext: python plot_odmr_positions.py")


if __name__ == "__main__":
    main()
