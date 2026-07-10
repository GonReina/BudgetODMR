"""
Lock-in ODMR with AMPLITUDE modulation (AM).

The SMCV microwave amplitude is modulated at f_mod (a few kHz); the photodiode's
response at f_mod, demodulated on the Red Pitaya, traces the ODMR line as a PEAK
in the lock-in magnitude. Much faster than DC step-and-dwell because detection
sits in a narrow band above mains/1/f noise.

Wiring: none for modulation -- the SMCV modulates itself internally (K197 LF gen).
Only the photodiode --> Red Pitaya IN1. Set the SMCV Modulation menu to AM, source
Internal/LF, LF frequency = config f_mod_hz, depth = am_depth_pct (the script also
tries to set these over SCPI). All settings live in config.json ("lockin" section).

Run on the PC:  python odmr_lockin_am_pc.py
Plot with:      python analysis/average_sweeps.py  (point RUNS_DIR at the AM run folder)
"""

from lockin_common import run

if __name__ == "__main__":
    run("am")
