"""
Record the photodiode output (fast ADC IN1) for a fixed duration on a RedPitaya.

Useful for checking laser/PL stability, drift and noise over time -- no
microwaves involved, the ADF4351 is not touched. Each logged point is the mean
(and standard deviation) of one ADC block capture, time-stamped from the start
of the run. The result is a "t_s,pl_mean_v,pl_std_v" CSV you can plot with
analysis/plot_photodiode.py.

Edit the CONFIGURATION block below and run on the RedPitaya:
    python3 record_photodiode.py
(There are no command-line arguments by design.)

Wiring:
  Photodiode -> IN1   (fast ADC; set the LV/HV jumper for your amp's range)
  GND        -> common ground with the photodiode amplifier
Run as root (ADC access).
"""

import math
import os
import time
from datetime import datetime

import rp


# ============================================================================
# CONFIGURATION  -- edit these, then run the script
# ============================================================================
DURATION_S      = 300.0          # total recording time (600 s = 10 minutes)
<<<<<<< HEAD
OUTPUT_FILE     = "/root/data/BudgetODMR/29-06-2026/photodiode_laser_off.csv"   # everything under data/ gets synced to the PC
=======
OUTPUT_FILE     = "/root/data/BudgetODMR/26-06-2026/photodiode_laser_on.csv"   # everything under data/ gets synced to the PC
>>>>>>> 6bfd5d8 (fjffjfj)

SAMPLE_PERIOD_S = 0.1            # min spacing between logged points (0 = as fast as possible)
PRINT_EVERY_S   = 10.0           # console progress interval

ADC_CHANNEL = rp.RP_CH_1         # IN1
DECIMATION  = rp.RP_DEC_64       # ~8 ms integration window per block (16384 samples)
N_SAMPLES   = 16384              # samples per block capture


# ============================================================================
# Acquisition
# ============================================================================
def capture_block(buff):
    """Trigger one immediate block capture and return (mean_v, std_v)."""
    rp.rp_AcqReset()
    rp.rp_AcqSetDecimation(DECIMATION)
    rp.rp_AcqSetTriggerDelay(N_SAMPLES)
    rp.rp_AcqStart()
    rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_NOW)

    while rp.rp_AcqGetBufferFillState()[1] is False:
        pass
    rp.rp_AcqGetOldestDataV(ADC_CHANNEL, N_SAMPLES, buff)

    total = 0.0
    total_sq = 0.0
    for i in range(N_SAMPLES):
        v = buff[i]
        total += v
        total_sq += v * v
    mean = total / N_SAMPLES
    var = max(0.0, total_sq / N_SAMPLES - mean * mean)   # guard float round-off
    return mean, math.sqrt(var)


def record():
    print(f"Recording IN1 for {DURATION_S:.0f} s -> {OUTPUT_FILE}")
    rp.rp_Init()
    buff = rp.fBuffer(N_SAMPLES)

    out_dir = os.path.dirname(OUTPUT_FILE)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    n = 0
    next_print = PRINT_EVERY_S
    try:
        with open(OUTPUT_FILE, "w") as f:
            f.write(f"# photodiode time series, {datetime.now().isoformat(timespec='seconds')}\n")
            f.write(f"# duration_s={DURATION_S} samples_per_point={N_SAMPLES}\n")
            f.write("t_s,pl_mean_v,pl_std_v\n")

            t0 = time.perf_counter()
            while True:
                t = time.perf_counter() - t0
                if t >= DURATION_S:
                    break

                mean, std = capture_block(buff)
                f.write(f"{t:.4f},{mean:.6f},{std:.6f}\n")
                f.flush()
                n += 1

                if t >= next_print:
                    print(f"  t={t:6.1f}s  PL={mean:.6f} V  (sd {std:.6f})  [{n} pts]")
                    next_print += PRINT_EVERY_S

                if SAMPLE_PERIOD_S > 0:
                    rem = SAMPLE_PERIOD_S - (time.perf_counter() - t0 - t)
                    if rem > 0:
                        time.sleep(rem)

        print(f"Done. Wrote {n} points to {OUTPUT_FILE}")
    except KeyboardInterrupt:
        print(f"\nStopped early. {n} points saved in {OUTPUT_FILE}")
    finally:
        rp.rp_Release()


if __name__ == "__main__":
    record()
