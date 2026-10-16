"""
Shared helpers for the laser / detector calibration protocol in this folder.
CALIBRATION_PROTOCOL.md gives the run order:

  cal0_*  check the PM101A analog output on Red Pitaya IN2, measure mW/V
  cal1_*  power after the objective vs laser current   (PM101A + S120C on IN2)
  cal2_*  laser noise vs current and vs photocurrent    (PDA10A2 on Red Pitaya IN1,
                                                         optional power monitor on IN2)
  cal3_*  PL vs power at the sample, with CW ODMR       (APD on IN1, SMCV100B,
                                                         power monitor typed in)

What lives here:
  * PowerMeter      -- Thorlabs PM101A read through its analog output on IN2;
                       prepare_power_meter zeroes it and gets the mW/V factor
  * Photodiode      -- raw Red Pitaya IN1 records (RedPitayaScope), optionally
                       with the IN2 power monitor in the same acquisition
  * wait_stable     -- wait until a reading stops drifting (TEC / DPSS settling)
  * prompts         -- ask_current, ask_tec, ask_float, ...
  * TableWriter / read_table -- the repo CSV convention ('# key=value' header)
  * load_power_table -- the current -> power-at-sample table made in step 1
  * fit_odmr        -- Lorentzian-dip fit giving contrast, FWHM and centres

Everything is written to <paths.data_dir>/calibration/ (config.json).

The laser current is set BY HAND on the LDC200C and typed in. The TEC
temperature is typed in from the controller display (blank if not available).
"""

import os
import sys
import time
from datetime import datetime

import numpy as np

# Shared instrument code lives in experiments/common/.
_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from expconfig import load_config

_cfg = load_config()
RP_IP, RP_PORT = _cfg["instruments"]["rp_ip"], _cfg["instruments"]["rp_port"]
RP_GAIN = _cfg["redpitaya"]["input_gain"]
IN2_GAIN = _cfg["redpitaya"].get("in2_gain", "HV")
F_MOD = _cfg["lockin"]["f_mod_hz"]
D_CENTER_MHZ = _cfg["analysis"]["d_center_mhz"]
MIN_SEP_MHZ = _cfg["analysis"]["min_sep_mhz"]

CAL_DIR = os.path.join(_cfg["paths"]["data_dir"], "calibration")
POWER_TABLE = os.path.join(CAL_DIR, "power_calibration.csv")
PM_CAL_FILE = os.path.join(CAL_DIR, "pm101a_analog_cal.csv")   # mW/V factors
# PM101A analog output in responsivity mode: V = P x responsivity (set on the
# meter, "AO responsivity"), independent of the range. The factor is still
# MEASURED against Optical Power Monitor; this nominal value is the cross-check.
PM_RESPONSIVITY_V_PER_W = _cfg["redpitaya"].get("pm_ao_responsivity_v_per_w")
# settled if the drift over 10 s is below this many volts, even near zero power:
# a few times the per-reading noise on each IN2 range
PM_SETTLE_FLOOR_V = {"LV": 0.5e-3, "HV": 5e-3}

MAINS_HZ = 50.0              # mains frequency: DC levels average whole cycles of it

DZFS_MHZ_PER_K = -0.074      # zero-field splitting temperature coefficient
N_BUF = 16384                # Red Pitaya fast-ADC buffer (samples per record)


def mains_mean(x, fs):
    """Mean of x over the largest whole number of mains cycles in the record, so
    50/100 Hz hum averages out instead of leaking into the DC level (a 134 ms
    record holds 6.7 cycles; a partial cycle makes the mean jump record to
    record). Falls back to the plain mean for records shorter than a cycle."""
    n = int(round(int(len(x) * MAINS_HZ / fs) * fs / MAINS_HZ))
    return float(np.mean(x[:n] if n > 0 else x))


def cal_path(name):
    """Path of an output file in CAL_DIR (created on first use)."""
    os.makedirs(CAL_DIR, exist_ok=True)
    return os.path.join(CAL_DIR, name)


def stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def latest(pattern, cal_dir=None, exclude=("_log.csv",)):
    """Newest file in cal_dir matching the glob pattern (the names carry a
    sortable time stamp), or None."""
    import glob
    hits = [p for p in glob.glob(os.path.join(cal_dir or CAL_DIR, pattern))
            if not p.endswith(tuple(exclude))]
    return max(hits) if hits else None


def cal_dir_from_argv():
    """Plotters accept an optional calibration directory as their only argument."""
    return sys.argv[1] if len(sys.argv) > 1 else CAL_DIR


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
class Stop(Exception):
    """The user typed q at a prompt."""


def ask(msg, default=None):
    tail = f" [{default}]" if default not in (None, "") else ""
    s = input(f"{msg}{tail}: ").strip()
    if s.lower() in ("q", "quit"):
        raise Stop
    return s if s else ("" if default is None else str(default))


def ask_float(msg, default=None, blank_ok=False):
    while True:
        s = ask(msg, default)
        if s == "" and blank_ok:
            return None
        try:
            return float(s)
        except ValueError:
            print("  not a number -- try again (q stops)")


def ask_yes(msg, default=True):
    s = ask(msg + (" (Y/n)" if default else " (y/N)")).lower()
    return default if s == "" else s.startswith("y")


def pause(msg):
    input(f"{msg}  [Enter, or Ctrl-C to abort] ")


def ask_current(planned_ma, i_max_ma):
    """Ask the user to dial a current and type what the LDC200C shows.
    Returns the current in mA, or None to skip this point. q stops (Stop)."""
    while True:
        s = ask(f"\nSet the LDC200C to {planned_ma:.2f} mA and type the current "
                f"it READS (Enter = {planned_ma:.2f}, s = skip, q = stop)")
        if s.lower() == "s":
            return None
        try:
            cur = float(s) if s else float(planned_ma)
        except ValueError:
            print("  not a number")
            continue
        if cur > i_max_ma:
            print(f"  {cur:.2f} mA is above I_MAX_MA = {i_max_ma:.2f} mA -- "
                  "refused. Lower the current.")
            continue
        return cur


def ask_tec():
    """TEC / crystal temperature from the controller display (NaN if blank)."""
    t = ask_float("  TEC temperature in C (blank if not available)", blank_ok=True)
    return float("nan") if t is None else t


def countdown(seconds, msg="waiting"):
    end = time.time() + seconds
    while True:
        left = end - time.time()
        if left <= 0:
            break
        print(f"\r  {msg}: {left:5.0f} s ", end="", flush=True)
        time.sleep(min(1.0, left))
    print("\r" + " " * 40 + "\r", end="")


def wait_stable(read, period_s=0.5, window_s=10.0, tol_frac=0.005, min_s=20.0,
                max_s=180.0, unit="", scale=1.0, abs_tol=0.0):
    """Read `read()` repeatedly until the drift over the last `window_s` seconds
    (linear fit) is below tol_frac of the mean, or below abs_tol (same units as
    read()) -- the floor that lets a reading near zero, e.g. below the laser
    threshold, count as stable -- after at least min_s. Gives up with a
    warning after max_s. Ctrl-C stops waiting early. Returns the elapsed time.
    Used to let the TEC and the DPSS output settle after a current step."""
    t0 = time.time()
    ts, vs = [], []
    try:
        while True:
            v = read()
            t = time.time() - t0
            ts.append(t)
            vs.append(v)
            keep = [i for i, ti in enumerate(ts) if ti >= t - window_s]
            change, limit = float("nan"), float("nan")
            tt, vv = np.array(ts)[keep], np.array(vs)[keep]
            if len(keep) >= 4 and np.ptp(tt) > 0.5 and np.all(np.isfinite(vv)):
                slope = np.polyfit(tt - tt.mean(), vv, 1)[0]
                change = abs(slope) * window_s
                limit = max(tol_frac * abs(vv.mean()), abs_tol)
            print(f"\r  settling {t:5.0f} s: {v * scale:10.4g} {unit}   drift over "
                  f"{window_s:.0f} s = {change * scale:8.3g} {unit} (target < "
                  f"{limit * scale:.3g} {unit})   ", end="", flush=True)
            if t >= min_s and change <= limit:
                print("\n  stable.")
                return t
            if t >= max_s:
                print(f"\n  WARNING: still drifting after {max_s:.0f} s -- "
                      "logging anyway (note it).")
                return t
            time.sleep(period_s)
    except KeyboardInterrupt:
        print("\n  (settling skipped by Ctrl-C)")
        return time.time() - t0


