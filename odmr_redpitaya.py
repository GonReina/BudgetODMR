"""
ODMR frequency sweep on a RedPitaya (STEMlab), all in on-board Python.

The RedPitaya does everything:
  * drives the ADF4351 over hardware SPI (spidev),
  * captures the photodiode on fast ADC IN1, with each capture HARDWARE-TRIGGERED
    on the ADF's Lock Detect (LD) pin so acquisition starts exactly when the new
    frequency is locked. That makes the command -> lock lag irrelevant: the ADC
    cannot start until the frequency is real.

Sweep is point-by-point: set frequency -> wait (in hardware) for LD lock edge ->
integrate a block of ADC samples -> next point.

------------------------------------------------------------------------------
WIRING (E1/E2 connectors -> ADF4351 module)
  E2 SPI SCK   -> ADF CLK
  E2 SPI MOSI  -> ADF DATA
  E2 SPI CS    -> ADF LE      (CS idles high, pulses the latch at end of transfer)
  P3V3         -> ADF CE      (chip enable; or hold a DIO high)
  ADF LD       -> E1 DIO0_P   (external trigger input for the fast ADC)
  Photodiode   -> IN1         (fast ADC; set the LV/HV jumper for your amp's range)
  GND          -> common ground between RedPitaya, ADF module, and photodiode amp
------------------------------------------------------------------------------

Run on the RedPitaya:  python3 odmr_redpitaya.py --out sweep.csv

Notes:
  * Run as root (ADC + SPI access).
  * The RedPitaya `rp` acquisition API varies by OS version. All of those calls
    are confined to the RedPitayaADC class below; if a name/constant differs on
    your image, fix it there (run `help(rp)` to check). Everything else is stable.
  * If the `rp` API is troublesome on your version, the SCPI server is a very
    stable alternative for the ADC half -- ask and I'll provide that variant.
"""

import argparse
import time

import spidev
import rp


# ============================================================================
# ADF4351 register math (identical to odmr_sweep.py / the Arduino sketches)
# ============================================================================
REF_MHZ = 25.0          # on-board reference oscillator feeding the ADF
FPFD_MHZ = REF_MHZ      # fPFD = REF * (1+D) / (R * (1+T)) with D=0, R=1, T=0
MOD_VAL = 1000          # fRES = fPFD/MOD = 25 kHz channel spacing

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
    def __init__(self, bus=1, device=0, speed_hz=1_000_000):
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
# Fast ADC, externally triggered on the LD pin (DIO0_P)
# ============================================================================
# NOTE: the calls in this class are the version-sensitive ones. They follow the
# RedPitaya 2.x `rp` API. Verify names against your image if acquisition errors.
class RedPitayaADC:
    def __init__(self, channel=rp.RP_CH_1, decimation=rp.RP_DEC_64, n_samples=16384):
        self.channel = channel
        self.decimation = decimation
        self.n_samples = n_samples
        rp.rp_Init()
        self.buff = rp.fBuffer(n_samples)

    def arm(self):
        rp.rp_AcqReset()
        rp.rp_AcqSetDecimation(self.decimation)
        # Put the trigger near the start of the buffer so captured samples are
        # post-trigger (i.e. after the lock edge).
        rp.rp_AcqSetTriggerDelay(self.n_samples)
        rp.rp_AcqStart()
        # External positive edge on DIO0_P (= ADF LD going high on lock).
        rp.rp_AcqSetTriggerSrc(rp.RP_TRIG_SRC_EXT_PE)

    def wait_and_read(self, timeout_s=0.5):
        """Block until the LD lock edge triggers, then return the mean voltage."""
        deadline = time.time() + timeout_s
        # Wait for the trigger (lock) edge.
        while True:
            state = rp.rp_AcqGetTriggerState()[1]
            if state == rp.RP_TRIG_STATE_TRIGGERED:
                break
            if time.time() > deadline:
                raise TimeoutError("PLL did not lock (no LD trigger edge)")
        # Wait for the post-trigger buffer to fill.
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
# Sweep
# ============================================================================
def frange(start, stop, step):
    f = start
    while f <= stop + 1e-6:
        yield round(f, 6)
        f += step


def main():
    p = argparse.ArgumentParser(description="ADF4351 + RedPitaya ODMR sweep")
    p.add_argument("--start", type=float, default=2800.0, help="start freq, MHz")
    p.add_argument("--stop", type=float, default=3000.0, help="stop freq, MHz")
    p.add_argument("--step", type=float, default=1.0, help="step size, MHz")
    p.add_argument("--spi-hz", type=int, default=1_000_000, help="SPI clock, Hz")
    p.add_argument("--lock-timeout", type=float, default=5, help="per-step lock timeout, s")
    p.add_argument("--dwell", type=float, default=0.0,
                   help="extra time to spend at each frequency after acquiring, in seconds "
                        "(e.g. 0.1 for 100 ms). Does not affect ADC integration time, "
                        "only the gap before moving to the next step.")
    p.add_argument("--out", default=None, help="CSV output file (freq_MHz,volts)")
    p.add_argument("--repeat", action="store_true", help="loop until interrupted")
    args = p.parse_args()

    adf = ADF4351(speed_hz=args.spi_hz)
    adc = RedPitayaADC()
    out = open(args.out, "w") if args.out else None
    if out:
        out.write("freq_MHz,volts\n")

    try:
        while True:
            for freq in frange(args.start, args.stop, args.step):
                adc.arm()                         # arm BEFORE changing frequency
                adf.set_frequency(freq)           # R0 write -> LD drops, re-locks
                volts = adc.wait_and_read(args.lock_timeout)  # triggers on lock edge
                if args.dwell > 0:
                    time.sleep(args.dwell)
                line = f"{freq:.3f},{volts:.6f}"
                print(line)
                if out:
                    out.write(line + "\n")
                    out.flush()
            if not args.repeat:
                break
    except KeyboardInterrupt:
        print("\n# stopped")
    finally:
        adf.close()
        adc.close()
        if out:
            out.close()


if __name__ == "__main__":
    main()
