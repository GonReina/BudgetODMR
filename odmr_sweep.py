"""
ODMR frequency sweep for ADF4351 + NV diamond.

All the PLL register math and the sweep itself live here, in Python. The
Arduino runs `adf4351_bridge.ino`, which simply latches each 32-bit register
it receives over USB serial into the ADF4351. The photodiode output is
recorded externally; this script only steps the RF frequency and prints each
value as it is set.

Requires pyserial:   pip install pyserial
Run:                 python odmr_sweep.py --port COM3
"""

import argparse
import time

import serial

# ---- Reference / PLL configuration -----------------------------------------
REF_MHZ = 25.0          # on-board reference oscillator
R_COUNTER = 1           # R divider
FPFD_MHZ = REF_MHZ      # fPFD = REF * (1+D) / (R * (1+T)) with D=0, R=1, T=0

# 2800-3000 MHz lies inside the 2200-4400 MHz VCO band, so RF divider = 1.
RF_DIV = 1              # output divider value
RF_DIV_SEL = 0          # R4[22:20] code: 0->/1, 1->/2, 2->/4, 3->/8, ...

# Fractional modulus. fRES = fPFD / MOD = 25 MHz / 1000 = 25 kHz channel spacing.
MOD_VAL = 1000

# ---- Sweep parameters -------------------------------------------------------
F_START = 2800.0        # MHz
F_STOP = 3000.0         # MHz
F_STEP = 1.0            # MHz  (multiple of fPFD/MOD = 0.025 MHz lands exactly)

SETTLE_S = 0.005        # PLL lock + settle time per step, seconds


def build_registers(freq_mhz):
    """Return [R0, R1, R2, R3, R4, R5] for the requested output frequency."""
    vco = freq_mhz * RF_DIV          # VCO frequency, MHz
    n = vco / FPFD_MHZ               # total division ratio

    int_val = int(n)                            # 16-bit integer part
    frac_val = int(round((n - int_val) * MOD_VAL))

    # Handle rounding that pushes FRAC up to MOD.
    if frac_val >= MOD_VAL:
        frac_val = 0
        int_val += 1

    # R0: INT[30:15], FRAC[14:3], control 000
    r0 = (int_val << 15) | (frac_val << 3) | 0x0

    # R1: prescaler 8/9 (bit27), phase=1 (bit15), MOD[14:3], control 001
    r1 = (1 << 27) | (1 << 15) | (MOD_VAL << 3) | 0x1

    # R2: low-noise mode, MUXOUT=digital lock detect, R=1, CP=5 mA,
    # LDF=frac-N, PD polarity positive (passive filter), control 010
    r2 = 0x18005E42

    # R3: standard frac-N settings (6 ns ABP, band-sel mode low), control 011
    r3 = 0x000004B3

    # R4: feedback=fundamental (VCO), RF divider select, band-select-divider=250
    # (25 MHz / 250 = 100 kHz < 125 kHz), RF output enabled, +5 dBm, control 100
    r4 = (1 << 23) | (RF_DIV_SEL << 20) | (250 << 12) | 0x3C

    # R5: LD pin = digital lock detect, control 101
    r5 = 0x00580005

    return [r0, r1, r2, r3, r4, r5]


def set_frequency(ser, freq_mhz):
    """Program one frequency by sending registers R5 -> R0 (R0 last)."""
    regs = build_registers(freq_mhz)
    for reg in reversed(regs):          # R5, R4, R3, R2, R1, R0
        ser.write(f"{reg:08X}\n".encode())
        ser.readline()                  # consume the "OK <hex>" acknowledgement


def frange(start, stop, step):
    """Inclusive float range that tolerates floating-point round-off."""
    f = start
    while f <= stop + 1e-6:
        yield round(f, 6)
        f += step


def main():
    parser = argparse.ArgumentParser(description="ADF4351 ODMR frequency sweep")
    parser.add_argument("--port", required=True, help="serial port, e.g. COM3 or /dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--start", type=float, default=F_START, help="start freq, MHz")
    parser.add_argument("--stop", type=float, default=F_STOP, help="stop freq, MHz")
    parser.add_argument("--step", type=float, default=F_STEP, help="step size, MHz")
    parser.add_argument("--settle", type=float, default=SETTLE_S, help="settle time per step, s")
    parser.add_argument("--repeat", action="store_true", help="loop the sweep until interrupted")
    args = parser.parse_args()

    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        time.sleep(2.0)                 # allow the Arduino to reset after opening the port
        ser.reset_input_buffer()

        try:
            while True:
                for freq in frange(args.start, args.stop, args.step):
                    set_frequency(ser, freq)
                    time.sleep(args.settle)
                    print(f"{freq:.3f}")
                print("# sweep complete")
                if not args.repeat:
                    break
        except KeyboardInterrupt:
            print("\n# stopped")


if __name__ == "__main__":
    main()