# ---------------------------------------------------------------------------
# Thorlabs PM101A power meter, read through its ANALOG OUTPUT on Red Pitaya IN2
# ---------------------------------------------------------------------------
class PowerMeter:
    """Thorlabs PM101A (+ S120C), read through its analog output on Red Pitaya IN2.

    The analog output (responsivity mode) is V = P x the "AO responsivity"
    set in Optical Power Monitor (1 mV/W .. 1 kV/W), independent of the range.
    So:
      * choose the responsivity so the HIGHEST power gives ~0.7-0.9 V on the LV
        jumper (e.g. 15 V/W for 50 mW), record it in config.json
        redpitaya.pm_ao_responsivity_v_per_w, and keep it for the whole run;
      * the volts -> mW factor (nominally 1000 / responsivity mW/V) also depends
        on the wavelength correction and the Red Pitaya IN2 front end. It is
        MEASURED by calibrate() against Optical Power Monitor, compared with the
        nominal value, and saved in PM_CAL_FILE for later scripts;
      * the offset (analog-output offset + ADC offset + room light) is
        measured with the beam blocked by zero().

    Wiring: PM101A analog out -> Red Pitaya IN2, jumper and config.json
    redpitaya.in2_gain matching (LV: +/- 1 V, ~20x finer steps; HV: +/- 20 V).

    read_v() works from the start; read_mw() is NaN until a factor is known.
    Pass scope= to share an already open RedPitayaScope (one SCPI connection).
    """

    def __init__(self, decimation=1024, gain=None, channel=2, scope=None):
        from redpitaya_scope import RedPitayaScope
        self._own_scope = scope is None
        self.scope = scope or RedPitayaScope(RP_IP, RP_PORT)
        self.decimation = decimation
        self.gain = gain or IN2_GAIN
        self.channel = channel
        self.clip_v = 0.95 if self.gain == "LV" else 19.0
        self.fs = 125e6 / decimation
        self.v_zero = 0.0
        self.mw_per_v = float("nan")
        self.pm_range = ""
        self._warned = set()
        print(f"Power meter: PM101A analog out on Red Pitaya IN{channel} "
              f"({RP_IP}:{RP_PORT}), gain {self.gain}, decimation {decimation}")

    @property
    def calibrated(self):
        return np.isfinite(self.mw_per_v)

    @property
    def idn(self):
        return (f"PM101A analog out on RP IN{self.channel} ({self.gain}); "
                f"range {self.pm_range or '?'}")

    def meta(self):
        """Settings for a CSV header."""
        return dict(power_meter=self.idn, pm_range=self.pm_range or "?",
                    in2_gain=self.gain, mw_per_v=self.mw_per_v,
                    v_zero_V=self.v_zero)

    def check_clip(self, x):
        peak = float(np.max(x))
        if peak > self.clip_v and "adc" not in self._warned:
            self._warned.add("adc")
            print(f"\n  WARNING: IN{self.channel} reaches {peak:.3f} V -- clipping on "
                  f"the {self.gain} range: LOWER the AO responsivity on the meter "
                  "(then calibrate again), or use the HV jumper.")

    def read_v(self):
        """Mean IN2 voltage over whole mains cycles of one record (offset NOT
        removed)."""
        x = self.record()
        self.check_clip(x)
        return mains_mean(x, self.fs)

    def record(self):
        return self.scope.acquire((self.channel,), self.decimation, self.gain,
                                  fill_timeout_s=5.0)

    def read_net_v(self):
        return self.read_v() - self.v_zero

    def read_mw(self):
        return self.read_net_v() * self.mw_per_v

    def mean_v(self, seconds):
        """Mean and std of the raw per-record level over `seconds`."""
        t0, v = time.time(), []
        while not v or time.time() - t0 < seconds:
            v.append(self.read_v())
        return float(np.mean(v)), float(np.std(v, ddof=1)) if len(v) > 1 else float("nan")

    def zero(self, seconds=3.0, prompt=True):
        """Offset with the beam blocked. prompt=False: the caller has already
        asked for the beam to be blocked (and will ask to unblock it)."""
        if prompt:
            pause("  ZERO: block the beam completely (sensor in place)")
        v, s = self.mean_v(seconds)
        self.v_zero = v
        print(f"  power meter zero = {v * 1e3:.2f} mV (+/- {s * 1e3:.2f})")
        if prompt:
            pause("  Unblock the beam")

    def calibrate(self, seconds=10.0):
        """Measure mW/V against Optical Power Monitor (beam on and steady, the
        brighter the better). zero() first. Appends the result to PM_CAL_FILE."""
        print("  CALIBRATE the analog output against Thorlabs Optical Power Monitor:\n"
              "    532 nm, AO responsivity FIXED (keep it for the whole run), "
              "averaging on.")
        resp = ask_float("  AO responsivity set on the meter (V/W)",
                         PM_RESPONSIVITY_V_PER_W)
        self.pm_range = f"AO {resp:g} V/W"
        while True:
            pause(f"  Watch the Optical Power Monitor reading for {seconds:.0f} s, "
                  "starting now")
            v, s = self.mean_v(seconds)
            net = v - self.v_zero
            print(f"  IN{self.channel}: {net * 1e3:.2f} mV above zero (+/- {s * 1e3:.2f})")
            p_ref = ask_float("  mean power Optical Power Monitor showed (mW)")
            if net > 0.02 and p_ref > 0:
                break
            print("  the signal is too small to calibrate on (< 20 mV, or P <= 0): "
                  "use a brighter point or a higher AO responsivity.")
            if not ask_yes("  try again?"):
                raise Stop
        self.mw_per_v = p_ref / net
        nominal = 1000.0 / resp if resp else float("nan")
        ratio = self.mw_per_v / nominal
        print(f"  factor = {self.mw_per_v:.6g} mW/V  (nominal for {resp:g} V/W: "
              f"{nominal:.6g} mW/V, measured / nominal = {ratio:.3f})")
        if not 0.9 < ratio < 1.1:
            print("  WARNING: more than 10 % from nominal. Check that the cable is on "
                  "the analog output you configured, that the IN2 jumper matches "
                  f"config.json in2_gain ({self.gain}; a mismatch gives ~x20), and "
                  "the Optical Power Monitor reading.")
        print(f"  full scale before IN2 clips: ~{self.clip_v * self.mw_per_v:.4g} mW")
        os.makedirs(CAL_DIR, exist_ok=True)
        new = not os.path.exists(PM_CAL_FILE)
        with open(PM_CAL_FILE, "a") as f:
            if new:
                f.write("# experiment=pm101a_analog_calibration\n"
                        "created,pm_range,in2_gain,decimation,v_zero_V,v_net_V,"
                        "v_std_V,P_ref_mW,mw_per_v\n")
            f.write(",".join(_fmt(x) for x in (
                datetime.now().isoformat(timespec="seconds"),
                self.pm_range.replace(",", " "), self.gain, self.decimation,
                self.v_zero, net, s, p_ref, self.mw_per_v)) + "\n")
        print(f"  saved to {PM_CAL_FILE}")

    def load_saved(self):
        """Offer the newest factor in PM_CAL_FILE. True if it was accepted."""
        if not os.path.exists(PM_CAL_FILE):
            return False
        _, c = read_table(PM_CAL_FILE)
        if not len(c.get("mw_per_v", [])):
            return False
        k, gain = float(c["mw_per_v"][-1]), str(c["in2_gain"][-1])
        rng, when = str(c["pm_range"][-1]), str(c["created"][-1])
        if gain != self.gain:
            print(f"  (saved factor is for IN2 {gain}, now {self.gain}: not reused)")
            return False
        if not ask_yes(f"  Reuse the saved factor {k:.6g} mW/V ({when}, {rng})? Only if "
                       "the AO responsivity, wavelength and IN2 jumper are unchanged"):
            return False
        self.mw_per_v, self.pm_range = k, rng
        return True

    def settle(self, min_s=20.0, max_s=180.0, tol_frac=0.005, window_s=10.0):
        # absolute floor: near zero power (below threshold) tol_frac of the mean
        # is below the noise and would never be reached
        floor_v = PM_SETTLE_FLOOR_V.get(self.gain, 5e-3)
        if self.calibrated:
            return wait_stable(self.read_mw, 0.5, window_s, tol_frac, min_s, max_s,
                               unit="mW", abs_tol=floor_v * self.mw_per_v)
        return wait_stable(self.read_net_v, 0.5, window_s, tol_frac, min_s, max_s,
                           unit="mV", scale=1e3, abs_tol=floor_v)

    def log(self, seconds, period_s=0.2):
        """Log for `seconds`, one record every >= period_s.
        Returns dict(mean, std, slope [mW/s], n, t, p [mW], v [V above zero])."""
        t0 = time.time()
        ts, vs = [], []
        while not ts or time.time() - t0 < seconds:
            t_rd = time.time()
            vs.append(self.read_net_v())
            ts.append(t_rd - t0)
            print(f"\r  logging {ts[-1]:5.1f}/{seconds:.0f} s: "
                  f"{vs[-1] * self.mw_per_v:10.5f} mW ({vs[-1] * 1e3:8.2f} mV) ",
                  end="", flush=True)
            time.sleep(max(0.0, period_s - (time.time() - t_rd)))
        print()
        t, v = np.array(ts), np.array(vs)
        p = v * self.mw_per_v
        slope = float(np.polyfit(t, p, 1)[0]) if len(t) > 2 else float("nan")
        return dict(mean=float(p.mean()), std=float(p.std(ddof=1)) if len(p) > 1
                    else float("nan"), slope=slope, n=len(p), t=t, p=p, v=v)

    def close(self):
        if self._own_scope:
            self.scope.close()


