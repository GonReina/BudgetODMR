"""
SPI-alive diagnostic for the ADF4351 -- proves the Red Pitaya -> ADF SPI path
end to end WITHOUT needing the PLL to lock or any RF to come out.

How it works
------------
The ADF4351 has no MISO/readback, so we can't read a register. But the LD pin's
behaviour is software-controlled by R5 bits [23:22]:
    00 -> pin driven LOW
    01 -> digital lock detect (normal operation)
    11 -> pin driven HIGH
So if we write R5 with "force HIGH" and the Red Pitaya reads DIO0_P high, then
write "force LOW" and read it low, the entire chain (SPI clock/data/latch, the
ADF receiving and latching writes, the LD pin, the wire to DIO0_P) is proven
good -- independent of power-to-the-VCO, reference, or lock.

This is the FIRST thing to run when "nothing works": it cleanly separates
"the Pitaya isn't talking to the ADF" (wiring/SPI/ground/power-dead) from
"the ADF is talking but won't lock" (power quality / reference / band select).

Run on the Red Pitaya as root:   sudo python3 diag_spi_alive.py

Wiring (as built):
    E2 SPI SCK  -> ADF CLK
    E2 SPI MOSI -> ADF DATA
    E2 SPI CS   -> ADF LE
    ADF LD      -> E1 DIO0_P
    VDD/CE      -> 3.0-3.6 V,  common ground
"""

import time
import spidev
import rp

# --- config -----------------------------------------------------------------
SPI_BUS   = 2          # Gen-2 Red Pitaya E2 SPI = /dev/spidev2.0. Gen-1: try 1.
SPI_DEV   = 0
SPI_HZ    = 1_000_000
LD_PIN    = rp.RP_DIO0_P
SETTLE_S  = 0.05       # let the pin settle before reading

# R5 with control bits 101 and reserved [20:19]=11 preserved; only LD-mode varies
R5_FORCE_HIGH = 0x00D80005   # LD pin bits [23:22] = 11 -> driven HIGH
R5_FORCE_LOW  = 0x00180005   # LD pin bits [23:22] = 00 -> driven LOW
R5_NORMAL_DLD = 0x00580005   # LD pin bits [23:22] = 01 -> digital lock detect


def open_spi():
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEV)
    spi.max_speed_hz = SPI_HZ
    spi.mode = 0
    return spi


def write_register(spi, value):
    spi.xfer2([(value >> 24) & 0xFF, (value >> 16) & 0xFF,
               (value >> 8) & 0xFF, value & 0xFF])


def ld_high():
    return rp.rp_DpinGetState(LD_PIN)[1] == rp.RP_HIGH


def main():
    rp.rp_Init()
    rp.rp_DpinSetDirection(LD_PIN, rp.RP_IN)   # never DRIVE this pin -- ADF owns it
    spi = open_spi()
    print(f"Using /dev/spidev{SPI_BUS}.{SPI_DEV} @ {SPI_HZ/1e6:.1f} MHz, mode 0\n")

    ok = True

    write_register(spi, R5_FORCE_HIGH)
    time.sleep(SETTLE_S)
    hi = ld_high()
    print(f"  force LD HIGH -> DIO0_P reads {'HIGH' if hi else 'low '}  "
          f"{'OK' if hi else 'FAIL'}")
    ok &= hi

    write_register(spi, R5_FORCE_LOW)
    time.sleep(SETTLE_S)
    lo = not ld_high()
    print(f"  force LD LOW  -> DIO0_P reads {'LOW ' if lo else 'high'}  "
          f"{'OK' if lo else 'FAIL'}")
    ok &= lo

    # leave the chip in a sane state
    write_register(spi, R5_NORMAL_DLD)
    spi.close()
    rp.rp_Release()

    print()
    if ok:
        print("PASS: the Red Pitaya is talking to the ADF4351 over SPI, and the")
        print("      LD wire to DIO0_P is good. SPI/wiring/ground are NOT the")
        print("      problem -- if it still won't lock, look at power & reference")
        print("      (see TROUBLESHOOTING_GUIDE.md sections 3 and 4).")
    else:
        print("FAIL: the LD pin did not follow the forced HIGH/LOW commands.")
        print("      The Pitaya is NOT reliably writing the ADF, OR the LD->DIO0_P")
        print("      wire/ground is bad, OR the module has no power. Check, in order:")
        print("        * VDD pin = 3.0-3.6 V on a multimeter (power applied?)")
        print("        * common ground Pitaya<->ADF (continuity beep)")
        print("        * CLK/DATA/LE wires on the right E2 pins, /dev/spidevX.0 exists")
        print("        * LD wire actually on DIO0_P")
        print("      See TROUBLESHOOTING_GUIDE.md section 5.")


if __name__ == "__main__":
    main()
