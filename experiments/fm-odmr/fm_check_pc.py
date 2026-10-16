"""
FM CHECK: does frequency modulation help, and at which modulation frequency?

  1. DC ODMR: N_DC_SWEEPS sweeps (MW on/off ratio, no modulation) at
     MW_POWER_DBM; N_LINES Lorentzians are fitted and ONE line (LINE) gives the
     dip, its steepest OUTER flank and its FWHM. Then a DC
     BENCHMARK at the dip: N_DC_PAIRS repeated MW off/on readings, the SNR the
     plain on/off method gets in one second.
  2. Parks the MW at PARK ("slope" or "dip", see below), switches FM on and,
     for each f_mod in F_MODS_HZ, sets that LF frequency, then records N_REC raw photodiode records ON resonance and N_REC OFF
     resonance (OFF_RES_MHZ: any tone left there is electrical pickup, not ODMR).

WHERE TO PARK. A magnitude FM lock-in measures the SLOPE of the line: at the
dip centre the slope is zero, the f_mod tone vanishes and only a 2 f_mod
component is left. PARK = "slope" (default) parks on the steepest flank, where
the f_mod tone is largest; PARK = "dip" parks at the centre (to see the 2 f_mod
signal). PARK_MHZ forces a frequency.

REMOTE vs BY HAND. FM on/off, shape (sine), deviation and the modulation
frequency are set over SCPI with the SMCV's [:SOURce]:BB:GENeral:FM:...
commands (lockin_common.SmcvFm; each is checked against SYSTem:ERRor? and a
read-back; the analog FM<ch>/LFOutput tree of other R&S generators does not
exist on the SMCV100B). Anything
the instrument refuses falls back to a prompt to set it in the Modulation
menu. Startup prints which settings work remotely.

FM DEVIATION: FM_DEV_KHZ, or None -> half of ONE line's FWHM from step 1 (the
script asks, with that as the default): about the largest flank tone. Not the
FWHM of both lines together (2026-10-15: 5.1 MHz swept over both lines and the
tone dropped ~7x).

Settings: MW_POWER_DBM here (the SMCV100B class enforces the config.json
mw_chain limit, -16.4 dBm with the amplifier); everything else from config.json.

Output: <data_dir>/fm_check_<stamp>/
          dc_odmr.csv        freq_MHz,signal,std  (+ park / FWHM / DC benchmark meta)
          dc_pairs.csv       k,t_s,off_V,on_V     (the DC benchmark readings)
          fm_<f_mod>Hz.npz   fs, f_mod_nominal_hz, deviation_hz, park_mhz,
                             off_res_mhz, on [N_REC x n], off [N_REC x n],
                             t_rec_s (wall-clock time per record)
Next:   plot_fm_check.py

Run on the PC:  python fm_check_pc.py
"""

import os
import sys
import time
from datetime import datetime

import numpy as np

_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
sys.path.insert(0, os.path.join(_EXP, "calibration"))
from calib_common import fit_odmr
from lockin_common import (DATA_DIR, F_START, F_STOP, RP_GAIN, RP_IP, RP_PORT,
                           SMCV_IP, SMCV_PORT, SMCV100B, SmcvFm, frange,
                           teardown_smcv_modulation)
from odmr_smcv100b_pc import SETTLE_S, RedPitayaADC, integrate

# --- settings ---------------------------------------------------------------
MW_POWER_DBM = -18.0          # SMCV level (amplifier in the chain: <= -16.4 dBm)
DC_STEP_MHZ = 0.25
N_DC_SWEEPS = 4
N_DC_PAIRS = 30               # DC benchmark: repeated off/on readings at the dip
SMOOTH = 3                    # points in the moving average used to find the dip

N_LINES = 2                   # Lorentzian dips fitted to the DC spectrum (the
                              # two lines ~5 MHz apart overlap into one ~11 MHz
                              # blob; treating them as one put the park point
                              # between them and the deviation across both)
