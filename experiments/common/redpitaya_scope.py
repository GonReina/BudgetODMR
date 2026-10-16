"""
Universal Red Pitaya fast-ADC acquisition over the SCPI server (port 5000),
following the official "instant signal acquisition" sequence:
https://redpitaya.readthedocs.io/en/latest/appsFeatures/examples/acquisition/acqRF-2-instant.html

Why this exists: the naive sequence (ACQ:START; ACQ:TRIG NOW; sleep; DATA?) reads a
buffer whose PRE-trigger half was never filled with fresh samples -> it comes back
as a block of zeros next to the real signal (a "square wave" when you concatenate
buffers).

The trigger is put at the START of the buffer (ACQ:TRIG:DLY = N_BUF/2; DLY 0
means "trigger in the middle"), so the whole record is POST-trigger: one
continuous stretch of samples. With the trigger in the middle (the old
sequence) the pre- and post-trigger halves were NOT continuous: fm_check
(2026-10-15) found a random phase jump of a test tone at the mid-record
trigger point in most records (lock-in magnitude scatter 25 % on full records
vs 0.5-1.7 % on the post-trigger half alone), and the pre-trigger half itself
was sometimes stale. That hurts anything that demodulates or Fourier-transforms
a record (lock-in, spectra, RIN, Rabi edges); plain DC means were unaffected.

    ACQ:RST
    ACQ:DEC <decimation>
    ACQ:SOUR<ch>:GAIN <LV|HV>
    ACQ:TRIG:DLY 8192              # trigger at the start: all samples post-trigger
    ACQ:START
    ACQ:TRIG NOW
    wait until ACQ:TRIG:FILL? == 1  # buffer completely filled after the trigger
    ACQ:SOUR<ch>:DATA?              # oldest sample first = the trigger sample

Pure standard library + numpy. Runs on the PC (talks to the Red Pitaya SCPI server).
"""

import socket
import time

import numpy as np


class RedPitayaScope:
    N_BUF = 16384          # fast-ADC buffer depth
    ADC_CLK = 125e6        # sample clock
    TRIG_DLY = N_BUF // 2  # trigger at the buffer start (0 = middle, the old seam)
    CONTIGUOUS = True      # records are one continuous stretch (saved in metadata)

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
        # trigger at the start of the buffer: every sample is post-trigger, so the
        # record is continuous and no pre-fill wait is needed (see module doc)
        self._write(f"ACQ:TRIG:DLY {self.TRIG_DLY}")
        self._write("ACQ:START")
        self._write("ACQ:TRIG NOW")
        # FILL: wait until the whole buffer has been written after the trigger
        # (one buffer time; never time out before 1.5 buffer times)
        deadline = time.time() + max(fill_timeout_s, 1.5 * self.N_BUF / fs + 1.0)
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
