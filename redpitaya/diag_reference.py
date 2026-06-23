"""
Reference / feedback diagnostic for the ADF4351.

When the VCO rails high and won't lock even though the supply, SPI and ground are
all good, the usual remaining cause is the REFERENCE CLOCK not reaching the phase
detector (a dead/cracked 25 MHz TCXO, a bad REFIN joint, or a disturbed ref path).
With no reference the charge pump has nothing to compare against and drives the VCO
to a rail -- exactly the "100 mV wandering 550-600 MHz, never locks" symptom.

This script doesn't try to lock. It routes an internal node to the MUXOUT pin so
you can watch it on a scope:

  MODE = "reference" -> MUXOUT = R-counter output. You should see a clean ~25 MHz
                        square wave (the reference divided by R=1). This is present
                        whether or not the PLL locks. ABSENT/erratic = reference is
                        the problem -> reflow the TCXO pins / check REFIN.

  MODE = "feedback"  -> MUXOUT = N-divider output. With the loop running you should
                        see ~ the PFD frequency (~25 MHz) if the VCO->N path is alive.

Wiring note: scope the MODULE's MUXOUT pin/pad (it's a SEPARATE pin from LD). If your
board doesn't break MUXOUT out, scope the 25 MHz TCXO can / REFIN pin directly
instead -- you're looking for the same thing: a steady 25 MHz.

Mechanical check while this runs: gently press the TCXO can / wiggle nothing else
with an insulated tool. If the 25 MHz comes and goes as you press, you've found a
cracked solder joint -> reflow it.

Run on the Red Pitaya as root:   sudo python3 diag_reference.py
"""

import time
import spidev
import rp

# ============================================================================
MODE      = "reference"   # "reference" (R-counter) or "feedback" (N-divider)
FREQ_MHZ  = 500.0
REF_MHZ   = 25.0
MOD_VAL   = 1000
SPI_BUS   = 2             # Gen-2 RP = /dev/spidev2.0
SPI_DEV   = 0
SPI_HZ    = 1_000_000
# ============================================================================

_MUX = {"reference": 0b011, "feedback": 0b100}   # R2[28:26]
_RF_DIV = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16), (5, 32), (6, 64)]


def _rf_div(f):
    for sel, div in _RF_DIV:
        if 2200.0 <= f * div <= 4400.0:
            return sel, div
    raise ValueError(f)


def build_registers(freq_mhz, mux_mode):
    sel, div = _rf_div(freq_mhz)
    n = (freq_mhz * div) / REF_MHZ
    int_val = int(n)
    frac_val = int(round((n - int_val) * MOD_VAL))
    if frac_val >= MOD_VAL:
        frac_val = 0
        int_val += 1
    is_int = frac_val == 0

    r0 = (int_val << 15) | (frac_val << 3)
    r1 = (1 << 27) | (1 << 15) | (MOD_VAL << 3) | 0x1
    r2 = 0x18005E42 | ((1 << 8) if is_int else 0)
    r2 = (r2 & ~(0b111 << 26)) | (mux_mode << 26)              # set MUXOUT source
    r3 = 0x000004B3 | (((1 << 22) | (1 << 21)) if is_int else 0)
    r4 = (1 << 23) | (sel << 20) | (250 << 12) | (1 << 5) | (3 << 3) | 0x4
    r5 = 0x00580005
    return [r0, r1, r2, r3, r4, r5]


def main():
    mux = _MUX[MODE]
    regs = build_registers(FREQ_MHZ, mux)

    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEV)
    spi.max_speed_hz = SPI_HZ
    spi.mode = 0
    rp.rp_Init()

    for reg in reversed(regs):
        spi.xfer2([(reg >> 24) & 0xFF, (reg >> 16) & 0xFF,
                   (reg >> 8) & 0xFF, reg & 0xFF])

    print(f"MUXOUT routed to: {MODE}  (R2 = 0x{regs[2]:08X})")
    if MODE == "reference":
        print("Scope the module's MUXOUT pin -> expect a steady ~25 MHz square wave.")
        print("  steady 25 MHz  = reference is ALIVE (look elsewhere for the no-lock)")
        print("  absent/erratic = reference is the FAULT -> reflow TCXO / check REFIN")
    else:
        print("Scope MUXOUT -> expect ~25 MHz (PFD rate) if the VCO->N path is alive.")
    print("\nHolding. Press the TCXO with an insulated tool to test for a cracked")
    print("joint (signal coming and going = bad joint). Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        spi.xfer2([0x00, 0x18, 0x00, 0x05])   # mute RF (R4 with RF-enable cleared-ish)
        spi.close()
        rp.rp_Release()
        print("\nDone.")


if __name__ == "__main__":
    main()
