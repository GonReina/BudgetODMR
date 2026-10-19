"""
Helmholtz-coil designer for the zero-field NV experiment (and a high-field bias).

Inspired by tarciszera/3D-Helmholtz-Coil-Simulator, but self-contained
(numpy + scipy, no magpylib) and aimed at the questions a build needs answered:

    for a target field B at the centre, a free bore (inner winding radius) and a
    wire, how many turns, how much wire, what current/voltage/power, how hot does
    it get, how homogeneous is the field over the sample, and how fast can it be
    modulated (inductance)?

Physics
  * Each coil is a real multi-layer winding: m layers x m turns per layer
    (square cross-section), layer pitch = enamelled wire diameter. Every turn is
    a circular loop; the field of a loop is the exact elliptic-integral formula.
  * The spacing of the two coils is not fixed at R: it is solved so that
    d2Bz/dz2 = 0 at the centre (the true Helmholtz condition for a thick
    winding). If the windings would touch first, they are put side by side.
  * The number of layers m grows until the centre field reaches the target at
    the rated current; the operating current is then scaled down to hit it.
  * Resistance uses the hot copper resistivity, found by iterating with a
    steady-state temperature rise dT = P / (h * area), h = H_COOL (natural
    convection + radiation ~ 12 W/m2/K; forced air ~ 30-50; water >> 100).
  * Inductance of the series pair: filament method (Maxwell mutual inductance
    between groups of turns, GMD self terms). Bandwidth f_3dB = R / (2 pi L); the
    drive voltage needed for a modulation amplitude follows from |Z| = |R + jwL|.

Run:  python theory/coils/helmholtz_designer.py      (numpy, scipy, matplotlib)
Out:  theory/coils/out/coil_<name>.png         field maps per design
      theory/coils/out/coil_sweep.png          power / wire / dT / L vs bore
      theory/coils/out/coil_designs.txt        the summary table printed below
      theory/coils/cad/coil_dims.scad          winding geometry for the OpenSCAD parts
"""

import os

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq
from scipy.special import ellipe, ellipk

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
CAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cad")

MU0 = 4e-7 * np.pi
RHO_CU = 1.72e-8          # ohm m at 20 C
ALPHA_CU = 0.00393        # 1/K
DENS_CU = 8960.0          # kg/m3
T_AMB = 22.0              # C
H_COOL = 12.0             # W/m2/K: still air. Raise for a fan / water cooling.
T_MAX = 80.0              # C: practical winding limit with a PETG/ABS former
                          # (PLA softens at ~55 C; aluminium/PEEK former -> 150 C)
GAP_MM = 2.0              # minimum clear gap between the two windings
J_DEFAULT = 3.0           # A/mm2 when a design gives no current (air-cooled, compact)
FIL = 16                  # max filament groups per dimension for maps and L

