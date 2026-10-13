"""
Magnet-distance ODMR scan using FM lock-in (magnitude).

Type a magnet position, it runs an FM (magnitude) lock-in sweep and saves it, then
asks for the next. Each NV line shows as the |derivative| (two lobes, null at the
centre). Analyse with experiments/magnet-scan/plot_magnet_lockin.py (MODE="fm").

Settings: config.json ("sweep", "lockin", "magnet"). Configure FM once in the SMCV
Modulation menu (internal LF source, freq = f_mod_hz, deviation). Run on the PC:
    python odmr_magnet_scan_fm.py
"""

import os
import sys

# Shared instrument code lives in experiments/common/.
_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from lockin_common import run_magnet

if __name__ == "__main__":
    run_magnet("fm")