def prepare_power_meter(pm, cal_ma=None, i_max_ma=None, settle_min_s=20.0,
                        settle_max_s=180.0, required=True, zeroed=False):
    """Zero the meter, then get a mW/V factor: reuse the saved one, or calibrate.
    With cal_ma the user first sets that current (pick the TOP of the run: the
    largest signal gives the best factor) and the output settles.
    required=False (power monitor): the factor may be skipped and only volts
    are then meaningful. zeroed=True: pm.zero() was already done."""
    if not zeroed:
        pm.zero()
    if pm.load_saved():
        return
    if not required and not ask_yes("  Calibrate the power meter now (needs "
                                     "Optical Power Monitor)? No = log volts only",
                                     default=False):
        return
    if cal_ma is not None:
        print("  calibration point: the brightest current of the run")
        cur = ask_current(cal_ma, i_max_ma if i_max_ma is not None else cal_ma)
        if cur is not None:
            pm.settle(settle_min_s, settle_max_s)
    pm.calibrate()

# ---------------------------------------------------------------------------
# Red Pitaya IN1 (PDA10A2 for noise, APD for PL)
# ---------------------------------------------------------------------------
class Photodiode:
    """Raw fast-ADC records from Red Pitaya IN1 via the SCPI server.

    monitor=True also reads the PM101A analog output on IN2 (self.pm, a
    PowerMeter on the same connection) as a laser power monitor: records()
    then acquires both channels together and leaves the per-record monitor
    level in self.mon_v (V above zero) and self.mon_mw (NaN without a factor).
    Zero / calibrate it first with prepare_power_meter(pd.pm, required=False)."""

    def __init__(self, decimation=1024, gain=None, channel=1, monitor=False):
        from redpitaya_scope import RedPitayaScope
        self.scope = RedPitayaScope(RP_IP, RP_PORT)
        self.decimation = decimation
        self.gain = gain or RP_GAIN
        self.channel = channel
        self.fs = 125e6 / decimation
        self.clip_v = 0.95 if self.gain == "LV" else 19.0
        print(f"Red Pitaya IN{channel} at {RP_IP}:{RP_PORT}: decimation "
              f"{decimation} (fs = {self.fs:.0f} Hz), gain {self.gain}")
        self.pm = PowerMeter(decimation, scope=self.scope) if monitor else None
        self.mon_v = self.mon_mw = np.array([])

    def record(self):
        return self.scope.acquire((self.channel,), self.decimation, self.gain,
                                  fill_timeout_s=5.0)

    def records(self, n):
        if self.pm is None:
            recs = np.array([self.record() for _ in range(n)])
        else:
            recs, mon = [], []
            for _ in range(n):
                a, b = self.scope.acquire((self.channel, self.pm.channel),
                                          self.decimation,
                                          {self.channel: self.gain,
                                           self.pm.channel: self.pm.gain},
                                          fill_timeout_s=5.0)
                self.pm.check_clip(b)
                recs.append(a)
                mon.append(mains_mean(b, self.fs) - self.pm.v_zero)
            recs = np.array(recs)
            self.mon_v = np.array(mon)
            self.mon_mw = self.mon_v * self.pm.mw_per_v
        peak = float(np.max(np.abs(recs)))
        if peak > self.clip_v:
            print(f"  WARNING: |V| reaches {peak:.3f} V -- IN1 may be clipping "
                  f"({self.gain} range). Attenuate, or use the HV jumper.")
        return recs

    def dc(self):
        return float(np.mean(self.record()))

    def dc_mean(self, seconds):
        """Mean and std of the per-record DC level over >= `seconds`."""
        n = max(1, int(np.ceil(seconds * self.fs / N_BUF)))
        v = [self.dc() for _ in range(n)]
        return float(np.mean(v)), float(np.std(v, ddof=1)) if n > 1 else float("nan")

    def close(self):
        self.scope.close()