# --- the designs ------------------------------------------------------------
# name, target_mT (centre field at operating current), r_in_mm (inner winding
# radius = free bore), wire_mm (bare copper), current_A (rated; None -> J_DEFAULT),
# v_drive_V (driver voltage swing available for modulation), f_mod_Hz,
# roi_mm (sample size: cube side for the homogeneity check)
DESIGNS = [
    # Dhungel et al. 2024 scan axis: +-4 mT (+-40 G) with ~1.7 mT/A at 0-3 A.
    # Nanodiamond features are up to ~4.5 mT wide, so 6 mT gives margin.
    # The scan pair can carry the lock-in modulation itself (DC + sine through a
    # bipolar current driver); f_mod_Hz shows the drive voltage that needs.
    dict(name="zf_scan_Z", target_mT=6.0, r_in_mm=30, wire_mm=1.0, current_A=3.0,
         v_drive_V=12, f_mod_Hz=1000, roi_mm=2.0),
    # Transverse axes: bias up to ~1.5 mT (the paper used up to 1.47 mT) and
    # cancelling Earth's field (~50 uT). Bigger bores so the pairs nest; 50 / 70 mm
    # (not 45 / 60) is what clears the printed formers and flanges in cad/v3_three_axis.scad.
    dict(name="zf_transverse_X", target_mT=2.0, r_in_mm=50, wire_mm=0.8, current_A=2.0,
         v_drive_V=12, f_mod_Hz=None, roi_mm=2.0),
    dict(name="zf_transverse_Y", target_mT=2.0, r_in_mm=70, wire_mm=0.8, current_A=2.0,
         v_drive_V=12, f_mod_Hz=None, roi_mm=2.0),
    # Small separate modulation pair on the scan axis, for lock-in detection:
    # amplitude ~ 1/2 of the zero-field feature width (bulk ~0.5 mT FWHM).
    dict(name="zf_modulation", target_mT=0.5, r_in_mm=20, wire_mm=0.5, current_A=1.0,
         v_drive_V=12, f_mod_Hz=1000, roi_mm=2.0),
    # The 0.2 T bias that was asked about (covers the GSLAC at 102.4 mT).
    dict(name="bias_200mT", target_mT=200.0, r_in_mm=15, wire_mm=1.5, current_A=None,
         v_drive_V=30, f_mod_Hz=None, roi_mm=2.0),
]

# --- sweep: power / wire / dT / L vs bore for these fields and wires ---------
SWEEP_TARGETS_MT = [6.0, 200.0]
SWEEP_WIRES_MM = [0.5, 0.8, 1.2, 2.0]
SWEEP_R_IN_MM = np.arange(10, 65, 5)


def d_overall_mm(d):
    """Enamelled diameter of a bare copper wire d (mm), IEC 60317 grade 2, approx."""
    return 1.08 * d + 0.02


# ---------------------------------------------------------------------------
# field of loops
# ---------------------------------------------------------------------------
def loops_field(a, z0, n, r, z):
    """(Br, Bz) in T per ampere at points (r, z) from loops of radius a at z0
    with n turns each (arrays of loops; points broadcast)."""
    r = np.maximum(np.asarray(r, float), 1e-7)[..., None]
    zz = np.asarray(z, float)[..., None] - z0
    a2, r2, z2 = a * a, r * r, zz * zz
    q = (a + r) ** 2 + z2
    m = 4 * a * r / q
    K, E = ellipk(m), ellipe(m)
    d = (a - r) ** 2 + z2
    pre = MU0 * n / (2 * np.pi * np.sqrt(q))
    bz = pre * (K + (a2 - r2 - z2) / d * E)
    br = pre * zz / r * (-K + (a2 + r2 + z2) / d * E)
    return br.sum(-1), bz.sum(-1)


def winding(m, r_in, d_o, s):
    """Every turn of the pair: radii and axial positions (m layers x m turns)."""
    a = r_in + (np.arange(m) + 0.5) * d_o
    u = (np.arange(m) - (m - 1) / 2) * d_o
    A, U = np.meshgrid(a, u, indexing="ij")
    A, U = A.ravel(), U.ravel()
    return np.r_[A, A], np.r_[U + s / 2, U - s / 2]


def filaments(m, r_in, d_o, s):
    """Turns lumped into <= FIL x FIL groups per coil: (a, z, n, ca, cz)."""
    g = min(m, FIL)
    edges = np.linspace(0, m, g + 1).round().astype(int)
    cnt = np.diff(edges)
    mid = (edges[:-1] + edges[1:] - 1) / 2
    a = r_in + (mid + 0.5) * d_o
    u = (mid - (m - 1) / 2) * d_o
    A, U = np.meshgrid(a, u, indexing="ij")
    N = np.outer(cnt, cnt).astype(float)
    C = np.outer(cnt, np.ones(g)) * d_o
    Cz = np.outer(np.ones(g), cnt) * d_o
    A, U, N, C, Cz = (x.ravel() for x in (A, U, N, C, Cz))
    return (np.r_[A, A], np.r_[U + s / 2, U - s / 2], np.r_[N, N],
            np.r_[C, C], np.r_[Cz, Cz])


