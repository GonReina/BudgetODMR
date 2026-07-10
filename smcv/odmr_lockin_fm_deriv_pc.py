"""
FM DERIVATIVE lock-in ODMR (phase-sensitive).

Same FM dither as odmr_lockin_fm_pc.py, but instead of the phase-independent
magnitude, this demodulates the photodiode IN PHASE with the modulation reference.
The result is the SIGNED derivative of the ODMR line -- a dispersive curve that
crosses zero exactly at the resonance centre. That zero-crossing is the most
precise centre estimate available here, ideal for tracking small Zeeman shifts.

Extra wiring vs the other lock-in scripts: the phase reference must be a real
signal, so route the SMCV's LF-generator output to Red Pitaya IN2 (set the IN2
jumper to HV unless the LF level is <1 V). Photodiode stays on IN1. If your SMCV
can't output its LF generator, use odmr_lockin_fm_pc.py (magnitude) instead -- its
null between the two lobes still locates the centre, just without the sign.

Settings live in config.json ("lockin" + "sweep").  Run on the PC:
    python odmr_lockin_fm_deriv_pc.py
"""

from lockin_common import run

if __name__ == "__main__":
    run("fm_deriv")
