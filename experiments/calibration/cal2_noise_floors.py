"""
Step 2a: NOISE FLOORS -- record these before any laser-noise measurement.

  1. TERMINATED INPUT: a 50 ohm terminator on Red Pitaya IN1 (detector cable
     off). This is the Red Pitaya's own floor (ADC + front end).
  2. BLOCKED BEAM: the PDA10A2 connected and powered, beam blocked. This is
     the detector floor (dark current + amplifier noise) on top of the ADC.

Use the SAME IN1 jumper (LV/HV) and decimation as in cal2_rin_vs_current.py
and cal2_noise_vs_photocurrent.py: both floors depend on them. Room lights as
during the measurements.

Output: <data_dir>/calibration/noise_floors_<stamp>.npz
        (fs, decimation, gain, terminated [N x 16384], blocked [N x 16384])
Next:   cal2_rin_vs_current.py, cal2_noise_vs_photocurrent.py, plot_cal2_noise.py

Run on the PC:  python cal2_noise_floors.py
"""

import numpy as np

from calib_common import Photodiode, cal_path, pause, stamp

DECIMATION = 1024      # fs = 122 kHz: covers 1-10 kHz modulation, Nyquist 61 kHz
GAIN = None            # None -> config.json redpitaya.input_gain ("LV" / "HV")
N_REC = 20             # 134 ms records


def main():
    pd = Photodiode(DECIMATION, GAIN)
    path = cal_path(f"noise_floors_{stamp()}.npz")
    try:
        pause("\n1/2 TERMINATED INPUT: disconnect the detector and put a 50 ohm "
              "terminator on IN1")
        term = pd.records(N_REC)
        print(f"  DC {term.mean() * 1e3:.3f} mV, rms {term.std() * 1e3:.3f} mV")
        pause("\n2/2 BLOCKED BEAM: reconnect the PDA10A2 (powered), block the beam")
        blk = pd.records(N_REC)
        print(f"  DC {blk.mean() * 1e3:.3f} mV, rms {blk.std() * 1e3:.3f} mV")
    finally:
        pd.close()
    np.savez(path, fs=pd.fs, decimation=DECIMATION, gain=pd.gain,
             terminated=term, blocked=blk)
    print(f"\nSaved {path}\nNext: cal2_rin_vs_current.py")


if __name__ == "__main__":
    main()
