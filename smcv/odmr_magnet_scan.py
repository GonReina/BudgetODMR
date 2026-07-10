"""
Magnet-distance ODMR experiment (PC-controlled).

Procedure: put magnets on a translation stage, run a full ODMR sweep, then type
in the magnet position (e.g. the micrometer / stage reading in mm). The script
saves that sweep tagged with the position and asks for the next one. As the
magnet approaches, the axial field grows and the two NV dips separate -- plot it
afterwards with analysis/plot_magnet_scan.py.

It reuses the instrument connection + sweep machinery from odmr_smcv100b_pc.py
(same IPs, power, frequency range, integration, MW on/off), so configure the
experiment there. Only the per-position loop and file saving live here.

Each position -> one averaged spectrum:  <OUT_DIR>/pos_XX.csv  (freq_MHz,signal)
Index of positions:                      <OUT_DIR>/magnet_index.csv

Run on the PC:   python odmr_magnet_scan.py
"""

import glob
import os
from datetime import datetime

from expconfig import load_config
from odmr_smcv100b_pc import (
    SMCV100B, RedPitayaADC, measure_point, frange,
    SMCV_IP, SMCV_PORT, RP_IP, RP_PORT, POWER_DBM,
    F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ, MW_ON_OFF,
)

# ============================================================================
# CONFIG -- from config.json ("magnet" section)
# ============================================================================
_m = load_config()["magnet"]
N_SWEEPS_PER_POS = _m["n_sweeps_per_pos"]   # sweeps averaged per magnet position
OUT_DIR    = _m["out_dir"]
INDEX_FILE = os.path.join(OUT_DIR, "magnet_index.csv")
POSITION_UNITS = _m["position_units"]        # label for what you type in

PLAY_SOUND = True   # goofy beep jingle when each position's sweeps finish


def play_done_sound():
    """Loud, goofy 'done' jingle so you can wander off between positions."""
    if not PLAY_SOUND:
        return
    try:
        import winsound   # Windows only; plays through the PC audio at system volume
        jingle = [(523, 120), (784, 120), (523, 120), (784, 120),
                  (1047, 200), (880, 120), (1047, 340)]   # cartoon-y toot
        for _ in range(2):                                 # twice = harder to miss
            for freq, dur in jingle:
                winsound.Beep(freq, dur)
    except Exception:
        try:
            print("\a\a\a\a\a", end="", flush=True)        # terminal-bell fallback
        except Exception:
            pass


def run_sweep(src, adc, freqs):
    """Average N_SWEEPS_PER_POS full sweeps; return one signal list."""
    acc = [0.0] * len(freqs)
    for sweep in range(1, N_SWEEPS_PER_POS + 1):
        for i, f in enumerate(freqs):
            acc[i] += measure_point(src, adc, f)
        print(f"    sweep {sweep}/{N_SWEEPS_PER_POS} done")
    return [a / N_SWEEPS_PER_POS for a in acc]


def main():
    freqs = list(frange(F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ))
    os.makedirs(OUT_DIR, exist_ok=True)
    start_idx = len(glob.glob(os.path.join(OUT_DIR, "pos_*.csv")))

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    adc = RedPitayaADC(RP_IP, RP_PORT)
    src.configure(POWER_DBM)
    src.output(True)

    new_index = not os.path.exists(INDEX_FILE) or os.path.getsize(INDEX_FILE) == 0
    index = open(INDEX_FILE, "a")
    if new_index:
        index.write("idx,position,units,filename,timestamp\n")
        index.flush()

    print(f"\nMagnet ODMR scan: {F_START_MHZ}-{F_STOP_MHZ} MHz / {F_STEP_MHZ} "
          f"({len(freqs)} pts), {N_SWEEPS_PER_POS} sweeps/position.")
    print(f"Saving to {OUT_DIR}. Enter a position (in {POSITION_UNITS}) to run a "
          f"sweep; q or blank to quit.\n")

    k = start_idx
    try:
        while True:
            s = input(f"Magnet position ({POSITION_UNITS}): ").strip()
            if s.lower() in ("", "q", "quit", "exit"):
                break
            try:
                pos = float(s)
            except ValueError:
                print("  not a number -- try again (e.g. 12.5)")
                continue

            print(f"  running {N_SWEEPS_PER_POS} sweep(s) at {pos} {POSITION_UNITS} ...")
            sig = run_sweep(src, adc, freqs)

            fname = f"pos_{k:02d}.csv"
            ts = datetime.now().isoformat(timespec="seconds")
            with open(os.path.join(OUT_DIR, fname), "w") as f:
                f.write(f"# magnet ODMR, position={pos} {POSITION_UNITS}, {ts}\n")
                f.write(f"# power_dBm={POWER_DBM} sweeps={N_SWEEPS_PER_POS} "
                        f"mw_on_off={MW_ON_OFF}\n")
                f.write("freq_MHz,signal\n")
                for fr, v in zip(freqs, sig):
                    f.write(f"{fr:.4f},{v:.6f}\n")
            index.write(f"{k},{pos},{POSITION_UNITS},{fname},{ts}\n")
            index.flush()
            print(f"  saved {fname} (position {pos} {POSITION_UNITS})\n")
            play_done_sound()
            k += 1

        print(f"Done. {k - start_idx} position(s) recorded this session -> {OUT_DIR}")
    except KeyboardInterrupt:
        print(f"\nStopped. {k - start_idx} position(s) recorded -> {OUT_DIR}")
    finally:
        index.close()
        src.close()
        adc.close()


if __name__ == "__main__":
    main()
