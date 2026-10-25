"""
Step 3e: ODMR CONTRAST MAP vs LASER POWER and MICROWAVE POWER.

For each laser current (set by hand on the LDC200C) the script sweeps the
MW power through MW_DBM and records a CW ODMR spectrum (MW on/off ratio) at
each one, then BEEPS and waits for the next current. plot_cal3_mw_laser_map.py
turns the result into a heatmap of the dip 1 - PL_on/PL_off (%) with laser
power on the y axis and MW power on the x axis, plus the linewidth, the
sensitivity and the saturation cuts.

Per laser level:
  1. set the current, wait for the PL to settle (optionally type a pick-off
     power meter reading; the TEC is not asked, tec_C stays empty);
  2. PL with the MW off (the in-situ laser power proxy);
  3. REFERENCE spectrum at the highest MW power: fits the two line centres,
     used for every other spectrum at this laser level (fit_odmr_fixed), so a
     weak dip at low MW power is still measured without bias;
  4. the other MW powers in SHUFFLED order (so heating / laser drift does not
     masquerade as a MW-power trend), each with ADAPTIVE averaging: sweeps are
     added until the contrast is known to TARGET_REL_ERR, up to MAX_SWEEPS,
     stopping early when a dip is clearly below what MAX_SWEEPS could resolve;
  5. at laser levels <= FINE_MAX_CURRENT_MA: FINE spectra (0.1 MHz steps,
     FINE_SWEEPS sweeps) at the low MW powers FINE_MW_DBM, where the lines are
     narrowest (intrinsic width, 14N hyperfine triplet);
  6. the reference again (drift check: contrast and line centre at the start
     and end of the level), then a beep.

LASER POWER AXIS: only the current is recorded here (plus the PL and the
optional typed-in power meter reading). plot_cal3_mw_laser_map.py converts the
current to power at the sample with <data_dir>/calibration/power_calibration.csv
WHEN IT PLOTS, so redoing the loss budget + plot_cal1_power.py later updates the
axis without re-measuring the map. Keep the alignment and the laser TEC
setpoint unchanged between the power calibration and this run.

The run is resumable: set RUN_DIR to an existing map folder to add laser
levels to it (e.g. after a stop, or a second day with the same alignment).

Signal path as cal3_pl_vs_power.py: detector -> Red Pitaya IN1, SMCV100B ->
amplifier -> antenna. Every MW level goes through SMCV100B.set_power_dbm(),
which enforces the config.json mw_chain limit (checked for the whole grid
before anything starts).

Output: <data_dir>/calibration/mw_laser_map_<stamp>/
          index.csv     one row per spectrum: laser_step,current_mA,tec_C,
                        P_mon_mW,PL_V,dark_V,mw_dBm,role,order,n_sweeps,
                        contrast,contrast_err,fwhm_MHz,fwhm_err_MHz,c1,c2,
                        f1_MHz,f2_MHz,PL_off_V,t_s,file
          L<step>_mw<dBm>_<role>.csv   freq_MHz,signal,std,sweep_01,...
Next:   plot_cal3_mw_laser_map.py

Run on the PC:  python cal3_mw_laser_map.py
"""

import os
import sys
import time

import numpy as np

from calib_common import (Stop, ask_current, ask_float, cal_path, fit_odmr,
                          fit_odmr_fixed, pause, read_table, stamp, wait_stable)

_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from odmr_smcv100b_pc import (AMP_IN_CHAIN, RP_IP, RP_PORT, SMCV_IP, SMCV_PORT,
                              RedPitayaADC, SMCV100B, frange, integrate)

# --- settings ---------------------------------------------------------------
CURRENTS_MA = np.arange(160.0, 380.0, 20.0)   # laser levels to measure (mA)
I_MAX_MA = 380.0
# SMCV levels (dBm). With the amplifier the limit is -16.4 dBm; about +44 dB
# reaches the antenna. 3 dB steps = factor 2 in MW power.
MW_DBM = [-40.0, -37.0, -34.0, -31.0, -28.0, -25.0, -22.0, -19.0, -16.5]
MW_REF_DBM = max(MW_DBM)      # reference spectrum, first and last at each level

