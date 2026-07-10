"""
Closed-loop FM ODMR magnetometer (PC-controlled): lock the MW frequency to a
resonance NULL and use the correction/error signal as the field measurement.

Same virtual lock-in as odmr_lockin_fm_pc.py / odmr_sensitivity_fm_pc.py: the SMCV
frequency-modulates itself internally at f_mod (config.json -> lockin.f_mod_hz) and
the Red Pitaya demodulates IN1 at that fixed, known frequency (magnitude lock-in,
no reference cable -- the SMCV100B cannot output its LF signal).

Why a lock, and why a TWO-POINT one:
  * Open loop (odmr_sensitivity_fm_pc.py) parks on a lobe flank. If the field (or
    laser) drifts more than ~half a lobe width, the working point slides off the
    linear region and the calibration is gone.
  * The magnitude R = sqrt(X^2+Y^2) is unsigned, so R alone cannot tell which WAY
    the line moved. But R(f) is symmetric about the null between the two
    |derivative| lobes, so the two-point difference

        e(f0) = R(f0 + delta) - R(f0 - delta)

    is an antisymmetric, SIGNED error signal that crosses zero exactly at the line
    centre. A software integrator then steers f0 to keep e = 0:

        f0 <- f0 - GAIN * e / D          (D = de/df0, measured, V/MHz)

    The locked f0(t) tracks the resonance wherever it goes; the field is

        B(t) = (f_est(t) - f_ref) / gamma,   f_est = f0 - e/D

    (f0 is the slow integrator state; the residual e/D adds back the in-loop,
    faster-than-the-loop part, so B keeps the full single-reading bandwidth.)

Advantages over the open-loop flank measurement:
  * the working point cannot drift away -- linearity is maintained indefinitely;
  * dynamic range = the whole sweep span, not ~half a linewidth;
  * the null position is first-order immune to laser-power / contrast drift
    (amplitude changes rescale the lobes but do not move the null).
Costs: two lock-in readings per cycle (half the sample rate), and the loop only
tracks field changes slower than ~GAIN/(2*cycle_time).

Procedure:
  1. SWEEP     -- average a few FM sweeps -> R(f).
  2. PICK NULL -- the null between the two strongest lobes is suggested; with
                  PICK_BY_HAND a matplotlib window opens: CLICK near any null to
                  choose it (click snaps to the local minimum, the sampling points
                  f0 +/- delta are drawn). ENTER / close = accept, 'a' = auto.
  3. CALIBRATE -- measure e at a few offsets around the null, fit the straight
                  line -> discriminant slope D [V/MHz] and re-centre f0.
  4. LOCK      -- run the integrator for N_LOCK_CYCLES, logging t, f0, e, B.
  5. ANALYSE   -- sigma/Allan/sensitivity of B(t), lock health (residual error,
                  capture-range violations), tracked drift range.

Run on the PC:  python odmr_fieldlock_fm_pc.py
Outputs in <DATA_DIR>: fieldlock_fm_spectrum.csv, fieldlock_fm_timeseries.csv,
                       fieldlock_fm_summary.txt
Plot with:      python analysis/plot_fieldlock_fm.py
"""

import os
import time
from datetime import datetime

import numpy as np

from lockin_common import (RedPitayaLockin, SMCV100B, demodulate, frange,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
                           F_START, F_STOP, F_STEP, POWER_DBM,
                           F_MOD, SETTLE_S, FS_HZ, N_BUF, DATA_DIR)
from odmr_sensitivity_fm_pc import (take_spectrum, moving_average,
                                    allan_deviation, welch_asd,
                                    GAMMA, SMOOTH_PTS)

# --- lock settings (local to this script; edit here, not config.json) ---
N_LOCK_CYCLES = 2000    # lock iterations (~2 readings each)
LOOP_GAIN     = 0.4     # integrator gain, 0<G<1 (0.4 = correct 40 % per cycle)
DITHER_MHZ    = None    # sampling offset delta; None -> half the lobe spacing
N_DISC_PTS    = 5       # points for the discriminant (D) calibration
PICK_BY_HAND  = True    # click the null in a UI (falls back to auto)
PARK_SETTLE_S = 0.5     # settle after big frequency moves


def read_R(src, rp, f_mhz):
    """One lock-in reading at MW frequency f (set + settle + demodulate)."""
    src.set_freq_mhz(f_mhz)
    time.sleep(SETTLE_S)
    return demodulate(rp.acquire_in1(), FS_HZ, F_MOD)


