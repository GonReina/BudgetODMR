"""
WIDEBAND FM sensitivity: field noise spectrum up to ~119 Hz (PC-controlled).

Why the standard script tops out at ~10 Hz: odmr_sensitivity_fm_pc.py produces one
field reading per SCPI round-trip (~50 ms wall-clock), so its field time series is
sampled at ~20 Hz -> PSD Nyquist ~10 Hz. Everything faster is invisible (and
partly aliased).

This version instead captures ONE LONG CONTIGUOUS ADC record per acquisition and
demodulates it OFFLINE in short overlapping blocks:

    decimation 8192  ->  fs = 15259 Hz, one 16384-sample buffer = 1.074 s
    block = 128 samples (8.4 ms, ~180 Hz lock-in bandwidth per point)
    hop   = 64 samples  (50 % overlap)  ->  field samples every 4.19 ms

    => gap-free field series at 238 Hz  =>  PSD from ~2 Hz up to ~119 Hz.

Many such buffers are averaged (Welch across buffers) for a clean spectrum. Mains
pickup at 50/150 Hz is now RESOLVED as spikes instead of aliasing invisibly.

Self-calibration detail: at decimation 8192 the Red Pitaya's decimating average
attenuates the 5 kHz tone (sinc response, ~0.83 at 5 kHz), so V/MHz measured at
the sweep decimation would be wrong here. The script therefore parks at f* and
measures the ratio of the SAME tone seen by both acquisition modes, and rescales
the transduction coefficient -- no assumptions about the RP filter needed.

Caveats:
  * fs = 15.26 kHz puts Nyquist at 7.6 kHz: f_mod (5 kHz) still fits, but the FM
    2nd harmonic (10 kHz) aliases to 5.26 kHz. The 8.4 ms block bandwidth
    (~180 Hz) keeps it out of the demod band; it would only add a small static
    offset anyway. If you change lockin.f_mod_hz, keep it below ~6.5 kHz here.
  * Each buffer's mean field is removed before the PSD (buffers are not phase-
    connected), so this measures the SPECTRUM, not slow drift -- use the standard
    script's Allan analysis for tau > 1 s.

Procedure: sweep (fast, standard decimation) -> pick the working point (same UI
as odmr_sensitivity_fm_pc.py) -> park -> calibrate the mode ratio -> capture
N_BUFFERS wideband records (+ MW-off floor records) -> PSD + summary.

Run on the PC:  python odmr_sensitivity_fm_wb_pc.py
Outputs in <DATA_DIR>: sensitivity_fm_wb_spectrum.csv, _timeseries.csv, _psd.csv,
                       sensitivity_fm_wb_summary.txt
Plot with:      python analysis/plot_sensitivity_fm_wb.py
"""

import os
import time
from datetime import datetime

import numpy as np

from redpitaya_scope import RedPitayaScope
from lockin_common import (RedPitayaLockin, SMCV100B, demodulate,
                           setup_smcv_modulation, teardown_smcv_modulation,
                           frange, SMCV_IP, SMCV_PORT, RP_IP, RP_PORT,
                           F_START, F_STOP, F_STEP, POWER_DBM,
                           F_MOD, SETTLE_S, FS_HZ, DATA_DIR, RP_GAIN)
from odmr_sensitivity_fm_pc import (take_spectrum, find_working_point,
                                    pick_working_point, welch_asd, GAMMA)

# --- wideband acquisition settings (local to this script) ---
DECIM_WB   = 8192                    # -> fs 15259 Hz, buffer 1.074 s
FS_WB      = 125e6 / DECIM_WB
N_SAMP_WB  = RedPitayaScope.N_BUF    # 16384 samples per contiguous record
BLOCK      = 128                     # demod block: 8.4 ms (~180 Hz bandwidth)
HOP        = 64                      # 50 % overlap -> field rate 238 Hz
N_BUFFERS  = 60                      # ~64 s of data (~2 min incl. overhead)
N_FLOOR_BUFFERS = 10                 # MW-off records for the detection floor
N_CAL_READS = 10                     # readings per mode for the ratio calibration
PICK_BY_HAND  = True
PARK_SETTLE_S = 0.5

FS_FIELD = FS_WB / HOP               # field sample rate inside a record
assert F_MOD < 0.43 * FS_WB, (
    f"f_mod = {F_MOD:.0f} Hz is too close to the wideband Nyquist "
    f"({FS_WB / 2:.0f} Hz) -- lower lockin.f_mod_hz or DECIM_WB.")


