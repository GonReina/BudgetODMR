"""
NOISE BUDGET for the FM lock-in magnetometer: where do the microvolts (and
therefore the nanoteslas) come from?

Measures the in-band lock-in noise (the scatter of standard 8.4 ms demodulated
readings at f_mod) in FIVE configurations, from full operation down to nothing,
and attributes the total in quadrature to each layer of the setup:

    A. ON SLOPE   (parked at f*, MW + modulation on)   full operation
    B. OFF RES.   (parked far away, MW + modulation on) no NV response
    C. MW OFF     (laser on, MW output off)             optics only
    D. BEAM BLOCKED (you block the laser at the diamond) ambient/scatter + dark
    E. LASER OFF  (you switch the laser output off)      electronics + ADC only

Decomposition (quadrature differences, converted to nT via the measured slope):
    electronics/ADC/dark      = sigma_E
    ambient & scattered light = sqrt(sigma_D^2 - sigma_E^2)
    laser intensity/shot      = sqrt(sigma_C^2 - sigma_D^2)
    MW chain (pickup, AM leak)= sqrt(sigma_B^2 - sigma_C^2)
    on-slope excess           = sqrt(sigma_A^2 - sigma_B^2)
                                 (genuine field noise + resonance jitter --
                                  the only part that is "real" magnetics)

Each stage also records the photodiode DC level, one raw fast buffer, and one
1.07 s wideband record (for per-stage PSDs). Stage A additionally verifies the
actual modulation tone frequency (detect_fmod) and amplitude.

The script PROMPTS you before stages D (block the beam) and E (laser off).
Total time ~4 minutes plus the initial sweep.

Run on the PC:  python odmr_noise_budget_pc.py
Outputs in <DATA_DIR>: noise_budget.txt, noise_budget.npz, noise_budget.png
"""

import os
import sys
import time
from datetime import datetime

import numpy as np

from lockin_common import (RedPitayaLockin, SMCV100B, demodulate, detect_fmod,
                           frange, setup_smcv_modulation,
                           teardown_smcv_modulation,
                           SMCV_IP, SMCV_PORT, RP_IP, RP_PORT, RP_GAIN,
                           F_START, F_STOP, F_STEP, POWER_DBM, F_MOD,
                           SETTLE_S, FS_HZ, DATA_DIR)
from odmr_sensitivity_fm_pc import (take_spectrum, find_working_point,
                                    pick_working_point, welch_asd, GAMMA)

# --- settings (local to this script) ---
N_READINGS = 30       # 8.4 ms demodulated readings per stage
DEC_WB     = 8192     # one wideband record per stage for the PSD
PICK_BY_HAND = True

STAGES = ("A_on_slope", "B_off_resonance", "C_mw_off",
          "D_beam_blocked", "E_laser_off")
LABELS = {
    "A_on_slope":      "A on slope (full operation)",
    "B_off_resonance": "B off resonance (MW + mod on)",
    "C_mw_off":        "C MW output off (laser only)",
    "D_beam_blocked":  "D beam blocked (ambient + dark)",
    "E_laser_off":     "E laser off (electronics/ADC)",
}


def measure_stage(rp):
    """N standard readings + DC level + one raw fast buffer + one wideband
    record. Returns a dict of arrays/values."""
    readings, dc = [], []
    raw = None
    for k in range(N_READINGS):
        v = rp.acquire_in1()
        if raw is None:
            raw = np.array(v)
        readings.append(demodulate(v, FS_HZ, F_MOD))
        dc.append(float(np.mean(v)))
    wb = rp.scope.acquire((1,), DEC_WB, RP_GAIN, fill_timeout_s=8.0)
    return {"R": np.array(readings), "dc": np.array(dc), "raw": raw,
            "wb": np.array(wb), "fs_wb": 125e6 / DEC_WB}