F_START_MHZ, F_STOP_MHZ = 2850.0, 2890.0   # both lines (~2867.7, 2873.1) + baseline
F_STEP_MHZ = 0.2
N_LINES = 2

MIN_SWEEPS = 3
REF_MIN_SWEEPS = 6            # references carry the drift / heating check
MAX_SWEEPS = 12
TARGET_REL_ERR = 0.06         # stop when contrast_err / contrast < 6 %

# FINE spectra (0.1 MHz steps) at LOW laser and LOW MW power, where the lines are
# narrowest: shows the intrinsic width and, if it is below ~1 MHz, the 14N
# hyperfine triplet (2.16 MHz spacing). Fixed number of sweeps (no early stop).
FINE_MAX_CURRENT_MA = 220.0   # laser levels at or below this current get fine spectra
FINE_MW_DBM = [-37.0, -31.0]
FINE_F_START_MHZ, FINE_F_STOP_MHZ = 2862.0, 2879.0
FINE_STEP_MHZ = 0.1
FINE_SWEEPS = 12
SHUFFLE_MW = True
MW_SETTLE_S = 0.02
PL_READS = 10
SETTLE_MIN_S, SETTLE_MAX_S, SETTLE_TOL = 5.0, 240.0, 0.005
MONITOR_POWER = False         # type in a pick-off power meter reading (blank = skip)
RUN_DIR = r"C:\Users\qute\Downloads\rsattempt\16-10-2026\calibration\mw_laser_map_20261016_142528"
FORCE_STEP = None    # set to a laser_step integer to delete and re-run that level only;
                  # None = normal resume behaviour

COLUMNS = ["laser_step", "current_mA", "tec_C", "P_mon_mW", "PL_V", "dark_V",
           "mw_dBm", "role", "order", "n_sweeps", "contrast", "contrast_err",
           "fwhm_MHz", "fwhm_err_MHz", "c1", "c2", "f1_MHz", "f2_MHz", "PL_off_V",
           "t_s", "file"]


def beep():
    try:
        import winsound
        for f, d in [(784, 150), (1047, 150), (1319, 300)]:
            winsound.Beep(f, d)
    except Exception:
        print("\a", end="", flush=True)


def pl_reading(adc, n=PL_READS):
    v = np.array([integrate(adc) for _ in range(n)])
    return float(v.mean()), float(v.std(ddof=1))


def one_sweep(src, adc, freqs):
    ratio, off_sum = np.zeros(len(freqs)), 0.0
    for i, f in enumerate(freqs):
        src.set_freq_mhz(f)
        src.output(True)
        time.sleep(MW_SETTLE_S)
        on = integrate(adc)
        src.output(False)
        time.sleep(MW_SETTLE_S)
        off = integrate(adc)
        ratio[i] = on / off if off else np.nan
        off_sum += off
    return ratio, off_sum / len(freqs)


