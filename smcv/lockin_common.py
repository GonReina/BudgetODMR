"""
Shared lock-in ODMR engine (PC-controlled), used by odmr_lockin_am_pc.py and
odmr_lockin_fm_pc.py.

Idea: instead of dwelling and DC-averaging at each frequency (slow, and swamped by
laser 1/f + mains noise), modulate the microwaves at f_mod (a few kHz) and detect
the photodiode's response AT that frequency with a software lock-in. Because the
detection band is a narrow window around f_mod -- far above mains and 1/f -- the
noise floor is tiny, so each point needs only a few ms instead of ~100 ms, and the
separate MW-off measurement is gone.

Signal path (no modulation cable):
    The SMCV modulates ITSELF using its internal LF generator (K197 AM/FM/PhiM):
    AM-internal (am wrapper) or FM-internal (fm wrapper) at F_MOD. The Red Pitaya
    only reads the photodiode on IN1 and demodulates against its own reference at
    the known F_MOD -- a magnitude lock-in is phase-independent, so no physical
    modulation/reference cable is needed. (The SMCV's "User" BNC connectors are
    trigger/marker only; there is no external-modulation input to wire to.)
    Photodiode --> Red Pitaya IN1.

The Red Pitaya's own SCPI server (port 5000) does the IN1 acquisition;
demodulation is done here in numpy. Uses a magnitude lock-in
R = sqrt(X^2 + Y^2), which is phase-independent (no need to phase-lock OUT1 to the
capture). For AM, R vs frequency is the ODMR line (a peak in contrast). For FM, R
is the |derivative| of the line (two lobes with a null at the centre).

Run the AM or FM wrapper, not this file directly.
"""

import os
import time
from datetime import datetime

import numpy as np

from expconfig import load_config
from odmr_smcv100b_pc import SMCV100B, Scpi, frange
from redpitaya_scope import RedPitayaScope

_cfg = load_config()
_i, _s, _p, _l = _cfg["instruments"], _cfg["sweep"], _cfg["paths"], _cfg["lockin"]

SMCV_IP, SMCV_PORT = _i["smcv_ip"], _i["smcv_port"]
RP_IP,   RP_PORT   = _i["rp_ip"],   _i["rp_port"]
F_START, F_STOP, F_STEP = _s["f_start_mhz"], _s["f_stop_mhz"], _s["f_step_mhz"]
POWER_DBM = _s["power_dbm"]
N_SWEEPS  = _s["n_sweeps"]
RP_GAIN   = _cfg["redpitaya"]["input_gain"]
N_BUF     = _cfg["redpitaya"]["n_buf"]

F_MOD      = _l["f_mod_hz"]
MOD_VOLT   = _l["mod_out_volt"]
DECIM      = _l["decimation"]
SETTLE_S   = _l["settle_s"]
AM_DEPTH   = _l["am_depth_pct"]
FM_DEV_HZ  = _l["fm_deviation_khz"] * 1e3
FS_HZ      = 125e6 / DECIM
DATA_DIR   = _p["data_dir"]
REF_GAIN   = "HV"          # IN2 (LF reference) input jumper, used only by fm_deriv


class RedPitayaLockin:
    """Photodiode acquisition for the lock-in, via the universal RedPitayaScope
    (correct fill-synchronised sequence -- no stale/zero buffers)."""

    def __init__(self, ip, port):
        self.scope = RedPitayaScope(ip, port)
        print(f"Red Pitaya SCPI server reachable at {ip}:{port}")

    def acquire_in1(self):
        return self.scope.acquire((1,), DECIM, RP_GAIN)

    def acquire_both(self):
        # IN1 = photodiode (RP_GAIN), IN2 = LF reference for fm_deriv (REF_GAIN)
        return self.scope.acquire((1, 2), DECIM, {1: RP_GAIN, 2: REF_GAIN})

    def close(self):
        self.scope.close()


