"""
Step 3f: RABI FREQUENCY from TRANSIENT NUTATION (CW laser, gated MW).

The DPSS laser stays ON (it cannot be pulsed fast; true pulsed Rabi needs an
AOM). Instead the MICROWAVE is switched on and off with a square gate, and the
photodiode is recorded at 8 ns resolution around every gate edge:

  MW switched ON (rising edge):  the spins start to rotate at the Rabi
      frequency, so the PL oscillates at f_R = Omega/2pi (generalised:
      sqrt(f_R^2 + detuning^2)) while it decays to the CW-ODMR level. The
      oscillation is damped by the ensemble's inhomogeneous width (T2*) and by
      optical pumping, so it is visible only when f_R is a few MHz or more.
  MW switched OFF (falling edge): the PL recovers exponentially as the laser
      re-polarises the spins into m_s = 0; the time constant is the OPTICAL
      PUMPING time at this laser power.

Repeating at several MW powers gives f_R vs MW power (f_R ~ sqrt(P)), which
calibrates the MW axis of the map (cal3_mw_laser_map.py) in MHz of Rabi
frequency. Repeating at several laser currents gives the pumping rate vs laser
power: the two rates whose ratio sets the ODMR contrast.

Each setting is measured ON resonance and OFF resonance (OFF_RES_MHZ); the
plotter subtracts the off-resonance trace, which removes electrical pickup of
the gate edge and amplifier switching transients (they do not depend on the
spin resonance).

HARDWARE / WIRING:
  * MW gate: the SMCV100B PULSE MODULATION (internal pulse generator, option
    K22/K23; check Modulation menu -> Pulse). Its pulse SYNC / signal-valid
    marker on a User connector -> Red Pitaya IN2 (HV jumper, TTL levels).
    Any other gate works if a copy of the TTL gate goes to IN2 (e.g. the
    ZASWA-2-50DRA+ switch driven by a pulse generator).
  * Detector -> IN1 (config.json redpitaya.input_gain). The detector must be
    FAST: bandwidth well above the Rabi frequency (the PDA10A2, 150 MHz, is
    fine; many APD modules are not).
  * MW chain as usual: SMCV -> isolator -> amplifier -> antenna; every level goes
    through SMCV100B.set_power_dbm() (config.json mw_chain limit).

Set the pulse generator BY HAND (this SMCV's modulation SCPI is unreliable):
PULSE_PERIOD_US and PULSE_WIDTH_US below are what you set (they are recorded,
and checked against the IN2 gate the script sees).

Output: <data_dir>/calibration/rabi_<stamp>/
          index.csv                 one row per setting
          L<step>_mw<dBm>.npz       t_us, rise_on, rise_off, fall_on, fall_off
                                    (mean IN1 volts around the edges), n_rise_*,
                                    n_fall_*, period/width seen on IN2
Next:   plot_cal3_rabi.py  (-> rabi_calibration.csv, used by the map plotter)

Run on the PC:  python cal3_rabi_transient.py
"""

import os
import sys
import time

import numpy as np

from calib_common import (Stop, ask_current, ask_tec, cal_path, pause, read_table,
                          stamp, wait_stable)

_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from lockin_common import teardown_smcv_modulation
from odmr_smcv100b_pc import (AMP_IN_CHAIN, RP_INPUT_GAIN, RP_IP, RP_PORT, SMCV_IP,
                              SMCV_PORT, SMCV100B)
from redpitaya_scope import RedPitayaScope

# --- settings ---------------------------------------------------------------
CURRENTS_MA = [250.0]               # laser levels (repeat for the pumping rate vs power)
I_MAX_MA = 400.0
RABI_MW_DBM = [-28.0, -25.0, -22.0, -19.0, -16.5]   # f_R ~ sqrt(P): 3 dB = x1.41
F_RES_MHZ = 2867.7                  # one line centre (from the map / a CW sweep)
OFF_RES_MHZ = 2820.0                # far from any line: pickup reference

PULSE_PERIOD_US = 50.0              # what you set on the SMCV pulse generator
PULSE_WIDTH_US = 10.0               # MW ON time (OFF time = period - width)
DECIMATION = 1                      # 8 ns per sample, 131 us per record
PRE_US = 1.0                        # kept before each edge (baseline)
RISE_POST_US = 8.0                  # kept after the MW turns ON (nutation)
FALL_POST_US = 30.0                 # kept after the MW turns OFF (re-polarisation)
N_RECORDS = 400                     # records ON resonance per setting
N_RECORDS_OFF = 200                 # records OFF resonance per setting
GATE_GAIN = "HV"                    # IN2 jumper (TTL gate)
SETTLE_MIN_S, SETTLE_MAX_S, SETTLE_TOL = 20.0, 240.0, 0.005
RUN_DIR = None                      # None -> new folder; existing folder -> append

