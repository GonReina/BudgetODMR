"""
Robust, repeatable, averaged ODMR sweep -- records the BPW34 photodiode (fast ADC
IN1) while stepping the ADF4351 across a frequency range, many times, averaging.

Design notes
------------
* No dependence on lock detect. It programs the frequency, waits a FIXED settle
  time, then captures -- so a flaky LD pin can't stall the run. LD is only read
  (optionally) as a logged quality flag.

* LONG INTEGRATION per point (the key noise win). A budget photodiode + op-amp on
  a fast ADC is wideband and noisy; the reference paper's TSL2591 wins by
  integrating ~100 ms per reading, which hardware-averages fast noise and mains
  hum. We emulate that: each point integrates over INTEGRATION_MS, and 100 ms is
  an integer number of cycles for BOTH 50 Hz (5) and 60 Hz (6), so mains hum
  cancels. This is usually what makes a buried dip appear.

* Optional MW ON/OFF per point (MW_ON_OFF). Measures PL with the microwaves on,
  then muted, and records the ratio PL_on/PL_off. Slow laser-intensity drift
  divides out, giving true fractional ODMR contrast -- the budget gold standard.

Outputs (everything under data/ is synced to the PC):
    data/odmr_runs/run_01.csv ...  per sweep: freq_MHz,signal,ld
                                   signal = PL_on/PL_off if MW_ON_OFF else mean volts
    data/odmr_average.csv          running average, rewritten after every sweep

Run on the Red Pitaya as root:   sudo python3 odmr_sweep_robust.py
Plot with (on the PC):           python3 analysis/average_sweeps.py
"""

import os
import time
from datetime import datetime

import spidev
import rp

# ============================================================================
# CONFIG -- edit, then run
# ============================================================================
F_START_MHZ = 2800.0
F_STOP_MHZ  = 2920.0
F_STEP_MHZ  = 1.0

N_SWEEPS       = 5        # full sweeps to average together
INTEGRATION_MS = 600.0     # photodiode integration per reading (100 ms rejects 50 & 60 Hz)
SETTLE_S       = 0.10     # dwell after (re)programming before integrating
MW_ON_OFF      = True      # True = measure PL_on/PL_off per point (cancels laser drift)
os.chdir(r"/root/data/BudgetODMR/23-06-2026")
RUNS_DIR = "data/odmr_runs4"
AVG_FILE = "data/odmr_average4.csv"

REF_MHZ   = 25.0
MOD_VAL   = 1000
POWER_DBM = 5

# Fast ADC (photodiode on IN1). DEC_1024 -> fs = 122.07 kS/s, 16384-sample buffer
# = 134 ms, enough to hold a 100 ms integration window.
ADC_CHANNEL = rp.RP_CH_1
DECIMATION  = rp.RP_DEC_1024
FS_HZ       = 125e6 / 1024
N_BUF       = 16384

# ADF4351 SPI
SPI_BUS = 2                # Gen-2 RP = /dev/spidev2.0; Gen-1 = 1
SPI_DEV = 0
SPI_HZ  = 1_000_000
LD_PIN  = rp.RP_DIO0_P
MONITOR_LD = False         # see set_frequency.py; LD wire adds a ground path that hurts lock

# Mains-clean integration. One ADC buffer holds 134 ms max, and 100 ms is an
# integer number of mains cycles for BOTH 50 Hz (5) and 60 Hz (6), so a 100 ms
# "sub-read" cancels hum every time. Longer integration is built by AVERAGING
# several sub-reads -- never by widening one buffer past 100 ms (that is 6.7
# cycles, leaves residual hum, and is the usual cause of run-to-run noise).
SUBREAD_MS = 100.0
N_SUBREAD  = min(N_BUF, int(round(SUBREAD_MS / 1000.0 * FS_HZ)))   # ~12207 samples
N_SUB      = max(1, int(round(INTEGRATION_MS / SUBREAD_MS)))       # sub-reads per reading

# ============================================================================
# ADF4351 register math (verified)
# ============================================================================
_RF_DIV = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16), (5, 32), (6, 64)]
_PWR    = {-4: 0, -1: 1, 2: 2, 5: 3}


def _rf_div(freq_mhz):
    for sel, div in _RF_DIV:
        if 2200.0 <= freq_mhz * div <= 4400.0:
            return sel, div
    raise ValueError(f"{freq_mhz} MHz outside 34.375-4400 MHz")


def build_registers(freq_mhz):
    sel, div = _rf_div(freq_mhz)
    n = (freq_mhz * div) / REF_MHZ
    int_val = int(n)
    frac_val = int(round((n - int_val) * MOD_VAL))
    if frac_val >= MOD_VAL:
        frac_val = 0
        int_val += 1
    is_int = frac_val == 0
    pwr = _PWR.get(POWER_DBM, 3)

    r0 = (int_val << 15) | (frac_val << 3)
    r1 = (1 << 27) | (1 << 15) | (MOD_VAL << 3) | 0x1
    r2 = 0x18005E42 | ((1 << 8) if is_int else 0)              # LDF=1 on integer-N
    r3 = 0x000004B3 | (((1 << 22) | (1 << 21)) if is_int else 0)   # ABP=3ns + charge-cancel
    r4 = (1 << 23) | (sel << 20) | (250 << 12) | (1 << 5) | (pwr << 3) | 0x4
    r5 = 0x00580005
    return [r0, r1, r2, r3, r4, r5]