def live_dc_monitor(pd, target_v=None, tol_frac=None):
    """Show the IN1 DC level live while the user adjusts the attenuation.
    `pd` is a Photodiode, or any function returning a level in V.
    Windows: updates until any key is pressed. Elsewhere: Enter re-reads,
    'a' accepts. Returns the last DC level."""
    read = getattr(pd, "dc", pd)
    try:
        import msvcrt
    except ImportError:
        msvcrt = None

    def line(v):
        s = f"  DC = {v * 1e3:9.2f} mV"
        if target_v:
            dev = (v - target_v) / target_v
            ok = tol_frac is not None and abs(dev) <= tol_frac
            s += f"   target {target_v * 1e3:.0f} mV  ({100 * dev:+6.1f} %) " \
                 + ("OK  " if ok else "    ")
        return s

    if msvcrt is not None:
        print("  Adjust the attenuation; press any key when done.")
        while True:
            v = read()
            print("\r" + line(v), end="", flush=True)
            if msvcrt.kbhit():
                while msvcrt.kbhit():
                    msvcrt.getwch()
                print()
                return v
    while True:
        v = read()
        print(line(v))
        if input("  Enter = read again, a = accept: ").strip().lower() == "a":
            return v


# ---------------------------------------------------------------------------
# CSV convention: '# key=value' metadata lines, then a header row
# ---------------------------------------------------------------------------
def _fmt(v):
    if isinstance(v, (float, np.floating)):
        return f"{v:.8g}"
    return str(v)


