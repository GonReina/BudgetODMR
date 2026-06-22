"""
Bench test: program the ADF4351 to 500 MHz and measure the time from sending
the register data to the PLL asserting Lock Detect (LD).

Run on the RedPitaya:   python3 test_500mhz_locktime.py

Wiring (as built):
  CLK -> SPI_CLK,  DAT -> SPI_MOSI,  LE -> SPI_CS
  3V3 -> ADF VDD and CE,  LD -> DIO0_P,  common ground
  ADF RF output -> oscilloscope (expect a single ~500 MHz tone)

Once locked, the RF output is held on continuously until you press Ctrl+C --
only then is it disabled, so the ADF doesn't keep transmitting after the
script has actually ended.

Note: the `rp` digital-pin calls (RP_DIO0_P, rp_DpinGetState, RP_HIGH/RP_LOW)
can vary by RedPitaya OS version. They're isolated in ld_state()/setup below;
run `help(rp)` if a name differs on your image.
"""

import time

import spidev
import rp

# --- 500 MHz register set (REF = 25 MHz, VCO = 4000 MHz, RF divider /8) ------
# Identical to the verified Arduino set500MHz(): INT=160, FRAC=0 (integer-N).
# R0 is last in the list but written last on purpose (it triggers the lock).
REGISTERS_500MHZ = [
    0x00500000,  # R0: INT=160 (VCO = 160 * 25 MHz = 4000 MHz), FRAC=0
    0x08008011,  # R1: prescaler 8/9, MOD=2, phase=1
    0x78005E42,  # R2: R=1, CP=5 mA, MUXOUT=digital lock detect, low-spur
                 # (was 0x18005E42/low-noise -- low noise/low spur select is
                 # bits[30:29] ("11"=low spur), set to suppress the reference
                 # sidebands seen around 500 MHz. NOT bit 31 -- that's
                 # RESERVED per the datasheet and must stay 0; a prior edit
                 # wrongly set it (0x98005E42), which broke PLL lock entirely)
    0x000004B3,  # R3
    0x00BFA03C,  # R4: RF divider /8, feedback=VCO, RF enabled, +5 dBm
    0x00580005,  # R5: LD pin = digital lock detect
]

# Same as R4 above but with bit 5 (RF Output Enable) cleared -- written at the
# end to kill the RF output instead of leaving it transmitting at 500 MHz.
R4_RF_OFF = REGISTERS_500MHZ[4] & ~(1 << 5)

LD_PIN = rp.RP_DIO0_P        # ADF LD is wired to DIO0_P
LOCK_TIMEOUT_S = 10


def open_spi(speed_hz=1_000_000):
    spi = spidev.SpiDev()
    spi.open(2, 0)           # /dev/spidev1.0 on the RedPitaya E2 connector
    spi.max_speed_hz = speed_hz
    spi.mode = 0             # CPOL=0, CPHA=0; CS rising edge = ADF LE latch
    return spi


def write_register(spi, value):
    spi.xfer2([
        (value >> 24) & 0xFF,
        (value >> 16) & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    ])


def ld_state():
    """Return True if the LD pin reads high (PLL locked)."""
    return rp.rp_DpinGetState(LD_PIN)[1] == rp.RP_HIGH


def wait_until(predicate, t_start):
    """Poll predicate() until True or timeout. Return True if satisfied."""
    while time.perf_counter() - t_start < LOCK_TIMEOUT_S:
        if predicate():
            return True
    return False


def main():
    rp.rp_Init()
    rp.rp_DpinSetDirection(LD_PIN, rp.RP_IN)
    spi = open_spi()

    try:
        # Program R5 -> R1 first; the final R0 write launches band-select + lock.
        for reg in REGISTERS_500MHZ[:0:-1]:      # R5, R4, R3, R2, R1
            write_register(spi, reg)

        t_send = time.perf_counter()
        write_register(spi, REGISTERS_500MHZ[0])  # R0 -- data sent, lock starts now

        # Writing R0 forces a VCO band-select, which drops LD low and then raises it
        # on lock. Wait through the drop (guards against reading a stale 'high'),
        # then time to the lock edge.
        wait_until(lambda: not ld_state(), t_send)   # LD goes low (re-acquiring)
        locked = wait_until(ld_state, t_send)        # LD goes high (locked)
        t_lock = time.perf_counter()

        if locked:
            print(f"LOCKED. Data-sent -> LD high: {(t_lock - t_send) * 1e3:.3f} ms")
            print("ADF is now outputting 500 MHz continuously -- check it on the "
                  "scope. Press Ctrl+C to stop and disable the RF output.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping.")
        else:
            print(f"NO LOCK within {LOCK_TIMEOUT_S * 1e3:.0f} ms.")
            print("Check: ADF VDD on 3.3 V, CE high, common ground, LD -> DIO0_P,")
            print("       SPI wiring, and /dev/spidev1.0 exists.")
    finally:
        # Kill the RF output instead of leaving the ADF transmitting 500 MHz
        # after the script exits.
        write_register(spi, R4_RF_OFF)
        spi.close()
        rp.rp_Release()


if __name__ == "__main__":
    main()