COLUMNS = ["laser_step", "current_mA", "tec_C", "mw_dBm", "f_res_MHz", "PL_V",
           "n_rise_on", "n_rise_off", "n_fall_on", "n_fall_off", "period_us",
           "width_us", "t_s", "file"]


def beep():
    try:
        import winsound
        for f, d in [(784, 150), (1047, 150), (1319, 300)]:
            winsound.Beep(f, d)
    except Exception:
        print("\a", end="", flush=True)


def record(scope):
    """One record: (IN1 detector, IN2 gate), both 16384 samples, same clock."""
    return scope.acquire((1, 2), DECIMATION, {1: RP_INPUT_GAIN, 2: GATE_GAIN})


def edges(gate):
    """Rising and falling sample indices of the TTL gate on IN2."""
    lo, hi = np.percentile(gate, [5, 95])
    if hi - lo < 0.2:                     # no gate: < 0.2 V swing
        return np.array([], int), np.array([], int)
    g = gate > 0.5 * (lo + hi)
    d = np.diff(g.astype(np.int8))
    return np.flatnonzero(d == 1) + 1, np.flatnonzero(d == -1) + 1


class Accumulator:
    """Sums the detector trace around every edge of one kind."""

    def __init__(self, pre, post):
        self.pre, self.post = pre, post
        self.sum = np.zeros(pre + post)
        self.n = 0

    def add(self, sig, idx):
        for i in idx:
            if i - self.pre >= 0 and i + self.post <= len(sig):
                self.sum += sig[i - self.pre: i + self.post]
                self.n += 1

    def mean(self):
        return self.sum / self.n if self.n else np.full_like(self.sum, np.nan)


def gate_timing(scope, fs):
    sig, gate = record(scope)
    r, f = edges(gate)
    if len(r) < 2 or len(f) < 1:
        return np.nan, np.nan
    period = np.median(np.diff(r)) / fs * 1e6
    width = np.median([(f[f > i][0] - i) for i in r if (f > i).any()]) / fs * 1e6
    return float(period), float(width)


def measure(scope, src, freq_mhz, n_rec, fs, label):
    """Accumulate rising- and falling-edge averages at one MW frequency."""
    pre = int(PRE_US * 1e-6 * fs)
    rise = Accumulator(pre, int(RISE_POST_US * 1e-6 * fs))
    fall = Accumulator(pre, int(FALL_POST_US * 1e-6 * fs))
    src.set_freq_mhz(freq_mhz)
    time.sleep(0.05)
    t0 = time.time()
    for k in range(n_rec):
        sig, gate = record(scope)
        r, f = edges(gate)
        rise.add(sig, r)
        fall.add(sig, f)
        if (k + 1) % 20 == 0 or k + 1 == n_rec:
            dt = (time.time() - t0) / (k + 1)
            print(f"\r  {label}: {k + 1}/{n_rec} records, {rise.n} rising / "
                  f"{fall.n} falling edges ({dt:.2f} s per record, "
                  f"{dt * (n_rec - k - 1) / 60:.1f} min left)   ", end="", flush=True)
    print()
    return rise, fall


