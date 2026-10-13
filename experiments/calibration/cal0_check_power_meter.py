"""
Step 0 (optional): can Python talk to the PM101A?

Lists the VISA resources, opens the first Thorlabs one (USB vendor 0x1313),
sets 532 nm, and prints ten readings. If this works, the cal1_* scripts log the
power automatically. If not, they still run: you type the readings in.

To get USB working (see calib_common.PowerMeter):
    pip install pyvisa
    install NI-VISA, then (if the meter is not listed) select the NI-VISA driver
    for the PM101 in Thorlabs' "Power Meter Driver Switcher".

Run on the PC:  python cal0_check_power_meter.py
"""

import time

from calib_common import PowerMeter

WAVELENGTH_NM = 532.0
N_READ = 10


def main():
    try:
        import pyvisa
        rm = pyvisa.ResourceManager()
        print(f"VISA library: {rm}")
        print(f"VISA resources: {rm.list_resources()}")
    except ImportError:
        print("pyvisa is not installed:  pip install pyvisa  (plus a VISA library)")
        return
    except Exception as e:
        print(f"pyvisa is installed but found no VISA library ({e}).\n"
              "Install NI-VISA, or:  pip install pyvisa-py pyusb  (needs libusb).")
        return

    pm = PowerMeter(WAVELENGTH_NM)
    if pm.manual:
        print("\nNo power meter connection -> the cal1 scripts will ask you to "
              "type the readings in.")
        return
    try:
        for i in range(N_READ):
            print(f"  reading {i + 1:2d}: {pm.read_mw():.6f} mW")
            time.sleep(0.2)
        print("\nOK: the PM101A answers. The cal1_* scripts will log it automatically.")
    finally:
        pm.close()


if __name__ == "__main__":
    main()