LINE = None                   # None -> the deeper line; or "lower" / "upper"
PARK = "slope"                # "slope" (FM tone is largest) or "dip"
PARK_MHZ = None               # e.g. 2867.4 to force the park frequency
OFF_RES_MHZ = F_START - 50.0  # far from any line: pickup check

# keep away from the 26.19 kHz Red Pitaya line and from mains harmonics
F_MODS_HZ = [500, 1000, 2000, 3000, 5000, 7000, 10000, 15000, 20000, 33000]
DECIMATION = 256              # fs = 488 kHz, 33.6 ms records, 30 Hz FFT bins
N_REC = 30                    # records per f_mod and position
FM_DEV_KHZ = None             # None -> ~FWHM/2 of one line (asked)


def ask(prompt, default=""):
    s = input(f"{prompt} [{default}]: ").strip()
    if s.lower() in ("q", "quit"):
        raise KeyboardInterrupt
    return s or str(default)


def ask_float(prompt, default):
    while True:
        try:
            return float(ask(prompt, default))
        except ValueError:
            print("  not a number")


def moving_average(y, n=SMOOTH):
    return np.convolve(y, np.ones(n) / n, mode="same") if n > 1 else y


def dc_sweeps(src, adc, freqs):
    data = np.zeros((N_DC_SWEEPS, len(freqs)))
    for s in range(N_DC_SWEEPS):
        for i, f in enumerate(freqs):
            src.set_freq_mhz(f)
            src.output(True)
            time.sleep(SETTLE_S)
            on = integrate(adc)
            src.output(False)
            time.sleep(SETTLE_S)
            off = integrate(adc)
            data[s, i] = on / off if off else np.nan
            print(f"\r  DC sweep {s + 1}/{N_DC_SWEEPS}: {i + 1}/{len(freqs)} "
                  f"({f:.2f} MHz)", end="", flush=True)
    print()
    return data


def find_points(freqs, sig):
    """Dip, steepest flank and a rough FWHM from the smoothed DC spectrum."""
    sm = moving_average(sig)
    edge = SMOOTH // 2                   # the moving average is biased at the ends
    inner = slice(edge, len(sm) - edge)
    i_dip = edge + int(np.nanargmin(sm[inner]))
    base = np.nanmedian(np.concatenate([sm[inner][:5], sm[inner][-5:]]))
    half = base - 0.5 * (base - sm[i_dip])
    lo = i_dip
    while lo > 0 and sm[lo] < half:
        lo -= 1
    hi = i_dip
    while hi < len(sm) - 1 and sm[hi] < half:
        hi += 1
    fwhm = freqs[hi] - freqs[lo]
    # steepest flank within one FWHM of the dip (not another line)
    grad = np.abs(np.gradient(sm, freqs))
    near = np.abs(freqs - freqs[i_dip]) <= max(fwhm, 2 * DC_STEP_MHZ)
    i_slope = int(np.flatnonzero(near)[np.argmax(grad[near])])
    return freqs[i_dip], freqs[i_slope], fwhm, 1 - sm[i_dip] / base


def choose_line(freqs, sig):
    """Fit N_LINES Lorentzians; for ONE line return its centre (the dip), the
    steepest point of its OUTER flank f0 +/- gamma/sqrt(3) (away from the other
    line, so a deviation ~gamma does not reach it), its FWHM and depth, and a
    text summary. Falls back to find_points() if the fit fails."""
    res = fit_odmr(freqs, sig, N_LINES) if N_LINES > 1 else None
    if not res:
        f_dip, f_slope, fwhm, depth = find_points(freqs, sig)
        return f_dip, f_slope, fwhm, depth, "fit failed: smoothed-spectrum estimate"
    ln = res["lines"]
    if LINE == "lower":
        k = 0
    elif LINE == "upper":
        k = len(ln) - 1
    else:
        k = int(np.argmax([x["contrast"] for x in ln]))
    x = ln[k]
    gamma = x["fwhm"] / 2
    others = [y["f0"] for j, y in enumerate(ln) if j != k]
    side = 1.0 if not others or np.mean(others) < x["f0"] else -1.0   # away from them
    f_slope = x["f0"] + side * gamma / np.sqrt(3)
    text = ("  lines: " + ", ".join(f"{y['f0']:.2f} MHz (C {100 * y['contrast']:.2f} %, "
                                    f"FWHM {y['fwhm']:.2f})" for y in ln)
            + f"\n  using line {k + 1}: outer flank on the "
            + ("high" if side > 0 else "low") + "-frequency side")
    return x["f0"], f_slope, x["fwhm"], x["contrast"], text


