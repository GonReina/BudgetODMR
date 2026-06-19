"""
Run the ODMR sweep repeatedly and save each run as its own file.

This is the same experiment as odmr_redpitaya.py (same frequency range, same
per-point "wait for PLL lock then average IN1" logic -- the classes and
functions are imported from it, not duplicated), but it repeats the whole
sweep N_SWEEPS times. Each sweep is written to RUNS_DIR/run_01.csv,
run_02.csv, ... so that analysis/average_sweeps.py can average them together
to beat down the noise.

Edit the CONFIGURATION block below (and the sweep range / averaging in
odmr_redpitaya.py, which this reuses) then run on the RedPitaya:
    python3 odmr_repeat_sweeps.py
(There are no command-line arguments by design.)
"""

import os
import time

from odmr_redpitaya import (
    ADF4351, RedPitayaADC, sweep_once, frange,
    F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ, AVERAGES_PER_POINT, SPI_HZ,
)


# ============================================================================
# CONFIGURATION  -- edit these, then run the script
# (the sweep range and averages/point come from odmr_redpitaya.py)
# ============================================================================
N_SWEEPS        = 10                 # how many full sweeps to record
RUNS_DIR        = "data/odmr_runs"   # everything under data/ gets synced to the PC
DELAY_BETWEEN_S = 0.0                # optional pause between sweeps, seconds


def run_repeated():
    freqs = list(frange(F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ))
    os.makedirs(RUNS_DIR, exist_ok=True)
    print(f"Repeated ODMR: {N_SWEEPS} sweeps of {F_START_MHZ}-{F_STOP_MHZ} MHz "
          f"({len(freqs)} points, {AVERAGES_PER_POINT} avg/point) -> {RUNS_DIR}/")

    adf = ADF4351(speed_hz=SPI_HZ)
    adc = RedPitayaADC()

    completed = 0
    try:
        for run in range(1, N_SWEEPS + 1):
            out_path = os.path.join(RUNS_DIR, f"run_{run:02d}.csv")
            print(f"\n===== sweep {run}/{N_SWEEPS} -> {out_path} =====")
            sweep_once(adf, adc, freqs, out_path, header_extra=f"run={run}/{N_SWEEPS}")
            completed += 1
            if DELAY_BETWEEN_S > 0 and run < N_SWEEPS:
                time.sleep(DELAY_BETWEEN_S)

        print(f"\nDone. {completed} sweeps written to {RUNS_DIR}/")
    except KeyboardInterrupt:
        print(f"\nStopped early after {completed} complete sweep(s). "
              f"Data so far is in {RUNS_DIR}/")
    finally:
        adf.close()
        adc.close()


if __name__ == "__main__":
    run_repeated()
