"""
Photodiode response vs laser current -- interactive characterization.

For each point you type in the laser-diode current you've dialled on the
Thorlabs LDC200C (read it off the controller), and this script averages the
PDA10A2 detector output on Red Pitaya fast-ADC IN1 for ~1 second and appends the
result to a CSV. Repeat for as many currents as you like; type q (or blank) to
quit. Data accumulates across sessions (the file is appended to, not overwritten).

Each row:  timestamp, ldc_current_mA, pl_mean_v, pl_std_v, n_samples, integ_s

Run on the Red Pitaya as root:   sudo python3 pd_vs_laser_current.py

Wiring / setup:
  * PDA10A2 output -> IN1.
  * IMPORTANT: the PDA10A2 can swing several volts, well past the Red Pitaya's
    LV (+/-1 V) input range. Set the IN1 jumper to HV (+/-20 V) and check on a
    scope that the signal never clips, or you'll just measure a flat ceiling.
  * Common ground between the detector and the Red Pitaya.
"""

import math
import os
import time
from datetime import datetime

import rp

# ============================================================================
# CONFIG
# ============================================================================
OUTPUT_FILE = "root/data/BudgetODMR/29-06-2026/laser_power_calibration.csv"
INTEGRATION_S = 1.0            # averaging time per point

ADC_CHANNEL = rp.RP_CH_1       # IN1
DECIMATION  = rp.RP_DEC_1024   # fs = 122.07 kS/s; one 16384-sample block = 134 ms
FS_HZ       = 125e6 / 1024
N_BUF       = 16384


def capture_block(buff):
    """Trigger one immediate block capture into buff (N_BUF samples)."""
    rp.rp_AcqReset()
    rp.rp_AcqSetDecimation(DECIMATION)
    rp.rp_AcqSetTriggerDelay(N_BUF)
    rp.rp_AcqStart()
    rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_NOW)
    while rp.rp_AcqGetBufferFillState()[1] is False:
        pass
    rp.rp_AcqGetOldestDataV(ADC_CHANNEL, N_BUF, buff)


def measure(buff, seconds):
    """Average IN1 over >= `seconds`. Return (mean_v, std_v, n_samples, integ_s)."""
    target = int(seconds * FS_HZ)
    total = total_sq = 0.0
    n = 0
    while n < target:
        capture_block(buff)
        for i in range(N_BUF):
            v = buff[i]
            total += v
            total_sq += v * v
        n += N_BUF
    mean = total / n
    var = max(0.0, total_sq / n - mean * mean)
    return mean, math.sqrt(var), n, n / FS_HZ


def main():
    out_dir = os.path.dirname(OUTPUT_FILE)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    new_file = not os.path.exists(OUTPUT_FILE) or os.path.getsize(OUTPUT_FILE) == 0

    rp.rp_Init()
    buff = rp.fBuffer(N_BUF)

    f = open(OUTPUT_FILE, "a")
    if new_file:
        f.write("timestamp,ldc_current_mA,pl_mean_v,pl_std_v,n_samples,integ_s\n")
        f.flush()

    print(f"Photodiode vs laser current -> appending to {OUTPUT_FILE}")
    print("Type the LDC200C current in mA and press Enter; q or blank to quit.\n")

    try:
        while True:
            s = input("Laser diode current (mA): ").strip()
            if s.lower() in ("", "q", "quit", "exit"):
                break
            try:
                current = float(s)
            except ValueError:
                print("  not a number -- try again (e.g. 12.5)")
                continue

            print(f"  measuring {INTEGRATION_S:.1f} s ...", end="", flush=True)
            mean, std, n, integ = measure(buff, INTEGRATION_S)
            ts = datetime.now().isoformat(timespec="seconds")
            f.write(f"{ts},{current:.4f},{mean:.6f},{std:.6f},{n},{integ:.3f}\n")
            f.flush()
            print(f" {current:.3f} mA -> {mean:.6f} V  (sd {std:.6f}, {n} samples)")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        f.close()
        rp.rp_Release()
        print(f"Done. Data in {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
