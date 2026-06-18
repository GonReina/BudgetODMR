"""
NV-centre ODMR experiment on a RedPitaya (STEMlab).

For every frequency step the RedPitaya:
  1. programs the ADF4351 over SPI to the next microwave frequency,
  2. waits (in hardware) for the PLL Lock Detect edge on DIO0_P, so acquisition
     only starts once the frequency is genuinely settled,
  3. samples the photodiode (photoluminescence) on fast ADC IN1 and averages it,
  4. writes "freq_MHz,pl_volts" to the output file,
and repeats until the sweep is complete. Plot the result with plot_odmr.py.

Edit the EXPERIMENT CONFIGURATION block below and run:  python3 odmr_redpitaya.py
(There are no command-line arguments by design.)

------------------------------------------------------------------------------
WIRING (E1/E2 connectors -> ADF4351 module)
  E2 SPI SCK   -> ADF CLK
  E2 SPI MOSI  -> ADF DATA
  E2 SPI CS    -> ADF LE      (CS idles high, pulses the latch at end of transfer)
  P3V3         -> ADF VDD and CE
  ADF LD       -> E1 DIO0_P   (external trigger input for the fast ADC)
  Photodiode   -> IN1         (fast ADC; set the LV/HV jumper for your amp's range)
  GND          -> common ground between RedPitaya, ADF module, and photodiode amp
------------------------------------------------------------------------------

Notes:
  * Run as root (ADC + SPI access).
  * The RedPitaya `rp` acquisition API varies by OS version. Those calls are
    confined to the RedPitayaADC class; if a name/constant differs on your
    image, fix it there (run `help(rp)` to check).
"""

import time
from datetime import datetime

import spidev
import rp


# ============================================================================
# EXPERIMENT CONFIGURATION  -- edit these, then run the script
# ============================================================================
F_START_MHZ = 2700.0      # sweep start frequency
F_STOP_MHZ  = 3000.0      # sweep stop frequency (inclusive)
F_STEP_MHZ  = 1.0         # step size

OUTPUT_FILE = "odmr_spectrum_2.csv"

AVERAGES_PER_POINT = 4    # photodiode captures averaged at each frequency
LOCK_TIMEOUT_S     = 10 # max wait for PLL lock per step before giving up

# Fast ADC (photodiode on IN1)
ADC_CHANNEL = rp.RP_CH_1      # IN1
DECIMATION  = rp.RP_DEC_64    # ~8 ms integration window per capture (16384 samples)
N_SAMPLES   = 16384           # samples per capture

# ADF4351 SPI
SPI_HZ = 1_000_000

# ADF4351 synthesis (25 MHz reference; fPFD = 25 MHz; MOD=1000 -> 25 kHz res)
REF_MHZ = 25.0
MOD_VAL = 1000


# ============================================================================
# ADF4351 register math
# ============================================================================
FPFD_MHZ = REF_MHZ        # fPFD = REF * (1+D) / (R * (1+T)) with D=0, R=1, T=0

# RF output divider options: select code (R4[22:20]) -> actual divisor.
# The VCO runs 2200-4400 MHz; we pick the smallest divider that keeps it there.
_RF_DIV_TABLE = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16), (5, 32), (6, 64)]


def _get_rf_div(freq_mhz):
    """Return (divider_select_code, divider_value) for a given output frequency."""
    for sel, div in _RF_DIV_TABLE:
        vco = freq_mhz * div
        if 2200.0 <= vco <= 4400.0:
            return sel, div
    raise ValueError(
        f"Frequency {freq_mhz} MHz is outside the ADF4351 range (34.375-4400 MHz)"
    )


def build_registers(freq_mhz):
    """Return [R0, R1, R2, R3, R4, R5] for the requested output frequency.

    The RF output divider is chosen automatically so the VCO stays in its
    valid 2200-4400 MHz band, covering the full 34.375-4400 MHz output range.
    """
    rf_div_sel, rf_div = _get_rf_div(freq_mhz)
    vco = freq_mhz * rf_div
    n = vco / FPFD_MHZ

    int_val = int(n)
    frac_val = int(round((n - int_val) * MOD_VAL))
    if frac_val >= MOD_VAL:          # rounding pushed FRAC up to MOD
        frac_val = 0
        int_val += 1

    r0 = (int_val << 15) | (frac_val << 3) | 0x0           # INT, FRAC, ctrl 000
    r1 = (1 << 27) | (1 << 15) | (MOD_VAL << 3) | 0x1      # presc 8/9, phase=1, MOD
    r2 = 0x18005E42                                         # R=1, CP=5mA, MUX=DLD
    r3 = 0x000004B3                                         # frac-N defaults
    r4 = (1 << 23) | (rf_div_sel << 20) | (250 << 12) | 0x3C  # fb=VCO, divsel, +5dBm
    r5 = 0x00580005                                         # LD pin = digital LD
    return [r0, r1, r2, r3, r4, r5]


# ============================================================================
# ADF4351 over SPI
# ============================================================================
class ADF4351:
    def __init__(self, bus=2, device=0, speed_hz=SPI_HZ):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)        # /dev/spidev1.0 on RedPitaya E2
        self.spi.max_speed_hz = speed_hz
        self.spi.mode = 0                 # CPOL=0, CPHA=0; data clocked on rising CLK
        # CS goes low for the transfer and back high afterwards; that rising
        # edge is exactly the ADF's LE latch. MSB-first is spidev's default.

    def write_register(self, value):
        self.spi.xfer2([
            (value >> 24) & 0xFF,
            (value >> 16) & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ])

    def set_frequency(self, freq_mhz):
        """Program a frequency; write R5 -> R0 so R0 last triggers VCO autocal.

        The R0 write forces a VCO band-select recalibration, which drops LD low
        and then raises it on lock -- giving the clean rising edge we trigger on.
        """
        for reg in reversed(build_registers(freq_mhz)):
            self.write_register(reg)

    def close(self):
        self.spi.close()


