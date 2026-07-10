"""
Magnet-distance ODMR scan using FM derivative (phase-sensitive) lock-in.

Type a magnet position, it runs an FM-derivative lock-in sweep and saves it, then
asks for the next. Each NV line shows as a signed dispersive derivative (zero
crossing at the centre) -- the most precise centre estimate. Analyse with
analysis/plot_magnet_lockin.py (MODE="fm_deriv").

Requires the SMCV LF-generator reference on Red Pitaya IN2 (see odmr_lockin_fm_deriv_pc.py).
Settings: config.json. Configure FM once in the SMCV Modulation menu. Run on the PC:
    python odmr_magnet_scan_fm_deriv.py
"""

from lockin_common import run_magnet

if __name__ == "__main__":
    run_magnet("fm_deriv")
