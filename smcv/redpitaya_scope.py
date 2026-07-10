"""
Universal Red Pitaya fast-ADC acquisition over the SCPI server (port 5000),
following the official "instant signal acquisition" sequence:
https://redpitaya.readthedocs.io/en/latest/appsFeatures/examples/acquisition/acqRF-2-instant.html

Why this exists: the naive sequence (ACQ:START; ACQ:TRIG NOW; sleep; DATA?) reads a
buffer whose PRE-trigger half was never filled with fresh samples -> it comes back
as a block of zeros next to the real signal (a "square wave" when you concatenate
buffers). The documented fix, implemented here:

    ACQ:RST
    ACQ:DEC <decimation>
    ACQ:SOUR<ch>:GAIN <LV|HV>
    ACQ:TRIG:DLY 0                 # trigger in the middle of the buffer
    ACQ:START
    <wait ~one buffer time>        # PRE-FILL: make the pre-trigger samples fresh
    ACQ:TRIG NOW
    wait until ACQ:TRIG:FILL? == 1  # POST-fill: buffer completely valid
    ACQ:SOUR<ch>:DATA?

Pure standard library + numpy. Runs on the PC (talks to the Red Pitaya SCPI server).
"""

import socket
import time

import numpy as np


class RedPitayaScope:
    N_BUF = 16384          # fast-ADC buffer depth
    ADC_CLK = 125e6        # sample clock

    def __init__(self, ip, port=5000, timeout=15.0):
        self.sock = socket.create_connection((ip, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self._query("ACQ:DEC?")           # reachability check (raises if server down)

    # --- low-level SCPI (Red Pitaya server uses CR/LF terminator) ---
    def _write(self, cmd):
        self.sock.sendall(cmd.encode() + b"\r\n")

    def _query(self, cmd):
        self._write(cmd)
        buf = b""
        while not buf.endswith(b"\r\n"):
            chunk = self.sock.recv(65536)
            if not chunk:
                break
            buf += chunk
        return buf.decode(errors="replace").strip()

    def _parse(self, raw):
        raw = raw.strip().strip("{}")
        return np.array([float(x) for x in raw.split(",") if x.strip()])

    def acquire(self, channels=(1,), decimation=64, gain="LV", fill_timeout_s=3.0):
        """Capture one buffer per channel. `gain` is 'LV'/'HV' for all channels, or
        a dict {ch: 'LV'/'HV'}. Returns one np.array for a single channel, else a
        tuple of arrays (in the order of `channels`)."""
        fs = self.ADC_CLK / decimation
        self._write("ACQ:RST")
        self._write(f"ACQ:DEC {decimation}")
        for ch in channels:
            g = gain.get(ch, "LV") if isinstance(gain, dict) else gain
            try:
                self._write(f"ACQ:SOUR{ch}:GAIN {g}")
            except Exception:
                pass
        self._write("ACQ:TRIG:DLY 0")
        self._write("ACQ:START")
        # PRE-FILL: with the trigger centred (DLY 0), only the pre-trigger HALF of
        # the buffer must be fresh before we trigger, so ~0.5 buffer-time + margin
        # is enough (not a whole buffer). This keeps points from being stale zeros
        # while roughly halving the acquisition overhead vs a full-buffer pre-fill.
        time.sleep(self.N_BUF / fs * 0.65 + 0.005)
        self._write("ACQ:TRIG NOW")
        # POST-FILL: wait until the buffer is completely filled with valid data.
        deadline = time.time() + fill_timeout_s
        while True:
            if self._query("ACQ:TRIG:FILL?").strip().startswith("1"):
                break
            if time.time() > deadline:
                raise TimeoutError("Red Pitaya ADC buffer did not fill (ACQ:TRIG:FILL?)")
        out = [self._parse(self._query(f"ACQ:SOUR{ch}:DATA?")) for ch in channels]
        return out[0] if len(out) == 1 else tuple(out)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
