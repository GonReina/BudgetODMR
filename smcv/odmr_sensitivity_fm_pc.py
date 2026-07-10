"""
Empirical magnetic-field sensitivity of the FM lock-in ODMR setup (PC-controlled).

Uses the SAME virtual lock-in as odmr_lockin_fm_pc.py: the SMCV frequency-modulates
itself internally at the known f_mod (config.json -> lockin.f_mod_hz, 5 kHz) and the
Red Pitaya demodulates IN1 against that fixed frequency with the phase-independent
magnitude lock-in R = sqrt(X^2+Y^2). No modulation/reference cable is needed (the
SMCV100B cannot output its LF signal anyway) -- this is deliberately NOT the
fm_deriv variant.

Method (slope + noise):
  1. SWEEP    -- run a few FM sweeps, average -> R(f) (the |derivative| two-lobe shape).
  2. SLOPE    -- pick the working point f* on a lobe flank and measure the local
                 slope s = dR/df [V/MHz] there. The steepest point is suggested
                 automatically; with PICK_BY_HAND = True a matplotlib window then
                 opens so you can CLICK the flank point you actually want (e.g. a
                 specific line of a specific NV orientation) -- the local slope is
                 re-fitted at every click. ENTER or closing the window accepts,
                 'a' reverts to the automatic suggestion. A field change dB moves
                 the NV line by gamma*dB (gamma = 28.024 MHz/mT), so the
                 transduction coefficient is dR/dB = s * gamma [V/mT].
                 (Sit on a lobe FLANK, not the null: the magnitude R is quadratic
                 around the null, but linear-in-dB on the flank.)
  3. LISTEN   -- park the MW at f*, record a long time series of lock-in readings.
  4. ANALYSE  -- convert volts -> field via dR/dB, then report
                   * shot-to-shot noise sigma_B of a single reading,
                   * sensitivity eta = sigma_B * sqrt(T) in nT/sqrt(Hz)
                     (T_int = ADC buffer time: intrinsic; dt_wall = actual cadence:
                     practical, includes SCPI dead time),
                   * Allan deviation vs averaging time (shows the optimal averaging
                     time and where drift takes over; eta via sqrt(T) assumes white
                     noise, the Allan curve tells you where that assumption holds),
                   * detection floor: same time series with MW output OFF (no tone
                     at all -> rectified photodiode/ADC noise in the lock-in band).

Caveats:
  * Sensitivity is to the field component ALONG the NV axis of the line you sit on.
  * The slope calibration trusts the sweep; validate it once by moving the magnet a
    known amount (or driving a small coil) and checking the response matches s*gamma.

Wiring: photodiode -> Red Pitaya IN1 (as usual). Set the SMCV Modulation menu to FM,
internal source, LF frequency = config f_mod_hz, deviation = fm_deviation_khz.

Run on the PC:  python odmr_sensitivity_fm_pc.py
Outputs in <DATA_DIR>: sensitivity_fm_spectrum.csv, sensitivity_fm_timeseries.csv,
                       sensitivity_fm_allan.csv, sensitivity_fm_summary.txt
"""

import os
import time
from datetime import datetime

import numpy as np

from expconfig import load_config
from lockin_common import (RedPitayaLockin, SMCV100B, demodulate, frange,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
                           F_START, F_STOP, F_STEP, POWER_DBM,
                           F_MOD, SETTLE_S, FS_HZ, N_BUF, DATA_DIR)

_cfg = load_config()
GAMMA = _cfg.get("analysis", {}).get("gamma_mhz_per_mt", 28.024)  # MHz/mT
SMOOTH_PTS = max(1, int(_cfg.get("analysis", {}).get("smooth_pts", 3)))

# --- measurement sizes (local to this script; edit here, not config.json) ---
N_FIT_SWEEPS  = 4      # sweeps averaged for the spectrum / slope fit
FIT_HALF_PTS  = 10      # slope fitted over f* +/- this many sweep points
N_TIMESERIES  = 2000   # lock-in readings parked at f*  (~N * cadence seconds)
N_FLOOR       = 300    # readings with the MW output OFF (detection floor)
PARK_SETTLE_S = 0.5    # extra settle after parking at f*
PICK_BY_HAND  = True   # open a UI to click the working point (needs matplotlib;
                       # falls back to the automatic point if it can't)