def d2bz0(m, r_in, d_o, s):
    """d2Bz/dz2 at the centre (on axis), per ampere (sign is what matters)."""
    a, z0 = winding(m, r_in, d_o, s)
    return np.sum(a * a * 3 * (4 * z0 * z0 - a * a) / (a * a + z0 * z0) ** 3.5)


def bz_axis(a, z0, z):
    z = np.asarray(z, float)[..., None]
    return (MU0 * a * a / (2 * (a * a + (z - z0) ** 2) ** 1.5)).sum(-1)


def best_spacing(m, r_in, d_o):
    """Centre-to-centre spacing with d2Bz/dz2 = 0 (or touching windings)."""
    s_min = m * d_o + GAP_MM * 1e-3
    s_max = 4 * (r_in + m * d_o)
    f0, f1 = d2bz0(m, r_in, d_o, s_min), d2bz0(m, r_in, d_o, s_max)
    if f0 * f1 < 0:
        return brentq(lambda s: d2bz0(m, r_in, d_o, s), s_min, s_max, xtol=1e-7), True
    return s_min, False


# ---------------------------------------------------------------------------
# inductance
# ---------------------------------------------------------------------------
def inductance(a, z, n, ca, cz, d_cu):
    """Self-inductance (H) of the series pair, filament method."""
    A1, A2 = a[:, None], a[None, :]
    D = z[:, None] - z[None, :]
    k2 = 4 * A1 * A2 / ((A1 + A2) ** 2 + D ** 2)
    k2 = np.minimum(k2, 1 - 1e-12)
    k = np.sqrt(k2)
    M = MU0 * np.sqrt(A1 * A2) * ((2 / k - k) * ellipk(k2) - 2 / k * ellipe(k2))
    gmd = np.where(n == 1, 0.7788 * d_cu / 2, 0.2235 * (ca + cz))
    Ls = MU0 * a * (np.log(8 * a / gmd) - 2)
    np.fill_diagonal(M, Ls)
    return float(n @ M @ n)


# ---------------------------------------------------------------------------
# one design
# ---------------------------------------------------------------------------
def design(p, maps=True):
    d = p["wire_mm"] * 1e-3
    d_o = d_overall_mm(p["wire_mm"]) * 1e-3
    area = np.pi * d * d / 4
    I_rated = p["current_A"] or J_DEFAULT * area * 1e6
    r_in, B_t = p["r_in_mm"] * 1e-3, p["target_mT"] * 1e-3

    for m in range(1, 600):
        s, helm = best_spacing(m, r_in, d_o)
        a, z0 = winding(m, r_in, d_o, s)
        k_TA = float(bz_axis(a, z0, 0.0))          # T per ampere
        if k_TA * I_rated >= B_t:
            break
    else:
        return None
    I = B_t / k_TA
    w, r_out = m * d_o, r_in + m * d_o
    N = m * m
    length = float(2 * np.pi * a.sum())            # both coils
    R20 = RHO_CU * length / area
    surf = 2 * (2 * np.pi * (r_out + r_in) * w + 2 * np.pi * (r_out ** 2 - r_in ** 2))
    T, runaway = T_AMB, False
    for _ in range(200):
        R = R20 * (1 + ALPHA_CU * (T - 20))
        T_new = T_AMB + I * I * R / (H_COOL * surf)
        if T_new > 1000:
            runaway, T = True, T_new
            break
        if abs(T_new - T) < 0.01:
            T = T_new
            break
        T = T_new
    # runaway: report the cold numbers (a lower bound, kept cold by real cooling)
    R = R20 if runaway else R20 * (1 + ALPHA_CU * (T - 20))
    P = I * I * R
    fa, fz, fn, fca, fcz = filaments(m, r_in, d_o, s)
    L = inductance(fa, fz, fn, fca, fcz, d)
    res = dict(p, m=m, N_per_coil=N, spacing_mm=s * 1e3, helmholtz=helm,
               width_mm=w * 1e3, r_out_mm=r_out * 1e3, mT_per_A=k_TA * 1e3,
               I_A=I, J_A_mm2=I / (area * 1e6), length_m=length, R20_ohm=R20,
               R_hot_ohm=R, V_V=I * R, P_W=P, T_C=T, runaway=runaway,
               mass_kg=DENS_CU * area * length, L_H=L, f3dB_Hz=R / (2 * np.pi * L),
               tau_ms=1e3 * L / R)
    if p.get("f_mod_Hz"):
        Z = abs(R + 2j * np.pi * p["f_mod_Hz"] * L)
        res["V_per_mT_mod"] = Z / (k_TA * 1e3)
        res["mod_max_mT"] = p["v_drive_V"] / Z * k_TA * 1e3
    if maps:
        res.update(homogeneity(m, r_in, d_o, s, p["roi_mm"] * 1e-3, B_t))
    return res


