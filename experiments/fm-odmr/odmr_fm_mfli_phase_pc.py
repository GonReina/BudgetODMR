"""
PHASE-SENSITIVE FM ODMR with the Zurich Instruments MFLI, compared with a plain
DC (MW on/off) sweep on the same grid.  Question: does a phase-sensitive FM
sweep give a better SNR than a DC ODMR sweep?

WIRING
  * SMCV100B REF OUT (rear BNC) -> MFLI "Clock In 10 MHz" (rear BNC).
    The SMCV outputs a 10 MHz reference derived from its own oscillator
    (:ROSCillator:OUTPut:FREQuency:MODE DER10M); the MFLI uses it as its time
    base (/dev/system/extclk = 1). The SMCV's FM (internal LF generator) and
    the MFLI's demodulation oscillator are then set to the same f_mod from the
    SAME clock: their relative phase is constant (unknown, but fixed), so the
    MFLI's X/Y is a phase-sensitive measurement. The phase is found from the
    data afterwards (plot_fm_mfli.py rotates X/Y onto the signal axis), so no
    separate calibration step is needed.
  * Photodiode -> MFLI Signal Input 1 (and, through a BNC tee, Red Pitaya IN1
    for the DC reference sweep).
  * Not usable for this: the SMCV's User 1/2 connectors. As outputs they only
    carry the ARB marker (MARKA1) or nothing, as inputs triggers / transport
    stream / PPS; the SMCV has no LF (modulation) output and no external FM
    input. REF IN takes an external 10/13 MHz reference (not needed here).

WHAT IT DOES
  0. SMCV: power (limit enforced by SMCV100B), REF OUT = 10 MHz, FM over SCPI
     ([:SOURce]:BB:GENeral:FM:..., lockin_common.SmcvFm): sine, deviation
     FM_DEV_KHZ, frequency F_MOD_HZ. MFLI: external 10 MHz clock, oscillator
     at F_MOD_HZ, demodulator 0 on Signal Input 1 (AC coupled, auto range).
  1. PICKUP CHECK: FM on, MW parked far off resonance (OFF_RES_MHZ): the
     demodulated amplitude there is electrical pickup, not ODMR.
  2. FM SWEEPS: N_SWEEPS sweeps over the config grid; at every point wait
     SETTLE_TC time constants, then average the MFLI X, Y for T_INT_S.
  3. DC SWEEPS (DO_DC): N_SWEEPS MW on/off sweeps with the Red Pitaya on the
     same grid (config integration time), the reference method.
  The wall-clock time of every sweep is recorded, so the plotter compares the
  two methods at equal measurement time.

Settings: F_MOD_HZ / FM_DEV_KHZ here (keep f_mod away from interference lines;
deviation ~ half the FWHM of ONE line, not of the two overlapping lines);
grid, power and Red Pitaya settings from config.json.

Output: <data_dir>/fm_mfli_<stamp>/
          fm_sweeps.csv   sweep,freq_MHz,X_V,Y_V,X_std_V,Y_std_V,t_s
                          (# meta: f_mod, deviation, pickup X/Y, sweep times)
          dc_sweeps.csv   sweep,freq_MHz,ratio,on_V,off_V,t_s
Next:   plot_fm_mfli.py

Requires:  pip install zhinst-core   (LabOne API). MFLI_DEVICE = None finds the
MFLI on the network (or set e.g. "dev1234", shown in LabOne).

Run on the PC:  python odmr_fm_mfli_phase_pc.py
"""

import os
import sys
import time
from datetime import datetime

import numpy as np

_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from lockin_common import (DATA_DIR, F_START, F_STEP, F_STOP, POWER_DBM, RP_IP,
                           RP_PORT, SMCV_IP, SMCV_PORT, SMCV100B, SmcvFm, frange,
                           teardown_smcv_modulation)
from odmr_smcv100b_pc import SETTLE_S, RedPitayaADC, integrate