def main():
    if max(CURRENTS_MA) > I_MAX_MA:
        raise SystemExit(f"CURRENTS_MA goes above I_MAX_MA = {I_MAX_MA} mA.")
    if FALL_POST_US > PULSE_PERIOD_US - PULSE_WIDTH_US or RISE_POST_US > PULSE_WIDTH_US:
        raise SystemExit("RISE_POST_US must fit in the MW-on time and FALL_POST_US in "
                         "the MW-off time (PULSE_PERIOD_US - PULSE_WIDTH_US).")
    fs = 125e6 / DECIMATION
    run_dir = RUN_DIR or cal_path(f"rabi_{stamp()}")
    os.makedirs(run_dir, exist_ok=True)
    idx_path = os.path.join(run_dir, "index.csv")
    new_index = not os.path.exists(idx_path)
    first_step = 0
    if not new_index:
        _, old = read_table(idx_path)
        if len(old.get("laser_step", [])):
            first_step = int(np.nanmax(old["laser_step"])) + 1

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    too_high = [p for p in RABI_MW_DBM if p > src.max_dbm + 1e-9]
    if too_high:
        src.close()
        raise SystemExit(f"RABI_MW_DBM {too_high} exceed the chain limit "
                         f"{src.max_dbm:+.2f} dBm (config.json mw_chain).")
    scope = RedPitayaScope(RP_IP, RP_PORT)
    index = open(idx_path, "a")
    if new_index:
        index.write(f"# experiment=rabi_transient\n# amp_in_chain={AMP_IN_CHAIN}\n"
                    f"# off_res_MHz={OFF_RES_MHZ}\n# decimation={DECIMATION}\n"
                    f"# pre_us={PRE_US}\n# pulse_period_us_set={PULSE_PERIOD_US}\n"
                    f"# pulse_width_us_set={PULSE_WIDTH_US}\n" + ",".join(COLUMNS) + "\n")
        index.flush()
    try:
        src.configure(min(RABI_MW_DBM))
        print("\nSMCV: set PULSE MODULATION by hand (Modulation menu -> Pulse):\n"
              f"  internal pulse generator, period {PULSE_PERIOD_US} us, width "
              f"{PULSE_WIDTH_US} us, pulse modulation ON;\n"
              "  route the pulse sync / marker to a User connector -> Red Pitaya IN2 "
              f"({GATE_GAIN} jumper).")
        pause("Done")
        try:
            src.s.write(":SOURce:MODulation:ALL:STATe ON")
            src.s.query("*OPC?")
        except Exception as e:
            print(f"  (could not enable modulation over SCPI: {e}; enable it by hand)")
        src.set_freq_mhz(F_RES_MHZ)
        src.output(True)
        period, width = gate_timing(scope, fs)
        print(f"  gate seen on IN2: period {period:.2f} us, width {width:.2f} us")
        if not np.isfinite(period):
            raise SystemExit("No gate edges on IN2: check the pulse sync wiring, the "
                             "IN2 jumper and that pulse modulation is ON.")
        if abs(period - PULSE_PERIOD_US) > 0.05 * PULSE_PERIOD_US or \
                abs(width - PULSE_WIDTH_US) > 0.1 * PULSE_WIDTH_US + 0.05:
            print("  WARNING: the gate on IN2 does not match PULSE_PERIOD_US / "
                  "PULSE_WIDTH_US; the measured values are recorded.")

        for k, planned in enumerate(CURRENTS_MA):
            step = first_step + k
            print("=" * 72 + f"\nLASER LEVEL {k + 1}/{len(CURRENTS_MA)}")
            cur = ask_current(planned, I_MAX_MA)
            if cur is None:
                continue
            wait_stable(lambda: float(np.mean(scope.acquire((1,), 1024, RP_INPUT_GAIN))),
                        0.0, 10.0, SETTLE_TOL, SETTLE_MIN_S, SETTLE_MAX_S,
                        unit="mV", scale=1e3)
            tec = ask_tec()
            for dbm in RABI_MW_DBM:
                t1 = time.time()
                src.set_power_dbm(dbm)
                ron, fon = measure(scope, src, F_RES_MHZ, N_RECORDS, fs,
                                   f"{dbm:+.1f} dBm ON resonance")
                roff, foff = measure(scope, src, OFF_RES_MHZ, N_RECORDS_OFF, fs,
                                     f"{dbm:+.1f} dBm OFF resonance")
                pre = ron.pre
                pl = float(np.nanmean(ron.mean()[:pre]))
                fname = f"L{step:02d}_mw{dbm:+06.1f}.npz"
                np.savez(os.path.join(run_dir, fname), fs=fs, pre=pre,
                         t_rise_us=(np.arange(len(ron.sum)) - pre) / fs * 1e6,
                         t_fall_us=(np.arange(len(fon.sum)) - pre) / fs * 1e6,
                         rise_on=ron.mean(), rise_off=roff.mean(),
                         fall_on=fon.mean(), fall_off=foff.mean(),
                         n_rise_on=ron.n, n_rise_off=roff.n, n_fall_on=fon.n,
                         n_fall_off=foff.n, current_mA=cur, mw_dBm=dbm,
                         f_res_MHz=F_RES_MHZ, off_res_MHz=OFF_RES_MHZ,
                         period_us=period, width_us=width)
                index.write(",".join(str(v) for v in (
                    step, cur, tec, dbm, F_RES_MHZ, f"{pl:.6g}", ron.n, roff.n, fon.n,
                    foff.n, f"{period:.4g}", f"{width:.4g}", f"{time.time() - t1:.1f}",
                    fname)) + "\n")
                index.flush()
                print(f"  -> {fname}  (PL {pl * 1e3:.2f} mV)")
            src.set_freq_mhz(F_RES_MHZ)
            beep()
        print(f"\nDone -> {run_dir}\nNext: python plot_cal3_rabi.py")
    except (Stop, KeyboardInterrupt):
        print(f"\nStopped. Settings so far are in {run_dir} (set RUN_DIR to resume).")
    finally:
        index.close()
        teardown_smcv_modulation(src, "pulse")
        src.close()
        scope.close()


if __name__ == "__main__":
    main()
