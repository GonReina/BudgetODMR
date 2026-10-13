"""
Continuously output ONE frequency on the ADF4351 and hold it.

Use this to:
  * put a known tone on the scope while you debug power / lock (e.g. 500 MHz),
  * sanity-check any frequency in the 35-4400 MHz range before sweeping,
  * confirm lock detect after the LDF fix.

It programs correct integer-N / fractional-N registers (including LDF=1 on
integer-N channels, which the old bench test got wrong), latches them R5->R0,
then optionally reads the LD pin purely as a STATUS flag -- it never blocks on
LD. The tone stays on until you press Ctrl+C.

Run on the Red Pitaya as root:   sudo python3 set_frequency.py

Wiring: same as the rest of the project (E2 SPI -> CLK/DATA/LE, VDD/CE 3.0-3.6 V,
common ground, RFOUT -> scope / SPF5189). LD -> DIO0_P only if MONITOR_LD = True.
"""

import time
import spidev
import rp

# ============================================================================
# CONFIG -- edit, then run
# ============================================================================
FREQ_MHZ  = 669.0       # any value 35 .. 4400 MHz
REF_MHZ   = 25.0        # on-board TCXO
MOD_VAL   = 1000        # fractional modulus -> 25 kHz channel raster at 25 MHz PFD
POWER_DBM = 5           # output power: -4, -1, +2, or +5 dBm (see _PWR table)

SPI_BUS   = 2           # Gen-2 RP = /dev/spidev2.0; Gen-1 = 1
SPI_DEV   = 0
SPI_HZ    = 1_000_000
LD_PIN    = rp.RP_DIO0_P
MONITOR_LD = False      # False = don't touch DIO0_P at all (LD wire left disconnected).
                        # The LD wire forms an extra ground path that can disturb lock;
                        # leaving it off is the reliable config. Set True only if LD is wired.

# ============================================================================
# Register math (verified; identical to odmr_redpitaya.build_registers)
# ============================================================================
_RF_DIV = [(0, 1), (1, 2), (2, 4), (3, 8), (4, 16), (5, 32), (6, 64)]
_PWR    = {-4: 0, -1: 1, 2: 2, 5: 3}


def _rf_div(freq_mhz):
    for sel, div in _RF_DIV:
        if 2200.0 <= freq_mhz * div <= 4400.0:
            return sel, div
    raise ValueError(f"{freq_mhz} MHz outside 34.375-4400 MHz")


def build_registers(freq_mhz, pwr_dbm=POWER_DBM):
    sel, div = _rf_div(freq_mhz)
    n = (freq_mhz * div) / REF_MHZ
    int_val = int(n)
    frac_val = int(round((n - int_val) * MOD_VAL))
    if frac_val >= MOD_VAL:
        frac_val = 0
        int_val += 1
    is_int = frac_val == 0
    pwr = _PWR.get(pwr_dbm, 3)

    r0 = (int_val << 15) | (frac_val << 3)
    r1 = (1 << 27) | (1 << 15) | (MOD_VAL << 3) | 0x1
    r2 = 0x18005E42 | ((1 << 8) if is_int else 0)            # LDF=1 on integer-N
    r3 = 0x000004B3 | (((1 << 22) | (1 << 21)) if is_int else 0)   # ABP=3ns + charge-cancel
    r4 = (1 << 23) | (sel << 20) | (250 << 12) | (1 << 5) | (pwr << 3) | 0x4
    r5 = 0x00580005
    return [r0, r1, r2, r3, r4, r5], int_val, frac_val, div, is_int


def open_spi():
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEV)
    spi.max_speed_hz = SPI_HZ
    spi.mode = 0
    return spi


def write_register(spi, value):
    spi.xfer2([(value >> 24) & 0xFF, (value >> 16) & 0xFF,
               (value >> 8) & 0xFF, value & 0xFF])


def program(spi, regs):
    for reg in reversed(regs):     # R5 -> R0; R0 last triggers band-select + lock
        write_register(spi, reg)


def ld_high():
    return rp.rp_DpinGetState(LD_PIN)[1] == rp.RP_HIGH


def main():
    regs, i, fr, div, is_int = build_registers(FREQ_MHZ)
    vco = FREQ_MHZ * div
    actual = REF_MHZ * (i + fr / MOD_VAL) / div
    print(f"Target {FREQ_MHZ} MHz -> VCO {vco:.3f} MHz / {div}  "
          f"(INT={i} FRAC={fr}, {'integer-N' if is_int else 'fractional-N'})")
    print(f"Actual output: {actual:.4f} MHz   power: {POWER_DBM:+d} dBm")
    print("Registers: " + " ".join(f"0x{r:08X}" for r in regs))

    rp.rp_Init()
    if MONITOR_LD:
        rp.rp_DpinSetDirection(LD_PIN, rp.RP_IN)
    spi = open_spi()
    program(spi, regs)

    time.sleep(0.05)
    if MONITOR_LD:
        print(f"\nLock detect: {'LOCKED (LD high)' if ld_high() else 'NOT locked (LD low)'}")
    else:
        print("\nLD not monitored (wire disconnected). Confirm the tone on the scope.")
    print("Sanity check on the scope: a clean tone at the frequency above, and if")
    print("you can reach VTUNE/CP, it should sit mid-range (~0.5-2.5 V), not at a")
    print("rail. Tone present but LD low = trust the tone; see GUIDE section 6.\n")
    print("Holding output. Ctrl+C to stop and mute RF.")

    try:
        while True:
            time.sleep(1.0)
            if MONITOR_LD:
                print(f"  LD: {'high (locked)' if ld_high() else 'low  (unlocked)'}",
                      end="\r", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        r4_off = regs[4] & ~(1 << 5)     # clear RF-enable bit -> mute
        write_register(spi, r4_off)
        spi.close()
        rp.rp_Release()
        print("\nRF muted. Done.")


if __name__ == "__main__":
    main()
