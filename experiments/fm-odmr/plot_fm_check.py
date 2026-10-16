"""
Analyse fm_check_pc.py: does FM help, and at which modulation frequency?

For every f_mod (fm_<f>Hz.npz) the photodiode records are turned into a
power spectrum (Hann window, averaged over the records), ON resonance (the
park point) and OFF resonance (pickup check). From it:

  tone      A_rms of the line at f_mod (exact frequency found near the nominal
            one), also at 2 f_mod, and the same bin OFF resonance;
  floor     the noise ASD around f_mod (median of 0.85-1.15 f_mod without the
            tone);
  SNR_1s_ideal     = sqrt(2) A_rms / floor: the SNR a lock-in reaches in 1 s of
                     continuous acquisition;
  SNR_1s_measured  = mean/std of the per-record lock-in magnitude, scaled to
                     1 s of WALL-CLOCK time (includes the Red Pitaya transfer
                     dead time): what this rig really gets.

These are compared with the DC benchmark of step 1 (MW off/on readings at the
dip, scaled to 1 s): FM helps where its SNR_1s is above the DC line. A tone OFF
resonance comparable to ON means the "signal" is electrical pickup, not ODMR.

Output (in the run folder):
  fm_check_<f>Hz.png      per f_mod: full spectrum and a zoom around f_mod, with SNR
  fm_check_raster.png     all f_mod as rows of power spectra (on and off resonance)
  fm_check_summary.png    DC ODMR + park point, SNR vs f_mod, tone on/off
  fm_check_summary.csv, fm_check_summary.txt

Run:  python plot_fm_check.py [run_dir]     (default: newest <data_dir>/fm_check_*)
"""

import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from expconfig import load_config

TONE_BINS = 3          # Hann main lobe: sum the PSD over +/- 3 bins
FLOOR_BAND = 0.15      # floor from f_mod * (1 +/- 0.15) ...
FLOOR_EXCL_BINS = 8    # ... without +/- 8 bins around the tone
SEARCH_FRAC = 0.03     # look for the tone within +/- 3 % of the nominal f_mod


def read_meta(path):
    meta = {}
    with open(path) as f:
        for line in f:
            if not line.startswith("#"):
                break
            k, _, v = line[1:].strip().partition("=")
            meta[k.strip()] = v.strip()
    return meta


def psd(rec, fs):
    """One-sided PSD (V^2/Hz) averaged over the records, Hann window."""
    rec = rec - rec.mean(axis=1, keepdims=True)
    w = np.hanning(rec.shape[1])
    p = 2 * np.abs(np.fft.rfft(rec * w, axis=1)) ** 2 / (fs * np.sum(w ** 2))
    return np.fft.rfftfreq(rec.shape[1], 1 / fs), p.mean(axis=0)


def tone(fr, p, f0, find=True):
    """(A_rms, exact frequency) of the line near f0."""
    df = fr[1]
    j = int(round(f0 / df))
    if find:
        m = np.flatnonzero(np.abs(fr - f0) <= max(SEARCH_FRAC * f0, 2 * df))
        j = int(m[np.argmax(p[m])])
    sl = slice(max(1, j - TONE_BINS), j + TONE_BINS + 1)
    return float(np.sqrt(p[sl].sum() * df)), float(fr[j])


def floor(fr, p, f0):
    df = fr[1]
    width = max(FLOOR_BAND * f0, (FLOOR_EXCL_BINS + 10) * df)   # low f_mod: >= 10 bins
    m = (np.abs(fr - f0) <= width) & (np.abs(fr - f0) > FLOOR_EXCL_BINS * df)
    return float(np.sqrt(np.median(p[m]))) if m.any() else np.nan


def lockin_mags(rec, fs, f0):
    """Per-record lock-in magnitude (peak V), at the frequency (within +/- 1 bin
    of f0) that maximises the mean power: a 30 Hz bin error would otherwise
    smear the phase over a 33 ms record."""
    rec = rec - rec.mean(axis=1, keepdims=True)
    n = rec.shape[1]
    t = np.arange(n) / fs
    w = np.hanning(n)
    grid = f0 + np.linspace(-1, 1, 41) * fs / n
    e = np.exp(-2j * np.pi * np.outer(t, grid)) * w[:, None]
    z = 2 * (rec @ e) / w.sum()
    best = int(np.argmax(np.mean(np.abs(z) ** 2, axis=0)))
    return np.abs(z[:, best])


