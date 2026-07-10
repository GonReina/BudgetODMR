"""
Watch a PARKED FM lock-in signal live for ~10 s, beeping when recording starts --
a quick "wave a magnet at it" test.

Park the SMCV on the SIDE (slope) of a resonance with FM modulation on, then this
records the lock-in magnitude R continuously and plots it against time in real
time. It beeps once at the start (your cue to move a magnet near the diamond) and
once at the end. When the magnet shifts the NV lines, the resonance moves under the
parked frequency and R changes -- so a bump/step in the live trace means the setup
is responding to the field.

It reuses the wideband acquisition trick (one contiguous ADC record demodulated in
short overlapping blocks) so the trace is smooth, not one-point-per-SCPI-round-trip:

    decimation 8192 -> fs 15259 Hz (keeps f_mod = 5 kHz demodulable), 1.07 s/record
    block 128 (~8.4 ms), hop 64 (50% overlap) -> a lock-in point every ~4.2 ms

Tips:
  * Set PARK_FREQ_MHZ on the STEEPEST part of a line you found in a sweep (not the
    exact centre -- the slope is where detuning gives the biggest R change).
  * FM modulation must be configured in the SMCV menu (depth/freq); this script just
    enables it, same as the other lock-in scripts.

Run on the PC:  python odmr_watch_magnet_pc.py
Outputs in <DATA_DIR>: watch_magnet.csv, watch_magnet.png
"""

import os
import time
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt

from lockin_common import (RedPitayaLockin, SMCV100B, demodulate,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           _beep, SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
                           POWER_DBM, F_MOD, RP_GAIN, DATA_DIR)

# ===== CONFIGURATION =====
PARK_FREQ_MHZ = 2865.0       # park on the SLOPE of a resonance for maximum response
RECORD_S      = 10.0         # how long to watch (seconds)
DECIM_WB      = 8192         # fs 15259 Hz, 1.07 s/record (keeps f_mod=5 kHz demodulable)
BLOCK         = 128          # demod block (~8.4 ms)
HOP           = 64           # 50% overlap -> a lock-in point every ~4.2 ms
PARK_SETTLE_S = 0.5          # settle after parking before recording

FS_WB = 125e6 / DECIM_WB
assert F_MOD < 0.43 * FS_WB, (
    f"f_mod = {F_MOD:.0f} Hz too close to wideband Nyquist ({FS_WB/2:.0f} Hz) -- "
    f"lower lockin.f_mod_hz or DECIM_WB.")


def block_demod(v, fs=FS_WB, f_mod=F_MOD, block=BLOCK, hop=HOP):
    """Demodulate one contiguous record in overlapping blocks -> (t_s, R_volts)."""
    v = np.asarray(v, float)
    starts = range(0, len(v) - block + 1, hop)
    t = np.array([(s + block / 2) / fs for s in starts])
    R = np.array([demodulate(v[s:s + block], fs, f_mod) for s in starts])
    return t, R


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "fm")
    src.set_freq_mhz(PARK_FREQ_MHZ)
    src.output(True)
    time.sleep(PARK_SETTLE_S)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    ts, rs = [], []
    base, base_line = None, None
    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    (line,) = ax.plot([], [], lw=1.0, color="tab:blue")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("lock-in R (mV)")
    ax.set_title(f"Parked at {PARK_FREQ_MHZ:.1f} MHz -- move the magnet")
    ax.grid(True, alpha=0.3)

    try:
        print(f"\nParked at {PARK_FREQ_MHZ} MHz, {POWER_DBM:+.0f} dBm, FM on.")
        print(f"Recording ~{RECORD_S:.0f} s. BEEP = start moving the magnet near "
              f"the diamond.\n")
        _beep()                                   # <-- start cue
        t0 = time.perf_counter()
        while True:
            t_buf = time.perf_counter() - t0
            v = rp.scope.acquire((1,), DECIM_WB, RP_GAIN, fill_timeout_s=5.0)
            t_blk, r_blk = block_demod(v)
            for tt, rr in zip(t_blk, r_blk):
                ts.append(t_buf + tt)
                rs.append(rr * 1e3)               # mV

            if base is None and rs:               # mark the starting level once
                base = float(np.median(rs))
                base_line = ax.axhline(base, color="0.6", lw=0.8, ls=":",
                                       label="start level")
                ax.legend(loc="upper right")

            line.set_data(ts, rs)
            ax.relim()
            ax.autoscale_view()
            fig.canvas.draw()
            fig.canvas.flush_events()
            plt.pause(0.001)

            if time.perf_counter() - t0 >= RECORD_S:
                break

        _beep()                                   # <-- end cue
        span = ts[-1] if ts else 0.0
        dev = (max(rs) - min(rs)) if rs else 0.0
        print(f"Done: {len(ts)} points over {span:.1f} s, "
              f"R range {dev:.3f} mV about {base:.3f} mV.")

        csv_path = os.path.join(DATA_DIR, "watch_magnet.csv")
        with open(csv_path, "w") as f:
            f.write(f"# parked {PARK_FREQ_MHZ} MHz, {stamp}, "
                    f"field-point rate ~{FS_WB / HOP:.0f} Hz, f_mod {F_MOD:.0f} Hz\n")
            f.write("t_s,lockin_R_mV\n")
            for tt, rr in zip(ts, rs):
                f.write(f"{tt:.4f},{rr:.5f}\n")

        png_path = os.path.join(DATA_DIR, "watch_magnet.png")
        ax.set_title(f"Parked at {PARK_FREQ_MHZ:.1f} MHz  "
                     f"({len(ts)} pts over {span:.1f} s)")
        fig.tight_layout()
        fig.savefig(png_path, dpi=140)
        print(f"Saved {csv_path}\n      {png_path}")

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.output(False)
        src.close()

    plt.ioff()
    plt.show()


if __name__ == "__main__":
    main()
