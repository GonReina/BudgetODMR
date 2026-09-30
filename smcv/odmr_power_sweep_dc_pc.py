"""
Conventional (unmodulated) ODMR sweeps across MW power.

The no-modulation companion to odmr_power_sweep_fm_pc.py. Each point is a
DC-integrated PL_on/PL_off ratio, as in odmr_smcv100b_pc.py, so the measured
lineshape is a TRUE Lorentzian -- no modulation broadening, no derivative model,
nothing to deconvolve. This is the reference measurement for the zero-power
intercept.

Why run both
------------
    FM lock-in     better SNR, much faster, but the measured width is convolved
                   with the FM deviation -- worst at LOW power, where the line is
                   narrowest and where you most want a clean Gamma_0.

    DC (this one)  slower and noisier, but the width is the real width.

Agreement at high power validates the FM analysis; divergence at low power is
your modulation broadening.

Physics: Gamma^2 = Gamma_0^2 + a * P_mw (P_mw linear, mW), so Gamma^2 against
linear power is a straight line -- intercept = unbroadened linewidth, slope set
by the Rabi coupling.

Why the averaging is tiered: below saturation the contrast falls roughly in
proportion to MW power, so the low-power end is both the noisiest and the end
that pins the Gamma_0 intercept. See powersweep_acq.AVG_SCHEDULE.

Resuming
--------
Every sweep is written as soon as it is taken and the combined mean+std file is
rebuilt after each one. Stop whenever you like -- at most one sweep is lost, the
combined files stay complete and analysable, and re-running continues from the
exact sweep it left off. Raising a tier in AVG_SCHEDULE and re-running simply
tops up the powers that are now short. The individual sweeps are kept under
sweeps/<power>/ so you can check afterwards for drift across a multi-day run.

>>> IF YOU RECONNECT THE AMPLIFIER <<<
With a power amplifier in the chain, compression means the power at the antenna
stops following the power you set, and the broadening fit becomes a fit to the
amplifier's compression curve. Characterise it first and cap POW_STOP at its
linear limit. Driving direct from the SMCV, as here, this does not apply.

Run on the PC:  python odmr_power_sweep_dc_pc.py
"""

import os
import time
from datetime import datetime

import numpy as np

from expconfig import load_config
from odmr_smcv100b_pc import (
    SMCV100B, RedPitayaADC, frange, integrate,
    SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
    F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ, SETTLE_S, MW_ON_OFF,
    N_SUB, N_SUBREAD, FS_HZ,
)
from powersweep_acq import (
    power_list, n_avg_for, count_existing, save_single_sweep, write_combined,
    print_plan, AVG_SCHEDULE,
)

# ============================================================================
# SETTINGS
# ============================================================================
POW_START = -15.0    # dBm
POW_STOP  = 16.0     # dBm
POW_STEP  = 0.5      # dB

# N_AVG per power band lives in powersweep_acq.AVG_SCHEDULE -- edit it there.

_cfg = load_config()
DATA_DIR = _cfg["paths"]["data_dir"]
OUT_DIR = os.path.join(DATA_DIR, "power_sweep_dc")

SMCV_MAX_DBM = 16.0


def set_power_dbm(src, dbm):
    src.s.write(f":SOURce:POWer:LEVel:IMMediate:AMPLitude {dbm:.2f}")
    src.s.query("*OPC?")


def measure_point(src, adc, freq_mhz):
    """PL_on/PL_off at one frequency (or raw PL if mw_on_off is disabled).

    Leaves the MW output ON at exit so the caller can keep sweeping.
    """
    src.set_freq_mhz(freq_mhz)
    time.sleep(SETTLE_S)
    pl_on = integrate(adc)
    if not MW_ON_OFF:
        return pl_on
    src.output(False)
    time.sleep(SETTLE_S)
    pl_off = integrate(adc)
    src.output(True)
    return pl_on / pl_off if pl_off else 0.0


def sweep_once(src, adc, freqs):
    return [measure_point(src, adc, fr) for fr in freqs]


def main():
    powers = power_list(POW_START, POW_STOP, POW_STEP)
    if max(powers) > SMCV_MAX_DBM:
        raise SystemExit(f"POW_STOP {POW_STOP} dBm exceeds the SMCV limit "
                         f"({SMCV_MAX_DBM} dBm). Lower POW_STOP.")

    freqs = list(frange(F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ))
    os.makedirs(OUT_DIR, exist_ok=True)

    integ_ms = N_SUB * N_SUBREAD / FS_HZ * 1e3
    pt_s = (2 if MW_ON_OFF else 1) * (integ_ms / 1e3 + SETTLE_S)

    print(f"DC POWER SWEEP: {F_START_MHZ}-{F_STOP_MHZ} MHz / {F_STEP_MHZ} "
          f"({len(freqs)} pts)")
    print(f"  {integ_ms:.0f} ms/reading, mw_on_off={MW_ON_OFF}")
    print(f"  ~{pt_s*len(freqs):.0f} s per sweep -> {OUT_DIR}")
    todo = print_plan(powers, len(freqs), pt_s, OUT_DIR, "PLAN")
    if not todo:
        return

    header = [f"DC (unmodulated) power sweep, "
              f"{datetime.now().isoformat(timespec='seconds')}",
              f"integrate_ms={integ_ms:.1f} mw_on_off={MW_ON_OFF} "
              f"signal={'PL_on/PL_off' if MW_ON_OFF else 'mean_V'}"]

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    adc = RedPitayaADC(RP_IP, RP_PORT)
    src.configure(powers[0])
    src.output(True)

    t0 = time.time()
    taken = 0
    try:
        for p, have, want in todo:
            set_power_dbm(src, p)
            time.sleep(0.2)
            for k in range(have + 1, want + 1):
                vals = sweep_once(src, adc, freqs)
                save_single_sweep(OUT_DIR, p, k, freqs, vals)
                n = write_combined(OUT_DIR, p, freqs, header)
                taken += 1
                med = float(np.median(vals))
                contrast = (med - float(np.min(vals))) / med * 100 if med else 0.0
                el = time.time() - t0
                print(f"  {p:+6.1f} dBm  sweep {k}/{want}  "
                      f"contrast = {contrast:5.2f} %   "
                      f"[{taken} this session, {el/3600:.2f} h]")
        print(f"\nDone. {taken} sweep(s) this session -> {OUT_DIR}")
        print("Now run:  python analysis/plot_power_sweep_dc.py")
    except KeyboardInterrupt:
        print(f"\nStopped after {taken} sweep(s) this session. "
              f"Re-run to resume exactly where it left off.")
    finally:
        adc.close()
        src.close()


if __name__ == "__main__":
    main()
