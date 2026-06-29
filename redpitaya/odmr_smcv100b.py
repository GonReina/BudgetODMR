"""
ODMR sweep driven by a Rohde & Schwarz SMCV100B vector signal generator.

The microwaves now come from the SMCV100B (-> Pasternack PE8301 amp -> antenna)
instead of the ADF4351. This script runs ON THE RED PITAYA: it reads the
photodiode on fast-ADC IN1 locally, and controls the SMCV100B over LAN using
raw SCPI on TCP port 5025 (no VISA / extra libraries needed). One script does
both, synchronised per frequency point.

Same noise strategy as odmr_sweep_robust.py:
  * each reading integrates whole 100 ms mains-clean blocks (averaged), and
  * MW_ON_OFF measures PL_on/PL_off per point so laser drift divides out.

Outputs (under data/):
    data/odmr_runs/run_01.csv ...  per sweep: freq_MHz,signal
                                   signal = PL_on/PL_off if MW_ON_OFF else mean V
    data/odmr_average.csv          running average, rewritten after every sweep

------------------------------------------------------------------------------
NETWORK SETUP (do this once)
  1. Connect the SMCV100B LAN port to the same network/switch as the Red Pitaya.
  2. On the instrument read its IP: Setup / System Config / Network (or the
     status bar). Put it in SMCV_IP below.
  3. From the Red Pitaya, check it's reachable:  ping <that IP>
The script sends *IDN? first and prints the reply, so you'll know immediately
if the link is good.
------------------------------------------------------------------------------

Run on the Red Pitaya as root:   sudo python3 odmr_smcv100b.py
Plot with (on the PC):           python3 analysis/average_sweeps.py
"""

import os
import socket
import time
from datetime import datetime

import rp

# ============================================================================
# CONFIG -- edit, then run
# ============================================================================
SMCV_IP   = "192.168.1.50"     # <-- SET THIS to your SMCV100B's IP address
SMCV_PORT = 5025               # R&S raw-SCPI socket port (default)

F_START_MHZ = 2800.0
F_STOP_MHZ  = 2940.0
F_STEP_MHZ  = 1.0

POWER_DBM   = -10.0            # SMCV output level. KEEP within the PE8301 amp's safe
                               # input range -- start low and raise it deliberately.

N_SWEEPS       = 20
INTEGRATION_MS = 100.0         # built from 100 ms mains-clean blocks (see odmr_sweep_robust)
SETTLE_S       = 0.02          # dwell after a freq change / output toggle (+ *OPC? sync)
MW_ON_OFF      = True          # measure PL_on/PL_off per point (cancels laser drift)

RUNS_DIR = "data/odmr_runs"
AVG_FILE = "data/odmr_average.csv"

# Fast ADC (photodiode on IN1)
ADC_CHANNEL = rp.RP_CH_1
DECIMATION  = rp.RP_DEC_1024   # fs = 122.07 kS/s; one 16384-sample block = 134 ms
FS_HZ       = 125e6 / 1024
N_BUF       = 16384

SUBREAD_MS = 100.0
N_SUBREAD  = min(N_BUF, int(round(SUBREAD_MS / 1000.0 * FS_HZ)))   # ~12207 samples
N_SUB      = max(1, int(round(INTEGRATION_MS / SUBREAD_MS)))


# ============================================================================
# SMCV100B over raw SCPI socket
# ============================================================================
class SMCV100B:
    def __init__(self, ip, port=5025, timeout=10.0):
        self.sock = socket.create_connection((ip, port), timeout=timeout)
        self.sock.settimeout(timeout)

    def write(self, cmd):
        self.sock.sendall((cmd + "\n").encode())

    def query(self, cmd):
        self.write(cmd)
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        return buf.decode(errors="replace").strip()

    def opc(self):
        self.query("*OPC?")           # blocks until the previous command finished

    def configure(self, power_dbm):
        idn = self.query("*IDN?")
        print(f"Connected: {idn}")
        self.write("*CLS")
        self.write(":SOURce:FREQuency:MODE CW")
        self.write(f":SOURce:POWer:LEVel:IMMediate:AMPLitude {power_dbm:.2f}")
        self.opc()

    def set_freq_mhz(self, freq_mhz):
        self.write(f":SOURce:FREQuency:CW {freq_mhz * 1e6:.0f}")
        self.opc()

    def output(self, on):
        self.write(":OUTPut:STATe " + ("ON" if on else "OFF"))
        self.opc()

    def close(self):
        try:
            self.output(False)
        except Exception:
            pass
        self.sock.close()