def block_demod(v, fs=FS_WB, f_mod=F_MOD, block=BLOCK, hop=HOP):
    """Demodulate one contiguous record in overlapping blocks.
    Returns (t_centres_s, R_volts): a gap-free lock-in time series."""
    v = np.asarray(v, float)
    starts = range(0, len(v) - block + 1, hop)
    t = np.array([(s + block / 2) / fs for s in starts])
    R = np.array([demodulate(v[s:s + block], fs, f_mod) for s in starts])
    return t, R


def acquire_wb(rp):
    """One contiguous wideband record from IN1 (1.074 s at 15.26 kHz)."""
    return rp.scope.acquire((1,), DECIM_WB, RP_GAIN, fill_timeout_s=5.0)


def calibrate_mode_ratio(rp):
    """Ratio (wideband tone amplitude) / (standard tone amplitude) at f*.
    Corrects for the RP decimating-average attenuation at f_mod."""
    r_std = np.mean([demodulate(rp.acquire_in1(), FS_HZ, F_MOD)
                     for _ in range(N_CAL_READS)])
    r_wb = np.mean([np.mean(block_demod(acquire_wb(rp))[1]) for _ in range(3)])
    if r_std <= 0:
        raise SystemExit("Calibration failed: no tone at f* in standard mode.")
    return float(r_wb / r_std), float(r_std), float(r_wb)