def analyse(path):
    d = np.load(path, allow_pickle=True)
    fs, fm = float(d["fs"]), float(d["f_mod_nominal_hz"])
    on, off = np.asarray(d["on"], float), np.asarray(d["off"], float)
    contiguous = bool(d["contiguous"]) if "contiguous" in d else False
    if not contiguous:
        # recorded with the old mid-buffer trigger: the two halves are not
        # continuous (phase jump at the seam), so use the post-trigger half only
        h = on.shape[1] // 2
        on, off = on[:, h:], off[:, h:]
    fr, p_on = psd(on, fs)
    _, p_off = psd(off, fs)
    a_on, f_true = tone(fr, p_on, fm)
    a_off, _ = tone(fr, p_off, f_true, find=False)
    a_2f, _ = tone(fr, p_on, 2 * f_true) if 2.2 * f_true < fs / 2 else (np.nan, np.nan)
    n_on = floor(fr, p_on, f_true)
    mags = lockin_mags(on, fs, f_true)
    t_rec = float(d["t_rec_s"])
    return dict(path=path, fs=fs, f_nom=fm, f=f_true, fr=fr, p_on=p_on, p_off=p_off,
                a_on=a_on, a_off=a_off, a_2f=a_2f, floor=n_on, dc=float(on.mean()),
                snr_ideal=np.sqrt(2) * a_on / n_on,
                snr_meas=float(mags.mean() / mags.std(ddof=1) * np.sqrt(1 / t_rec)),                t_rec=t_rec, contiguous=contiguous,
                dev=float(d["deviation_hz"]), park=float(d["park_mhz"]),
                off_mhz=float(d["off_res_mhz"]))