# --- settings ---------------------------------------------------------------
MFLI_DEVICE = None          # None -> discover; or e.g. "dev1234"
MW_POWER_DBM = POWER_DBM    # config sweep.power_dbm (<= -16.4 dBm with the amplifier)
F_MOD_HZ = 5000.0           # FM rate = MFLI oscillator (avoid the ~10.5 kHz pickup)
FM_DEV_KHZ = 2300.0         # ~half the FWHM of ONE line
TIME_CONSTANT = 0.01        # s, MFLI demodulator filter (4th order)
FILTER_ORDER = 4
SETTLE_TC = 5               # wait this many time constants after a frequency step
T_INT_S = 0.1               # averaging time per point (DC: config integration_ms)
DEMOD_RATE = 1000.0         # Sa/s streamed from the demodulator
N_SWEEPS = 4
DO_DC = True                # also take DC on/off sweeps with the Red Pitaya
OFF_RES_MHZ = F_START - 50.0
T_PICKUP_S = 2.0


# ---------------------------------------------------------------------------
# MFLI
# ---------------------------------------------------------------------------
def zi_api():
    try:
        import zhinst.core as zi            # LabOne >= 22.08
    except ImportError:
        try:
            import zhinst.ziPython as zi    # older API
        except ImportError:
            raise SystemExit("zhinst not installed: pip install zhinst-core")
    return zi


class Mfli:
    def __init__(self, device=MFLI_DEVICE):
        zi = zi_api()
        disc = zi.ziDiscovery()
        if device is None:
            found = disc.findAll()
            if not found:
                raise SystemExit("No Zurich Instruments device found on the network: "
                                 "set MFLI_DEVICE (LabOne shows it, e.g. dev1234).")
            device = found[0]
        props = disc.get(disc.find(device))
        self.daq = zi.ziDAQServer(props["serveraddress"], props["serverport"], 6)
        self.daq.connectDevice(device, props["interfaces"][0])
        self.dev = device.lower()
        self.path = f"/{self.dev}/demods/0/sample"
        print(f"MFLI {self.dev} via {props['serveraddress']}:{props['serverport']}")

    def set(self, node, value):
        full = f"/{self.dev}/{node}"
        if isinstance(value, float):
            self.daq.setDouble(full, value)
        else:
            self.daq.setInt(full, int(value))

    def get_int(self, node):
        return int(self.daq.getInt(f"/{self.dev}/{node}"))

    def configure(self):
        self.set("system/extclk", 1)                 # 10 MHz from the SMCV REF OUT
        self.set("oscs/0/freq", float(F_MOD_HZ))
        self.set("sigins/0/ac", 1)                   # AC: drop the PL DC level
        self.set("sigins/0/imp50", 0)                # 10 MOhm
        self.set("sigins/0/diff", 0)
        self.set("demods/0/adcselect", 0)            # Signal Input 1
        self.set("demods/0/oscselect", 0)
        self.set("demods/0/harmonic", 1)
        self.set("demods/0/order", FILTER_ORDER)
        self.set("demods/0/timeconstant", float(TIME_CONSTANT))
        self.set("demods/0/rate", float(DEMOD_RATE))
        self.set("demods/0/enable", 1)
        self.daq.sync()
        self.set("sigins/0/autorange", 1)
        time.sleep(1.0)
        self.daq.sync()
        clk = self.get_int("system/extclk")
        print(f"  MFLI clock: {'EXTERNAL 10 MHz' if clk == 1 else 'INTERNAL'}")
        if clk != 1:
            print("  WARNING: the MFLI did not take the external clock (cable SMCV "
                  "REF OUT -> MFLI Clock In?). The phase will drift: X/Y are then "
                  "not phase-sensitive.")
        return clk == 1

    def read_xy(self, t_int=T_INT_S):
        """Mean and std of X, Y streamed for t_int seconds."""
        self.daq.subscribe(self.path)
        self.daq.sync()
        data = self.daq.poll(t_int, 200, 0, True)
        self.daq.unsubscribe(self.path)
        s = next((v for k, v in data.items() if k.lower() == self.path), None)
        if s is None or len(s["x"]) == 0:
            raise RuntimeError("no MFLI demodulator samples (demods/0 enabled?)")
        x, y = np.asarray(s["x"], float), np.asarray(s["y"], float)
        return x.mean(), y.mean(), x.std(), y.std()

    def close(self):
        try:
            self.daq.disconnect()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# SMCV
