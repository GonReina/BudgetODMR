"""
FM lock-in ODMR sweeps across MW power -- for power broadening.

Runs FM lock-in sweeps at every power from POW_START to POW_STOP, with MORE
AVERAGING at low power (see powersweep_acq.AVG_SCHEDULE), and saves one
mean+std CSV per power. The companion analysis/plot_power_sweep_fm.py fits each
sweep and produces FWHM versus MW power.

Physics
-------
A CW ODMR line broadens with drive as

    Gamma^2 = Gamma_0^2 + a * P_mw          (P_mw linear, in mW)

so Gamma^2 against LINEAR power is a straight line: intercept = unbroadened
linewidth, slope set by the Rabi coupling (Omega ~ sqrt(P_mw)).

Why the averaging is tiered: below saturation the ODMR contrast falls roughly in
proportion to MW power, so the low-power end is the noisy end -- and it is also
the end that pins the Gamma_0 intercept. A flat N_AVG would spend the whole run
polishing points that were already good.

Why go so low in power: to measure Gamma_0 you need points where a*P << Gamma_0^2.
If your lowest power still shows a visibly broadened line, the intercept is an
extrapolation from data that never saw the unbroadened line.

Resuming
--------
Every sweep is written as soon as it is taken, and the combined mean+std file is
rebuilt after each one. Stop the script whenever you like -- at most one sweep is
lost, the combined files stay complete and analysable, and re-running continues
from the exact sweep it left off. Raise a tier in AVG_SCHEDULE and re-run and it
will simply top up the powers that are now short.

Because the individual sweeps are kept under sweeps/<power>/, you can also go
back afterwards and check for drift across a multi-day run.

Prerequisite: enable FM on the SMCV Modulation menu ONCE (internal source,
LF frequency = config lockin.f_mod_hz, deviation = lockin.fm_deviation_khz).

>>> FM DEVIATION vs LINEWIDTH <<<
The derivative approximation needs the deviation small compared with the
linewidth. At LOW power the line is narrowest and the measured width is most
inflated by the modulation. That is why the unmodulated companion
(odmr_power_sweep_dc_pc.py) exists: slower and noisier, but free of modulation
broadening. Trust DC for Gamma_0, FM for the high-power end.

>>> AMPLIFIER <<<
Set mw_chain.amp_in_chain in config.json to match the hardware. With the amplifier
(SMCV -> PE8301 isolator -> ZHL-16W-43-S+ -> antenna) the power grid moves to
POW_RANGE = -45..-16.5 dBm on the SMCV, and check_power_range() refuses to run
anything above the amplifier's linear limit (-16.4 dBm) or its +9 dBm damage
limit. Compression would make the broadening fit a fit to the amplifier, so
measure the real gain/P1dB before relaxing the limit.

Run on the PC:  python odmr_power_sweep_fm_pc.py
"""

import os
import time
from datetime import datetime

import numpy as np

from expconfig import load_config
from odmr_smcv100b_pc import SMCV100B, frange
from lockin_common import (
    RedPitayaLockin, demodulate, setup_smcv_modulation,
    teardown_smcv_modulation, F_MOD, FS_HZ, SETTLE_S, FM_DEV_HZ, N_BUF,
    SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
    F_START, F_STOP, F_STEP,
)
from powersweep_acq import (
    power_list, n_avg_for, count_existing, save_single_sweep, write_combined,
    print_plan, AVG_SCHEDULE, POW_RANGE, check_power_range, chain_header,
)

# ============================================================================
# SETTINGS
# ============================================================================
POW_START, POW_STOP = POW_RANGE   # SMCV dBm; set by config mw_chain.amp_in_chain
POW_STEP  = 0.5      # dB

# N_AVG per power band lives in powersweep_acq.AVG_SCHEDULE -- edit it there.

_cfg = load_config()
DATA_DIR = _cfg["paths"]["data_dir"]
OUT_DIR = os.path.join(DATA_DIR, "power_sweep_fm")

SMCV_MAX_DBM = 16.0


def set_power_dbm(src, dbm):
    """Set the SMCV CW output level (SMCV100B.configure only sets it once)."""
    src.set_power_dbm(dbm)


def sweep_once(src, rp, freqs):
    """One FM lock-in sweep -> list of R values."""
    out = []
    for fr in freqs:
        src.set_freq_mhz(fr)
        time.sleep(SETTLE_S)
        out.append(demodulate(rp.acquire_in1(), FS_HZ, F_MOD))
    return out


def main():
    powers = power_list(POW_START, POW_STOP, POW_STEP)
    if max(powers) > SMCV_MAX_DBM:
        raise SystemExit(f"POW_STOP {POW_STOP} dBm exceeds the SMCV limit "
                         f"({SMCV_MAX_DBM} dBm). Lower POW_STOP.")
    check_power_range(powers)

    freqs = list(frange(F_START, F_STOP, F_STEP))
    os.makedirs(OUT_DIR, exist_ok=True)
    pt_s = SETTLE_S + N_BUF / FS_HZ

    print(f"FM POWER SWEEP: {F_START}-{F_STOP} MHz / {F_STEP} ({len(freqs)} pts)")
    print(f"  f_mod = {F_MOD:.0f} Hz, FM deviation = {FM_DEV_HZ/1e6:.2f} MHz")
    print(f"  ~{pt_s*len(freqs):.0f} s per sweep -> {OUT_DIR}")
    todo = print_plan(powers, len(freqs), pt_s, OUT_DIR, "PLAN")
    if not todo:
        return

    header = [f"FM lock-in power sweep, {datetime.now().isoformat(timespec='seconds')}",
              f"f_mod_Hz={F_MOD:.0f} fm_deviation_MHz={FM_DEV_HZ/1e6:.4f} "
              f"signal=lockin_R",
              chain_header()]

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(powers[0])
    setup_smcv_modulation(src, "fm")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    t0 = time.time()
    taken = 0
    try:
        for p, have, want in todo:
            set_power_dbm(src, p)
            time.sleep(0.2)
            for k in range(have + 1, want + 1):
                vals = sweep_once(src, rp, freqs)
                save_single_sweep(OUT_DIR, p, k, freqs, vals)
                n = write_combined(OUT_DIR, p, freqs, header)
                taken += 1
                el = time.time() - t0
                print(f"  {p:+6.1f} dBm  sweep {k}/{want}  "
                      f"peak R = {np.max(vals)*1e3:7.3f} mV   "
                      f"[{taken} this session, {el/3600:.2f} h]")
        print(f"\nDone. {taken} sweep(s) this session -> {OUT_DIR}")
        print("Now run:  python analysis/plot_power_sweep_fm.py")
    except KeyboardInterrupt:
        print(f"\nStopped after {taken} sweep(s) this session. "
              f"Re-run to resume exactly where it left off.")
        raise SystemExit(1)
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
