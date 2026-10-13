"""
Run directly on the Red Pitaya:
    python rp_sine_out2_local.py [--freq 1000] [--amp 0.5] [--duration 10]

Uses the 'rp' C extension module that ships with the Red Pitaya OS image.
"""

import rp
import time

rp.rp_Init()

rp.rp_GenReset()
rp.rp_GenWaveform(rp.RP_CH_2, rp.RP_WAVEFORM_SINE)
rp.rp_GenFreq(rp.RP_CH_2, 1000.0)
rp.rp_GenAmp(rp.RP_CH_2, 0.5)
rp.rp_GenOffset(rp.RP_CH_2, 0.0)
rp.rp_GenOutEnable(rp.RP_CH_2)

print(f"OUT2 sine wave")

try:
    time.sleep(20)
except KeyboardInterrupt:
    print("Interrupted.")

rp.rp_GenOutDisable(rp.RP_CH_2)
rp.rp_GenReset()
rp.rp_Release()
print("Done.")