# ---------------------------------------------------------------------------
def smcv_ref_out_10mhz(src):
    """REF OUT = 10 MHz derived from the internal reference (the SMCV itself
    stays on its internal reference). Best effort: prints what it read back."""
    try:
        src.s.write("*CLS")
        src.s.write(":SOURce:ROSCillator:SOURce INTernal")
        src.s.write(":SOURce:ROSCillator:OUTPut:FREQuency:MODE DER10M")
        err = src.s.query(":SYSTem:ERRor?")
        mode = src.s.query(":SOURce:ROSCillator:OUTPut:FREQuency:MODE?")
        print(f"  SMCV REF OUT mode: {mode} ({err})")
    except Exception as e:
        print(f"  could not set REF OUT over SCPI ({e}): set Reference Frequency "
              "output to 10 MHz on the SMCV.")


def setup_fm(src, fm):
    """FM sine, deviation, rate, on; master modulation on. Prompts for what the
    SMCV refuses over SCPI."""
    remote = dict(shape=fm.shape_sine(), dev=fm.deviation_hz(FM_DEV_KHZ * 1e3),
                  lf=fm.lf_freq_hz(F_MOD_HZ), state=fm.state(True))
    print("  SCPI control: " + ", ".join(
        f"{k} {'remote' if v else 'BY HAND'}" for k, v in remote.items())
        + f"  ({fm.report()})")
    need = [n for k, n in (("shape", "FM shape sine"),
                           ("dev", f"deviation {FM_DEV_KHZ:.0f} kHz"),
                           ("lf", f"FM frequency {F_MOD_HZ:.0f} Hz"),
                           ("state", "FM ON")) if not remote[k]]
    if need:
        input("  SMCV Modulation menu: " + "; ".join(need) + ". Enter when done...")
    src.s.write(":SOURce:MODulation:ALL:STATe ON")
    src.s.query("*OPC?")


# ---------------------------------------------------------------------------
# sweeps
# ---------------------------------------------------------------------------
def fm_sweeps(src, mfli, freqs, path, meta):
    with open(path, "w") as f:
        for k, v in meta.items():
            f.write(f"# {k}={v}\n")
        f.write("sweep,freq_MHz,X_V,Y_V,X_std_V,Y_std_V,t_s\n")
        t0 = time.monotonic()
        for s in range(N_SWEEPS):
            for i, fr in enumerate(freqs):
                src.set_freq_mhz(fr)
                time.sleep(SETTLE_TC * TIME_CONSTANT)
                x, y, sx, sy = mfli.read_xy()
                f.write(f"{s},{fr:.4f},{x:.8e},{y:.8e},{sx:.4e},{sy:.4e},"
                        f"{time.monotonic() - t0:.3f}\n")
                print(f"\r  FM sweep {s + 1}/{N_SWEEPS}: {i + 1}/{len(freqs)} "
                      f"({fr:.2f} MHz)", end="", flush=True)
            f.flush()
        print()
    return (time.monotonic() - t0) / N_SWEEPS


