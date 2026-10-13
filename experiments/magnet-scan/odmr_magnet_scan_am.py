"""
Magnet-distance ODMR scan using AM lock-in.

Type a magnet position, it runs an AM lock-in sweep at that position and saves it,
then asks for the next. As the magnet approaches, the NV lines (up to 8, from the
four NV orientations) fan out. Analyse with experiments/magnet-scan/plot_magnet_lockin.py (MODE="am").

Settings: config.json ("sweep", "lockin", "magnet"). Configure AM once in the SMCV
Modulation menu (internal LF source, freq = f_mod_hz, depth). Run on the PC:
    python odmr_magnet_scan_am.py
"""

import os
import sys

# Shared instrument code lives in experiments/common/.
_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from lockin_common import run_magnet

if __name__ == "__main__":
    run_magnet("am")
