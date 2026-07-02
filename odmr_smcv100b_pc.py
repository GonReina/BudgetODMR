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

# ============================================================================
# CONFIG -- edit, then run
# ============================================================================
SMCV_IP = "169.254.2.20"      # <-- SMCV100B IP (its NIC/subnet on your PC)
RP_IP   = "192.168.137.150"      # <-- Red Pitaya IP (its NIC/subnet on your PC)
SMCV_PORT = 5025
RP_PORT   = 5000

F_START_MHZ = 2700.0
F_STOP_MHZ  = 3000.0
F_STEP_MHZ  = 1.0

POWER_DBM   = 16.0           # SMCV output level -- keep within the PE8301's safe input
N_SWEEPS       = 20
INTEGRATION_MS = 100.0        # built from 100 ms mains-clean blocks
SETTLE_S       = 0.02         # dwell after a freq change / output toggle
MW_ON_OFF      = True         # measure PL_on/PL_off per point

DATA_DIR = r"C:\Users\qute\Downloads\rsattempt\29-06-2026"
RUNS_DIR = os.path.join(DATA_DIR, "odmr_runs_magnet")
AVG_FILE = os.path.join(DATA_DIR, "odmr_average.csv")

# Red Pitaya fast-ADC acquisition
RP_DECIMATION = 1024          # fs = 122.07 kS/s; one 16384-sample block = 134 ms
FS_HZ = 125e6 / RP_DECIMATION
N_BUF = 16384
RP_INPUT_GAIN = "LV"          # match the physical IN1 jumper: "LV" (+/-1V) or "HV" (+/-20V)

SUBREAD_MS = 100.0
N_SUBREAD  = min(N_BUF, int(round(SUBREAD_MS / 1000.0 * FS_HZ)))   # ~12207 samples
N_SUB      = max(1, int(round(INTEGRATION_MS / SUBREAD_MS)))


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
        self.s = Scpi(ip, port, term="\r\n")
        # quick reachability check (raises if the SCPI server isn't running)
        self.s.write("ACQ:RST")
        self.s.query("ACQ:DEC?")
        print(f"Red Pitaya SCPI server reachable at {ip}:{port}")

    def acquire(self):
        """Capture one buffer and return it as a list of float volts."""
        self.s.write("ACQ:RST")
        self.s.write(f"ACQ:DEC {RP_DECIMATION}")
        try:
            self.s.write(f"ACQ:SOUR1:GAIN {RP_INPUT_GAIN}")   # tell SW the jumper setting
        except Exception:
            pass
        self.s.write("ACQ:START")
        self.s.write("ACQ:TRIG NOW")
        time.sleep(N_BUF / FS_HZ + 0.03)        # wait for the buffer to fill (~134 ms)
        raw = self.s.query("ACQ:SOUR1:DATA?")
        raw = raw.strip().strip("{}")
        return [float(x) for x in raw.split(",") if x.strip()]

    def close(self):
        self.s.close()


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
