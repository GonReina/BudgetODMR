"""
Plots for odmr_positions_pc.py: one DC ODMR figure per diamond position (mean
of the sweeps, error bars = standard error of the mean, std / sqrt(n)), and one
figure with every position overlaid on the same axes, legend outside.

Output (in the run folder): odmr_pos_<k>_<label>.png, odmr_positions_overlay.png

Run:  python plot_odmr_positions.py [run_dir]   (default: newest <data_dir>/positions_*)
"""

import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from expconfig import load_config


def read(path):
    meta, rows, head = {}, [], None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                k, _, v = line[1:].partition("=")
                meta[k.strip()] = v.strip()
            elif head is None:
                head = line.split(",")
            else:
                rows.append([float(x) for x in line.split(",")])
    a = np.array(rows)
    return meta, {h: a[:, j] for j, h in enumerate(head)}


def main():
    if len(sys.argv) > 1:
        run_dir = sys.argv[1]
    else:
        runs = [r for r in sorted(glob.glob(os.path.join(
            load_config()["paths"]["data_dir"], "positions_*"))) if os.path.isdir(r)]
        if not runs:
            raise SystemExit("No positions_* folder: run odmr_positions_pc.py first.")
        run_dir = runs[-1]
    files = sorted(glob.glob(os.path.join(run_dir, "pos_*.csv")))
    if not files:
        raise SystemExit(f"No pos_*.csv in {run_dir}")

    data = []
    for p in files:
        meta, c = read(p)
        n = int(meta.get("n_sweeps", 1))
        sem = c["std"] / np.sqrt(n) if n > 1 else np.zeros_like(c["std"])
        label = f"{meta.get('label', os.path.basename(p))} ({n} sweeps)"
        data.append((p, label, c["freq_MHz"], c["signal"], sem))

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.errorbar(c["freq_MHz"], c["signal"], yerr=sem, fmt=".-", ms=3, lw=0.8,
                    capsize=1.5, elinewidth=0.6)
        ax.set(xlabel="MW frequency (MHz)", ylabel="PL_on / PL_off",
               title=f"DC ODMR, position {meta.get('position', '?')}: {label}\n"
                     "error bars: standard error of the mean")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        out = os.path.join(run_dir, "odmr_" + os.path.basename(p)[:-4] + ".png")
        fig.savefig(out, dpi=150)
        plt.close(fig)
        print(f"  {os.path.basename(out)}")

    cmap = plt.get_cmap("viridis" if len(data) > 10 else "tab10")
    fig, ax = plt.subplots(figsize=(11, 6))
    for k, (_, label, f, s, e) in enumerate(data):
        col = cmap(k / max(1, len(data) - 1)) if len(data) > 10 else cmap(k)
        ax.errorbar(f, s, yerr=e, fmt=".-", ms=3, lw=0.9, capsize=1.5,
                    elinewidth=0.6, color=col, label=label)
    ax.set(xlabel="MW frequency (MHz)", ylabel="PL_on / PL_off",
           title=f"DC ODMR vs diamond position ({os.path.basename(run_dir)}; "
                 "error bars: standard error of the mean)")
    ax.grid(alpha=0.3)
    ax.legend(title="position", loc="upper left", bbox_to_anchor=(1.01, 1.0),
              fontsize=8, frameon=False)
    out = os.path.join(run_dir, "odmr_positions_overlay.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved {len(data)} position figures and {out}")
    plt.show()


if __name__ == "__main__":
    main()