def spectrum(src, adc, freqs, dbm, centres, label, min_sweeps=MIN_SWEEPS,
             max_sweeps=MAX_SWEEPS):
    """Adaptive averaging. Returns (sweeps [n x len(freqs)], fit, mean PL_off)."""
    src.set_power_dbm(dbm)
    sweeps, offs, fit = [], [], None
    t0 = time.time()
    while len(sweeps) < max_sweeps:
        r, off = one_sweep(src, adc, freqs)
        sweeps.append(r)
        offs.append(off)
        n = len(sweeps)
        avg = np.nanmean(sweeps, axis=0)
        cen = centres
        if cen is None and n >= min_sweeps:          # reference: centres from a full fit
            full = fit_odmr(freqs, avg, N_LINES)
            cen = [ln["f0"] for ln in full["lines"]] if full else None
        fit = fit_odmr_fixed(freqs, avg, cen) if cen is not None else None
        rel = (fit["contrast_err"] / fit["contrast"]
               if fit and fit["contrast"] > 0 else np.inf)
        dt = (time.time() - t0) / n
        print(f"\r  {label}: sweep {n}/{max_sweeps} ({dt:.0f} s each)  "
              + (f"C = {100 * fit['contrast']:.3f} +/- {100 * fit['contrast_err']:.3f} %"
                 if fit else "") + "      ", end="", flush=True)
        if n < min_sweeps or fit is None:
            continue
        if rel < TARGET_REL_ERR:
            break
        # hopeless: even MAX_SWEEPS would not reach the target -> do not waste time
        n_needed = n * (rel / TARGET_REL_ERR) ** 2
        if n >= 4 and n_needed > 2 * max_sweeps:
            break
    print()
    return np.array(sweeps), fit, float(np.mean(offs))


def save_spectrum(path, freqs, sweeps, meta):
    with open(path, "w") as f:
        for k, v in meta.items():
            f.write(f"# {k}={v}\n")
        f.write("freq_MHz,signal,std," + ",".join(f"sweep_{k + 1:02d}"
                                                for k in range(len(sweeps))) + "\n")
        avg = np.nanmean(sweeps, axis=0)
        std = np.nanstd(sweeps, axis=0)
        for i, fr in enumerate(freqs):
            f.write(f"{fr:.4f},{avg[i]:.7f},{std[i]:.7f}," +
                    ",".join(f"{s[i]:.7f}" for s in sweeps) + "\n")


class Index:
    """index.csv, appended to (resumable)."""

    def __init__(self, path, meta):
        new = not os.path.exists(path)
        self.f = open(path, "a")
        if new:
            for k, v in meta.items():
                self.f.write(f"# {k}={v}\n")
            self.f.write(",".join(COLUMNS) + "\n")
            self.f.flush()

    def row(self, **kw):
        vals = [kw.get(c, np.nan) for c in COLUMNS]
        self.f.write(",".join(f"{v:.8g}" if isinstance(v, (float, np.floating))
                              else str(v) for v in vals) + "\n")
        self.f.flush()

    def close(self):
        self.f.close()