# ============================================================================
# Step 1+2: spectrum and working point
# ============================================================================
def take_spectrum(src, rp, freqs):
    """Average N_FIT_SWEEPS FM lock-in sweeps -> R(f)."""
    acc = np.zeros(len(freqs))
    for sweep in range(1, N_FIT_SWEEPS + 1):
        for i, f in enumerate(freqs):
            src.set_freq_mhz(f)
            time.sleep(SETTLE_S)
            acc[i] += demodulate(rp.acquire_in1(), FS_HZ, F_MOD)
        print(f"  spectrum sweep {sweep}/{N_FIT_SWEEPS} done")
    return acc / N_FIT_SWEEPS


def moving_average(y, n):
    if n <= 1:
        return np.asarray(y, float)
    k = np.ones(n) / n
    return np.convolve(y, k, mode="same")


def fit_slope_at(freqs, R, i):
    """Local slope of R(f) around index i: linear least-squares fit over the RAW
    points i +/- FIT_HALF_PTS (index clamped away from the sweep edges).
    Returns (clamped index, slope [V/MHz])."""
    freqs = np.asarray(freqs, float)
    edge = max(SMOOTH_PTS, FIT_HALF_PTS)
    i = int(np.clip(i, edge, len(freqs) - edge - 1))
    lo, hi = i - FIT_HALF_PTS, i + FIT_HALF_PTS + 1
    slope, _ = np.polyfit(freqs[lo:hi], R[lo:hi], 1)
    return i, float(slope)


def find_working_point(freqs, R):
    """Automatic suggestion: steepest flank of the |derivative| pattern.
    Returns (f*, slope [V/MHz], peak_snr)."""
    freqs = np.asarray(freqs, float)
    Rs = moving_average(R, SMOOTH_PTS)
    grad = np.gradient(Rs, freqs)
    # exclude the sweep edges, where np.gradient/smoothing are one-sided
    edge = max(SMOOTH_PTS, FIT_HALF_PTS)
    inner = slice(edge, len(freqs) - edge)
    i_star = edge + int(np.argmax(np.abs(grad[inner])))
    i_star, slope = fit_slope_at(freqs, R, i_star)

    # crude signal check: lobe height vs baseline scatter
    base = np.median(R)
    mad = np.median(np.abs(R - base)) or 1e-12
    peak_snr = (np.max(R) - base) / (1.4826 * mad)
    return float(freqs[i_star]), slope, float(peak_snr)


