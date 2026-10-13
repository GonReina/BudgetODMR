"""
Shared helpers for the laser / detector calibration protocol in this folder.
CALIBRATION_PROTOCOL.md gives the run order:

  cal0_*  check that the PM101A answers over USB (optional)
  cal1_*  power after the objective vs laser current   (PM101A + S120C)
  cal2_*  laser noise vs current and vs photocurrent    (PDA10A2 on Red Pitaya IN1)
  cal3_*  PL vs power at the sample, with CW ODMR       (APD on IN1, SMCV100B)

What lives here:
  * PowerMeter      -- Thorlabs PM101A over USB/VISA, with a type-it-in fallback
  * Photodiode      -- raw Red Pitaya IN1 records (RedPitayaScope)
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
F_MOD = _cfg["lockin"]["f_mod_hz"]
D_CENTER_MHZ = _cfg["analysis"]["d_center_mhz"]
MIN_SEP_MHZ = _cfg["analysis"]["min_sep_mhz"]

CAL_DIR = os.path.join(_cfg["paths"]["data_dir"], "calibration")
POWER_TABLE = os.path.join(CAL_DIR, "power_calibration.csv")

DZFS_MHZ_PER_K = -0.074      # zero-field splitting temperature coefficient
N_BUF = 16384                # Red Pitaya fast-ADC buffer (samples per record)


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
                max_s=180.0, unit="", scale=1.0):
    """Read `read()` repeatedly until the drift over the last `window_s` seconds
    (linear fit) is below tol_frac of the mean, after at least min_s. Gives up
    with a warning after max_s. Ctrl-C stops waiting early. Returns the elapsed
    time. Used to let the TEC and the DPSS output settle after a current step."""
    t0 = time.time()
    ts, vs = [], []
    try:
        while True:
            v = read()
            t = time.time() - t0
            ts.append(t)
            vs.append(v)
            keep = [i for i, ti in enumerate(ts) if ti >= t - window_s]
            drift = float("nan")
            tt, vv = np.array(ts)[keep], np.array(vs)[keep]
            if len(keep) >= 4 and np.ptp(tt) > 0.5 and np.all(np.isfinite(vv)):
                slope = np.polyfit(tt - tt.mean(), vv, 1)[0]
                mean = abs(vv.mean())
                drift = abs(slope) * window_s / mean if mean > 0 else float("inf")
            print(f"\r  settling {t:5.0f} s: {v * scale:10.4g} {unit}   drift over "
                  f"{window_s:.0f} s = {100 * drift:6.2f} % (target "
                  f"{100 * tol_frac:.2f} %)   ", end="", flush=True)
            if t >= min_s and drift <= tol_frac:
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
# Thorlabs PM101A power meter
# ---------------------------------------------------------------------------
class PowerMeter:
    """Thorlabs PM101A (+ S120C) over USB, or typed in by hand.

    The PM101 series speaks SCPI over USB-TMC. To use it from Python:
      1. pip install pyvisa
      2. a VISA library: NI-VISA (install it before Thorlabs' Optical Power
         Monitor software), or pyvisa-py + pyusb + libusb.
      3. If the meter does not appear in pyvisa's list_resources(), run the
         Thorlabs "Power Meter Driver Switcher" and select the NI-VISA driver
         for the PM101 (the default TLPM driver hides it from other VISA
         software). Switch back to use Optical Power Monitor again.
    Check it with cal0_check_power_meter.py.

    If no meter is found, or manual=True, every reading is TYPED IN instead:
    the scripts tell you what to read and for how long.
    """

    def __init__(self, wavelength_nm=532.0, resource=None, manual=False,
                 avg_count=10):
        self.wavelength_nm = wavelength_nm
        self.inst = None
        self.idn = "manual entry"
        if manual:
            print("Power meter: MANUAL entry (manual=True).")
            return
        try:
            import pyvisa
        except ImportError:
            print("Power meter: pyvisa not installed -> MANUAL entry. "
                  "(pip install pyvisa; see the PowerMeter docstring.)")
            return
        try:
            rm = pyvisa.ResourceManager()
            if resource is None:
                found = [r for r in rm.list_resources() if "0x1313" in r.lower()]
                if not found:
                    print("Power meter: no Thorlabs USB instrument in "
                          f"{rm.list_resources()} -> MANUAL entry. "
                          "(Driver Switcher -> NI-VISA? See cal0_check_power_meter.py.)")
                    return
                resource = found[0]
            self.inst = rm.open_resource(resource)
            self.inst.timeout = 5000
            self.idn = self.inst.query("*IDN?").strip()
        except Exception as e:
            print(f"Power meter: could not open it ({e}) -> MANUAL entry.")
            self.inst = None
            return
        print(f"Power meter: {self.idn}  ({resource})")
        for cmd in ("SENS:POW:UNIT W", "SENS:POW:RANG:AUTO ON",
                    f"SENS:AVER:COUN {int(avg_count)}", "CONF:POW"):
            self._try_write(cmd)
        self.set_wavelength(wavelength_nm)
        try:
            print(f"  sensor: {self.inst.query('SYST:SENS:IDN?').strip()}")
        except Exception:
            pass

    @property
    def manual(self):
        return self.inst is None

    def _try_write(self, cmd):
        try:
            self.inst.write(cmd)
        except Exception as e:
            print(f"  WARNING: '{cmd}' failed ({e})")

    def set_wavelength(self, nm):
        self.wavelength_nm = nm
        if self.manual:
            print(f"  >> Set the PM101A correction wavelength to {nm:.0f} nm.")
            return
        self._try_write(f"SENS:CORR:WAV {nm:.1f}")
        try:
            got = float(self.inst.query("SENS:CORR:WAV?"))
            print(f"  wavelength correction = {got:.1f} nm")
            if abs(got - nm) > 0.5:
                print(f"  WARNING: asked for {nm:.1f} nm -- set it on the meter.")
        except Exception:
            print(f"  (could not read back the wavelength; check it is {nm:.0f} nm)")

    def zero(self):
        """Dark zero with the beam blocked."""
        pause("  ZERO: block the beam completely (sensor in place)")
        if self.manual:
            pause("  Press the PM101A's Zero function and wait for it to finish")
            pause("  Unblock the beam")
            return
        try:
            self.inst.write("SENS:CORR:COLL:ZERO:INIT")
            deadline = time.time() + 30
            while time.time() < deadline:
                time.sleep(0.5)
                if self.inst.query("SENS:CORR:COLL:ZERO:STAT?").strip() in ("0", "OFF"):
                    break
            mag = float(self.inst.query("SENS:CORR:COLL:ZERO:MAGN?"))
            print(f"  zeroed (offset {mag * 1e9:.2f} nW).")
        except Exception as e:
            print(f"  WARNING: zeroing over USB failed ({e}); zero it on the meter.")
            pause("  Zero done on the front panel?")
        pause("  Unblock the beam")

    def read_mw(self):
        """One reading in mW (USB mode only)."""
        return float(self.inst.query("MEAS:POW?")) * 1e3

    def settle(self, min_s=20.0, max_s=180.0, tol_frac=0.005, window_s=10.0):
        if self.manual:
            countdown(min_s, "wait for the TEC / laser to settle")
            pause("  Reading steady on the PM101A?")
            return min_s
        return wait_stable(self.read_mw, 0.5, window_s, tol_frac, min_s, max_s,
                           unit="mW")

    def log(self, seconds, period_s=0.2):
        """Log for `seconds`. Returns dict(mean, std, slope [mW/s], n, t, p)."""
        if self.manual:
            print(f"  Watch the PM101A for {seconds:.0f} s.")
            mean = ask_float("  mean power over that time (mW)")
            pk = ask_float("  peak-to-peak fluctuation (mW, blank = skip)",
                           blank_ok=True)
            std = pk / 6.0 if pk is not None else float("nan")
            return dict(mean=mean, std=std, slope=float("nan"), n=1,
                        t=np.array([0.0]), p=np.array([mean]))
        t0 = time.time()
        ts, ps = [], []
        while time.time() - t0 < seconds:
            ps.append(self.read_mw())
            ts.append(time.time() - t0)
            print(f"\r  logging {ts[-1]:5.1f}/{seconds:.0f} s: {ps[-1]:10.5f} mW ",
                  end="", flush=True)
            time.sleep(period_s)
        print()
        t, p = np.array(ts), np.array(ps)
        slope = float(np.polyfit(t, p, 1)[0]) if len(t) > 2 else float("nan")
        return dict(mean=float(p.mean()), std=float(p.std(ddof=1)) if len(p) > 1
                    else float("nan"), slope=slope, n=len(p), t=t, p=p)

    def close(self):
        if self.inst is not None:
            try:
                self.inst.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Red Pitaya IN1 (PDA10A2 for noise, APD for PL)
# ---------------------------------------------------------------------------
class Photodiode:
    """Raw fast-ADC records from Red Pitaya IN1 via the SCPI server."""

    def __init__(self, decimation=1024, gain=None, channel=1):
        from redpitaya_scope import RedPitayaScope
        self.scope = RedPitayaScope(RP_IP, RP_PORT)
        self.decimation = decimation
        self.gain = gain or RP_GAIN
        self.channel = channel
        self.fs = 125e6 / decimation
        self.clip_v = 0.95 if self.gain == "LV" else 19.0
        print(f"Red Pitaya IN{channel} at {RP_IP}:{RP_PORT}: decimation "
              f"{decimation} (fs = {self.fs:.0f} Hz), gain {self.gain}")

    def record(self):
        return self.scope.acquire((self.channel,), self.decimation, self.gain,
                                  fill_timeout_s=5.0)

    def records(self, n):
        recs = np.array([self.record() for _ in range(n)])
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
    Windows: updates until any key is pressed. Elsewhere: Enter re-reads,
    'a' accepts. Returns the last DC level."""
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
            v = pd.dc()
            print("\r" + line(v), end="", flush=True)
            if msvcrt.kbhit():
                while msvcrt.kbhit():
                    msvcrt.getwch()
                print()
                return v
    while True:
        v = pd.dc()
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