def homogeneity(m, r_in, d_o, s, roi, B_t):
    fa, fz, fn, *_ = filaments(m, r_in, d_o, s)
    br0, bz0 = loops_field(fa, fz, fn, 0.0, 0.0)
    B0 = np.hypot(br0, bz0)
    zr = max(s / 2 - m * d_o / 2, 1e-3) * 0.9
    rr = r_in * 0.9
    R, Z = np.meshgrid(np.linspace(0, rr, 91), np.linspace(-zr, zr, 121))
    br, bz = loops_field(fa, fz, fn, R, Z)
    dev = np.hypot(br, bz - B0) / B0           # |B - B0| / |B0|  (vector)
    rp, zp = np.meshgrid(np.linspace(0, roi / 2, 11), np.linspace(-roi / 2, roi / 2, 21))
    br, bz = loops_field(fa, fz, fn, rp, zp)
    roi_dev = float(np.max(np.hypot(br, bz - B0) / B0))
    out = dict(map_R=R, map_Z=Z, map_dev=dev, roi_dev=roi_dev,
               roi_dB_uT=roi_dev * B_t * 1e6)
    # sizes of the 1e-3 / 1e-2 regions along the axis and in the mid-plane
    for lvl, tag in ((1e-3, "1e-3"), (1e-2, "1e-2")):
        za = np.linspace(0, zr, 400)
        bz = loops_field(fa, fz, fn, 0.0 * za, za)[1]
        okz = np.abs(bz - B0) / B0 < lvl
        ra = np.linspace(0, rr, 400)
        br, bz = loops_field(fa, fz, fn, ra, 0.0 * ra)
        okr = np.hypot(br, bz - B0) / B0 < lvl
        out[f"z_{tag}_mm"] = 2e3 * za[np.argmin(okz)] if not okz.all() else 2e3 * zr
        out[f"r_{tag}_mm"] = 2e3 * ra[np.argmin(okr)] if not okr.all() else 2e3 * rr
    return out


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def summary_lines(res):
    L = []
    for r in res:
        if r is None:
            continue
        L += [f"\n== {r['name']}: {r['target_mT']:g} mT at the centre ==",
              f"  bore r_in {r['r_in_mm']:.0f} mm (diameter {2 * r['r_in_mm']:.0f} mm), "
              f"outer r {r['r_out_mm']:.1f} mm, winding {r['width_mm']:.1f} x "
              f"{r['r_out_mm'] - r['r_in_mm']:.1f} mm",
              f"  wire {r['wire_mm']} mm Cu ({d_overall_mm(r['wire_mm']):.2f} mm enamelled), "
              f"{r['m']} layers x {r['m']} turns = {r['N_per_coil']} turns per coil",
              f"  spacing {r['spacing_mm']:.1f} mm centre-centre "
              + ("(d2B/dz2 = 0)" if r["helmholtz"] else "(windings touching: thicker than Helmholtz allows)")
              + f";  {r['mT_per_A']:.3f} mT/A",
              f"  current {r['I_A']:.2f} A ({r['J_A_mm2']:.1f} A/mm2), {r['V_V']:.1f} V, "
              f"{r['P_W']:.1f} W for the pair, R {r['R20_ohm']:.2f} ohm cold / "
              f"{r['R_hot_ohm']:.2f} hot" + ("  (cold: kept at 20 C)" if r["runaway"] else ""),
              f"  wire {r['length_m']:.0f} m for the pair ({r['mass_kg'] * 1e3:.0f} g Cu)",
              f"  winding temperature (still air, h={H_COOL:g}): "
              + ("RUNAWAY: needs forced/water cooling" if r["runaway"] else
                 f"{r['T_C']:.0f} C" + ("  <-- above T_MAX" if r["T_C"] > T_MAX else "")),
              f"  inductance {r['L_H'] * 1e3:.2f} mH, L/R {r['tau_ms']:.2f} ms, "
              f"f_3dB {r['f3dB_Hz']:.1f} Hz"]
        if "V_per_mT_mod" in r:
            L.append(f"  modulation at {r['f_mod_Hz']} Hz: {r['V_per_mT_mod']:.1f} V per mT "
                     f"amplitude; {r['v_drive_V']} V drive -> {r['mod_max_mT']:.3f} mT")
        if "roi_dev" in r:
            L.append(f"  homogeneity: {r['roi_dev']:.1e} ({r['roi_dB_uT']:.2f} uT) over a "
                     f"{r['roi_mm']} mm cube; 1e-3 region {r['z_1e-3_mm']:.1f} mm (axis) x "
                     f"{r['r_1e-3_mm']:.1f} mm (dia); 1e-2 region {r['z_1e-2_mm']:.1f} x "
                     f"{r['r_1e-2_mm']:.1f} mm")
    return L