def dc_sweeps(src, adc, freqs, path):
    with open(path, "w") as f:
        f.write(f"# experiment=fm_mfli_dc\n# power_dBm={MW_POWER_DBM}\n"
                "sweep,freq_MHz,ratio,on_V,off_V,t_s\n")
        t0 = time.monotonic()
        for s in range(N_SWEEPS):
            for i, fr in enumerate(freqs):
                src.set_freq_mhz(fr)
                src.output(True)
                time.sleep(SETTLE_S)
                on = integrate(adc)
                src.output(False)
                time.sleep(SETTLE_S)
                off = integrate(adc)
                f.write(f"{s},{fr:.4f},{on / off if off else np.nan:.8f},{on:.8e},"
                        f"{off:.8e},{time.monotonic() - t0:.3f}\n")
                print(f"\r  DC sweep {s + 1}/{N_SWEEPS}: {i + 1}/{len(freqs)} "
                      f"({fr:.2f} MHz)", end="", flush=True)
            f.flush()
        print()
    return (time.monotonic() - t0) / N_SWEEPS


def main():
    run_dir = os.path.join(DATA_DIR, f"fm_mfli_{datetime.now():%Y%m%d_%H%M%S}")
    os.makedirs(run_dir, exist_ok=True)
    freqs = np.array(list(frange(F_START, F_STOP, F_STEP)))
    print(f"FM (MFLI) vs DC -> {run_dir}\n  {len(freqs)} points {F_START}-{F_STOP} MHz, "
          f"{N_SWEEPS} sweeps each; f_mod {F_MOD_HZ:.0f} Hz, deviation {FM_DEV_KHZ:.0f} kHz, "
          f"MW {MW_POWER_DBM:+.1f} dBm")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    fm = SmcvFm(src)
    mfli = adc = None
    try:
        src.configure(MW_POWER_DBM)
        smcv_ref_out_10mhz(src)
        mfli = Mfli()
        locked = mfli.configure()
        input("\nLaser on, focus on the diamond, photodiode -> MFLI Signal Input 1 "
              "(tee to Red Pitaya IN1 for the DC sweeps). Enter to start...")

        # ---- FM ---------------------------------------------------------
        setup_fm(src, fm)
        src.output(True)
        src.set_freq_mhz(OFF_RES_MHZ)
        time.sleep(SETTLE_TC * TIME_CONSTANT + 0.5)
        px, py, _, _ = mfli.read_xy(T_PICKUP_S)
        print(f"  pickup check at {OFF_RES_MHZ:.0f} MHz: R = "
              f"{np.hypot(px, py) * 1e6:.2f} uV")
        meta = dict(experiment="fm_mfli", power_dBm=MW_POWER_DBM, f_mod_Hz=F_MOD_HZ,
                    deviation_Hz=FM_DEV_KHZ * 1e3, time_constant_s=TIME_CONSTANT,
                    filter_order=FILTER_ORDER, settle_tc=SETTLE_TC, t_int_s=T_INT_S,
                    n_sweeps=N_SWEEPS, ext_clock=int(locked), off_res_MHz=OFF_RES_MHZ,
                    pickup_X_V=px, pickup_Y_V=py,
                    created=datetime.now().isoformat(timespec="seconds"))
        t_fm = fm_sweeps(src, mfli, freqs, os.path.join(run_dir, "fm_sweeps.csv"), meta)
        print(f"  {t_fm:.1f} s per FM sweep")

        # ---- DC ---------------------------------------------------------
        if DO_DC:
            fm.state(False)
            teardown_smcv_modulation(src, "fm")
            adc = RedPitayaADC(RP_IP, RP_PORT)
            t_dc = dc_sweeps(src, adc, freqs, os.path.join(run_dir, "dc_sweeps.csv"))
            print(f"  {t_dc:.1f} s per DC sweep")
        print(f"\nDone -> {run_dir}\nNext: python plot_fm_mfli.py")
    except KeyboardInterrupt:
        print(f"\nStopped. Files so far are in {run_dir}")
    finally:
        fm.state(False)
        teardown_smcv_modulation(src, "fm")
        src.close()
        for x in (mfli, adc):
            if x is not None:
                x.close()


if __name__ == "__main__":
    main()