def dc_benchmark(src, adc, f_dip, path):
    """Repeated MW-off / MW-on readings at the dip: the plain on/off method."""
    src.set_freq_mhz(f_dip)
    t0 = time.monotonic()
    rows = []
    with open(path, "w") as f:
        f.write(f"# experiment=fm_check_dc_pairs\n# freq_MHz={f_dip}\n"
                "k,t_s,off_V,on_V\n")
        for k in range(N_DC_PAIRS):
            src.output(False)
            time.sleep(SETTLE_S)
            off = integrate(adc)
            src.output(True)
            time.sleep(SETTLE_S)
            on = integrate(adc)
            rows.append((time.monotonic() - t0, off, on))
            f.write(f"{k},{rows[-1][0]:.4f},{off:.8f},{on:.8f}\n")
            print(f"\r  DC benchmark {k + 1}/{N_DC_PAIRS}", end="", flush=True)
    print()
    t, off, on = map(np.array, zip(*rows))
    d = off - on
    t_pair = t[-1] / len(t)
    snr_1s = d.mean() / d.std(ddof=1) * np.sqrt(1.0 / t_pair)
    return snr_1s, t_pair, d.mean()


def records(scope, n):
    out, t0 = [], time.monotonic()
    for _ in range(n):
        out.append(scope.acquire((1,), DECIMATION, RP_GAIN).astype(np.float32))
    return np.array(out), (time.monotonic() - t0) / n


