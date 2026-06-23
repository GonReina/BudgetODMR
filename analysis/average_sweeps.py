"""
Average the repeated ODMR sweeps produced by redpitaya/odmr_sweep_robust.py
(or odmr_repeat_sweeps.py).

Reads every run_*.csv in RUNS_DIR, groups the photoluminescence values by
frequency, and writes the per-frequency mean (+ standard deviation across runs
and the number of contributing samples) to a single averaged CSV. It plots the
averaged spectrum with a +/-1 sd band and marks the deepest dip (NV resonance).

Two features that matter when the dip is buried in noise:

  * REQUIRE_LOCK -- discard any point whose lock flag (3rd CSV column, written by
    odmr_sweep_robust.py) is 0. Off-lock points sit at the wrong frequency and
    just add scatter. NOTE: this needs lock data, i.e. the sweep must have been
    run with MONITOR_LD = True. If the column is all zeros / missing, filtering
    is skipped with a warning.

  * NORMALIZE_PER_SWEEP -- before averaging, divide each sweep by its own
    baseline (median PL of that sweep). Slow laser-intensity drift between and
    within sweeps is the usual reason the std dev looks huge; normalising makes
    every sweep comparable so drift cancels instead of averaging in. The dip then
    shows as a fractional drop below 1.0.

Edit CONFIGURATION and run on your PC:  python3 average_sweeps.py
Requires matplotlib:  pip install matplotlib
"""

import csv
import glob
import math
import os

import matplotlib.pyplot as plt

# ===== CONFIGURATION =====
DATA_DIR   = r"D:\data"
RUNS_DIR   = os.path.join(DATA_DIR, "odmr_runs")
RUNS_GLOB  = "run_*.csv"
OUTPUT_CSV = os.path.join(DATA_DIR, "odmr_average.csv")
SAVE_FIG   = os.path.join(DATA_DIR, "odmr_average.png")   # None to skip saving

REQUIRE_LOCK        = True    # drop points with lock flag == 0 (needs MONITOR_LD=True sweeps)
NORMALIZE_PER_SWEEP = True    # divide each sweep by its own median before averaging


def load_spectrum(path):
    """Return list of (freq, pl, ld) rows. ld is None if no 3rd column."""
    rows = []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0].startswith("freq"):
                continue
            fr = float(row[0])
            pl = float(row[1])
            ld = int(float(row[2])) if len(row) > 2 and row[2].strip() != "" else None
            rows.append((fr, pl, ld))
    return rows


def median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def main():
    paths = sorted(glob.glob(os.path.join(RUNS_DIR, RUNS_GLOB)))
    if not paths:
        raise SystemExit(f"No '{RUNS_GLOB}' files found in {RUNS_DIR}")
    print(f"Averaging {len(paths)} run(s) from {RUNS_DIR}/")

    # See whether lock data actually exists before trying to filter on it.
    any_ld   = False
    any_lock = False
    sweeps = []
    for p in paths:
        rows = load_spectrum(p)
        sweeps.append((p, rows))
        for _, _, ld in rows:
            if ld is not None:
                any_ld = True
                if ld == 1:
                    any_lock = True

    require_lock = REQUIRE_LOCK
    if require_lock and not any_ld:
        print("  WARNING: no lock column in these files -> can't filter on lock. "
              "Re-run the sweep with MONITOR_LD=True to get lock flags. "
              "Proceeding without lock filtering.")
        require_lock = False
    elif require_lock and not any_lock:
        print("  WARNING: lock flag is 0 at every point (PLL never reported lock, "
              "or LD wire disconnected). Filtering would discard everything, so it "
              "is disabled. Re-run with MONITOR_LD=True and LD wired.")
        require_lock = False

    # Group (optionally normalized) PL by frequency, carrying the lock flag.
    by_freq = {}
    for p, rows in sweeps:
        if NORMALIZE_PER_SWEEP:
            base_src = [pl for _, pl, ld in rows if (ld == 1 or not require_lock)]
            base = median(base_src) if base_src else median([pl for _, pl, _ in rows])
            if not base:
                base = 1.0
        else:
            base = 1.0
        for fr, pl, ld in rows:
            by_freq.setdefault(fr, []).append((pl / base, ld))
        kept = sum(1 for _, _, ld in rows if ld == 1) if any_ld else len(rows)
        print(f"  {os.path.basename(p)}: {len(rows)} points"
              + (f", {kept} locked" if any_ld else ""))

    freqs_all = sorted(by_freq)
    freqs, means, stds, counts = [], [], [], []
    dropped = 0
    for fr in freqs_all:
        vals = [v for v, ld in by_freq[fr]
                if (ld == 1 or not require_lock)]
        if not vals:
            dropped += 1
            continue
        m = sum(vals) / len(vals)
        var = sum((v - m) ** 2 for v in vals) / len(vals)
        freqs.append(fr)
        means.append(m)
        stds.append(math.sqrt(var))
        counts.append(len(vals))

    if not freqs:
        raise SystemExit("All points were filtered out -- nothing to plot.")
    if dropped:
        print(f"  dropped {dropped} frequency point(s) with no locked samples")

    unit = "normalized PL" if NORMALIZE_PER_SWEEP else "Photoluminescence (V)"
    with open(OUTPUT_CSV, "w") as f:
        f.write(f"# averaged ODMR from {len(paths)} runs in {RUNS_DIR}\n")
        f.write(f"# require_lock={require_lock} normalize_per_sweep={NORMALIZE_PER_SWEEP}\n")
        f.write("freq_MHz,pl_mean,pl_std,n_samples\n")
        for fr, m, s, c in zip(freqs, means, stds, counts):
            f.write(f"{fr:.4f},{m:.6f},{s:.6f},{c}\n")
    print(f"Wrote {OUTPUT_CSV}")

    i_dip = min(range(len(means)), key=lambda i: means[i])
    f_dip = freqs[i_dip]
    contrast = (1.0 - means[i_dip]) * 100 if NORMALIZE_PER_SWEEP else None
    if contrast is not None:
        print(f"Deepest dip @ {f_dip:.2f} MHz, depth {contrast:.2f}% below baseline")

    lo = [m - s for m, s in zip(means, stds)]
    hi = [m + s for m, s in zip(means, stds)]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.fill_between(freqs, lo, hi, color="tab:blue", alpha=0.2, label="+/-1 sd")
    ax.plot(freqs, means, "-", lw=1.2, color="tab:blue", label=f"mean of {len(paths)} runs")
    ax.axvline(f_dip, color="tab:red", ls="--", lw=1, label=f"dip @ {f_dip:.2f} MHz")
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel(unit)
    ax.set_title(f"NV centre ODMR (averaged, {len(paths)} runs"
                 + (", lock-filtered" if require_lock else "") + ")")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if SAVE_FIG:
        fig.savefig(SAVE_FIG, dpi=150)
        print(f"Saved {SAVE_FIG}")
    plt.show()


if __name__ == "__main__":
    main()