def per_fmod_figure(r, snr_dc, out):
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
    fr = r["fr"]
    for a in ax:
        a.semilogy(fr[1:], np.sqrt(r["p_on"][1:]) * 1e9, lw=0.8,
                   label=f"on resonance ({r['park']:.3f} MHz)")
        a.semilogy(fr[1:], np.sqrt(r["p_off"][1:]) * 1e9, lw=0.8, alpha=0.7,
                   label=f"off resonance ({r['off_mhz']:.0f} MHz)")
        a.axvline(r["f"], color="tab:red", lw=0.7, ls=":")
        a.axvline(2 * r["f"], color="tab:purple", lw=0.7, ls=":")
        a.set(xlabel="frequency (Hz)", ylabel="ASD (nV/rtHz)")
        a.grid(alpha=0.3, which="both")
    ax[0].set_xscale("log")
    ax[0].set_xlim(fr[1], fr[-1])
    ax[0].set_title(f"photodiode spectrum, f_mod = {r['f_nom']:.0f} Hz "
                    f"(red f_mod, purple 2 f_mod)")
    ax[0].legend(fontsize=8)
    half = 0.25 * r["f"]
    ax[1].set_xlim(r["f"] - half, r["f"] + half)
    ax[1].axhline(r["floor"] * 1e9, color="k", ls="--", lw=0.8, label="noise floor")
    ax[1].set_title("zoom around f_mod")
    verdict = "FM beats DC" if r["snr_meas"] > snr_dc else "DC on/off is better"
    txt = (f"tone at {r['f']:.1f} Hz: {r['a_on'] * 1e6:.2f} uV rms\n"
           f"off resonance: {r['a_off'] * 1e6:.2f} uV rms\n"
           f"2 f_mod: {r['a_2f'] * 1e6:.2f} uV rms\n"
           f"floor: {r['floor'] * 1e9:.0f} nV/rtHz\n"
           f"SNR 1 s ideal: {r['snr_ideal']:.1f}\n"
           f"SNR 1 s measured: {r['snr_meas']:.1f}\n"
           f"DC on/off SNR 1 s: {snr_dc:.1f}\n-> {verdict}")
    ax[1].text(0.02, 0.97, txt, transform=ax[1].transAxes, va="top", fontsize=8,
               family="monospace", bbox=dict(fc="white", alpha=0.85))
    ax[1].legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def raster_figure(res, out):
    fr = res[0]["fr"]
    if any(len(r["fr"]) != len(fr) for r in res):
        print("  (records of different lengths: raster skipped)")
        return
    y = np.arange(len(res))
    on = np.array([10 * np.log10(r["p_on"][1:]) for r in res])
    off = np.array([10 * np.log10(r["p_off"][1:]) for r in res])
    both = np.concatenate([on, off])
    vmin, vmax = np.percentile(both, 5), both.max()
    fig, ax = plt.subplots(1, 2, figsize=(15, max(4.0, 0.45 * len(res) + 2)),
                           sharey=True)
    for a, img, name in ((ax[0], on, "ON resonance"), (ax[1], off, "OFF resonance")):
        im = a.pcolormesh(fr[1:], y, img, cmap="magma", vmin=vmin, vmax=vmax,
                          shading="nearest", rasterized=True)
        # f_mod marked by a small tick at the top edge of each row, not on the tone
        a.plot([r["f"] for r in res], y + 0.42, "cv", ms=5)
        a.set_xscale("log")
        a.set_xlim(fr[2], fr[-1])
        a.set(xlabel="frequency (Hz)", title=f"power spectra, {name} (cyan: f_mod)")
    ax[0].set_yticks(y, [f"{r['f_nom']:.0f} Hz" for r in res])
    ax[0].set_ylabel("SMCV FM modulation frequency")
    fig.colorbar(im, ax=ax, pad=0.01, label="PSD (dB re 1 V^2/Hz)")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main():
    if len(sys.argv) > 1:
        run_dir = sys.argv[1]
    else:
        runs = sorted(glob.glob(os.path.join(load_config()["paths"]["data_dir"],
                                             "fm_check_*")))
        runs = [r for r in runs if os.path.isdir(r)]
        if not runs:
            raise SystemExit("No fm_check_* folder: run fm_check_pc.py first.")
        run_dir = runs[-1]
    meta = read_meta(os.path.join(run_dir, "dc_odmr.csv"))
    dc_arr = np.loadtxt(os.path.join(run_dir, "dc_odmr.csv"), delimiter=",",
                        comments="#", skiprows=len(meta) + 1, ndmin=2)
    dc = dict(zip(("freq_MHz", "signal", "std"), dc_arr.T))
    snr_dc = float(meta.get("dc_snr_1s", "nan"))
    files = sorted(glob.glob(os.path.join(run_dir, "fm_*Hz.npz")))
    res = sorted((analyse(f) for f in files), key=lambda r: r["f_nom"])

    lines = [f"FM CHECK ({os.path.basename(run_dir)}, {meta.get('power_dBm')} dBm)",
             f"  DC ODMR: dip {float(meta['f_dip_MHz']):.3f} MHz, depth "
             f"{100 * float(meta['depth']):.2f} %, FWHM ~{float(meta['fwhm_MHz']):.2f} MHz",
             f"  park ({meta.get('park')}): {float(meta['park_MHz']):.3f} MHz",
             f"  DC on/off benchmark at the dip: SNR in 1 s = {snr_dc:.1f} "
             f"({float(meta['dc_t_pair_s']):.2f} s per off/on pair)", ""]
    if res and not all(r["contiguous"] for r in res):
        lines += ["  OLD acquisition (trigger mid-buffer, phase jump at the seam): "
                  "only the post-trigger HALF of each record is analysed.", ""]
    if res:
        lines += [f"  FM deviation {res[0]['dev'] / 1e3:.0f} kHz",
                  "   f_mod (Hz)  tone on (uV)  off (uV)  2f (uV)  floor (nV/rtHz)"
                  "  SNR1s ideal  SNR1s meas"]
    for r in res:
        per_fmod_figure(r, snr_dc, os.path.join(run_dir,
                                                f"fm_check_{r['f_nom']:05.0f}Hz.png"))
        flag = "  <-- pickup" if r["a_off"] > 0.3 * r["a_on"] else ""
        lines.append(f"  {r['f_nom']:10.0f}  {r['a_on'] * 1e6:12.2f}  "
                     f"{r['a_off'] * 1e6:8.2f}  {r['a_2f'] * 1e6:7.2f}  "
                     f"{r['floor'] * 1e9:15.0f}  {r['snr_ideal']:11.1f}  "
                     f"{r['snr_meas']:10.1f}{flag}")
    if res:
        best = max(res, key=lambda r: r["snr_meas"])
        gain = best["snr_meas"] / snr_dc
        lines += ["", f"  best f_mod (measured): {best['f_nom']:.0f} Hz, SNR in 1 s "
                      f"{best['snr_meas']:.1f} = {gain:.2f} x the DC on/off method "
                      f"-> FM {'HELPS' if gain > 1 else 'does NOT help'} here.",
                  f"  SNR ideal / measured = {best['snr_ideal'] / best['snr_meas']:.1f}: "
                  f"dead time alone gives sqrt(wall time / record) = "
                  f"{np.sqrt(best['t_rec'] / (2 * (len(best['fr']) - 1) / best['fs'])):.1f}; "
                  "much more than that = drift or glitches between records.",
                  f"  noise floor near f_mod: median {np.median([r['floor'] for r in res]) * 1e9:.0f}"
                  " nV/rtHz (a clean run was ~250; much higher = electrical interference, "
                  "check the per-f_mod spectra OFF resonance)"]
        raster_figure(res, os.path.join(run_dir, "fm_check_raster.png"))
        with open(os.path.join(run_dir, "fm_check_summary.csv"), "w") as f:
            f.write(f"# dc_snr_1s={snr_dc}\nf_mod_nominal_Hz,f_mod_Hz,tone_on_Vrms,"
                    "tone_off_Vrms,tone_2f_Vrms,floor_V_per_rtHz,snr_1s_ideal,"
                    "snr_1s_measured,dc_level_V\n")
            for r in res:
                f.write(",".join(f"{v:.6g}" for v in (
                    r["f_nom"], r["f"], r["a_on"], r["a_off"], r["a_2f"], r["floor"],
                    r["snr_ideal"], r["snr_meas"], r["dc"])) + "\n")

    fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))
    ax[0].errorbar(dc["freq_MHz"], dc["signal"], yerr=dc["std"], fmt=".-", ms=3)
    for k, c, name in (("f_dip_MHz", "tab:red", "dip"),
                       ("park_MHz", "tab:green", "park")):
        ax[0].axvline(float(meta[k]), color=c, ls=":", label=f"{name} {float(meta[k]):.3f}")
    ax[0].set(xlabel="MW frequency (MHz)", ylabel="PL_on / PL_off",
              title="DC ODMR (step 1)")
    ax[0].legend(fontsize=8)
    if res:
        f = [r["f_nom"] for r in res]
        ax[1].semilogx(f, [r["snr_ideal"] for r in res], "o-", label="FM ideal (no dead time)")
        ax[1].semilogx(f, [r["snr_meas"] for r in res], "s-", label="FM measured")
        ax[1].axhline(snr_dc, color="k", ls="--", label="DC on/off (measured)")
        ax[1].set(xlabel="f_mod (Hz)", ylabel="SNR in 1 s", title="does FM help?")
        ax[1].legend(fontsize=8)
        ax[2].loglog(f, [r["a_on"] * 1e6 for r in res], "o-", label="tone on resonance")
        ax[2].loglog(f, [r["a_off"] * 1e6 for r in res], "x-", label="same bin off resonance")
        ax[2].loglog(f, [r["a_2f"] * 1e6 for r in res], "^-", label="2 f_mod on resonance")
        ax[2].loglog(f, [r["floor"] * 1e6 for r in res], "k:", label="floor (uV/rtHz)")
        ax[2].set(xlabel="f_mod (Hz)", ylabel="uV rms", title="tone amplitudes")
        ax[2].legend(fontsize=8)
    for a in ax:
        a.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(os.path.join(run_dir, "fm_check_summary.png"), dpi=130)

    summary = "\n".join(lines)
    print(summary)
    with open(os.path.join(run_dir, "fm_check_summary.txt"), "w") as f:
        f.write(summary + "\n")
    print(f"\nSaved figures in {run_dir}")
    plt.show()


if __name__ == "__main__":
    main()
