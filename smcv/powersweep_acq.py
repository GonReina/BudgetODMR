"""
Shared acquisition machinery for odmr_power_sweep_fm_pc.py and
odmr_power_sweep_dc_pc.py.

Two things live here that both scripts need to get right.

1. TIERED AVERAGING
   Contrast falls roughly in proportion to MW power below saturation, so a flat
   N_AVG spends most of the run polishing the points that were already good and
   leaves the low-power end -- the end that actually pins the Gamma_0 intercept
   -- buried in noise. AVG_SCHEDULE therefore sets N_AVG per power band.

2. SWEEP-LEVEL RESUME
   Every individual sweep is written to its own file under sweeps/<power>/ as
   soon as it is taken, and the combined mean+std file is regenerated after each
   one. So:
     * stopping at any moment loses at most ONE sweep, not a whole power;
     * re-running picks up from the exact sweep it left off;
     * the combined file is always complete and analysable, even mid-run;
     * the individual sweeps are preserved, which is what lets you check for
       drift across a multi-day acquisition afterwards.

   Writes are atomic (temp file + os.replace), so an interruption during the
   write cannot leave a truncated CSV behind.
"""

import os

import numpy as np

# ---------------------------------------------------------------------------
# Tiered averaging: (p_lo_dBm, p_hi_dBm, n_avg), inclusive bounds.
# More averaging where the signal is weakest.
# ---------------------------------------------------------------------------
AVG_SCHEDULE = (
    (-15.0, -6.5, 4),
    (-6.0,   1.5, 2),
    (2.0,    9.5,  2),
    (10.0,  16.0,  2),
)
AVG_DEFAULT = 8

# Order in which powers are visited. "desc" (high power first) is the sane
# default for a first run: the strongest signal is acquired first, so you find
# out within minutes whether the setup is working, instead of spending the first
# hour grinding 60 averages at the weakest power in the scan. Switch to "asc"
# only if you have a reason to.
POWER_ORDER = "desc"


def n_avg_for(p, schedule=None, default=None):
    """N_AVG for a given power.

    The schedule is looked up at CALL time, not bound as a default argument --
    otherwise reassigning AVG_SCHEDULE (from a test, or another module) would
    silently have no effect.
    """
    schedule = AVG_SCHEDULE if schedule is None else schedule
    default = AVG_DEFAULT if default is None else default
    for lo, hi, n in schedule:
        if lo - 1e-9 <= p <= hi + 1e-9:
            return n
    return default


def power_list(start, stop, step):
    n = int(round((stop - start) / step)) + 1
    return [round(start + k * step, 2) for k in range(n)]


# ---------------------------------------------------------------------------
# Paths.  Note the filename uses a signed, zero-padded field so it is readable;
# it does NOT sort lexicographically once negative powers are involved, so the
# plotting scripts sort by the PARSED power instead.
# ---------------------------------------------------------------------------
def combined_path(out_dir, p):
    return os.path.join(out_dir, f"sweep_{p:+06.2f}dBm.csv")


def sweeps_dir(out_dir, p):
    return os.path.join(out_dir, "sweeps", f"p{p:+06.2f}")


def count_existing(out_dir, p):
    d = sweeps_dir(out_dir, p)
    if not os.path.isdir(d):
        return 0
    return len([f for f in os.listdir(d)
                if f.startswith("s") and f.endswith(".csv")])


def _atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def save_single_sweep(out_dir, p, index, freqs, values):
    d = sweeps_dir(out_dir, p)
    os.makedirs(d, exist_ok=True)
    body = "freq_MHz,signal\n" + "".join(
        f"{fr:.5f},{v:.8f}\n" for fr, v in zip(freqs, values))
    _atomic_write(os.path.join(d, f"s{index:04d}.csv"), body)


def load_all_sweeps(out_dir, p, n_points):
    """-> (n_sweeps, array of shape (n_sweeps, n_points)). Skips malformed files."""
    d = sweeps_dir(out_dir, p)
    if not os.path.isdir(d):
        return 0, np.zeros((0, n_points))
    rows = []
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith("s") and fn.endswith(".csv")):
            continue
        vals = []
        try:
            with open(os.path.join(d, fn)) as fh:
                for line in fh:
                    if line.startswith("freq") or line.startswith("#"):
                        continue
                    parts = line.split(",")
                    if len(parts) >= 2:
                        vals.append(float(parts[1]))
        except Exception:
            continue
        if len(vals) == n_points:
            rows.append(vals)
    if not rows:
        return 0, np.zeros((0, n_points))
    return len(rows), np.asarray(rows, dtype=float)


def write_combined(out_dir, p, freqs, header_lines):
    """Rebuild the mean+std file for one power from every sweep on disk.

    Returns the number of sweeps that went into it.
    """
    n, arr = load_all_sweeps(out_dir, p, len(freqs))
    if n == 0:
        return 0
    mean = arr.mean(axis=0)
    std = arr.std(axis=0, ddof=1) if n > 1 else np.zeros(len(freqs))
    body = "".join(f"# {h}\n" for h in header_lines)
    body += f"# power_dBm={p:.2f} n_avg={n}\n"
    body += "freq_MHz,signal,signal_std\n"
    body += "".join(f"{fr:.5f},{m:.8f},{s:.8f}\n"
                    for fr, m, s in zip(freqs, mean, std))
    _atomic_write(combined_path(out_dir, p), body)
    return n


# ---------------------------------------------------------------------------
def plan(powers, n_points, pt_s, out_dir):
    """Report what is already done and what is left. -> (todo, est_seconds)."""
    todo, done_sweeps, total_sweeps = [], 0, 0
    ordered = sorted(powers, reverse=(POWER_ORDER == "desc"))
    for p in ordered:
        want = n_avg_for(p)
        have = count_existing(out_dir, p)
        total_sweeps += want
        done_sweeps += min(have, want)
        if have < want:
            todo.append((p, have, want))
    remaining = sum(w - h for _, h, w in todo)
    return todo, remaining, done_sweeps, total_sweeps, remaining * n_points * pt_s


def print_plan(powers, n_points, pt_s, out_dir, label):
    todo, remaining, done, total, est = plan(powers, n_points, pt_s, out_dir)
    print(f"\n{label}")
    print(f"  power grid : {powers[0]:+.1f} to {powers[-1]:+.1f} dBm, "
          f"{len(powers)} points")
    print(f"  averaging  : " + ", ".join(
        f"[{lo:+.1f},{hi:+.1f}] x{n}" for lo, hi, n in AVG_SCHEDULE))
    print(f"  order      : {POWER_ORDER} "
          f"({'high power first' if POWER_ORDER == 'desc' else 'low power first'})")
    print(f"  sweeps     : {done}/{total} done, {remaining} remaining")
    if remaining:
        print(f"  estimated  : {est/3600:.1f} h ({est/86400:.2f} days) left")
    else:
        print("  nothing left to do -- every power already has its full N_AVG.")
    return todo