def pick_working_point(freqs, R, f_auto, slope_auto):
    """Interactive working-point picker.

    Shows the averaged FM spectrum with the automatic suggestion pre-selected.
    LEFT-CLICK any point to move the working point there (the local slope is
    re-fitted over +/- FIT_HALF_PTS around the click); press 'a' to go back to
    the automatic point; press ENTER or close the window to accept.

    Returns (f*, slope [V/MHz], hand_picked). Falls back to the automatic point
    if matplotlib / a display is unavailable (e.g. headless instrument PC)."""
    try:
        import matplotlib
        import matplotlib.pyplot as plt
        if matplotlib.get_backend().lower() == "agg":
            raise RuntimeError("no interactive backend (Agg)")
    except Exception as e:
        print(f"  (no working-point UI: {e} -- using the automatic point)")
        return f_auto, slope_auto, False

    freqs = np.asarray(freqs, float)
    sel = {"f": float(f_auto), "slope": float(slope_auto)}
    df_fit = FIT_HALF_PTS * (freqs[1] - freqs[0])

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(freqs, 1e3 * R, lw=0.8, color="0.65", label="lock-in R (raw)")
    ax.plot(freqs, 1e3 * moving_average(R, SMOOTH_PTS), lw=1.2,
            color="tab:blue", label=f"smoothed ({SMOOTH_PTS} pts)")
    vline = ax.axvline(sel["f"], color="tab:red", ls="--", lw=1)
    fit_line, = ax.plot([], [], "-", lw=2.5, color="tab:red",
                        label=f"local fit (+/-{FIT_HALF_PTS} pts)")
    marker, = ax.plot([], [], "o", ms=9, color="tab:red", zorder=5)
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel("Lock-in R (mV)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    def redraw():
        f_star, slope = sel["f"], sel["slope"]
        r_star = float(np.interp(f_star, freqs, R))
        fx = np.array([f_star - df_fit, f_star + df_fit])
        marker.set_data([f_star], [1e3 * r_star])
        fit_line.set_data(fx, 1e3 * (r_star + slope * (fx - f_star)))
        vline.set_xdata([f_star])
        tag = "auto" if (f_star == f_auto and slope == slope_auto) else "hand-picked"
        ax.set_title(
            "CLICK a lobe flank to choose the working point --  "
            "ENTER / close window = accept,  'a' = back to auto\n"
            f"f* = {f_star:.3f} MHz ({tag}),   dR/df = {slope * 1e3:+.3f} mV/MHz,"
            f"   dR/dB = {abs(slope) * GAMMA * 1e3:.3f} mV/mT",
            fontsize=10)
        fig.canvas.draw_idle()

    def on_click(ev):
        # ignore clicks outside the axes or while the zoom/pan tool is active
        toolbar = getattr(fig.canvas, "toolbar", None)
        if ev.inaxes is not ax or ev.button != 1 or (toolbar and toolbar.mode):
            return
        i = int(np.argmin(np.abs(freqs - ev.xdata)))
        i, slope = fit_slope_at(freqs, R, i)
        sel["f"], sel["slope"] = float(freqs[i]), slope
        redraw()

    def on_key(ev):
        if ev.key == "enter":
            plt.close(fig)
        elif ev.key == "a":
            sel["f"], sel["slope"] = float(f_auto), float(slope_auto)
            redraw()

    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("key_press_event", on_key)
    redraw()
    plt.show()          # blocks until the window is closed

    hand = not (sel["f"] == f_auto and sel["slope"] == slope_auto)
    if abs(sel["slope"]) < 0.1 * abs(slope_auto):
        print("  WARNING: chosen slope is <10 % of the steepest one -- all nT "
              "numbers scale as 1/slope, so expect them to look much worse.")
    return sel["f"], sel["slope"], hand


# ============================================================================
# Step 3: time series
# ============================================================================
def record_timeseries(rp, n, label):
    """n consecutive lock-in readings; returns (t_seconds, R_volts)."""
    ts, rs = [], []
    t0 = time.perf_counter()
    for k in range(n):
        rs.append(demodulate(rp.acquire_in1(), FS_HZ, F_MOD))
        ts.append(time.perf_counter() - t0)
        if (k + 1) % 200 == 0:
            print(f"  {label}: {k + 1}/{n} readings "
                  f"({(k + 1) / ts[-1]:.1f} /s)")
    return np.array(ts), np.array(rs)


# ============================================================================
# Step 4: analysis
# ============================================================================
def welch_asd(y, dt, n_seg=8):
    """One-sided amplitude spectral density of y in units/sqrt(Hz) (Welch's
    method, numpy only): split into n_seg half-overlapping Hann-windowed
    segments, average the periodograms, take the square root.
    Returns (freq_Hz, asd). For white noise of per-sample std s the flat level
    is s*sqrt(2*dt) = sqrt(2) * (s*sqrt(dt))."""
    y = np.asarray(y, float) - np.mean(y)
    n = len(y)
    seg = max(16, int(2 * n / (n_seg + 1)))
    step = max(1, seg // 2)
    w = np.hanning(seg)
    u = float(np.sum(w ** 2))
    psds = []
    for s0 in range(0, n - seg + 1, step):
        x = y[s0:s0 + seg]
        X = np.fft.rfft((x - x.mean()) * w)
        psds.append(2.0 * dt * np.abs(X) ** 2 / u)
    fr = np.fft.rfftfreq(seg, dt)
    return fr, np.sqrt(np.mean(psds, axis=0))


def allan_deviation(y, dt):
    """Non-overlapping Allan deviation of time series y (sample spacing dt).
    Returns (tau_s, adev) for averaging factors 1, 2, 4, 8, ... ."""
    y = np.asarray(y, float)
    taus, adevs = [], []
    m = 1
    while len(y) // m >= 4:
        n_blk = len(y) // m
        means = y[: n_blk * m].reshape(n_blk, m).mean(axis=1)
        adevs.append(np.sqrt(0.5 * np.mean(np.diff(means) ** 2)))
        taus.append(m * dt)
        m *= 2
    return np.array(taus), np.array(adevs)


def analyse(t, R, dRdB_v_per_mt, t_floor=None, R_floor=None):
    """Convert the parked time series to field units and compute sensitivities.
    Returns a dict of results (all field quantities in nT)."""
    dt = float(np.median(np.diff(t)))          # wall-clock cadence per reading
    t_int = N_BUF / FS_HZ                      # ADC integration per reading
    b_nT = (R - np.mean(R)) / dRdB_v_per_mt * 1e6

    sigma = float(np.std(b_nT))
    taus, adev = allan_deviation(b_nT, dt)
    i_best = int(np.argmin(adev))

    res = {
        "dt_s": dt, "t_int_s": t_int, "duty": t_int / dt,
        "sigma_nT": sigma,
        "eta_int_nT_rtHz": sigma * np.sqrt(t_int),
        "eta_wall_nT_rtHz": sigma * np.sqrt(dt),
        "taus_s": taus, "adev_nT": adev,
        "tau_best_s": float(taus[i_best]), "adev_best_nT": float(adev[i_best]),
    }
    if R_floor is not None:
        sig_fl = float(np.std(R_floor)) / dRdB_v_per_mt * 1e6
        res["floor_sigma_nT"] = sig_fl
        res["floor_eta_wall_nT_rtHz"] = sig_fl * np.sqrt(dt)
    return res


# ============================================================================
# Main
# ============================================================================
def main():
    freqs = list(frange(F_START, F_STOP, F_STEP))
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")

    print(f"FM sensitivity run: {F_START}-{F_STOP} MHz / {F_STEP} "
          f"({len(freqs)} pts), {POWER_DBM:+.1f} dBm, f_mod={F_MOD:.0f} Hz")
    print(f"  gamma = {GAMMA} MHz/mT, lock-in T_int = {N_BUF / FS_HZ * 1e3:.1f} ms")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "fm")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        # ---- 1) spectrum ----
        print("\nStep 1/4: FM spectrum for the slope calibration")
        R = take_spectrum(src, rp, freqs)
        spec_path = os.path.join(DATA_DIR, "sensitivity_fm_spectrum.csv")
        with open(spec_path, "w") as f:
            f.write(f"# FM lock-in spectrum for sensitivity, {stamp}, "
                    f"{N_FIT_SWEEPS} sweeps averaged\nfreq_MHz,lockin_R\n")
            for fr, r in zip(freqs, R):
                f.write(f"{fr:.5f},{r:.8f}\n")

        # ---- 2) working point ----
        f_auto, slope_auto, peak_snr = find_working_point(freqs, R)
        print(f"\nStep 2/4: automatic suggestion f* = {f_auto:.3f} MHz "
              f"(slope {slope_auto * 1e3:+.4f} mV/MHz)")
        print(f"  spectrum peak SNR ~ {peak_snr:.1f}")
        if peak_snr < 5:
            print("  WARNING: weak spectrum -- slope (and hence the nT numbers) "
                  "will be unreliable. Increase N_FIT_SWEEPS or MW power.")
        if PICK_BY_HAND:
            print("  pick the working point in the plot window "
                  "(click a flank, ENTER to accept, 'a' = auto)...")
            f_star, slope, hand_picked = pick_working_point(freqs, R,
                                                            f_auto, slope_auto)
        else:
            f_star, slope, hand_picked = f_auto, slope_auto, False
        dRdB = abs(slope) * GAMMA                     # V/mT
        picked_tag = "hand-picked" if hand_picked else "auto"
        print(f"  working point ({picked_tag}): f* = {f_star:.3f} MHz")
        print(f"  slope dR/df  = {slope * 1e3:+.4f} mV/MHz")
        print(f"  dR/dB        = {dRdB * 1e3:.4f} mV/mT  (x gamma = {GAMMA} MHz/mT)")

        # ---- 3) time series at f* ----
        print(f"\nStep 3/4: parking at {f_star:.3f} MHz, "
              f"{N_TIMESERIES} readings")
        src.set_freq_mhz(f_star)
        time.sleep(PARK_SETTLE_S)
        t, r = record_timeseries(rp, N_TIMESERIES, "on-slope")

        print(f"  detection floor: MW output OFF, {N_FLOOR} readings")
        src.output(False)
        time.sleep(PARK_SETTLE_S)
        t_fl, r_fl = record_timeseries(rp, N_FLOOR, "MW-off floor")
        src.output(True)

        ts_path = os.path.join(DATA_DIR, "sensitivity_fm_timeseries.csv")
        with open(ts_path, "w") as f:
            f.write(f"# parked at {f_star:.5f} MHz, {stamp}, "
                    f"slope_V_per_MHz={slope:.8e}, dRdB_V_per_mT={dRdB:.8e}\n")
            f.write("t_s,lockin_R,mw_on\n")
            for tt, rr in zip(t, r):
                f.write(f"{tt:.4f},{rr:.8f},1\n")
            for tt, rr in zip(t_fl, r_fl):
                f.write(f"{tt:.4f},{rr:.8f},0\n")

        # ---- 4) analysis ----
        print("\nStep 4/4: analysis")
        res = analyse(t, r, dRdB, t_fl, r_fl)

        allan_path = os.path.join(DATA_DIR, "sensitivity_fm_allan.csv")
        with open(allan_path, "w") as f:
            f.write(f"# Allan deviation of the field reading, {stamp}\n")
            f.write("tau_s,adev_nT\n")
            for tau, ad in zip(res["taus_s"], res["adev_nT"]):
                f.write(f"{tau:.4f},{ad:.4f}\n")

        lines = [
            f"FM lock-in sensitivity summary  ({stamp})",
            f"  working point        : {f_star:.3f} MHz ({picked_tag}) "
            f"(slope {slope * 1e3:+.4f} mV/MHz, dR/dB {dRdB * 1e3:.4f} mV/mT)",
            f"  cadence              : {res['dt_s'] * 1e3:.1f} ms/reading "
            f"(integration {res['t_int_s'] * 1e3:.1f} ms, "
            f"duty cycle {100 * res['duty']:.0f} %)",
            f"  single-reading noise : {res['sigma_nT']:.1f} nT rms",
            f"  sensitivity          : {res['eta_int_nT_rtHz']:.1f} nT/sqrt(Hz) "
            f"(intrinsic, integration time only)",
            f"                         {res['eta_wall_nT_rtHz']:.1f} nT/sqrt(Hz) "
            f"(practical, wall-clock incl. dead time)",
            f"  Allan minimum        : {res['adev_best_nT']:.1f} nT "
            f"at tau = {res['tau_best_s']:.2f} s "
            f"(best field resolution; drift dominates beyond)",
            f"  MW-off floor         : {res['floor_sigma_nT']:.1f} nT rms/reading "
            f"-> {res['floor_eta_wall_nT_rtHz']:.1f} nT/sqrt(Hz) "
            f"(photodiode+ADC limit; gap to the on-slope value = MW/NV noise)",
            "",
            "  Allan deviation vs averaging time:",
        ]
        lines += [f"    tau = {tau:7.2f} s : {ad:8.2f} nT"
                  for tau, ad in zip(res["taus_s"], res["adev_nT"])]
        lines += [
            "",
            "  NOTE: sensitivity is to the field component along the NV axis of",
            "  the chosen line; eta = sigma*sqrt(T) assumes white noise (check",
            "  the Allan curve: it should fall ~1/sqrt(tau) where that holds).",
            "  Validate the calibration once with a known field change.",
        ]
        summary = "\n".join(lines)
        print("\n" + summary)
        with open(os.path.join(DATA_DIR, "sensitivity_fm_summary.txt"), "w") as f:
            f.write(summary + "\n")
        print(f"\nSaved: {spec_path}\n       {ts_path}\n       {allan_path}\n"
              f"       {os.path.join(DATA_DIR, 'sensitivity_fm_summary.txt')}")

    except KeyboardInterrupt:
        print("\nStopped early -- nothing (more) saved.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
