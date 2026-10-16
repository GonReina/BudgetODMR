"""
Step 0: check the PM101A analog output on Red Pitaya IN2 and measure mW/V.

The PM101A is read through its ANALOG OUTPUT, not over USB:

    PM101A analog out -> Red Pitaya IN2   (jumper = config.json
                                           redpitaya.in2_gain; LV: +/- 1 V)

In Optical Power Monitor set the analog output to RESPONSIVITY mode: V = P x
"AO responsivity" (V/W), independent of the range. Choose it so the highest
power gives ~0.7-0.9 V on LV (15 V/W for 50 mW, 60 V/W for ~14 mW), write it
in config.json redpitaya.pm_ao_responsivity_v_per_w, and keep it for the whole
calibration. Set the 532 nm correction too. Step 3 compares the measured
factor with the nominal 1000 / responsivity mW/V.

What this does:
  1. shows the IN2 level live: block / unblock the beam and check it follows
     (and that it is not clipping);
  2. zeroes it with the beam blocked;
  3. measures the mW/V factor against a reading from Thorlabs Optical Power
     Monitor (laser on, steady, as bright as you will use), and saves it in
     <data_dir>/calibration/pm101a_analog_cal.csv. The cal1/cal2/cal3 scripts
     offer to reuse it while the range, wavelength and IN2 jumper stay the same;
  4. NOISE CHECK (beam on, steady): the scatter of the per-record readings,
     with and without whole-mains-cycle averaging, and the largest line in
     the IN2 spectrum. Compare the scatter with what Optical Power Monitor
     shows: much larger here means pickup on the cable (ground loop, mains
     hum) or fast laser noise that the meter's display averages away;
  5. prints N_READ readings in mW.

Run on the PC:  python cal0_check_power_meter.py
"""

import time

import numpy as np

from calib_common import MAINS_HZ, PowerMeter, Stop, live_dc_monitor, mains_mean

N_READ = 10
N_NOISE = 20               # records for the noise check (134 ms each)


def noise_check(pm, n=N_NOISE):
    recs = np.array([pm.record() for _ in range(n)])
    k = pm.mw_per_v
    plain = recs.mean(axis=1) - pm.v_zero
    clean = np.array([mains_mean(r, pm.fs) for r in recs]) - pm.v_zero
    w = np.hanning(recs.shape[1])
    amp = 2 * np.abs(np.fft.rfft((recs - recs.mean(axis=1, keepdims=True)) * w,
                                 axis=1)).mean(axis=0) / w.sum()
    fr = np.fft.rfftfreq(recs.shape[1], 1 / pm.fs)
    j = 1 + int(np.argmax(amp[1:]))
    j50 = int(np.argmin(abs(fr - MAINS_HZ)))

    def mv_mw(v):
        return f"{v * 1e3:8.3f} mV = {v * k:8.4f} mW"

    print(f"  level                     {mv_mw(clean.mean())}")
    print(f"  rms inside a record       {mv_mw(recs.std(axis=1).mean())}")
    print(f"  largest line              {fr[j]:8.1f} Hz, amplitude {mv_mw(amp[j])}")
    print(f"  line at {MAINS_HZ:.0f} Hz             amplitude {mv_mw(amp[j50])}")
    print(f"  record-to-record scatter  {mv_mw(plain.std(ddof=1))}  (plain mean)")
    print(f"                            {mv_mw(clean.std(ddof=1))}  "
          "(whole mains cycles: what the scripts use)")
    print("  -> compare the last line with the fluctuation Optical Power Monitor "
          "shows.\n     A strong 50/100 Hz line = ground loop / pickup: one ground "
          "only, short\n     coax. Broadband rms = fast laser noise the meter "
          "display averages away.")


def main():
    pm = PowerMeter()
    try:
        print("\n1. LIVE IN2 level: block and unblock the beam, the level should follow.")
        live_dc_monitor(pm.read_v)
        print("\n2. ZERO")
        pm.zero()
        print("\n3. mW/V FACTOR (laser on, steady)")
        pm.calibrate()
        print(f"\n4. NOISE CHECK (beam on, steady; {N_NOISE} records)")
        noise_check(pm)
        print(f"\n5. {N_READ} readings:")
        for i in range(N_READ):
            print(f"  reading {i + 1:2d}: {pm.read_mw():.6f} mW")
            time.sleep(0.2)
        print("\nOK: the cal1_* scripts can log the PM101A through IN2.")
    except (Stop, KeyboardInterrupt):
        print("\nStopped.")
    finally:
        pm.close()


if __name__ == "__main__":
    main()