# ============================================================================
# Hardware wrappers
# ============================================================================
class ADF4351:
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(SPI_BUS, SPI_DEV)
        self.spi.max_speed_hz = SPI_HZ
        self.spi.mode = 0

    def write_register(self, value):
        self.spi.xfer2([(value >> 24) & 0xFF, (value >> 16) & 0xFF,
                        (value >> 8) & 0xFF, value & 0xFF])

    def set_frequency(self, freq_mhz):
        self._regs = build_registers(freq_mhz)
        for reg in reversed(self._regs):      # R5->R0, R0 last triggers lock
            self.write_register(reg)

    def rf_off(self):
        self.write_register(self._regs[4] & ~(1 << 5))   # clear RF-enable -> mute

    def rf_on(self):
        self.write_register(self._regs[4])               # restore R4 (RF enabled)

    def close(self):
        self.spi.close()


def ld_high():
    return rp.rp_DpinGetState(LD_PIN)[1] == rp.RP_HIGH


def subread(buff):
    """One mains-clean block capture; mean of the first N_SUBREAD samples
    (= a whole number of mains cycles)."""
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
    """Median of N_SUB mains-clean sub-reads. Median (not mean) rejects a single
    transient sub-read (e.g. a momentary PLL unlock) that would otherwise show as
    a sharp one-point spike."""
    vals = sorted(subread(buff) for _ in range(N_SUB))
    n = len(vals)
    return vals[n // 2] if n % 2 else 0.5 * (vals[n // 2 - 1] + vals[n // 2])


def measure_point(adf, buff, freq_mhz):
    adf.set_frequency(freq_mhz)
    time.sleep(SETTLE_S)
    ld = (1 if ld_high() else 0) if MONITOR_LD else 0
    pl_on = integrate(buff)

    if MW_ON_OFF:
        adf.rf_off()
        time.sleep(SETTLE_S)
        pl_off = integrate(buff)
        adf.rf_on()                      # leave RF on for the next step's transition
        signal = pl_on / pl_off if pl_off else 0.0
    else:
        signal = pl_on
    return signal, ld


# ============================================================================
# Sweep driver with running average across runs
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
    pt_time = (2 if MW_ON_OFF else 1) * (SETTLE_S + N_SUB * N_BUF / FS_HZ)
    print(f"ODMR: {F_START_MHZ}-{F_STOP_MHZ} MHz / {F_STEP_MHZ} ({len(freqs)} pts), "
          f"{N_SWEEPS} sweeps")
    print(f"  integrate {integ_ms:.0f} ms/reading ({N_SUB}x{SUBREAD_MS:.0f}ms), "
          f"MW_on_off={MW_ON_OFF}, ~{pt_time*len(freqs):.0f}s/sweep")

    rp.rp_Init()
    if MONITOR_LD:
        rp.rp_DpinSetDirection(LD_PIN, rp.RP_IN)
    buff = rp.fBuffer(N_BUF)
    adf = ADF4351()

    running_sum = [0.0] * len(freqs)
    completed = 0

    try:
        for run in range(1, N_SWEEPS + 1):
            run_path = os.path.join(RUNS_DIR, f"run_{run:02d}.csv")
            with open(run_path, "w") as f:
                f.write(f"# run {run}/{N_SWEEPS}, "
                        f"{datetime.now().isoformat(timespec='seconds')}\n")
                f.write(f"# integrate_ms={integ_ms:.1f} mw_on_off={MW_ON_OFF} "
                        f"signal={'PL_on/PL_off' if MW_ON_OFF else 'mean_volts'}\n")
                f.write("freq_MHz,signal,ld\n")
                for idx, freq in enumerate(freqs):
                    sig, ld = measure_point(adf, buff, freq)
                    f.write(f"{freq:.4f},{sig:.6f},{ld}\n")
                    running_sum[idx] += sig
            completed += 1

            with open(AVG_FILE, "w") as f:
                f.write(f"# running average over {completed} sweep(s), "
                        f"{datetime.now().isoformat(timespec='seconds')}\n")
                f.write("freq_MHz,signal_avg\n")
                for idx, freq in enumerate(freqs):
                    f.write(f"{freq:.4f},{running_sum[idx]/completed:.6f}\n")

            print(f"  sweep {run}/{N_SWEEPS} done -> {AVG_FILE}")

        print(f"\nDone. {completed} sweeps averaged -> {AVG_FILE}")
    except KeyboardInterrupt:
        print(f"\nStopped early after {completed} sweep(s). Average in {AVG_FILE}")
    finally:
        try:
            adf.rf_off()
        except Exception:
            pass
        adf.close()
        rp.rp_Release()


if __name__ == "__main__":
    main()
