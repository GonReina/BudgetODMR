"""
ODMR sweep controlled entirely from the PC (no script runs on the Red Pitaya).

Topology: both instruments plug into the PC (two network interfaces -- e.g. the
built-in Ethernet plus a USB-Ethernet adapter). The PC opens two SCPI sockets:

    PC --SCPI 5025--> R&S SMCV100B        (sets MW frequency / power / output)
    PC --SCPI 5000--> Red Pitaya server   (reads photodiode on fast-ADC IN1)

Microwave chain: SMCV100B -> Pasternack PE8301 amp -> antenna.
Detector: PDA10A2 (or similar) -> Red Pitaya IN1.

PREREQUISITE on the Red Pitaya (once): start its SCPI server -- open the Red
Pitaya web interface and run "SCPI server" (it listens on TCP port 5000). No
other software needs to run on the Pitaya.

Pure Python standard library -- no pyvisa, no rp module. Runs on Windows/Mac/Linux.

Same noise strategy as the on-Pitaya version: each reading averages whole 100 ms
mains-clean ADC blocks, and MW_ON_OFF measures PL_on/PL_off per point so laser
drift divides out.

Outputs (compatible with analysis/average_sweeps.py):
    <DATA_DIR>/odmr_runs/run_01.csv ...   per sweep: freq_MHz,signal
    <DATA_DIR>/odmr_average.csv           running average, rewritten each sweep

Run on the PC:   python odmr_smcv100b_pc.py
"""

import os
import socket
import time
from datetime import datetime

from redpitaya_scope import RedPitayaScope

# ============================================================================
# CONFIG -- all settings live in config.json (edit that, not this file)
# ============================================================================
from expconfig import load_config

_cfg = load_config()
_i, _s, _r, _p = _cfg["instruments"], _cfg["sweep"], _cfg["redpitaya"], _cfg["paths"]

SMCV_IP, SMCV_PORT = _i["smcv_ip"], _i["smcv_port"]
RP_IP,   RP_PORT   = _i["rp_ip"],   _i["rp_port"]

F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ = _s["f_start_mhz"], _s["f_stop_mhz"], _s["f_step_mhz"]
POWER_DBM      = _s["power_dbm"]
N_SWEEPS       = _s["n_sweeps"]
INTEGRATION_MS = _s["integration_ms"]
SETTLE_S       = _s["settle_s"]
MW_ON_OFF      = _s["mw_on_off"]

DATA_DIR = _p["data_dir"]
RUNS_DIR = os.path.join(DATA_DIR, _p["runs_subdir"])
AVG_FILE = os.path.join(DATA_DIR, _p["avg_file"])

# Red Pitaya fast-ADC acquisition
RP_DECIMATION = _r["decimation"]
N_BUF         = _r["n_buf"]
RP_INPUT_GAIN = _r["input_gain"]
SUBREAD_MS    = _r["subread_ms"]
FS_HZ         = _r["fs_hz"]         # derived in expconfig
N_SUBREAD     = _r["n_subread"]     # derived
N_SUB         = _s["n_sub"]         # derived


# ============================================================================
# Minimal SCPI-over-socket client (configurable line terminator)
# ============================================================================
class Scpi:
    def __init__(self, ip, port, term="\n", timeout=15.0):
        self.term = term.encode()
        self.sock = socket.create_connection((ip, port), timeout=timeout)
        self.sock.settimeout(timeout)

    def write(self, cmd):
        self.sock.sendall(cmd.encode() + self.term)

    def query(self, cmd):
        self.write(cmd)
        buf = b""
        while not buf.endswith(self.term):
            chunk = self.sock.recv(65536)
            if not chunk:
                break
            buf += chunk
        return buf[: -len(self.term)].decode(errors="replace").strip()

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


# ============================================================================
# SMCV100B (SCPI, '\n' terminated)
# ============================================================================
class SMCV100B:
    def __init__(self, ip, port):
        self.s = Scpi(ip, port, term="\n")

    def configure(self, power_dbm):
        print(f"SMCV100B: {self.s.query('*IDN?')}")
        self.s.write("*CLS")
        self.s.write(":SOURce:FREQuency:MODE CW")
        self.s.write(f":SOURce:POWer:LEVel:IMMediate:AMPLitude {power_dbm:.2f}")
        self.s.query("*OPC?")

    def set_freq_mhz(self, freq_mhz):
        self.s.write(f":SOURce:FREQuency:CW {freq_mhz * 1e6:.0f}")
        self.s.query("*OPC?")

    def output(self, on):
        self.s.write(":OUTPut:STATe " + ("ON" if on else "OFF"))
        self.s.query("*OPC?")

    def close(self):
        try:
            self.output(False)
        except Exception:
            pass
        self.s.close()


# ============================================================================
# Red Pitaya ADC via its SCPI server ('\r\n' terminated)
# ============================================================================
class RedPitayaADC:
    def __init__(self, ip, port):
        self.scope = RedPitayaScope(ip, port)
        print(f"Red Pitaya SCPI server reachable at {ip}:{port}")

    def acquire(self):
        """Capture one fill-synchronised buffer (no stale/zero samples) -> np.array."""
        return self.scope.acquire((1,), RP_DECIMATION, RP_INPUT_GAIN)

    def close(self):
        self.scope.close()


# ============================================================================
# Integration (mains-clean; same scheme as the on-Pitaya scripts)
# ============================================================================
def subread(adc):
    data = adc.acquire()
    n = min(N_SUBREAD, len(data))
    if n == 0:
        raise RuntimeError("Red Pitaya returned no samples -- check the SCPI server")
    return sum(data[:n]) / n


def integrate(adc):
    vals = sorted(subread(adc) for _ in range(N_SUB))
    n = len(vals)
    return vals[n // 2] if n % 2 else 0.5 * (vals[n // 2 - 1] + vals[n // 2])


def measure_point(src, adc, freq_mhz):
    src.set_freq_mhz(freq_mhz)
    time.sleep(SETTLE_S)
    pl_on = integrate(adc)
    if MW_ON_OFF:
        src.output(False)
        time.sleep(SETTLE_S)
        pl_off = integrate(adc)
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
    if os.path.dirname(AVG_FILE):
        os.makedirs(os.path.dirname(AVG_FILE), exist_ok=True)

    integ_ms = N_SUB * N_SUBREAD / FS_HZ * 1e3
    print(f"ODMR (SMCV100B, PC-controlled): {F_START_MHZ}-{F_STOP_MHZ} MHz / "
          f"{F_STEP_MHZ} ({len(freqs)} pts), {N_SWEEPS} sweeps, {POWER_DBM:+.1f} dBm")
    print(f"  integrate {integ_ms:.0f} ms/reading ({N_SUB}x{SUBREAD_MS:.0f}ms), "
          f"MW_on_off={MW_ON_OFF}")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    adc = RedPitayaADC(RP_IP, RP_PORT)
    src.configure(POWER_DBM)
    src.output(True)

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
                    sig = measure_point(src, adc, freq)
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
        adc.close()


if __name__ == "__main__":
    main()
