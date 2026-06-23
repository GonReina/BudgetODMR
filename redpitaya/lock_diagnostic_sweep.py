"""
Diagnostic sweep: step the ADF4351 from 500 MHz down to 80 MHz in 20 MHz
steps, holding each frequency for a fixed dwell time so the oscilloscope and
the board's D3 lock LED can be watched at each point.

Earlier bench tests found the lock-detect circuit (LD pin / D3 LED) gives
unreliable readings at frequencies far from the working ODMR sweep range
(2700-3000 MHz). This script doesn't try to make automated lock/no-lock
calls -- it just dwells long enough at each step for a human to look and
note what's actually on the scope and the LED, across a range of VCO
targets and RF dividers, to map out where this board does and doesn't lock.

Run on the RedPitaya:   python3 lock_diagnostic_sweep.py
(There are no command-line arguments by design.)

Wiring: same as odmr_redpitaya.py / test_500mhz_locktime.py. The RF output
is disabled when the script ends or you press Ctrl+C.
"""

import time

import rp

from odmr_redpitaya import ADF4351, SPI_HZ, build_registers

START_FREQ_MHZ = 100.0
STOP_FREQ_MHZ = 200.0
STEP_MHZ = 10.0      # negative: sweeping downward
DWELL_S = 5.0         # time spent at each frequency before moving on

LD_PIN = rp.RP_DIO0_P  # ADF LD is wired to DIO0_P


def ld_state():
    """Return True if the LD pin reads high (PLL locked)."""
    return rp.rp_DpinGetState(LD_PIN)[1] == rp.RP_HIGH


def frange(start, stop, step):
    f = start
    while (f >= stop - 1e-6) if step < 0 else (f <= stop + 1e-6):
        yield round(f, 6)
        f += step


def main():
    rp.rp_Init()
    rp.rp_DpinSetDirection(LD_PIN, rp.RP_IN)
    adf = ADF4351(speed_hz=SPI_HZ)

    freqs = list(frange(START_FREQ_MHZ, STOP_FREQ_MHZ, STEP_MHZ))
    current_freq = START_FREQ_MHZ
    print(f"Sweeping {START_FREQ_MHZ:.0f} -> {STOP_FREQ_MHZ:.0f} MHz in "
          f"{STEP_MHZ:.0f} MHz steps, {DWELL_S:.0f} s/step. "
          "Watch the scope and the D3 LED.")

    try:
        for i, freq in enumerate(freqs, 1):
            current_freq = freq
            adf.set_frequency(freq)
            t0 = time.perf_counter()

            # Writing R0 forces a band-select recal, which should drop LD low
            # before it can rise again on a genuine lock. Give that a brief,
            # bounded moment so a stale 'high' from the previous step isn't
            # mistaken for an instant lock -- but don't eat the whole dwell
            # if LD is stuck (it's been unreliable at some frequencies).
            drop_deadline = t0 + min(1.0, DWELL_S)
            while ld_state() and time.perf_counter() < drop_deadline:
                time.sleep(0.01)

            lock_ms = None
            while time.perf_counter() - t0 < DWELL_S:
                if lock_ms is None and ld_state():
                    lock_ms = (time.perf_counter() - t0) * 1e3
                    print(f"[{i}/{len(freqs)}] {freq:.0f} MHz -- "
                          f"LD high after {lock_ms:.0f} ms")
                time.sleep(0.05)

            if lock_ms is None:
                print(f"[{i}/{len(freqs)}] {freq:.0f} MHz -- "
                      f"LD never went high in {DWELL_S:.0f} s")
    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        # Kill the RF output instead of leaving the ADF transmitting.
        r4_off = build_registers(current_freq)[4] & ~(1 << 5)
        adf.write_register(r4_off)
        adf.close()
        rp.rp_Release()


if __name__ == "__main__":
    main()