def main():
    run_dir = os.path.join(DATA_DIR, f"fm_check_{datetime.now():%Y%m%d_%H%M%S}")
    os.makedirs(run_dir, exist_ok=True)
    freqs = np.array(list(frange(F_START, F_STOP, DC_STEP_MHZ)))
    fs = 125e6 / DECIMATION
    print(f"FM CHECK -> {run_dir}\n  MW {MW_POWER_DBM:+.1f} dBm; DC sweep {F_START}-"
          f"{F_STOP} MHz / {DC_STEP_MHZ} ({len(freqs)} pts) x {N_DC_SWEEPS}; "
          f"f_mod {F_MODS_HZ} Hz")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    adc = None
    try:
        src.configure(MW_POWER_DBM)
        teardown_smcv_modulation(src, "fm")          # step 1 without modulation
        fm_ctl = SmcvFm(src)
        remote = dict(state=fm_ctl.state(False), shape=fm_ctl.shape_sine(),
                      lf=fm_ctl.lf_freq_hz(F_MODS_HZ[0]),
                      dev=fm_ctl.deviation_hz(FM_DEV_KHZ * 1e3 if FM_DEV_KHZ else 1e5))
        print("  SCPI control: " + ", ".join(
            f"{k} {'remote' if v else 'BY HAND'}" for k, v in remote.items())
            + f"  ({fm_ctl.report()})")
        adc = RedPitayaADC(RP_IP, RP_PORT)
        need = [] if remote["state"] else ["FM OFF for now"]
        need += [] if remote["shape"] else ["FM shape = sine"]
        input("\n" + ("SMCV Modulation menu: " + "; ".join(need) + ". " if need else "")
              + "Laser on, focus on the diamond. Enter to start the DC sweeps "
              "(Ctrl+C stops)...")

        # ---- 1. DC ODMR + benchmark --------------------------------------
        data = dc_sweeps(src, adc, freqs)
        sig, std = np.nanmean(data, 0), np.nanstd(data, 0)
        f_dip, f_slope, fwhm, depth, text = choose_line(freqs, sig)
        print(text)
        print(f"  dip {f_dip:.3f} MHz (depth {100 * depth:.2f} %), steepest flank "
              f"{f_slope:.3f} MHz, FWHM ~{fwhm:.2f} MHz")
        snr_dc, t_pair, d_dc = dc_benchmark(src, adc, f_dip,
                                            os.path.join(run_dir, "dc_pairs.csv"))
        print(f"  DC on/off at the dip: signal {d_dc * 1e3:.3f} mV, "
              f"{t_pair:.2f} s per pair, SNR in 1 s = {snr_dc:.1f}")
        park = PARK_MHZ if PARK_MHZ is not None else (f_slope if PARK == "slope"
                                                      else f_dip)
        park = ask_float(f"  park frequency (MHz; {PARK})", round(park, 3))
        with open(os.path.join(run_dir, "dc_odmr.csv"), "w") as f:
            f.write(f"# experiment=fm_check_dc\n# power_dBm={MW_POWER_DBM}\n"
                    f"# n_sweeps={N_DC_SWEEPS}\n# f_dip_MHz={f_dip}\n"
                    f"# f_slope_MHz={f_slope}\n# fwhm_MHz={fwhm}\n# depth={depth}\n"
                    f"# park={PARK}\n# park_MHz={park}\n# dc_snr_1s={snr_dc}\n"
                    f"# dc_t_pair_s={t_pair}\n# dc_signal_V={d_dc}\n"
                    "freq_MHz,signal,std\n")
            for row in zip(freqs, sig, std):
                f.write(",".join(f"{v:.7f}" for v in row) + "\n")

        # ---- 2. FM at the park point, f_mod by f_mod ---------------------
        dev_hz = (FM_DEV_KHZ * 1e3 if FM_DEV_KHZ else
                  ask_float("\n  FM deviation (kHz; ~FWHM/2 of ONE line)",
                            round(fwhm / 2 * 1e3)) * 1e3)
        if not fm_ctl.deviation_hz(dev_hz):
            dev_hz = ask_float("  set the FM deviation in the Modulation menu; value "
                               "you set (kHz)", round(dev_hz / 1e3)) * 1e3
        if not fm_ctl.state(True):
            input("  Switch FM ON in the SMCV Modulation menu (internal source), "
                  "then Enter...")
        src.s.write(":SOURce:MODulation:ALL:STATe ON")
        src.s.query("*OPC?")
        src.output(True)
        for fm in F_MODS_HZ:
            print("-" * 72)
            if fm_ctl.lf_freq_hz(fm):
                print(f"  LF frequency {fm} Hz (remote)")
            elif ask(f"Set the SMCV LF frequency to {fm} Hz, then Enter (s = skip)",
                     "").lower() == "s":
                continue
            src.set_freq_mhz(park)
            time.sleep(0.2)
            on, t_rec = records(adc.scope, N_REC)
            src.set_freq_mhz(OFF_RES_MHZ)
            time.sleep(0.2)
            off, _ = records(adc.scope, N_REC)
            src.set_freq_mhz(park)
            path = os.path.join(run_dir, f"fm_{fm:05d}Hz.npz")
            np.savez(path, fs=fs, decimation=DECIMATION, gain=RP_GAIN,
                     f_mod_nominal_hz=fm, deviation_hz=dev_hz, park_mhz=park,
                     off_res_mhz=OFF_RES_MHZ, power_dbm=MW_POWER_DBM,
                     on=on, off=off, t_rec_s=t_rec,
                     contiguous=bool(getattr(adc.scope, "CONTIGUOUS", False)))
            print(f"  {fm} Hz: DC {on.mean() * 1e3:.1f} mV, {t_rec * 1e3:.0f} ms per "
                  f"record -> {os.path.basename(path)}")
            if np.abs(on).max() > 0.98:
                print("  WARNING: IN1 near full scale (clipping?)")
        print(f"\nDone -> {run_dir}\nNext: python plot_fm_check.py")
    except KeyboardInterrupt:
        print(f"\nStopped. Files so far are in {run_dir}")
    finally:
        teardown_smcv_modulation(src, "fm")
        src.close()
        if adc is not None:
            adc.close()


if __name__ == "__main__":
    main()