def detect_fmod(v, fs, f_nominal, lo=300.0, hi=30000.0):
    """Find the actual modulation tone in v: the strongest FFT bin in [lo,hi] Hz.
    This makes the lock-in immune to the exact SMCV LF frequency -- whatever
    modulation is present in the signal is what we demodulate against. Falls back
    to f_nominal if nothing is found in the band."""
    n = len(v)
    if n < 8:
        return f_nominal
    spec = np.abs(np.fft.rfft((v - np.mean(v)) * np.hanning(n)))
    fr = np.fft.rfftfreq(n, 1.0 / fs)
    band = (fr >= lo) & (fr <= min(hi, 0.45 * fs))
    if not band.any() or spec[band].max() <= 0:
        return f_nominal
    return float(fr[band][int(np.argmax(spec[band]))])


def demodulate(v, fs, f_mod):
    """Magnitude lock-in R = sqrt(X^2+Y^2) at the FIXED, known modulation frequency
    f_mod. This must be fixed, not auto-detected from IN1: the AM/FM response tone
    only appears in the photodiode ON resonance, so there is nothing to detect off
    resonance. Demodulating at the known SMCV LF frequency gives ~0 off resonance
    (correct baseline) and the peak on resonance."""
    n = len(v)
    t = np.arange(n) / fs
    w = np.hanning(n)
    norm = np.sum(w)
    x = 2.0 * np.sum(v * np.cos(2 * np.pi * f_mod * t) * w) / norm
    y = 2.0 * np.sum(v * np.sin(2 * np.pi * f_mod * t) * w) / norm
    return float(np.hypot(x, y))


def demodulate_signed(v_sig, v_ref, fs, f_nominal):
    """Phase-sensitive lock-in: in-phase amplitude of v_sig referenced to v_ref.
    The reference (IN2 = the LF modulation signal) defines both the frequency (via
    detect_fmod) and the phase, so the SIGN is stable across the sweep -- the
    dispersive FM derivative whose zero-crossing marks the line centre."""
    f_mod = detect_fmod(v_ref, fs, f_nominal)
    m = min(len(v_sig), len(v_ref))
    t = np.arange(m) / fs
    w = np.hanning(m)
    e = np.exp(-1j * 2 * np.pi * f_mod * t) * w
    zs = np.sum(v_sig[:m] * e)
    zr = np.sum(v_ref[:m] * e)
    if abs(zr) == 0:
        return 0.0
    return float((zs * np.conj(zr) / abs(zr)).real)


def setup_smcv_modulation(src, mode):
    """Enable AM/FM. On this SMCV the modulation SOURCE and LF-frequency SCPI
    mnemonics are not accepted, so set those ONCE by hand in the touchscreen
    Modulation menu. The lock-in auto-detects the actual modulation frequency from
    the signal, so the LF frequency you dial in only needs to be roughly in the
    1-10 kHz range -- it need not equal config f_mod_hz exactly."""
    if mode == "am":
        pep = POWER_DBM + 20 * np.log10(1 + AM_DEPTH / 100.0)
        if pep > 16.3:      # SMCV standard max ~+16 dBm (+25 with K31)
            safe = 16.0 - 20 * np.log10(1 + AM_DEPTH / 100.0)
            print(f"  WARNING: AM PEP ~{pep:.1f} dBm exceeds the SMCV max (~+16 dBm) at "
                  f"carrier {POWER_DBM:+.1f} dBm / depth {AM_DEPTH:.0f}%. Lower "
                  f"sweep.power_dbm to <= {safe:+.1f} dBm or reduce lockin.am_depth_pct.")

    print(f"  >> Configure {mode.upper()} ONCE on the SMCV (Modulation menu):")
    if mode == "am":
        print(f"       enable AM, internal modulation source, mod. frequency = {F_MOD:.0f} Hz, "
              f"depth {AM_DEPTH:.0f} %.")
    else:
        print(f"       enable FM, internal modulation source, mod. frequency = {F_MOD:.0f} Hz, "
              f"deviation {FM_DEV_HZ/1e6:.2f} MHz.")
    print(f"     The modulation frequency MUST equal config f_mod_hz ({F_MOD:.0f} Hz) so the "
          f"lock-in demodulates at the right frequency.")

    # Enable whatever modulation is configured in the menu. The master modulation
    # switch IS a valid SCPI command on the SMCV (unlike :AM:SOURce / :LFOutput,
    # whose command tree differs on this model -- see rssmcv.readthedocs.io).
    try:
        src.s.write(":SOURce:MODulation:ALL:STATe ON")
        src.s.query("*OPC?")
        st = src.s.query(":SOURce:MODulation:ALL:STATe?").strip()
        if st not in ("1", "ON"):
            print(f"  NOTE: modulation master state reads '{st}' -- enable {mode.upper()} "
                  f"in the Modulation menu.")
    except Exception as e:
        print(f"  (couldn't toggle modulation over SCPI: {e}; enable it in the menu.)")


