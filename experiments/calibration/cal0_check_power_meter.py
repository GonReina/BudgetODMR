"""
Step 0: check the PM101A analog output on Red Pitaya IN2 and measure mW/V.

The PM101A is read through its ANALOG OUTPUT, not over USB:

    PM101A analog out -> Red Pitaya IN2   (IN2 jumper on HV: config.json
                                           redpitaya.in2_gain; LV clips at ~1 V)

The analog output is proportional to the sensor photocurrent, scaled to the
selected range, so set the range BY HAND to a fixed value (no auto-range)
whose full scale is above the highest power you will measure, and keep it for
the whole calibration. Set the 532 nm correction too.

What this does:
  1. shows the IN2 level live: block / unblock the beam and check it follows
     (and that it is not clipping);
  2. zeroes it with the beam blocked;
  3. measures the mW/V factor against a reading from Thorlabs Optical Power
     Monitor (laser on, steady, as bright as you will use), and saves it in
     <data_dir>/calibration/pm101a_analog_cal.csv. The cal1/cal2/cal3 scripts
     offer to reuse it while the range, wavelength and IN2 jumper stay the same;
  4. prints N_READ readings in mW.

Run on the PC:  python cal0_check_power_meter.py
"""

import time

from calib_common import PowerMeter, Stop, live_dc_monitor

N_READ = 10


def main():
    pm = PowerMeter()
    try:
        print("\n1. LIVE IN2 level: block and unblock the beam, the level should follow.")
        live_dc_monitor(pm.read_v)
        print("\n2. ZERO")
        pm.zero()
        print("\n3. mW/V FACTOR (laser on, steady)")
        pm.calibrate()
        print(f"\n4. {N_READ} readings:")
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
