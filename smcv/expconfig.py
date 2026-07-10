"""
Shared experiment configuration loader.

All the PC-side scripts (check_instruments.py, odmr_smcv100b_pc.py,
odmr_magnet_scan.py, analysis/plot_magnet_scan.py) read their settings from
config.json via this loader, so instrument IPs, frequency range, sweeps, etc.
live in ONE place.

Usage:
    from expconfig import load_config
    cfg = load_config()
    ip = cfg["instruments"]["smcv_ip"]

By default it loads config.json sitting next to this file. Override with the
BUDGETODMR_CONFIG environment variable or by passing a path to load_config().
A few derived values (fs_hz, n_subread, n_sub) are computed and added in.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(_HERE, "config.json")


def load_config(path=None):
    if path is None:
        path = os.environ.get("BUDGETODMR_CONFIG", DEFAULT_CONFIG)
    with open(path) as f:
        cfg = json.load(f)

    # --- derived values ---
    rp = cfg["redpitaya"]
    sw = cfg["sweep"]
    fs = 125e6 / rp["decimation"]
    rp["fs_hz"] = fs
    rp["n_subread"] = min(rp["n_buf"], int(round(rp["subread_ms"] / 1000.0 * fs)))
    sw["n_sub"] = max(1, int(round(sw["integration_ms"] / rp["subread_ms"])))
    return cfg


if __name__ == "__main__":
    import pprint
    pprint.pprint(load_config())