def teardown_smcv_modulation(src, mode):
    try:
        src.s.write(":SOURce:MODulation:ALL:STATe OFF")
        src.s.query("*OPC?")
    except Exception:
        pass


def run(mode):
    """mode: 'am' (magnitude, peak), 'fm' (magnitude, |derivative| null),
    or 'fm_deriv' (phase-sensitive, signed dispersive derivative; needs the SMCV
    LF-generator signal on Red Pitaya IN2 as the reference)."""
    assert mode in ("am", "fm", "fm_deriv")
    mod_mode = "fm" if mode == "fm_deriv" else mode
    signed = mode == "fm_deriv"
    freqs = list(frange(F_START, F_STOP, F_STEP))
    runs_dir = os.path.join(DATA_DIR, _l["runs_subdir"] + "_" + mode)
    avg_file = os.path.join(DATA_DIR, f"odmr_lockin_{mode}_average.csv")
    os.makedirs(runs_dir, exist_ok=True)

    pt_ms = N_BUF / FS_HZ * 1e3
    print(f"LOCK-IN {mode.upper()} ODMR: {F_START}-{F_STOP} MHz / {F_STEP} "
          f"({len(freqs)} pts), {N_SWEEPS} sweeps, {POWER_DBM:+.1f} dBm")
    print(f"  f_mod={F_MOD:.0f} Hz, ~{pt_ms:.0f} ms/point (dec {DECIM}), "
          f"{'depth '+str(AM_DEPTH)+'%' if mod_mode=='am' else 'dev '+str(FM_DEV_HZ/1e6)+' MHz'}")
    if signed:
        print("  fm_deriv: connect the SMCV LF-generator output to Red Pitaya IN2.")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, mod_mode)
    src.output(True)

    rp = RedPitayaLockin(RP_IP, RP_PORT)
    if signed:
        # fm_deriv: IN2 carries the LF reference, which is present at every point,
        # so we can detect + demodulate against its exact frequency.
        ref = rp.acquire_both()[1]
        probe = detect_fmod(ref, FS_HZ, F_MOD)
        print(f"  IN2 reference tone = {probe:.0f} Hz (demodulating against IN2).")
    else:
        print(f"  demodulating at FIXED f_mod = {F_MOD:.0f} Hz.")
        print(f"  -> set the SMCV internal LF frequency to {F_MOD:.0f} Hz so they match "
              f"(off resonance the lock-in reads ~0; the peak appears on resonance).")

    sig_label = "lockin_X_signed" if signed else "lockin_R"
    running = [0.0] * len(freqs)
    completed = 0
    try:
        for run_i in range(1, N_SWEEPS + 1):
            path = os.path.join(runs_dir, f"run_{run_i:02d}.csv")
            with open(path, "w") as f:
                f.write(f"# lock-in {mode} ODMR, {datetime.now().isoformat(timespec='seconds')}\n")
                f.write(f"# f_mod_Hz={F_MOD} power_dBm={POWER_DBM} signal={sig_label}\n")
                f.write("freq_MHz,signal\n")
                for idx, fr in enumerate(freqs):
                    src.set_freq_mhz(fr)
                    time.sleep(SETTLE_S)
                    if signed:
                        s1, s2 = rp.acquire_both()
                        val = demodulate_signed(s1, s2, FS_HZ, F_MOD)
                    else:
                        val = demodulate(rp.acquire_in1(), FS_HZ, F_MOD)
                    f.write(f"{fr:.5f},{val:.8f}\n")
                    running[idx] += val
            completed += 1
            with open(avg_file, "w") as f:
                f.write(f"# running average over {completed} sweep(s), signal={sig_label}\n")
                f.write("freq_MHz,signal\n")
                for idx, fr in enumerate(freqs):
                    f.write(f"{fr:.5f},{running[idx]/completed:.8f}\n")
            print(f"  sweep {run_i}/{N_SWEEPS} -> {avg_file}")
        print(f"\nDone. {completed} sweeps -> {avg_file}")
    except KeyboardInterrupt:
        print(f"\nStopped after {completed} sweep(s). Average in {avg_file}")
    finally:
        rp.close()
        teardown_smcv_modulation(src, mod_mode)
        src.close()


