"""
Lock-in ODMR with FREQUENCY modulation (FM) -- derivative detection.

The SMCV microwave frequency is dithered by ~a linewidth at f_mod (a few kHz).
The photodiode's response at f_mod is proportional to the DERIVATIVE of the ODMR
line, so the lock-in magnitude shows two lobes with a null at the line centre --
a very precise way to locate the dip (ideal for measuring small Zeeman splittings).

Wiring: none for modulation -- the SMCV modulates itself internally (K197 LF gen).
Only the photodiode --> Red Pitaya IN1. Set the SMCV Modulation menu to FM, source
Internal/LF, LF frequency = config f_mod_hz, deviation = fm_deviation_khz (the
script also tries to set these over SCPI). Settings live in config.json.

Note: this uses a phase-independent magnitude lock-in, so the line centre appears
as the NULL between the two derivative lobes. A signed (dispersive) version would
need a hardware phase reference, which this SMCV can't easily expose -- the null
is perfectly usable for locating the dip.

Run on the PC:  python odmr_lockin_fm_pc.py
"""

from lockin_common import run

if __name__ == "__main__":
    run("fm")