class TableWriter:
    """Write rows incrementally (flushed), so a Ctrl-C keeps what was done."""

    def __init__(self, path, columns, meta=None):
        self.path = path
        self.f = open(path, "w")
        meta = dict(meta or {})
        meta.setdefault("created", datetime.now().isoformat(timespec="seconds"))
        for k, v in meta.items():
            self.f.write(f"# {k}={_fmt(v)}\n")
        self.f.write(",".join(columns) + "\n")
        self.f.flush()

    def row(self, *values):
        self.f.write(",".join(_fmt(v) for v in values) + "\n")
        self.f.flush()

    def close(self):
        self.f.close()


def read_table(path):
    """Returns (meta, cols): meta = {key: str}, cols = {name: np.array}.
    Numeric columns become float arrays, others string arrays."""
    meta, rows, header = {}, [], None
    with open(path) as f:
        for raw in f:
            s = raw.strip()
            if not s:
                continue
            if s.startswith("#"):
                if "=" in s:
                    k, v = s[1:].split("=", 1)
                    meta[k.strip()] = v.strip()
                continue
            if header is None:
                header = s.split(",")
            else:
                rows.append(s.split(","))
    cols = {}
    for j, name in enumerate(header or []):
        vals = [r[j] if j < len(r) else "" for r in rows]
        try:
            cols[name] = np.array([float(v) if v != "" else np.nan for v in vals])
        except ValueError:
            cols[name] = np.array(vals)
    return meta, cols