# ============================================================================
# Null finding / picking
# ============================================================================
def find_lobes_and_nulls(freqs, R):
    """Detect |derivative| lobes (local maxima) and the nulls between adjacent
    lobe pairs. Returns (lobe_freqs, nulls) where each null is a dict with
    f0 (null), f_lo/f_hi (its two lobes) and 'height' (smaller lobe height)."""
    freqs = np.asarray(freqs, float)
    Rs = moving_average(R, SMOOTH_PTS)
    base = float(np.median(Rs))
    thr = base + 0.25 * (float(np.max(Rs)) - base)
    step = freqs[1] - freqs[0]

    lobes = []
    for i in range(1, len(Rs) - 1):
        if Rs[i] > thr and Rs[i] >= Rs[i - 1] and Rs[i] > Rs[i + 1]:
            if not lobes or freqs[i] - freqs[lobes[-1]] > 2 * step:
                lobes.append(i)
            elif Rs[i] > Rs[lobes[-1]]:
                lobes[-1] = i

    nulls = []
    for a, b in zip(lobes, lobes[1:]):
        if freqs[b] - freqs[a] > 6.0:      # too far apart: different resonances
            continue
        k = a + int(np.argmin(Rs[a:b + 1]))
        nulls.append({"f0": float(freqs[k]),
                      "f_lo": float(freqs[a]), "f_hi": float(freqs[b]),
                      "height": float(min(Rs[a], Rs[b]) - base)})
    return [float(freqs[i]) for i in lobes], nulls


def null_delta(null):
    """Sampling offset for a null: half its lobe spacing (or DITHER_MHZ)."""
    if DITHER_MHZ is not None:
        return float(DITHER_MHZ)
    return 0.5 * (null["f_hi"] - null["f_lo"])


