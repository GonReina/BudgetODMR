"""
Lock-in raw-signal diagnostic.

Parks the SMCV at ONE frequency (put it on a resonance you know), turns on the
modulation, and captures the raw photodiode waveform on Red Pitaya IN1. It then
shows the time trace and its spectrum so you can answer the questions behind an
"aliased"-looking lock-in sweep:

  * Is there a clean modulation tone reaching IN1, and at WHAT frequency?
    (If the detected tone != config f_mod_hz, the fixed-frequency demod is
     off-tune -> set the SMCV LF frequency to match, or set f_mod_hz to the
     detected value.)
  * Is the tone a clean sine, or distorted / clipped / full of harmonics
    (PEP clamp, over-modulation) -> that shows up as extra spectral peaks.
  * Does anything appear with the LASER BLOCKED? (run once laser-on, once
    laser-blocked) -> if the tone persists with no light, it's direct
    electrical pickup of the modulated MW, not the optical ODMR signal.

Run on the PC:  python diag_lockin_raw.py     (needs numpy + matplotlib)
"""

import os

import numpy as np
import matplotlib.pyplot as plt

from expconfig import load_config
from odmr_smcv100b_pc import SMCV100B
from lockin_common import (RedPitayaLockin, detect_fmod, demodulate,
                           FS_HZ, F_MOD, SMCV_IP, SMCV_PORT, RP_IP, RP_PORT, POWER_DBM)

# ===== CONFIG =====
PARK_FREQ_MHZ = 2873.0        # park here -- put it ON a resonance you've found
SAVE_PNG = os.path.join(load_config()["paths"]["data_dir"], "diag_lockin_raw.png")


def main():
    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    try:
        src.s.write(":SOURce:MODulation:ALL:STATe OFF")
        src.s.query("*OPC?")
    except Exception:
        pass
    src.set_freq_mhz(PARK_FREQ_MHZ)
    src.output(True)

    rp = RedPitayaLockin(RP_IP, RP_PORT)
    # data = []
    # for x in range(21):
    #     data.append(rp.acquire_in1())
    
    # v = np.concat(data,axis=0)
    v = rp.acquire_in1()
    fs = FS_HZ
    n = len(v)
    print("Data length is {}".format(n))
    t = np.arange(n) / fs

    spec = np.abs(np.fft.rfft((v - v.mean()) * np.hanning(n)))
    fr = np.fft.rfftfreq(n, 1.0 / fs)
    f_det = detect_fmod(v, fs, F_MOD)
    R = demodulate(v, fs, F_MOD)

    print(f"Parked at {PARK_FREQ_MHZ} MHz, {POWER_DBM:+.1f} dBm")
    print(f"  IN1: mean {v.mean():.4f} V, pk-pk {v.max()-v.min():.4f} V")
    print(f"  strongest tone in 0.3-30 kHz: {f_det:.0f} Hz  (config f_mod = {F_MOD:.0f} Hz)")
    print(f"  lock-in R at fixed {F_MOD:.0f} Hz: {R:.6f}")
    if abs(f_det - F_MOD) > 0.05 * F_MOD:
        print("  --> MISMATCH: the detected tone differs from f_mod. Set the SMCV LF")
        print("      frequency to it (or set config f_mod_hz = detected value).")

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7))
    ncyc = min(n, int(20 * fs / max(f_det, 100.0)))     # ~5 modulation cycles
    a1.plot(t[:ncyc] * 1e3, v[:ncyc], lw=0.8)
    a1.set_xlabel("time (ms)")
    a1.set_ylabel("IN1 (V)")
    a1.set_title(f"raw photodiode @ {PARK_FREQ_MHZ} MHz  (should be a clean sine)")
    a1.grid(True, alpha=0.3)

    a2.semilogy(fr, spec, lw=0.8, color="tab:purple")
    a2.axvline(F_MOD, color="tab:red", ls="--", lw=1, label=f"f_mod {F_MOD:.0f} Hz")
    a2.axvline(f_det, color="tab:green", ls=":", lw=1, label=f"detected {f_det:.0f} Hz")
    a2.set_xlim(0, 20000)
    a2.set_xlabel("frequency (Hz)")
    a2.set_ylabel("amplitude (a.u.)")
    a2.set_title("IN1 spectrum -- one clean peak = good; extra peaks = distortion/pickup")
    a2.legend()
    a2.grid(True, alpha=0.3, which="both")
    fig.tight_layout()
    if SAVE_PNG:
        fig.savefig(SAVE_PNG, dpi=150)
        print(f"  saved {SAVE_PNG}")

    rp.close()
    try:
        src.s.write(":SOURce:MODulation:ALL:STATe OFF")
    except Exception:
        pass
    src.close()
    plt.show()


if __name__ == "__main__":
    main()
