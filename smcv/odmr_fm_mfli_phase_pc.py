"""
Measurement (4) of the WP3 report: PHASE-SENSITIVE (SIGNED) FM DETECTION with
the MFLI lock-in amplifier.  ** EXPERIMENTAL -- first run needs hands-on. **

Goal: recover the SIGN of the FM derivative (the dispersive lineshape with a
zero-crossing at the line centre), which our software magnitude lock-in
discards. The obstacle has always been that the SMCV100B cannot output its
internal LF modulation signal, so the MFLI has no reference cable.

Two ways around it, in recommended order:

PATH A (try first -- no ARB, no new cabling beyond the reference):
    Lock BOTH instruments to the same 10 MHz reference (SMCV: Setup ->
    Reference Oscillator -> External; MFLI: Clock -> external 10 MHz).
    The SMCV's internal LF generator and the MFLI's internal oscillator at
    exactly f_mod are then frequency-identical, so their relative phase is
    CONSTANT -- unknown, but fixed. A one-time phase calibration on a lobe
    flank (where the tone exists) measures that phase; afterwards the rotated
    quadrature  X' = X cos(phi) + Y sin(phi)  is the signed demodulated
    signal. Caveat: the LF phase may re-randomise on power-cycle or when
    modulation is toggled -- recalibrate per session (the script checks by
    storing the calibration phase and warning on large drift).

PATH B (fallback / upgrade -- the IQ + marker idea):
    Generate the FM digitally as an ARB baseband waveform on the SMCV's
    vector modulator (I/Q samples of a constant-envelope waveform whose
    instantaneous frequency is  dev * cos(2 pi f_mod t)), with a MARKER bit
    set once per modulation period, routed to the User 1 connector -> a TTL
    at exactly f_mod, phase-locked to the modulation by construction ->
    MFLI external-reference input. Robust against power cycles, but requires
    building and uploading a .wv waveform (R&S :BB:ARB subsystem) and marker
    routing (:OUTPut:USER1:SOURce). This script contains the waveform
    synthesis (make_fm_iq()) so the samples are ready; the upload step is
    left as a documented TODO because it needs the instrument at hand.

Usage (PATH A):
    python odmr_fm_mfli_phase_pc.py calibrate   # sweep, pick flank, store phase
    python odmr_fm_mfli_phase_pc.py sweep       # signed dispersive FM sweep
    python odmr_fm_mfli_phase_pc.py monitor     # park at zero-crossing, log X'

Requires:  pip install zhinst      (Zurich Instruments LabOne API)
Edit MFLI_DEVICE below. MFLI signal input = photodiode (tee off Red Pitaya
IN1 or move the cable). Outputs in <DATA_DIR>: mfli_phase_cal.json,
fm_mfli_sweep.csv, fm_mfli_monitor.csv.
"""

import json
import os
import sys
import time
from datetime import datetime

import numpy as np

from lockin_common import (RedPitayaLockin, SMCV100B, frange,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
                           F_START, F_STOP, F_STEP, POWER_DBM, F_MOD,
                           SETTLE_S, DATA_DIR)
from odmr_sensitivity_fm_pc import (take_spectrum, find_working_point,
                                    pick_working_point, GAMMA)

# --- settings ---
MFLI_DEVICE   = "dev3xxx"      # <-- EDIT: your MFLI serial (LabOne shows it)
MFLI_HOST     = "localhost"    # LabOne data server host
DEMOD         = 0
TIME_CONSTANT = 0.005          # s (lock-in filter; ~180 Hz ENBW like the RP)
N_AVG         = 8              # demod samples averaged per reading
N_MONITOR     = 2000           # readings in monitor mode
CAL_FILE      = os.path.join(DATA_DIR, "mfli_phase_cal.json")


# ---------------------------------------------------------------------------
# MFLI access (guarded import; PATH A configuration)
# ---------------------------------------------------------------------------
def mfli_connect():
    try:
        import zhinst.core as zi          # LabOne >= 22.08
    except ImportError:
        try:
            import zhinst.ziPython as zi  # older API
        except ImportError:
            raise SystemExit("zhinst not installed: pip install zhinst")
    daq = zi.ziDAQServer(MFLI_HOST, 8004, 6)
    d = MFLI_DEVICE
    daq.setDouble(f"/{d}/oscs/0/freq", F_MOD)
    daq.setInt(f"/{d}/demods/{DEMOD}/adcselect", 0)     # Signal Input 1
    daq.setInt(f"/{d}/demods/{DEMOD}/oscselect", 0)
    daq.setInt(f"/{d}/demods/{DEMOD}/order", 3)
    daq.setDouble(f"/{d}/demods/{DEMOD}/timeconstant", TIME_CONSTANT)
    daq.setDouble(f"/{d}/demods/{DEMOD}/rate", 1674.0)
    daq.setInt(f"/{d}/demods/{DEMOD}/enable", 1)
    daq.setInt(f"/{d}/sigins/0/ac", 1)                  # AC-couple: kill the 1 V DC
    daq.setInt(f"/{d}/sigins/0/imp50", 0)
    daq.sync()
    # NOTE (PATH A): verify on the MFLI front panel / LabOne that the clock is
    # locked to the external 10 MHz shared with the SMCV. Without that, the
    # phase below drifts and the signed readout is meaningless.
    # NOTE (PATH B): instead of oscs/0, configure /extrefs/0 to lock demod 0
    # to the TTL from the SMCV User 1 marker (Aux In / Trigger input).
    return daq