def pick_null(freqs, R, nulls, auto_idx):
    """Interactive null picker: CLICK near a null to choose it (snaps to the
    nearest detected null), ENTER / close = accept, 'a' = auto suggestion.
    Returns the chosen null dict. Falls back to auto without a display."""
    try:
        import matplotlib
        import matplotlib.pyplot as plt
        if matplotlib.get_backend().lower() == "agg":
            raise RuntimeError("no interactive backend (Agg)")
    except Exception as e:
        print(f"  (no null-picker UI: {e} -- using the automatic null)")
        return nulls[auto_idx]

    freqs = np.asarray(freqs, float)
    sel = {"i": auto_idx}

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(freqs, 1e3 * R, lw=0.8, color="0.65", label="lock-in R (raw)")
    ax.plot(freqs, 1e3 * moving_average(R, SMOOTH_PTS), lw=1.2,
            color="tab:blue", label=f"smoothed ({SMOOTH_PTS} pts)")
    for nu in nulls:
        ax.axvline(nu["f0"], color="tab:green", ls=":", lw=1, alpha=0.6)
    vline = ax.axvline(nulls[auto_idx]["f0"], color="tab:red", ls="--", lw=1.5)
    samp, = ax.plot([], [], "v", ms=10, color="tab:red",
                    label=r"sampling points $f_0 \pm \delta$")
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel("Lock-in R (mV)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    def redraw():
        nu = nulls[sel["i"]]
        d = null_delta(nu)
        vline.set_xdata([nu["f0"]])
        samp.set_data([nu["f0"] - d, nu["f0"] + d],
                      [1e3 * float(np.interp(nu["f0"] - d, freqs, R)),
                       1e3 * float(np.interp(nu["f0"] + d, freqs, R))])
        tag = "auto" if sel["i"] == auto_idx else "hand-picked"
        ax.set_title("CLICK near a null (green) to lock there --  "
                     "ENTER / close = accept,  'a' = auto\n"
                     f"null f0 = {nu['f0']:.3f} MHz ({tag}),   "
                     f"delta = {d:.3f} MHz,   lobes {nu['f_lo']:.2f} / "
                     f"{nu['f_hi']:.2f} MHz", fontsize=10)
        fig.canvas.draw_idle()

    def on_click(ev):
        toolbar = getattr(fig.canvas, "toolbar", None)
        if ev.inaxes is not ax or ev.button != 1 or (toolbar and toolbar.mode):
            return
        sel["i"] = int(np.argmin([abs(nu["f0"] - ev.xdata) for nu in nulls]))
        redraw()

    def on_key(ev):
        if ev.key == "enter":
            plt.close(fig)
        elif ev.key == "a":
            sel["i"] = auto_idx
            redraw()

    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("key_press_event", on_key)
    redraw()
    plt.show()
    return nulls[sel["i"]]


# ============================================================================
# Discriminant calibration and the lock loop
# ============================================================================
def error_signal(src, rp, f0, delta):
    """Signed two-point error e = R(f0+delta) - R(f0-delta)."""
    return read_R(src, rp, f0 + delta) - read_R(src, rp, f0 - delta)


def calibrate_discriminant(src, rp, f0, delta):
    """Measure e at N_DISC_PTS offsets around the null and fit a line.
    Returns (D [V/MHz], e0 [V at offset 0], offsets, errors)."""
    offs = np.linspace(-delta / 2, delta / 2, N_DISC_PTS)
    errs = np.array([error_signal(src, rp, f0 + o, delta) for o in offs])
    D, e0 = np.polyfit(offs, errs, 1)
    return float(D), float(e0), offs, errs


def run_lock(src, rp, f0, delta, D, n_cycles):
    """The integrator loop. Returns (t, f0_trace, err_trace, n_clipped)."""
    lo, hi = F_START + delta, F_STOP - delta
    ts, f0s, errs = [], [], []
    n_clip = 0
    t_start = time.perf_counter()
    for k in range(n_cycles):
        e = error_signal(src, rp, f0, delta)
        f0 -= LOOP_GAIN * e / D
        if not lo <= f0 <= hi:
            f0 = min(max(f0, lo), hi)
            n_clip += 1
        ts.append(time.perf_counter() - t_start)
        f0s.append(f0)
        errs.append(e)
        if (k + 1) % 100 == 0:
            print(f"  lock: {k + 1}/{n_cycles}  f0 = {f0:.4f} MHz  "
                  f"e = {e * 1e3:+.3f} mV  ({(k + 1) / ts[-1]:.1f} cycles/s)")
    return np.array(ts), np.array(f0s), np.array(errs), n_clip


# ============================================================================
# Main
# ============================================================================
def main():
    freqs = list(frange(F_START, F_STOP, F_STEP))
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")

    print(f"FIELD-LOCK FM run: {F_START}-{F_STOP} MHz / {F_STEP} "
          f"({len(freqs)} pts), {POWER_DBM:+.1f} dBm, f_mod={F_MOD:.0f} Hz")
    print(f"  gamma = {GAMMA} MHz/mT, gain = {LOOP_GAIN}, "
          f"{N_LOCK_CYCLES} lock cycles")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "fm")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        # ---- 1) spectrum ----
        print("\nStep 1/4: FM spectrum")
        R = take_spectrum(src, rp, freqs)
        spec_path = os.path.join(DATA_DIR, "fieldlock_fm_spectrum.csv")
        with open(spec_path, "w") as f:
            f.write(f"# FM lock-in spectrum for field lock, {stamp}\n"
                    "freq_MHz,lockin_R\n")
            for fr, r in zip(freqs, R):
                f.write(f"{fr:.5f},{r:.8f}\n")

        # ---- 2) choose the null ----
        lobes, nulls = find_lobes_and_nulls(freqs, R)
        if not nulls:
            raise SystemExit("No lobe-pair null found in the spectrum -- "
                             "check the sweep range / signal level.")
        auto_idx = int(np.argmax([nu["height"] for nu in nulls]))
        print(f"\nStep 2/4: {len(lobes)} lobes, {len(nulls)} null(s) found; "
              f"auto = {nulls[auto_idx]['f0']:.3f} MHz")
        null = pick_null(freqs, R, nulls, auto_idx) if PICK_BY_HAND \
            else nulls[auto_idx]
        f0, delta = null["f0"], null_delta(null)
        print(f"  locking at f0 = {f0:.3f} MHz, delta = {delta:.3f} MHz")

        # ---- 3) discriminant ----
        print("\nStep 3/4: discriminant calibration")
        src.set_freq_mhz(f0)
        time.sleep(PARK_SETTLE_S)
        D, e0, offs, errs = calibrate_discriminant(src, rp, f0, delta)
        cap_mV = abs(D) * delta * 1e3
        print(f"  D = de/df0 = {D * 1e3:+.4f} mV/MHz "
              f"(dB equivalent {abs(D) * GAMMA * 1e3:.4f} mV/mT)")
        print(f"  capture range ~ +/-{delta:.3f} MHz (error up to ~{cap_mV:.2f} mV)")
        if abs(D) * delta < 3 * float(np.std(errs - (D * offs + e0))):
            print("  WARNING: discriminant barely above its own scatter -- "
                  "lock will be noisy. More MW power / narrower delta?")
        f0 -= e0 / D                     # re-centre using the calibration
        print(f"  re-centred to f0 = {f0:.4f} MHz")

        # ---- 4) lock ----
        print(f"\nStep 4/4: locking for {N_LOCK_CYCLES} cycles")
        t, f0s, es, n_clip = run_lock(src, rp, f0, delta, D, N_LOCK_CYCLES)

        # field: integrator state + in-loop residual, relative to the start.
        # f0s[k] already includes this cycle's correction (-G*e/D), so the
        # instantaneous centre estimate f0_before - e/D equals f0s + (G-1)*e/D.
        f_est = f0s + (LOOP_GAIN - 1.0) * es / D
        f_ref = float(f_est[0])
        b_nT = (f_est - f_ref) / GAMMA * 1e6

        ts_path = os.path.join(DATA_DIR, "fieldlock_fm_timeseries.csv")
        with open(ts_path, "w") as f:
            f.write(f"# field lock at null, {stamp}, f_ref_MHz={f_ref:.6f}, "
                    f"delta_MHz={delta:.5f}, D_V_per_MHz={D:.8e}, "
                    f"gain={LOOP_GAIN}, gamma_MHz_per_mT={GAMMA}\n")
            f.write("t_s,f0_MHz,err_V,B_nT\n")
            for tt, ff, ee, bb in zip(t, f0s, es, b_nT):
                f.write(f"{tt:.4f},{ff:.6f},{ee:.8e},{bb:.4f}\n")

        # ---- analysis ----
        dt = float(np.median(np.diff(t)))
        sigma = float(np.std(b_nT - np.mean(b_nT)))
        taus, adev = allan_deviation(b_nT, dt)
        i_best = int(np.argmin(adev))
        resid_nT = float(np.std(es / D / GAMMA * 1e6))   # in-loop residual, nT
        span_nT = (float(np.max(f_est)) - float(np.min(f_est))) / GAMMA * 1e6

        lines = [
            f"FM field-lock summary  ({stamp})",
            f"  null                 : {f_ref:.4f} MHz, delta = {delta:.3f} MHz, "
            f"D = {D * 1e3:+.4f} mV/MHz, gain = {LOOP_GAIN}",
            f"  cadence              : {dt * 1e3:.1f} ms/cycle (2 readings), "
            f"loop bandwidth ~ {LOOP_GAIN / (2 * np.pi * dt):.1f} Hz",
            f"  field noise          : {sigma:.1f} nT rms per cycle",
            f"  sensitivity          : {sigma * np.sqrt(dt):.1f} nT/sqrt(Hz) "
            f"(wall-clock, closed loop)",
            f"  Allan minimum        : {adev[i_best]:.1f} nT at "
            f"tau = {taus[i_best]:.2f} s",
            f"  in-loop residual     : {resid_nT:.1f} nT rms "
            f"(how far the lock let the null wander)",
            f"  tracked field span   : {span_nT:.1f} nT "
            f"({(np.max(f_est) - np.min(f_est)) * 1e3:.2f} kHz of line motion)",
            f"  capture violations   : {n_clip} "
            f"(f0 hit the sweep edge; 0 = healthy lock)",
            "",
            "  Allan deviation vs averaging time:",
        ]
        lines += [f"    tau = {tau:7.2f} s : {ad:8.2f} nT"
                  for tau, ad in zip(taus, adev)]
        lines += [
            "",
            "  NOTE: B is the field component along the NV axis of the locked",
            "  line, relative to the start of the lock. The null lock is",
            "  first-order immune to laser/contrast drift; validate the scale",
            "  once with a known field change.",
        ]
        summary = "\n".join(lines)
        print("\n" + summary)
        with open(os.path.join(DATA_DIR, "fieldlock_fm_summary.txt"), "w") as f:
            f.write(summary + "\n")
        print(f"\nSaved: {spec_path}\n       {ts_path}\n"
              f"       {os.path.join(DATA_DIR, 'fieldlock_fm_summary.txt')}")

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