# ============================================================================
# Fast-ADC integration (mains-clean; identical scheme to odmr_sweep_robust.py)
# ============================================================================
def subread(buff):
    rp.rp_AcqReset()
    rp.rp_AcqSetDecimation(DECIMATION)
    rp.rp_AcqSetTriggerDelay(N_BUF)
    rp.rp_AcqStart()
    rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_NOW)
    while rp.rp_AcqGetBufferFillState()[1] is False:
        pass
    rp.rp_AcqGetOldestDataV(ADC_CHANNEL, N_BUF, buff)
    total = 0.0
    for i in range(N_SUBREAD):
        total += buff[i]
    return total / N_SUBREAD


def integrate(buff):
    """Median of N_SUB mains-clean sub-reads (median rejects a transient block)."""
    vals = sorted(subread(buff) for _ in range(N_SUB))
    n = len(vals)
    return vals[n // 2] if n % 2 else 0.5 * (vals[n // 2 - 1] + vals[n // 2])


def measure_point(src, buff, freq_mhz):
    src.set_freq_mhz(freq_mhz)
    time.sleep(SETTLE_S)
    pl_on = integrate(buff)
    if MW_ON_OFF:
        src.output(False)
        time.sleep(SETTLE_S)
        pl_off = integrate(buff)
        src.output(True)
        return pl_on / pl_off if pl_off else 0.0
    return pl_on


# ============================================================================
# Sweep driver with running average
# ============================================================================
def frange(start, stop, step):
    f = start
    while f <= stop + 1e-6:
        yield round(f, 6)
        f += step


def main():
    freqs = list(frange(F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ))
    os.makedirs(RUNS_DIR, exist_ok=True)
    avg_dir = os.path.dirname(AVG_FILE)
    if avg_dir:
        os.makedirs(avg_dir, exist_ok=True)

    integ_ms = N_SUB * N_SUBREAD / FS_HZ * 1e3
    print(f"ODMR (SMCV100B): {F_START_MHZ}-{F_STOP_MHZ} MHz / {F_STEP_MHZ} "
          f"({len(freqs)} pts), {N_SWEEPS} sweeps, {POWER_DBM:+.1f} dBm")
    print(f"  integrate {integ_ms:.0f} ms/reading ({N_SUB}x{SUBREAD_MS:.0f}ms), "
          f"MW_on_off={MW_ON_OFF}")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    src.output(True)

    rp.rp_Init()
    buff = rp.fBuffer(N_BUF)

    running_sum = [0.0] * len(freqs)
    completed = 0

    try:
        for run in range(1, N_SWEEPS + 1):
            run_path = os.path.join(RUNS_DIR, f"run_{run:02d}.csv")
            with open(run_path, "w") as f:
                f.write(f"# run {run}/{N_SWEEPS}, "
                        f"{datetime.now().isoformat(timespec='seconds')}\n")
                f.write(f"# source=SMCV100B power_dBm={POWER_DBM} integrate_ms={integ_ms:.1f} "
                        f"mw_on_off={MW_ON_OFF} signal={'PL_on/PL_off' if MW_ON_OFF else 'mean_V'}\n")
                f.write("freq_MHz,signal\n")
                for idx, freq in enumerate(freqs):
                    sig = measure_point(src, buff, freq)
                    f.write(f"{freq:.4f},{sig:.6f}\n")
                    running_sum[idx] += sig
            completed += 1

            with open(AVG_FILE, "w") as f:
                f.write(f"# running average over {completed} sweep(s), "
                        f"{datetime.now().isoformat(timespec='seconds')}\n")
                f.write("freq_MHz,signal\n")
                for idx, freq in enumerate(freqs):
                    f.write(f"{freq:.4f},{running_sum[idx]/completed:.6f}\n")

            print(f"  sweep {run}/{N_SWEEPS} done -> {AVG_FILE}")

        print(f"\nDone. {completed} sweeps averaged -> {AVG_FILE}")
    except KeyboardInterrupt:
        print(f"\nStopped early after {completed} sweep(s). Average in {AVG_FILE}")
    finally:
        src.close()
        rp.rp_Release()


if __name__ == "__main__":
    main()
