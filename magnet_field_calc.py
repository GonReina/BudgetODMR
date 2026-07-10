"""
How close does the magnet need to be? -- on-axis field & Zeeman-splitting estimator.

A permanent magnet's field on its axis, at distance z from the pole face, is

    B(z) = (Br/2) * [ (z+L)/sqrt(R^2+(z+L)^2)  -  z/sqrt(R^2+z^2) ]

with Br = remanence, L = magnet length (times the number stacked), R = radius.
Far away this falls off like a dipole, B ~ 1/z^3, so distance matters a LOT.

The NV Zeeman splitting is  df = 2 * gamma * B_parallel , gamma = 28.024 MHz/mT,
where B_parallel is the field PROJECTED onto the NV axis (0..1 of |B| depending on
orientation). This script uses |B| on axis, so it gives the MAXIMUM possible
splitting (perfect alignment); real splitting = that x cos(angle).

You "significantly" resolve two dips once df exceeds roughly your ODMR linewidth
(a couple of MHz at high power, less if you turn the power down). Set the target
below and the script prints/plots the distance where you reach it.

Edit CONFIG and run on the PC:  python magnet_field_calc.py   (needs numpy+matplotlib)
"""

import numpy as np
import matplotlib.pyplot as plt

# ===== CONFIG =====
# NdFeB remanence by grade (Tesla). Pick your magnet's grade.
BR_BY_GRADE = {"N35": 1.17, "N42": 1.30, "N45": 1.35, "N52": 1.44}
GRADE          = "N42"
DIAMETER_MM    = 10.0     # magnet diameter (use the width for a block, approx)
LENGTH_MM      = 10.0     # length of ONE magnet along the field axis
N_STACKED      = 1        # magnets stacked end-to-end (multiplies effective length)

TARGET_SPLIT_MHZ = 3.0    # "significant" splitting you want to resolve (~1-2x linewidth)
GAMMA_MHZ_PER_MT = 28.024


def b_on_axis_mT(z_mm, Br_T, R_mm, L_mm):
    """On-axis flux density (mT) at distance z_mm from the pole face."""
    zL = z_mm + L_mm
    term = zL / np.sqrt(R_mm**2 + zL**2) - z_mm / np.sqrt(R_mm**2 + z_mm**2)
    return 0.5 * Br_T * term * 1e3        # T -> mT


def main():
    Br = BR_BY_GRADE[GRADE]
    R = DIAMETER_MM / 2.0
    L = LENGTH_MM * N_STACKED

    z = np.linspace(1.0, 600.0, 4000)     # 1 mm .. 60 cm
    B = b_on_axis_mT(z, Br, R, L)         # mT
    df = 2 * GAMMA_MHZ_PER_MT * B         # max splitting (MHz), perfect alignment

    # distance where the max splitting crosses the target (interpolate, decreasing df)
    z_target = None
    if df[0] >= TARGET_SPLIT_MHZ >= df[-1]:
        z_target = float(np.interp(TARGET_SPLIT_MHZ, df[::-1], z[::-1]))

    print(f"Magnet: {GRADE} (Br={Br} T), D={DIAMETER_MM} mm, "
          f"L={LENGTH_MM} mm x{N_STACKED} = {L} mm effective")
    print(f"Target splitting: {TARGET_SPLIT_MHZ} MHz "
          f"(= {TARGET_SPLIT_MHZ/(2*GAMMA_MHZ_PER_MT):.3f} mT axial)\n")
    print(f"{'z (cm)':>8} {'|B| (mT)':>10} {'max split (MHz)':>16}")
    for zc in (1, 2, 3, 5, 10, 15, 20, 30, 50):
        b = b_on_axis_mT(zc * 10.0, Br, R, L)
        print(f"{zc:>8} {b:>10.4f} {2*GAMMA_MHZ_PER_MT*b:>16.2f}")
    if z_target is not None:
        print(f"\n-> reach {TARGET_SPLIT_MHZ} MHz splitting at about "
              f"{z_target/10:.1f} cm from the pole face (if the field is aligned "
              f"with an NV axis; farther if not).")
    else:
        print(f"\n-> target {TARGET_SPLIT_MHZ} MHz not reached within 1 mm..60 cm "
              f"with this magnet (need a bigger magnet or get closer).")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    ax1.semilogy(z / 10, B, color="tab:blue")
    ax1.set_ylabel("|B| on axis (mT)")
    ax1.set_title(f"{GRADE} magnet D{DIAMETER_MM}xL{L} mm: field & NV splitting vs distance")
    ax1.grid(True, which="both", alpha=0.3)

    ax2.semilogy(z / 10, df, color="tab:green", label="max splitting (aligned)")
    ax2.axhline(TARGET_SPLIT_MHZ, color="tab:red", ls="--", label=f"target {TARGET_SPLIT_MHZ} MHz")
    if z_target is not None:
        ax2.axvline(z_target / 10, color="tab:red", ls=":", label=f"{z_target/10:.1f} cm")
    ax2.set_xlabel("Distance from magnet face (cm)")
    ax2.set_ylabel("Zeeman splitting (MHz)")
    ax2.legend()
    ax2.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
