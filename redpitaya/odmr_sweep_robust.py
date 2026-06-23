"""
Robust, repeatable, averaged ODMR sweep -- records the photodiode (fast ADC IN1)
while stepping the ADF4351 across a frequency range, many times, and averaging.

Why this exists (vs odmr_redpitaya.py)
--------------------------------------
The original sweep arms the ADC on the LD *rising edge* for every point. If lock
detect is even slightly flaky (marginal supply, integer-N LDF bug, etc.) the run
stalls or times out. For a budget rig the dependable approach is:

    program frequency -> wait a FIXED settle time -> capture -> average

The PLL settles in well under a millisecond; a few-ms fixed dwell is plenty. LD is
still *read* and logged per point as a quality flag, but acquisition never blocks
on it, so one bad point can't kill the sweep.

It runs the whole sweep N_SWEEPS times and keeps a running average across runs, so
noise drops as ~1/sqrt(N_SWEEPS * AVERAGES_PER_POINT). Many fast sweeps beat a few
slow ones because slow laser drift averages out across runs instead of tilting a
single long baseline. Outputs:
    data/odmr_runs/run_01.csv ...   one CSV per sweep (freq_MHz,pl_volts,ld)
    data/odmr_average.csv           running average over all completed sweeps

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
F_START_MHZ = 2700.0
F_STOP_MHZ  = 3000.0
F_STEP_MHZ  = 1.0

N_SWEEPS           = 20      # full sweeps to average together
AVERAGES_PER_POINT = 4       # ADC block captures averaged at each frequency
SETTLE_S           = 0.005   # fixed dwell after programming, before capturing (>> lock time)

RUNS_DIR    = "data/odmr_runs"
AVG_FILE    = "data/odmr_average.csv"

REF_MHZ   = 25.0
MOD_VAL   = 1000
POWER_DBM = 5

# Fast ADC (photodiode on IN1)
ADC_CHANNEL = rp.RP_CH_1
DECIMATION  = rp.RP_DEC_64      # ~8 ms per 16384-sample block
N_SAMPLES   = 16384

# ADF4351 SPI
SPI_BUS = 2                     # Gen-2 RP = /dev/spidev2.0; Gen-1 = 1
SPI_DEV = 0
SPI_HZ  = 1_000_000
LD_PIN  = rp.RP_DIO0_P

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
        regs = build_registers(freq_mhz)
        for reg in reversed(regs):        # R5->R0, R0 last triggers lock
            self.write_register(reg)
        return regs

    def mute(self, freq_mhz):
        self.write_register(build_registers(freq_mhz)[4] & ~(1 << 5))

    def close(self):
        self.spi.close()


def ld_high():
    return rp.rp_DpinGetState(LD_PIN)[1] == rp.RP_HIGH


def capture_mean(buff):
    """Immediate-trigger block capture -> mean voltage (no dependence on LD)."""
    rp.rp_AcqReset()
    rp.rp_AcqSetDecimation(DECIMATION)
    rp.rp_AcqSetTriggerDelay(N_SAMPLES)
    rp.rp_AcqStart()
    rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_NOW)
    while rp.rp_AcqGetBufferFillState()[1] is False:
        pass
    rp.rp_AcqGetOldestDataV(ADC_CHANNEL, N_SAMPLES, buff)
    total = 0.0
    for i in range(N_SAMPLES):
        total += buff[i]
    return total / N_SAMPLES


def measure_point(adf, buff, freq_mhz):
    adf.set_frequency(freq_mhz)
    time.sleep(SETTLE_S)                  # fixed dwell -- robust against flaky LD
    ld = 1 if ld_high() else 0            # logged as a quality flag only
    total = 0.0
    for _ in range(AVERAGES_PER_POINT):
        total += capture_mean(buff)
    return total / AVERAGES_PER_POINT, ld


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

    print(f"Robust ODMR: {F_START_MHZ}-{F_STOP_MHZ} MHz / {F_STEP_MHZ} MHz "
          f"({len(freqs)} pts), {AVERAGES_PER_POINT} avg/pt, {N_SWEEPS} sweeps, "
          f"{SETTLE_S*1e3:.0f} ms settle")

    rp.rp_Init()
    rp.rp_DpinSetDirection(LD_PIN, rp.RP_IN)
    buff = rp.fBuffer(N_SAMPLES)
    adf = ADF4351()

    running_sum = [0.0] * len(freqs)
    ld_hits     = [0]   * len(freqs)
    completed   = 0
    last_freq   = freqs[-1]

    try:
        for run in range(1, N_SWEEPS + 1):
            run_path = os.path.join(RUNS_DIR, f"run_{run:02d}.csv")
            n_locked = 0
            with open(run_path, "w") as f:
                f.write(f"# run {run}/{N_SWEEPS}, "
                        f"{datetime.now().isoformat(timespec='seconds')}\n")
                f.write(f"# start={F_START_MHZ} stop={F_STOP_MHZ} "
                        f"step={F_STEP_MHZ} MHz avg/pt={AVERAGES_PER_POINT}\n")
                f.write("freq_MHz,pl_volts,ld\n")
                for idx, freq in enumerate(freqs):
                    pl, ld = measure_point(adf, buff, freq)
                    last_freq = freq
                    f.write(f"{freq:.4f},{pl:.6f},{ld}\n")
                    running_sum[idx] += pl
                    ld_hits[idx] += ld
                    n_locked += ld
            completed += 1

            # rewrite the running-average file after every completed sweep
            with open(AVG_FILE, "w") as f:
                f.write(f"# running average over {completed} sweep(s), "
                        f"{datetime.now().isoformat(timespec='seconds')}\n")
                f.write("freq_MHz,pl_volts_avg,ld_fraction\n")
                for idx, freq in enumerate(freqs):
                    f.write(f"{freq:.4f},{running_sum[idx]/completed:.6f},"
                            f"{ld_hits[idx]/completed:.3f}\n")

            print(f"  sweep {run}/{N_SWEEPS} done  "
                  f"(LD high on {n_locked}/{len(freqs)} pts)  -> {AVG_FILE}")

        print(f"\nDone. {completed} sweeps averaged -> {AVG_FILE}")
    except KeyboardInterrupt:
        print(f"\nStopped early after {completed} sweep(s). "
              f"Average so far in {AVG_FILE}")
    finally:
        adf.mute(last_freq)
        adf.close()
        rp.rp_Release()


if __name__ == "__main__":
    main()
