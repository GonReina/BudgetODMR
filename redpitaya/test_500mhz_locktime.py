"""
Bench test: program the ADF4351 to 500 MHz and measure the time from sending
the register data to the PLL asserting Lock Detect (LD).

Reuses ADF4351/build_registers from odmr_redpitaya.py -- the exact same
register-construction code the working ODMR sweep uses (R=1, CP=5 mA,
MUXOUT=digital lock detect, low-noise mode) -- instead of a separately
hand-maintained register set, so this bench test can't drift out of sync
with what's actually verified to work.

Run on the RedPitaya:   python3 test_500mhz_locktime.py

Wiring (as built):
  CLK -> SPI_CLK,  DAT -> SPI_MOSI,  LE -> SPI_CS
  3V3 -> ADF VDD and CE,  LD -> DIO0_P,  common ground
  ADF RF output -> oscilloscope (expect a single ~500 MHz tone)

Once locked, the RF output is held on continuously until you press Ctrl+C --
only then is it disabled, so the ADF doesn't keep transmitting after the
script has actually ended.

Note: the `rp` digital-pin calls (RP_DIO0_P, rp_DpinGetState, RP_HIGH/RP_LOW)
can vary by RedPitaya OS version. They're isolated in ld_state() below; run
`help(rp)` if a name differs on your image.
"""

import time

import rp

from odmr_redpitaya import ADF4351, SPI_HZ, build_registers

TEST_FREQ_MHZ = 500.0
LD_PIN = rp.RP_DIO0_P        # ADF LD is wired to DIO0_P
LOCK_TIMEOUT_S = 10

# Same R4 the sweep would use for this frequency but with bit 5 (RF Output
# Enable) cleared -- written at the end to kill the RF output instead of
# leaving it transmitting at 500 MHz.
R4_RF_OFF = build_registers(TEST_FREQ_MHZ)[4] & ~(1 << 5)


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
    adf = ADF4351(speed_hz=SPI_HZ)

    try:
        t_send = time.perf_counter()
        adf.set_frequency(TEST_FREQ_MHZ)  # writes R5->R1 then R0 last (triggers lock)

        # Writing R0 forces a VCO band-select, which drops LD low and then raises it
        # on lock. Wait through the drop (guards against reading a stale 'high'),
        # then time to the lock edge.
        wait_until(lambda: not ld_state(), t_send)   # LD goes low (re-acquiring)
        locked = wait_until(ld_state, t_send)        # LD goes high (locked)
        t_lock = time.perf_counter()

        if locked:
            print(f"LOCKED. Data-sent -> LD high: {(t_lock - t_send) * 1e3:.3f} ms")
            print(f"ADF is now outputting {TEST_FREQ_MHZ:.0f} MHz continuously -- "
                  "check it on the scope. Press Ctrl+C to stop and disable the RF output.")
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
        adf.write_register(R4_RF_OFF)
        adf.close()
        rp.rp_Release()


if __name__ == "__main__":
    main()