def quad_diff(a, b):
    """sqrt(a^2 - b^2), clipped at 0 (measurement scatter can invert order)."""
    return float(np.sqrt(max(a * a - b * b, 0.0)))


def budget_table(sig, dRdB):
    """sig: dict stage -> sigma_R [V]. Returns list of (name, uV, nT) rows."""
    to_nT = lambda s: s / dRdB * 1e6 if dRdB > 0 else float("nan")
    rows = [
        ("electronics / ADC / PD dark", sig["E_laser_off"]),
        ("ambient & scattered light",
         quad_diff(sig["D_beam_blocked"], sig["E_laser_off"])),
        ("laser intensity / shot noise",
         quad_diff(sig["C_mw_off"], sig["D_beam_blocked"])),
        ("MW chain (pickup / AM leakage)",
         quad_diff(sig["B_off_resonance"], sig["C_mw_off"])),
        ("on-slope excess (REAL field + line jitter)",
         quad_diff(sig["A_on_slope"], sig["B_off_resonance"])),
        ("TOTAL (on slope)", sig["A_on_slope"]),
    ]
    return [(name, 1e6 * s, to_nT(s)) for name, s in rows]


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    freqs = list(frange(F_START, F_STOP, F_STEP))

    print(f"NOISE BUDGET run, {N_READINGS} readings/stage, f_mod={F_MOD:.0f} Hz")
    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "fm")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        # ---- working point ----
        print("\nStep 1: FM spectrum + working point")
        R = take_spectrum(src, rp, freqs)
        f_auto, slope_auto, snr = find_working_point(freqs, R)
        if PICK_BY_HAND:
            f_star, slope, _ = pick_working_point(freqs, R, f_auto, slope_auto)
        else:
            f_star, slope = f_auto, slope_auto
        dRdB = abs(slope) * GAMMA
        print(f"  f* = {f_star:.3f} MHz, slope {slope * 1e3:+.4f} mV/MHz "
              f"-> dR/dB = {dRdB * 1e3:.4f} mV/mT (spectrum SNR ~ {snr:.0f})")

        data = {}

        # ---- A: on slope, full operation ----
        print("\nStage A: on slope (full operation)")
        src.set_freq_mhz(f_star)
        time.sleep(0.5)
        data["A_on_slope"] = measure_stage(rp)
        f_tone = detect_fmod(data["A_on_slope"]["raw"], FS_HZ, F_MOD)
        print(f"  tone check: strongest LF component at {f_tone:.1f} Hz "
              f"(demodulating at {F_MOD:.1f} Hz)")

        # ---- B: off resonance, MW + modulation still on ----
        print("Stage B: off resonance (MW + modulation on)")
        src.set_freq_mhz(F_START)
        time.sleep(0.5)
        data["B_off_resonance"] = measure_stage(rp)

        # ---- C: MW output off ----
        print("Stage C: MW output OFF (laser only)")
        src.output(False)
        time.sleep(0.5)
        data["C_mw_off"] = measure_stage(rp)

        # ---- D: beam blocked (user) ----
        input("\nStage D: BLOCK the laser beam before the diamond "
              "(card/shutter), then press Enter... ")
        data["D_beam_blocked"] = measure_stage(rp)

        # ---- E: laser off (user) ----
        input("\nStage E: switch the LASER OUTPUT OFF (LTC56A), "
              "then press Enter... ")
        data["E_laser_off"] = measure_stage(rp)

        print("\n(You can unblock / switch the laser back on now.)")

        # ---- analysis ----
        sig = {k: float(np.std(d["R"])) for k, d in data.items()}
        mean_R_on = float(np.mean(data["A_on_slope"]["R"]))
        dc = {k: float(np.mean(d["dc"])) for k, d in data.items()}
        rows = budget_table(sig, dRdB)

        lines = [
            f"FM lock-in NOISE BUDGET  ({stamp})",
            f"  working point : {f_star:.3f} MHz, slope {slope * 1e3:+.4f} "
            f"mV/MHz, dR/dB {dRdB * 1e3:.4f} mV/mT",
            f"  tone          : R(f*) = {mean_R_on * 1e6:.1f} uV at "
            f"{f_tone:.1f} Hz (expected {F_MOD:.1f} Hz)",
            f"  PL background : "
            + ", ".join(f"{LABELS[k].split()[0]}={1e3 * dc[k]:.1f} mV"
                        for k in STAGES),
            "",
            "  per-stage in-band noise (std of 8.4 ms readings):",
        ] + [
            f"    {LABELS[k]:38s}: {1e6 * sig[k]:8.2f} uV"
            for k in STAGES
        ] + [
            "",
            "  BUDGET (quadrature attribution -> equivalent field noise):",
        ] + [
            f"    {name:44s}: {uv:8.2f} uV  = {nt:10.1f} nT/reading"
            for name, uv, nt in rows
        ] + [
            "",
            "  reading the table:",
            "    * the LAST line divided by sqrt(8.4 ms) is your per-root-Hz",
            "      sensitivity; every line above shows who is responsible.",
            "    * 'on-slope excess' is the only genuinely magnetic part",
            "      (field noise + resonance jitter incl. temperature/strain).",
            "    * if 'laser intensity' dominates -> intensity stabilisation /",
            "      normalise R by the DC level; if 'MW chain' -> check cable",
            "      routing & amplifier; if 'electronics' -> more optical power",
            "      or PD gain; if 'ambient light' -> shielding/darkness.",
        ]
        summary = "\n".join(lines)
        print("\n" + summary)
        with open(os.path.join(DATA_DIR, "noise_budget.txt"), "w") as f:
            f.write(summary + "\n")
        np.savez(os.path.join(DATA_DIR, "noise_budget.npz"),
                 stamp=stamp, f_star=f_star, slope=slope, dRdB=dRdB,
                 f_mod=F_MOD, fs=FS_HZ,
                 **{f"{k}_{q}": data[k][q] for k in STAGES
                    for q in ("R", "dc", "raw", "wb")})

        # ---- figure: budget bars + per-stage wideband PSDs ----
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
            names = [r[0] for r in rows[:-1]]
            vals = [r[1] for r in rows[:-1]]
            ax1.barh(range(len(names)), vals, color="tab:blue")
            ax1.set_yticks(range(len(names)))
            ax1.set_yticklabels(names, fontsize=8)
            ax1.axvline(rows[-1][1], color="tab:red", ls="--", lw=1,
                        label=f"total {rows[-1][1]:.1f} uV")
            ax1.set_xlabel("in-band noise contribution (uV per reading)")
            ax1.set_title("Noise budget")
            ax1.legend(fontsize=8)
            ax1.grid(alpha=0.3, axis="x")
            for k, c in zip(STAGES, ("C3", "C1", "C2", "C7", "k")):
                d = data[k]
                fr_, asd = welch_asd(d["wb"] - np.mean(d["wb"]),
                                     1.0 / d["fs_wb"], n_seg=8)
                ax2.loglog(fr_[1:], asd[1:], lw=0.8, color=c,
                           label=LABELS[k], alpha=0.85)
            ax2.axvline(F_MOD, color="0.5", ls=":", lw=1)
            ax2.set_xlabel("frequency (Hz)")
            ax2.set_ylabel(r"photodiode ASD (V/$\sqrt{Hz}$)")
            ax2.set_title("Per-stage noise spectra (dotted line = f_mod)")
            ax2.legend(fontsize=7)
            ax2.grid(alpha=0.3, which="both")
            fig.tight_layout()
            fig.savefig(os.path.join(DATA_DIR, "noise_budget.png"), dpi=150)
            print(f"\nSaved figure -> "
                  f"{os.path.join(DATA_DIR, 'noise_budget.png')}")
        except Exception as e:
            print(f"(figure skipped: {e})")

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