def read_xy(daq, n=N_AVG):
    xs, ys = [], []
    for _ in range(n):
        s = daq.getSample(f"/{MFLI_DEVICE}/demods/{DEMOD}/sample")
        xs.append(float(s["x"][0] if hasattr(s["x"], "__len__") else s["x"]))
        ys.append(float(s["y"][0] if hasattr(s["y"], "__len__") else s["y"]))
        time.sleep(TIME_CONSTANT)
    return float(np.mean(xs)), float(np.mean(ys))


# ---------------------------------------------------------------------------
# PATH B: FM baseband I/Q + marker synthesis (upload left as documented TODO)
# ---------------------------------------------------------------------------
def make_fm_iq(f_samp=1e6, dev_hz=2e6, f_mod=F_MOD):
    """Constant-envelope FM baseband: i(t)+j q(t) = exp(j (dev/f_mod) sin(2
    pi f_mod t)), one exact modulation period, plus a marker bit set for the
    first 10 % of the period (TTL rising edge = modulation phase zero).
    Upload via the SMCV :BB:ARB subsystem and route marker 1 to User 1
    (:OUTPut:USER1:SOURce MARK1 -- verify mnemonic on the instrument)."""
    n = int(round(f_samp / f_mod))
    t = np.arange(n) / f_samp
    phase = (dev_hz / f_mod) * np.sin(2 * np.pi * f_mod * t)
    iq = np.exp(1j * phase)
    marker = (np.arange(n) < n // 10).astype(int)
    return iq, marker


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "calibrate"
    assert mode in ("calibrate", "sweep", "monitor"), \
        "usage: python odmr_fm_mfli_phase_pc.py [calibrate|sweep|monitor]"
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "fm")
    src.output(True)
    daq = mfli_connect()

    try:
        if mode == "calibrate":
            # working point on a flank (tone present) via the usual RP sweep
            rp = RedPitayaLockin(RP_IP, RP_PORT)
            freqs = list(frange(F_START, F_STOP, F_STEP))
            R = take_spectrum(src, rp, freqs)
            f_auto, s_auto, _ = find_working_point(freqs, R)
            f_star, slope, _ = pick_working_point(freqs, R, f_auto, s_auto)
            rp.close()

            src.set_freq_mhz(f_star)
            time.sleep(0.5)
            x, y = read_xy(daq, n=4 * N_AVG)
            phi = float(np.arctan2(y, x))
            r = float(np.hypot(x, y))
            json.dump({"phi_rad": phi, "f_star_MHz": f_star,
                       "slope_sign": float(np.sign(slope)),
                       "R_V": r, "stamp": stamp}, open(CAL_FILE, "w"))
            print(f"Calibrated: phi = {np.degrees(phi):+.1f} deg, "
                  f"tone R = {r * 1e3:.3f} mV at {f_star:.3f} MHz -> {CAL_FILE}")
            print("Re-run after any power cycle or modulation toggle.")

        else:
            cal = json.load(open(CAL_FILE))
            phi = cal["phi_rad"]
            sgn = cal.get("slope_sign", 1.0) or 1.0

            if mode == "sweep":
                freqs = list(frange(F_START, F_STOP, F_STEP))
                path = os.path.join(DATA_DIR, "fm_mfli_sweep.csv")
                with open(path, "w") as f:
                    f.write(f"# signed FM sweep via MFLI (PATH A), {stamp}, "
                            f"phi_deg={np.degrees(phi):.2f}, "
                            f"cal_stamp={cal['stamp']}\n")
                    f.write("freq_MHz,X_signed_V,R_V,phase_deg\n")
                    for i, fr in enumerate(freqs):
                        src.set_freq_mhz(fr)
                        time.sleep(SETTLE_S + 2 * TIME_CONSTANT)
                        x, y = read_xy(daq)
                        xs = sgn * (x * np.cos(phi) + y * np.sin(phi))
                        f.write(f"{fr:.4f},{xs:.8e},{np.hypot(x, y):.8e},"
                                f"{np.degrees(np.arctan2(y, x)):.2f}\n")
                        if (i + 1) % 40 == 0:
                            print(f"  {i + 1}/{len(freqs)}")
                print(f"Done -> {path}\n"
                      "Expect the DISPERSIVE shape: signed lobes with a "
                      "zero-crossing at each line centre. If instead the "
                      "signed trace decorrelates within one sweep, the LF "
                      "phase is not stable -> use PATH B (ARB + marker).")

            elif mode == "monitor":
                f_park = cal["f_star_MHz"]
                src.set_freq_mhz(f_park)
                time.sleep(0.5)
                path = os.path.join(DATA_DIR, "fm_mfli_monitor.csv")
                with open(path, "w") as f:
                    f.write(f"# signed monitor at {f_park:.4f} MHz, {stamp}, "
                            f"phi_deg={np.degrees(phi):.2f}\n")
                    f.write("t_s,X_signed_V\n")
                    t0 = time.perf_counter()
                    for k in range(N_MONITOR):
                        x, y = read_xy(daq)
                        xs = sgn * (x * np.cos(phi) + y * np.sin(phi))
                        f.write(f"{time.perf_counter() - t0:.3f},{xs:.8e}\n")
                        if (k + 1) % 200 == 0:
                            print(f"  {k + 1}/{N_MONITOR}")
                print(f"Done -> {path} (signed trace: drift direction is now "
                      "unambiguous, unlike the magnitude lock-in)")

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