def main():
    freqs = list(frange(F_START, F_STOP, F_STEP))
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")

    print(f"WIDEBAND FM sensitivity: {F_START}-{F_STOP} MHz, f_mod={F_MOD:.0f} Hz")
    print(f"  wideband: fs={FS_WB:.0f} Hz, {N_SAMP_WB / FS_WB:.2f} s/record, "
          f"block {BLOCK / FS_WB * 1e3:.1f} ms, field rate {FS_FIELD:.0f} Hz "
          f"-> PSD to {FS_FIELD / 2:.0f} Hz")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, "fm")
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    try:
        # ---- 1) fast spectrum (standard decimation) + working point ----
        print("\nStep 1/4: FM spectrum (standard mode)")
        R = take_spectrum(src, rp, freqs)
        spec_path = os.path.join(DATA_DIR, "sensitivity_fm_wb_spectrum.csv")
        with open(spec_path, "w") as f:
            f.write(f"# FM spectrum for wideband sensitivity, {stamp}\n"
                    "freq_MHz,lockin_R\n")
            for fr, r in zip(freqs, R):
                f.write(f"{fr:.5f},{r:.8f}\n")

        f_auto, slope_auto, peak_snr = find_working_point(freqs, R)
        print(f"  auto working point {f_auto:.3f} MHz "
              f"(slope {slope_auto * 1e3:+.4f} mV/MHz, SNR ~ {peak_snr:.1f})")
        if PICK_BY_HAND:
            f_star, slope, hand = pick_working_point(freqs, R, f_auto, slope_auto)
        else:
            f_star, slope, hand = f_auto, slope_auto, False
        picked_tag = "hand-picked" if hand else "auto"
        print(f"  working point ({picked_tag}): {f_star:.3f} MHz")

        # ---- 2) park + mode-ratio calibration ----
        print("\nStep 2/4: parking + wideband/standard calibration")
        src.set_freq_mhz(f_star)
        time.sleep(PARK_SETTLE_S)
        ratio, r_std, r_wb = calibrate_mode_ratio(rp)
        dRdB = abs(slope) * GAMMA * ratio          # V/mT, in WIDEBAND units
        print(f"  tone at f*: standard {r_std * 1e3:.3f} mV, "
              f"wideband {r_wb * 1e3:.3f} mV  -> ratio {ratio:.3f}")
        print(f"  dR/dB (wideband) = {dRdB * 1e3:.4f} mV/mT")
        if not 0.3 < ratio < 1.5:
            print("  WARNING: unexpected mode ratio -- check ACQ averaging / "
                  "signal level before trusting the calibration.")

        # ---- 3) wideband records ----
        print(f"\nStep 3/4: {N_BUFFERS} wideband records (MW on)")
        bufs = []
        t0 = time.perf_counter()
        for k in range(N_BUFFERS):
            _, r = block_demod(acquire_wb(rp))
            bufs.append(r)
            if (k + 1) % 10 == 0:
                print(f"  record {k + 1}/{N_BUFFERS} "
                      f"({(time.perf_counter() - t0) / (k + 1):.1f} s each)")

        print(f"  MW OFF: {N_FLOOR_BUFFERS} floor records")
        src.output(False)
        time.sleep(PARK_SETTLE_S)
        floor_bufs = [block_demod(acquire_wb(rp))[1]
                      for _ in range(N_FLOOR_BUFFERS)]
        src.output(True)

        # ---- 4) analysis ----
        print("\nStep 4/4: analysis")
        dt_f = HOP / FS_WB
        to_nT = 1e6 / dRdB                 # volts / (V/mT) = mT; x1e6 -> nT

        def buf_field_nT(r):
            return (r - np.mean(r)) * to_nT        # per-record mean removed

        # averaged PSD across records (Welch within each, mean of PSDs)
        psds, psds_fl = [], []
        for r in bufs:
            fr_psd, asd = welch_asd(buf_field_nT(r), dt_f, n_seg=3)
            psds.append(asd ** 2)
        for r in floor_bufs:
            _, asd = welch_asd(buf_field_nT(r), dt_f, n_seg=3)
            psds_fl.append(asd ** 2)
        asd = np.sqrt(np.mean(psds, axis=0))
        asd_fl = np.sqrt(np.mean(psds_fl, axis=0))

        band = (fr_psd >= 20.0) & (fr_psd <= 100.0)
        eta_white = float(np.median(asd[band])) / np.sqrt(2)
        sigma_blk = float(np.mean([np.std(buf_field_nT(r)) for r in bufs]))
        i50 = int(np.argmin(np.abs(fr_psd - 50.0)))
        mains_50 = float(asd[i50] / np.median(asd[band]))

        ts_path = os.path.join(DATA_DIR, "sensitivity_fm_wb_timeseries.csv")
        with open(ts_path, "w") as f:
            f.write(f"# wideband parked records at {f_star:.5f} MHz, {stamp}, "
                    f"slope_V_per_MHz={slope:.8e}, mode_ratio={ratio:.6f}, "
                    f"dRdB_V_per_mT={dRdB:.8e}, fs_field_Hz={FS_FIELD:.4f}, "
                    f"picked={picked_tag}\n")
            f.write("buf,t_s,B_nT\n")
            for k, r in enumerate(bufs):
                b = buf_field_nT(r)
                for i, bb in enumerate(b):
                    f.write(f"{k},{(i * dt_f):.5f},{bb:.4f}\n")

        psd_path = os.path.join(DATA_DIR, "sensitivity_fm_wb_psd.csv")
        with open(psd_path, "w") as f:
            f.write(f"# averaged field ASD over {N_BUFFERS} records "
                    f"(+{N_FLOOR_BUFFERS} MW-off), {stamp}\n")
            f.write("freq_Hz,asd_nT_rtHz,asd_floor_nT_rtHz\n")
            for fr_, a, afl in zip(fr_psd, asd, asd_fl):
                f.write(f"{fr_:.4f},{a:.4f},{afl:.4f}\n")

        lines = [
            f"WIDEBAND FM sensitivity summary  ({stamp})",
            f"  working point        : {f_star:.3f} MHz ({picked_tag}), "
            f"slope {slope * 1e3:+.4f} mV/MHz, mode ratio {ratio:.3f}, "
            f"dR/dB {dRdB * 1e3:.4f} mV/mT",
            f"  field series         : {FS_FIELD:.0f} Hz sample rate, "
            f"{N_SAMP_WB / FS_WB:.2f} s/record x {N_BUFFERS} records",
            f"  PSD band             : {fr_psd[1]:.1f} - {fr_psd[-1]:.0f} Hz",
            f"  sensitivity (white)  : {eta_white:.1f} nT/sqrt(Hz) "
            f"(median ASD 20-100 Hz / sqrt(2))",
            f"  per-block noise      : {sigma_blk:.1f} nT rms "
            f"({BLOCK / FS_WB * 1e3:.1f} ms blocks)",
            f"  50 Hz mains line     : {mains_50:.1f}x the white floor "
            f"({asd[i50]:.1f} nT/sqrt(Hz))",
            f"  MW-off floor (white) : "
            f"{float(np.median(asd_fl[band])) / np.sqrt(2):.1f} nT/sqrt(Hz)",
            "",
            "  NOTE: per-record means are removed -> no information below "
            f"~{1.0 / (N_SAMP_WB / FS_WB):.0f} Hz;",
            "  use odmr_sensitivity_fm_pc.py for the slow/Allan side. Field is",
            "  along the NV axis of the chosen line.",
        ]
        summary = "\n".join(lines)
        print("\n" + summary)
        with open(os.path.join(DATA_DIR, "sensitivity_fm_wb_summary.txt"), "w") as f:
            f.write(summary + "\n")
        print(f"\nSaved: {spec_path}\n       {ts_path}\n       {psd_path}")

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        rp.close()
        teardown_smcv_modulation(src, "fm")
        src.close()


if __name__ == "__main__":
    main()