def plot_design(r):
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    a = ax[0]
    R, Z, dev = r["map_R"] * 1e3, r["map_Z"] * 1e3, r["map_dev"]
    cs = a.contourf(Z, R, np.log10(np.maximum(dev, 1e-8)), levels=np.arange(-8, 0.5, 0.5),
                    cmap="Blues_r")
    a.contour(Z, R, dev, levels=[1e-3, 1e-2], colors="k", linewidths=0.8)
    h = r["roi_mm"] / 2
    a.add_patch(plt.Rectangle((-h, 0), 2 * h, h, fill=False, ec="tab:orange", lw=1.5,
                              label=f"sample ({r['roi_mm']} mm)"))
    fig.colorbar(cs, ax=a, label="log10 |B - B0| / B0")
    a.set(xlabel="z, along the coil axis (mm)", ylabel="r, radial (mm)", aspect="equal",
          title="field error (black: 1e-3 and 1e-2)")
    a.legend(loc="upper right", fontsize=8)

    a = ax[1]
    s, w = r["spacing_mm"], r["width_mm"]
    for zc in (-s / 2, s / 2):
        for sgn in (1, -1):
            a.add_patch(plt.Rectangle((zc - w / 2, sgn * r["r_in_mm"]), w,
                                      sgn * (r["r_out_mm"] - r["r_in_mm"]),
                                      color="tab:brown", alpha=0.7))
    a.plot([-h, h, h, -h, -h], [-h, -h, h, h, -h], color="tab:orange", lw=1.5)
    lim = max(r["r_out_mm"], s / 2 + w / 2) * 1.15
    a.set(xlim=(-lim, lim), ylim=(-lim, lim), aspect="equal", xlabel="z (mm)",
          ylabel="r (mm)", title="cross-section (to scale)")
    a.grid(alpha=0.3)
    txt = (f"{r['N_per_coil']} turns/coil, {r['wire_mm']} mm wire, "
           f"{r['I_A']:.2f} A, {r['V_V']:.1f} V, {r['P_W']:.1f} W, "
           f"{r['length_m']:.0f} m wire, L = {r['L_H'] * 1e3:.1f} mH, "
           + ("thermal RUNAWAY" if r["runaway"] else f"winding ~{r['T_C']:.0f} C"))
    fig.suptitle(f"{r['name']}: {r['target_mT']:g} mT, bore diameter "
                 f"{2 * r['r_in_mm']:.0f} mm\n{txt}", fontsize=11)
    fig.tight_layout()
    out = os.path.join(OUT, f"coil_{r['name']}.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def plot_sweep():
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    colors = plt.get_cmap("tab10")
    for ti, B in enumerate(SWEEP_TARGETS_MT):
        ls = "-" if ti == 0 else "--"
        for wi, wd in enumerate(SWEEP_WIRES_MM):
            rows = [design(dict(name="s", target_mT=B, r_in_mm=r, wire_mm=wd, current_A=None,
                                v_drive_V=0, roi_mm=1), maps=False) for r in SWEEP_R_IN_MM]
            ok = [(r_, x) for r_, x in zip(SWEEP_R_IN_MM, rows) if x is not None]
            if not ok:
                continue
            rr = np.array([o[0] for o in ok]) * 2
            g = lambda k: np.array([o[1][k] for o in ok])
            lab = f"{B:g} mT, {wd} mm wire ({J_DEFAULT * np.pi * wd ** 2 / 4:.1f} A)"
            c = colors(wi)
            ax[0, 0].semilogy(rr, g("P_W"), ls, color=c, lw=1.5, label=lab)
            T = np.where(g("runaway"), np.nan, g("T_C"))
            ax[0, 1].semilogy(rr, T - T_AMB, ls, color=c, lw=1.5, label=lab)
            ax[1, 0].semilogy(rr, g("length_m"), ls, color=c, lw=1.5, label=lab)
            ax[1, 1].semilogy(rr, g("V_V"), ls, color=c, lw=1.5, label=lab)
    ax[0, 0].set(ylabel="power, pair (W)", title=f"power at J = {J_DEFAULT} A/mm2 "
                 "(solid: 6 mT, dashed: 200 mT)")
    ax[0, 1].axhline(T_MAX - T_AMB, color="k", lw=0.8, ls=":")
    ax[0, 1].set(ylabel="temperature rise (K)", title=f"still air (h = {H_COOL:g}); dotted: "
                 f"{T_MAX:g} C limit; missing = runaway")
    ax[1, 0].set(ylabel="wire length, pair (m)", title="how much wire to buy")
    ax[1, 1].set(ylabel="supply voltage (V)", title="voltage across the pair (hot)")
    for a in ax.ravel():
        a.set_xlabel("bore diameter 2 r_in (mm)")
        a.grid(alpha=0.3, which="both")
    ax[0, 0].legend(fontsize=7, ncol=2, loc="center left")
    fig.tight_layout()
    out = os.path.join(OUT, "coil_sweep.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def write_scad(res):
    """Winding geometry for the CAD (cad/*.scad include this file), in mm."""
    path = os.path.join(CAD, "coil_dims.scad")
    L = ["// GENERATED by helmholtz_designer.py: do not edit, re-run the designer.",
         "// Per design: [r_in, r_out, winding width (axial), centre-centre spacing,",
         "//              enamelled wire diameter, layers, turns per coil]"]
    for r in res:
        if r is None:
            continue
        L.append(f"{r['name']} = [{r['r_in_mm']:.3f}, {r['r_out_mm']:.3f}, {r['width_mm']:.3f}, "
                 f"{r['spacing_mm']:.3f}, {d_overall_mm(r['wire_mm']):.3f}, {r['m']}, "
                 f"{r['N_per_coil']}];")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    res = [design(p) for p in DESIGNS]
    for p, r in zip(DESIGNS, res):
        if r is None:
            print(f"{p['name']}: target not reachable within 600 layers")
    lines = summary_lines(res)
    print("\n".join(lines))
    with open(os.path.join(OUT, "coil_designs.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("saved", write_scad(res))
    for r in res:
        if r is not None:
            print("saved", plot_design(r))
    print("saved", plot_sweep())


if __name__ == "__main__":
    main()
