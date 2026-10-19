"""
Interactive hyperfine checker for odmr_positions_pc.py data.

For each position shows the ODMR spectrum and lets you place edge markers on
the hyperfine features by clicking:

  Left-click (1st, 3rd, ...): green dashed line  -- left edge of a feature
  Left-click (2nd, 4th, ...): red dashed line    -- right edge; prints width
  Right-click                : undo last marker

Close the window to move to the next position. A summary is printed at the
end and saved as <run_dir>/hf_widths.txt, together with annotated PNG figures.

Run:  python plot_odmr_positions_hf.py [run_dir]
      (default: newest <data_dir>/positions_*)
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


def interactive_hf(fig, ax, label):
    """Block until the figure is closed; return list of (f_left, f_right, width)."""
    clicks = []    # x-coordinates of all clicks so far
    artists = []   # parallel to clicks: (vline, [extra_artists]) per click
    features = []  # completed (f_left, f_right) pairs

    def update_title():
        next_side = "LEFT edge (green)" if len(clicks) % 2 == 0 else "RIGHT edge (red)"
        ax.set_title(
            f"{label}\n"
            f"Left-click: {next_side}  |  Right-click: undo  |  "
            f"Close window to finish  ({len(features)} feature(s) marked)",
            fontsize=9,
        )
        fig.canvas.draw_idle()

    def on_click(event):
        if event.inaxes != ax or event.xdata is None:
            return

        if event.button == 3:  # right-click: undo last marker
            if not clicks:
                return
            clicks.pop()
            vl, extras = artists.pop()
            vl.remove()
            for e in extras:
                e.remove()
            # if the removed click was a right edge (len now odd), drop last feature
            if len(clicks) % 2 == 1 and features:
                features.pop()
            update_title()
            return

        # left-click: place marker
        x = event.xdata
        is_left = (len(clicks) % 2 == 0)
        color = "green" if is_left else "crimson"
        vl = ax.axvline(x, color=color, lw=1.2, ls="--", alpha=0.85)
        extras = []
        clicks.append(x)

        if not is_left:
            xl, xr = sorted([clicks[-2], clicks[-1]])
            width = xr - xl
            centre = 0.5 * (xl + xr)
            features.append((xl, xr))
            span = ax.axvspan(xl, xr, alpha=0.12, color="steelblue")
            txt = ax.text(
                centre, 0.02, f"{width:.2f} MHz",
                fontsize=7, color="steelblue", ha="center", va="bottom",
                transform=ax.get_xaxis_transform(),
            )
            extras = [span, txt]
            print(f"  feature {len(features)}: "
                  f"{xl:.3f} -- {xr:.3f} MHz  |  width = {width:.3f} MHz  |  "
                  f"centre = {centre:.3f} MHz")

        artists.append((vl, extras))
        update_title()

    cid = fig.canvas.mpl_connect("button_press_event", on_click)
    update_title()
    plt.show(block=True)
    fig.canvas.mpl_disconnect(cid)
    return [(xl, xr, xr - xl) for xl, xr in features]


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

    all_results = []
    for p in files:
        meta, c = read(p)
        n = int(meta.get("n_sweeps", 1))
        sem = c["std"] / np.sqrt(n) if n > 1 else np.zeros_like(c["std"])
        pos_label = meta.get("label", os.path.basename(p)[:-4])
        label = f"pos {meta.get('position', '?')}: {pos_label} ({n} sweep{'s' if n != 1 else ''})"

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.errorbar(c["freq_MHz"], c["signal"], yerr=sem, fmt=".-", ms=3, lw=0.8,
                    capsize=1.5, elinewidth=0.6, color="C0")
        ax.set(xlabel="MW frequency (MHz)", ylabel="PL_on / PL_off")
        ax.grid(alpha=0.3)
        fig.tight_layout(rect=[0, 0, 1, 0.88])  # leave room for two-line title

        print(f"\n{'=' * 60}\n{label}")
        features = interactive_hf(fig, ax, label)

        out = os.path.join(run_dir, "hf_" + os.path.basename(p)[:-4] + ".png")
        try:
            fig.savefig(out, dpi=150, bbox_inches="tight")
            print(f"  saved {os.path.basename(out)}")
        except Exception:
            pass
        plt.close(fig)
        all_results.append((pos_label, features))

    # summary
    print(f"\n{'=' * 60}\nSUMMARY")
    lines = []
    for pos_label, features in all_results:
        if features:
            for i, (xl, xr, w) in enumerate(features, 1):
                line = (f"  {pos_label}  feature {i}:  "
                        f"{xl:.3f} -- {xr:.3f} MHz  "
                        f"width = {w:.3f} MHz  centre = {0.5*(xl+xr):.3f} MHz")
                print(line)
                lines.append(line)
        else:
            line = f"  {pos_label}  (no features marked)"
            print(line)
            lines.append(line)

    out_txt = os.path.join(run_dir, "hf_widths.txt")
    with open(out_txt, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nSaved summary -> {out_txt}")


if __name__ == "__main__":
    main()