# ============================================================================
# Interactive magnet scan (lock-in): type a position, sweep, repeat
# ============================================================================
_MAG = load_config()["magnet"]


def _measure(src, rp, freq, signed):
    src.set_freq_mhz(freq)
    time.sleep(SETTLE_S)
    if signed:
        s1, s2 = rp.acquire_both()
        return demodulate_signed(s1, s2, FS_HZ, F_MOD)
    return demodulate(rp.acquire_in1(), FS_HZ, F_MOD)


def _beep():
    try:
        import winsound
        for f, d in [(784, 120), (1047, 120), (784, 120), (1319, 260)]:
            winsound.Beep(f, d)
    except Exception:
        try:
            print("\a\a\a", end="", flush=True)
        except Exception:
            pass


def run_magnet(mode):
    """Interactive lock-in magnet scan. Type a magnet position, it runs a lock-in
    sweep at that position and saves it, then asks for the next; q/blank to quit.
    Files: <magnet.out_dir>_<mode>/pos_XX.csv + magnet_index.csv."""
    import glob
    assert mode in ("am", "fm", "fm_deriv")
    mod_mode = "fm" if mode == "fm_deriv" else mode
    signed = mode == "fm_deriv"
    freqs = list(frange(F_START, F_STOP, F_STEP))
    n_per = _MAG["n_sweeps_per_pos"]
    units = _MAG["position_units"]
    out_dir = _MAG["out_dir"] + "_" + mode
    index_file = os.path.join(out_dir, "magnet_index.csv")
    os.makedirs(out_dir, exist_ok=True)
    start_idx = len(glob.glob(os.path.join(out_dir, "pos_*.csv")))

    print(f"MAGNET lock-in scan ({mode}): {F_START}-{F_STOP} MHz / {F_STEP} "
          f"({len(freqs)} pts), {n_per} sweep(s)/position -> {out_dir}")

    src = SMCV100B(SMCV_IP, SMCV_PORT)
    src.configure(POWER_DBM)
    setup_smcv_modulation(src, mod_mode)
    src.output(True)
    rp = RedPitayaLockin(RP_IP, RP_PORT)

    new_index = not os.path.exists(index_file) or os.path.getsize(index_file) == 0
    index = open(index_file, "a")
    if new_index:
        index.write("idx,position,units,filename,timestamp,mode\n")
        index.flush()

    k = start_idx
    try:
        while True:
            s = input(f"\nMagnet position ({units}), q to quit: ").strip()
            if s.lower() in ("", "q", "quit", "exit"):
                break
            try:
                pos = float(s)
            except ValueError:
                print("  not a number -- try again")
                continue
            acc = [0.0] * len(freqs)
            for sweep in range(1, n_per + 1):
                for i, fr in enumerate(freqs):
                    acc[i] += _measure(src, rp, fr, signed)
                print(f"    sweep {sweep}/{n_per} done")
            sig = [a / n_per for a in acc]

            fname = f"pos_{k:02d}.csv"
            ts = datetime.now().isoformat(timespec="seconds")
            with open(os.path.join(out_dir, fname), "w") as f:
                f.write(f"# magnet lock-in {mode}, position={pos} {units}, {ts}\n")
                f.write(f"# f_mod_Hz={F_MOD} power_dBm={POWER_DBM} sweeps={n_per}\n")
                f.write("freq_MHz,signal\n")
                for fr, v in zip(freqs, sig):
                    f.write(f"{fr:.5f},{v:.8f}\n")
            index.write(f"{k},{pos},{units},{fname},{ts},{mode}\n")
            index.flush()
            print(f"  saved {fname} (position {pos} {units})")
            _beep()
            k += 1
        print(f"\nDone. {k - start_idx} position(s) this session -> {out_dir}")
    except KeyboardInterrupt:
        print(f"\nStopped. {k - start_idx} position(s) -> {out_dir}")
    finally:
        index.close()
        rp.close()
        teardown_smcv_modulation(src, mod_mode)
        src.close()