# ============================================================================
# Fast ADC, triggered on the LD lock edge (DIO0_P) or immediately
# ============================================================================
# NOTE: the calls in this class are the version-sensitive ones. They follow the
# RedPitaya 2.x `rp` API. Verify names against your image if acquisition errors.
class RedPitayaADC:
    def __init__(self, channel=ADC_CHANNEL, decimation=DECIMATION, n_samples=N_SAMPLES):
        self.channel = channel
        self.decimation = decimation
        self.n_samples = n_samples
        rp.rp_Init()
        self.buff = rp.fBuffer(n_samples)

    def arm(self, trigger_src):
        """Arm an acquisition. Use RP_TRIG_SRC_EXT_PE for the LD lock edge, or
        RP_TRIG_SRC_NOW for an immediate capture once already locked."""
        rp.rp_AcqReset()
        rp.rp_AcqSetDecimation(self.decimation)
        # Trigger near the start of the buffer so captured samples are post-trigger.
        rp.rp_AcqSetTriggerDelay(self.n_samples)
        rp.rp_AcqStart()
        rp.rp_AcqSetTriggerSrc(trigger_src)

    def wait_for_lock(self, timeout_s):
        """Wait for the armed EXT_PE trigger (LD lock edge); return lock time in ms.

        Call this after arm(RP_TRIG_SRC_EXT_PE) + set_frequency() so the caller
        knows the exact moment the PLL confirmed lock before reading the buffer.
        """
        deadline = time.time() + timeout_s
        t0 = time.perf_counter()
        while rp.rp_AcqGetTriggerState()[1] != rp.RP_TRIG_STATE_TRIGGERED:
            if time.time() > deadline:
                raise TimeoutError("no trigger (PLL did not lock / LD not on DIO0_P)")
        return (time.perf_counter() - t0) * 1e3

    def read_mean(self, timeout_s):
        """Wait for the buffer to fill after triggering, then return the mean voltage."""
        deadline = time.time() + timeout_s
        while rp.rp_AcqGetBufferFillState()[1] is False:
            if time.time() > deadline:
                raise TimeoutError("ADC buffer did not fill after trigger")
        rp.rp_AcqGetOldestDataV(self.channel, self.n_samples, self.buff)
        total = 0.0
        for i in range(self.n_samples):
            total += self.buff[i]
        return total / self.n_samples

    def close(self):
        rp.rp_Release()


# ============================================================================
# Measurement
# ============================================================================
def frange(start, stop, step):
    f = start
    while f <= stop + 1e-6:
        yield round(f, 6)
        f += step


def measure_point(adf, adc, freq_mhz):
    """Set the frequency, wait for lock, and return the averaged photoluminescence."""
    # Arm BEFORE writing registers so the ADC is ready for the LD rising edge.
    adc.arm(rp.RP_TRIG_SRC_EXT_PE)
    adf.set_frequency(freq_mhz)

    # Wait for the LD lock edge and print confirmation the instant it fires.
    lock_ms = adc.wait_for_lock(LOCK_TIMEOUT_S)
    print(f"locked ({lock_ms:.1f} ms) ", end="", flush=True)

    total = adc.read_mean(LOCK_TIMEOUT_S)

    # Additional averages at the same (now-locked) frequency use an immediate
    # trigger, since LD is already high and won't produce another rising edge.
    for _ in range(AVERAGES_PER_POINT - 1):
        adc.arm(rp.RP_TRIG_SRC_NOW)
        total += adc.read_mean(LOCK_TIMEOUT_S)

    return total / AVERAGES_PER_POINT


def run_sweep():
    freqs = list(frange(F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ))
    print(f"ODMR sweep: {F_START_MHZ}-{F_STOP_MHZ} MHz, {F_STEP_MHZ} MHz steps "
          f"({len(freqs)} points), {AVERAGES_PER_POINT} averages/point")

    adf = ADF4351(speed_hz=SPI_HZ)
    adc = RedPitayaADC()

    try:
        with open(OUTPUT_FILE, "w") as f:
            f.write(f"# NV ODMR spectrum, {datetime.now().isoformat(timespec='seconds')}\n")
            f.write(f"# start={F_START_MHZ} stop={F_STOP_MHZ} step={F_STEP_MHZ} MHz\n")
            f.write(f"# averages_per_point={AVERAGES_PER_POINT} "
                    f"samples_per_capture={N_SAMPLES}\n")
            f.write("freq_MHz,pl_volts\n")

            for i, freq in enumerate(freqs, 1):
                print(f"[{i}/{len(freqs)}] {freq:.3f} MHz  ", end="", flush=True)
                pl = measure_point(adf, adc, freq)
                f.write(f"{freq:.4f},{pl:.6f}\n")
                f.flush()
                print(f"-> {pl:.6f} V")

        print(f"Done. Wrote {OUTPUT_FILE}")
    except KeyboardInterrupt:
        print(f"\nStopped early. Partial data in {OUTPUT_FILE}")
    finally:
        adf.close()
        adc.close()


if __name__ == "__main__":
    run_sweep()