def main():
    if max(CURRENTS_MA) > I_MAX_MA:
        raise SystemExit(f"CURRENTS_MA goes above I_MAX_MA = {I_MAX_MA} mA.")
    freqs = np.array(list(frange(F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ)))
    fine_freqs = np.array(list(frange(FINE_F_START_MHZ, FINE_F_STOP_MHZ, FINE_STEP_MHZ)))
    run_dir = RUN_DIR or cal_path(f"mw_laser_map_{stamp()}")
    os.makedirs(run_dir, exist_ok=True)
    idx_path = os.path.join(run_dir, "index.csv")
    first_step = 0
    if FORCE_STEP is not None:
        step_to_redo = int(FORCE_STEP)
        first_step = step_to_redo
        if os.path.exists(idx_path):
            with open(idx_path) as _f:
                _raw = _f.readlines()
            _keep, _purge, _hdr, _sc, _fc = [], [], False, 0, -1
            for _line in _raw:
                _s = _line.strip()
                if _s.startswith("#"):
                    _keep.append(_line)
                elif not _hdr:
                    _keep.append(_line)
                    _cols = _s.split(",")
                    _sc = _cols.index("laser_step") if "laser_step" in _cols else 0
                    _fc = _cols.index("file") if "file" in _cols else -1
                    _hdr = True
                else:
                    _p = _s.split(",")
                    try:
                        if int(round(float(_p[_sc]))) == step_to_redo:
                            if _fc >= 0 and len(_p) > _fc:
                                _purge.append(_p[_fc].strip())
                            continue
                    except (ValueError, IndexError):
                        pass
                    _keep.append(_line)
            for _fn in _purge:
                _fp = os.path.join(run_dir, _fn)
                if os.path.exists(_fp):
                    os.remove(_fp)
            with open(idx_path, "w") as _f:
                _f.writelines(_keep)
            print(f"FORCE_STEP={step_to_redo}: purged {len(_purge)} file(s), "
                  f"re-running {CURRENTS_MA[step_to_redo]:.0f} mA only")
        currents_to_run = CURRENTS_MA[step_to_redo:step_to_redo + 1]
    else:
        if os.path.exists(idx_path):
            _, old = read_table(idx_path)
            if len(old.get("laser_step", [])):
                first_step = int(np.nanmax(old["laser_step"])) + 1
            print(f"Resuming {run_dir}: new laser levels start at step {first_step}")
        currents_to_run = CURRENTS_MA[first_step:]

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    too_high = [p for p in MW_DBM if p > src.max_dbm + 1e-9]
    if too_high:
        src.close()
        raise SystemExit(f"MW_DBM {too_high} exceed the chain limit "
                         f"{src.max_dbm:+.2f} dBm (config.json mw_chain).")
    adc = RedPitayaADC(RP_IP, RP_PORT)
    index = Index(idx_path, dict(experiment="mw_laser_map", amp_in_chain=AMP_IN_CHAIN,
                                 f_start_MHz=F_START_MHZ, f_stop_MHz=F_STOP_MHZ,
                                 f_step_MHz=F_STEP_MHZ, target_rel_err=TARGET_REL_ERR,
                                 max_sweeps=MAX_SWEEPS, n_lines=N_LINES))
    print(f"\nMW x LASER MAP -> {run_dir}\n  {len(CURRENTS_MA)} laser levels x "
          f"{len(MW_DBM)} MW powers ({min(MW_DBM)} .. {max(MW_DBM)} dBm) + 1 repeat; "
          f"{len(freqs)} points per sweep, {MIN_SWEEPS}-{MAX_SWEEPS} sweeps each")
    try:
        src.configure(MW_REF_DBM)
        src.output(False)
        pause("\nDARK: block the LASER (detector on, same gain)")
        dark, _ = pl_reading(adc)
        print(f"  dark = {dark * 1e3:.3f} mV")
        pause("Unblock the laser")
        rng = np.random.default_rng()
        for k, planned in enumerate(currents_to_run):
            step = first_step + k
            print("=" * 72 + f"\nLASER LEVEL {step + 1}/{len(CURRENTS_MA)}")
            cur = ask_current(planned, I_MAX_MA)
            if cur is None:
                continue
            wait_stable(lambda: integrate(adc), 0.0, 10.0, SETTLE_TOL, SETTLE_MIN_S,
                        SETTLE_MAX_S, unit="mV", scale=1e3)
            tec = np.nan                # TEC not asked; column kept for the format
            mon = np.nan
            if MONITOR_POWER:
                p = ask_float("  power meter reading (mW, blank = skip)", blank_ok=True)
                mon = np.nan if p is None else p
            pl, _ = pl_reading(adc)
            print(f"  PL (MW off) = {(pl - dark) * 1e3:.3f} mV above dark")
            t_level = time.time()
            common = dict(laser_step=step, current_mA=cur, tec_C=tec, P_mon_mW=mon,
                          PL_V=pl, dark_V=dark)

            # reference: strong dip -> line centres for this laser level
            sw, _, off = spectrum(src, adc, freqs, MW_REF_DBM, None, "reference",
                                  REF_MIN_SWEEPS)
            full = fit_odmr(freqs, np.nanmean(sw, axis=0), N_LINES)
            if full is None:
                print("  reference fit failed: centres from the config window middle")
                mid = 0.5 * (F_START_MHZ + F_STOP_MHZ)
                centres = [mid - 2.7, mid + 2.7][:N_LINES]
            else:
                centres = [ln["f0"] for ln in full["lines"]]
            print("  line centres: " + ", ".join(f"{c:.2f}" for c in centres) + " MHz")

            plan = [(MW_REF_DBM, "ref_start", sw, off)]
            others = [p for p in MW_DBM if p != MW_REF_DBM]
            if SHUFFLE_MW:
                others = list(rng.permutation(others))
            plan += [(float(p), "map", None, None) for p in others]
            if cur <= FINE_MAX_CURRENT_MA:
                plan += [(float(p), "fine", None, None) for p in FINE_MW_DBM]
            plan += [(MW_REF_DBM, "ref_end", None, None)]     # last: spans everything
            for order, (dbm, role, sw, off) in enumerate(plan):
                t1 = time.time()
                fr_ = fine_freqs if role == "fine" else freqs
                if sw is None:
                    label = f"[{order + 1}/{len(plan)}] {dbm:+.1f} dBm {role}"
                    if role == "fine":
                        sw, _, off = spectrum(src, adc, fr_, dbm, centres, label,
                                              FINE_SWEEPS, FINE_SWEEPS)
                    else:
                        sw, _, off = spectrum(
                            src, adc, fr_, dbm, centres, label,
                            REF_MIN_SWEEPS if role == "ref_end" else MIN_SWEEPS)
                fit = fit_odmr_fixed(fr_, np.nanmean(sw, axis=0), centres)
                fname = f"L{step:02d}_mw{dbm:+06.1f}_{role}.csv"
                save_spectrum(os.path.join(run_dir, fname), fr_, sw,
                              dict(experiment="mw_laser_map_spectrum", current_mA=cur,
                                   mw_dBm=dbm, role=role, n_sweeps=len(sw),
                                   centres_MHz=" ".join(f"{c:.4f}" for c in centres),
                                   signal="PL_on/PL_off"))
                f12 = (centres + [np.nan])[:2]
                index.row(**common, mw_dBm=dbm, role=role, order=order,
                          n_sweeps=len(sw),
                          contrast=fit["contrast"] if fit else np.nan,
                          contrast_err=fit["contrast_err"] if fit else np.nan,
                          fwhm_MHz=fit["fwhm"] if fit else np.nan,
                          fwhm_err_MHz=fit["fwhm_err"] if fit else np.nan,
                          c1=fit["contrasts"][0] if fit else np.nan,
                          c2=fit["contrasts"][-1] if fit else np.nan,
                          f1_MHz=f12[0], f2_MHz=f12[1], PL_off_V=off,
                          t_s=time.time() - t1, file=fname)
                if fit:
                    print(f"    {dbm:+6.1f} dBm: C = {100 * fit['contrast']:.3f} +/- "
                          f"{100 * fit['contrast_err']:.3f} %, FWHM {fit['fwhm']:.2f} MHz,"
                          f" {len(sw)} sweeps")
                done = time.time() - t_level
                print(f"    level time {done / 60:.1f} min, about "
                      f"{done / (order + 1) * (len(plan) - order - 1) / 60:.0f} min left")
            beep()                      # come back: this level is done
            if MONITOR_POWER:
                p = ask_float("  power meter reading at the END of this level "
                              "(mW, blank = skip)", blank_ok=True)
                if p is not None and np.isfinite(mon) and mon:
                    print(f"    laser drift over the level: {100 * (p / mon - 1):+.2f} %")
            print(f"  level done in {(time.time() - t_level) / 60:.1f} min")
        beep()
        print(f"\nAll levels done -> {run_dir}\nNext: python plot_cal3_mw_laser_map.py")
    except (Stop, KeyboardInterrupt):
        print(f"\nStopped. Everything so far is in {run_dir} (set RUN_DIR to resume).")
    finally:
        index.close()
        adc.close()
        src.close()


if __name__ == "__main__":
    main()