def meta_float(meta, key, default=float("nan")):
    try:
        return float(meta[key])
    except (KeyError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Step 1 output: current -> power at the sample
# ---------------------------------------------------------------------------
def load_power_table(path=None, required=True):
    """Returns (P_of_I, meta). P_of_I(current_mA) -> mW at the sample (NaN
    outside the calibrated range). None if the table is missing and not required."""
    path = path or POWER_TABLE
    if not os.path.exists(path):
        if required:
            raise SystemExit(f"No power calibration at {path}: run step 1 "
                             "(cal1_power_vs_current.py, then plot_cal1_power.py).")
        return None, {}
    meta, c = read_table(path)
    order = np.argsort(c["current_mA"])
    cur, pw = c["current_mA"][order], c["P_sample_mW"][order]

    def p_of_i(i_ma):
        return np.interp(i_ma, cur, pw, left=np.nan, right=np.nan)
    return p_of_i, meta


# ---------------------------------------------------------------------------
# ODMR: Lorentzian dips on a sloping baseline
# ---------------------------------------------------------------------------
def _dips(f, f_mid, *p):
    """p = [baseline, slope, (amp, f0, hwhm) * n]."""
    f = np.asarray(f, float)
    y = p[0] + p[1] * (f - f_mid)
    for k in range((len(p) - 2) // 3):
        amp, f0, hw = p[2 + 3 * k: 5 + 3 * k]
        y = y - amp / (1.0 + ((f - f0) / hw) ** 2)
    return y


def fit_odmr(freqs, sig, n_lines=2, min_sep_mhz=MIN_SEP_MHZ):
    """Fit n Lorentzian dips. Returns a list of dicts (sorted by frequency)
    with f0, fwhm, contrast (dip depth / baseline) and their 1-sigma errors,
    or None if the fit fails. Single Lorentzians per resonance: at the powers
    used here the 14N hyperfine triplet is normally unresolved, and the
    envelope width is what sets the sensitivity."""
    from scipy.optimize import curve_fit
    f, y = np.asarray(freqs, float), np.asarray(sig, float)
    ok = np.isfinite(y)
    f, y = f[ok], y[ok]
    if len(f) < 3 * n_lines + 4:
        return None
    k = max(1, len(y) // 60)
    ys = np.convolve(np.pad(y, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1),
                     mode="valid")
    base = float(np.median(np.r_[y[: len(y) // 10 + 1], y[-(len(y) // 10 + 1):]]))
    picks = []
    for i in np.argsort(ys):
        if all(abs(f[i] - f[j]) >= min_sep_mhz for j in picks):
            picks.append(i)
        if len(picks) == n_lines:
            break
    f_mid = float(f.mean())
    p0, lo, hi = [base, 0.0], [-np.inf, -np.inf], [np.inf, np.inf]
    for i in sorted(picks):
        depth = max(base - ys[i], 1e-6 * abs(base))
        p0 += [depth, float(f[i]), 1.5]
        lo += [0.0, f.min(), 0.05]
        hi += [np.inf, f.max(), 0.5 * (f.max() - f.min())]
    try:
        p, cov = curve_fit(lambda x, *q: _dips(x, f_mid, *q), f, y, p0=p0,
                           bounds=(lo, hi), maxfev=20000)
        err = np.sqrt(np.clip(np.diag(cov), 0, None))
    except Exception as e:
        print(f"    (ODMR fit failed: {e})")
        return None
    out = []
    for j in range(n_lines):
        amp, f0, hw = p[2 + 3 * j: 5 + 3 * j]
        e_amp, e_f0, e_hw = err[2 + 3 * j: 5 + 3 * j]
        b0 = p[0] + p[1] * (f0 - f_mid)
        out.append(dict(f0=float(f0), f0_err=float(e_f0), fwhm=float(2 * hw),
                        fwhm_err=float(2 * e_hw), contrast=float(amp / b0),
                        contrast_err=float(e_amp / abs(b0))))
    out.sort(key=lambda d: d["f0"])
    return dict(lines=out, model=lambda x: _dips(x, f_mid, *p))


def fit_odmr_fixed(freqs, sig, centres, hw_grid=None):
    """Lorentzian dips at KNOWN centres (from a strong reference spectrum),
    one shared half-width scanned over hw_grid; baseline, slope and the
    amplitudes are linear, so this never wanders onto noise and still returns
    an honest contrast +/- error for a weak or absent dip. Returns a dict with
    contrast (mean over the lines), contrast_err, fwhm, fwhm_err (Delta chi^2
    = 1 on the grid), per-line contrasts and the model; None if too few points."""
    f, y = np.asarray(freqs, float), np.asarray(sig, float)
    ok = np.isfinite(y)
    f, y = f[ok], y[ok]
    n_l = len(centres)
    if len(f) < n_l + 4:
        return None
    if hw_grid is None:
        # a FWHM below two frequency steps is not resolved by the sweep
        hw_min = max(0.25, float(np.median(np.diff(np.sort(f)))))
        hw_grid = np.linspace(hw_min, 6.0, 70)
    f_mid = float(f.mean())
    best, chis = None, []
    for hw in hw_grid:
        X = np.column_stack([np.ones_like(f), f - f_mid] +
                            [-1.0 / (1.0 + ((f - c) / hw) ** 2) for c in centres])
        p, *_ = np.linalg.lstsq(X, y, rcond=None)
        chi = float(np.sum((y - X @ p) ** 2))
        chis.append(chi)
        if best is None or chi < best[0]:
            best = (chi, hw, p, X)
    chi, hw, p, X = best
    dof = max(1, len(f) - X.shape[1])
    s2 = chi / dof
    cov = s2 * np.linalg.pinv(X.T @ X)
    base = p[0]
    amps, a_cov = p[2:], cov[2:, 2:]
    c_lines = amps / base
    c_mean = float(np.mean(c_lines))
    c_err = float(np.sqrt(np.sum(a_cov)) / n_l / abs(base))
    inside = np.array(hw_grid)[np.array(chis) / s2 <= chi / s2 + 1.0]
    fwhm_err = float(inside.max() - inside.min()) if inside.size > 1 else float("nan")

    def model(x):
        x = np.asarray(x, float)
        out = p[0] + p[1] * (x - f_mid)
        for a, c in zip(amps, centres):
            out = out - a / (1.0 + ((x - c) / hw) ** 2)
        return out
    return dict(contrast=c_mean, contrast_err=c_err, fwhm=float(2 * hw),
                fwhm_err=fwhm_err, contrasts=[float(v) for v in c_lines],
                base=float(base), model=model, noise=float(np.sqrt(s2)))
