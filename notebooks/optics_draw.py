"""
2-D layout drawing for notebooks/Optical_Setup.ipynb.

Folded geometry, drawn in millimetres at true scale:
  * collection axis along +x, diamond top surface at x = 0;
  * excitation arm vertical (along +y) up to the dichroic at (x_dichroic, 0),
    where it is reflected towards -x into the focusing optic.
Component outlines are schematic (correct position and clear aperture, not
mechanical housings).  Beam envelopes are drawn at true scale from the model.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, FancyArrowPatch

C_EXC = "#1a9e3a"      # 532 nm excitation
C_PL = "#c8102e"       # NV photoluminescence
C_OPT = "#3a5f8a"      # glass
C_MECH = "0.35"


def _txt(ax, x, y, s, **kw):
    kw.setdefault("fontsize", 7.5)
    kw.setdefault("ha", "center")
    kw.setdefault("va", "bottom")
    ax.text(x, y, s, **kw)


def lens_v(ax, x, r, t=4.0, kind="biconvex", label=None, ly=None):
    """Lens with its axis along x.  kind: biconvex | planoconvex_right (curved side +x)."""
    y = np.linspace(-r, r, 50)
    sag = t / 2 * (1 - (y / r) ** 2)
    if kind == "biconvex":
        xs = np.r_[x - sag, (x + sag)[::-1]]
    else:  # asphere/condenser: flat face at x, curved towards +x, thickness t
        xs = np.r_[np.full_like(y, x), (x + t * (1 - (y / r) ** 2) ** 0.8)[::-1]]
    ax.add_patch(Polygon(np.c_[xs, np.r_[y, y[::-1]]], fc=C_OPT, alpha=0.35, ec=C_OPT, lw=0.8))
    if label:
        _txt(ax, x + (t / 2 if kind != "biconvex" else 0), (ly or r + 1.5), label)


def lens_h(ax, y, r, x=0.0, t=3.0, label=None, side="right"):
    """Thin lens with its axis along y (excitation arm)."""
    xx = np.linspace(-r, r, 40)
    sag = t / 2 * (1 - (xx / r) ** 2)
    ys = np.r_[y - sag, (y + sag)[::-1]]
    ax.add_patch(Polygon(np.c_[np.r_[x + xx, x + xx[::-1]], ys], fc=C_OPT, alpha=0.35, ec=C_OPT, lw=0.8))
    if label:
        _txt(ax, x + r + 2 if side == "right" else x - r - 2, y, label,
             ha="left" if side == "right" else "right", va="center")


def plate_v(ax, x, r, t=2.0, fc="0.6", label=None, hatch=None, ly=None):
    ax.add_patch(Rectangle((x - t / 2, -r), t, 2 * r, fc=fc, ec="0.2", lw=0.6, alpha=0.6, hatch=hatch))
    if label:
        _txt(ax, x, (ly or r + 1.5), label)


def plate_h(ax, y, r, x=0.0, t=2.0, fc="0.6", label=None, hatch=None, side="right"):
    ax.add_patch(Rectangle((x - r, y - t / 2), 2 * r, t, fc=fc, ec="0.2", lw=0.6, alpha=0.6, hatch=hatch))
    if label:
        _txt(ax, x + r + 2 if side == "right" else x - r - 2, y, label,
             ha="left" if side == "right" else "right", va="center")


def dichroic(ax, x, length=36.0, t=1.0, label="DMLP550R"):
    c, s = np.cos(np.pi / 4), np.sin(np.pi / 4)
    L, T = length / 2, t / 2
    pts = np.array([[-L, -T], [L, -T], [L, T], [-L, T]])
    R = np.array([[c, -s], [s, c]])
    ax.add_patch(Polygon(pts @ R.T + [x, 0], fc="#b58cd6", ec="0.2", lw=0.6, alpha=0.7))
    _txt(ax, x - 7, 14, label, ha="right")


def objective(ax, x_front, x_back, pupil_r, label="N40X-PF 40x/0.75"):
    body = [[x_front, -3.5], [x_front + 7, -3.5], [x_front + 17, -10], [x_back, -10],
            [x_back, 10], [x_front + 17, 10], [x_front + 7, 3.5], [x_front, 3.5]]
    ax.add_patch(Polygon(body, fc="0.85", ec=C_MECH, lw=0.8))
    ax.plot([x_back, x_back], [-pupil_r, pupil_r], color=C_MECH, lw=2.2)
    _txt(ax, (x_front + x_back) / 2 + 5, 11, label)


def diamond(ax, t=0.5, h=1.5, label="DNVB14\n3x3x0.5 mm"):
    ax.add_patch(Rectangle((-t, -h), t, 2 * h, fc="#9ad0f5", ec="0.2", lw=0.6))
    _txt(ax, -3, -3, label, ha="right", va="top")


def detector(ax, x, r_active, label="PDA10A2", body=6.0):
    ax.add_patch(Rectangle((x, -body), 4, 2 * body, fc="0.3", ec="k", lw=0.6))
    ax.plot([x, x], [-r_active, r_active], color="gold", lw=3)
    _txt(ax, x + 2, body + 1.5, label)


def pinhole(ax, x, r_hole, h=8.0, label="pinhole"):
    ax.plot([x, x], [r_hole, h], color="k", lw=2)
    ax.plot([x, x], [-h, -r_hole], color="k", lw=2)
    _txt(ax, x, -h - 1.5, label, va="top")


def laser(ax, y, x=0.0, label="DJ532-40\n+ pointer collimator"):
    ax.add_patch(Rectangle((x - 6, y - 30), 12, 30, fc="0.25", ec="k", lw=0.6))
    _txt(ax, x - 8, y - 15, label, ha="right", va="center")


def fibre(ax, y, x=0.0, label="PM fibre (FC/APC)"):
    ax.plot([x, x - 20, x - 35], [y - 6, y - 25, y - 28], color="orange", lw=2.5)
    ax.add_patch(Rectangle((x - 1.5, y - 8), 3, 8, fc="0.5", ec="k", lw=0.6))
    _txt(ax, x - 8, y - 12, label, ha="right", va="center")


def axis_lines(ax, x_end, y_start, x_dich):
    ax.plot([-3, x_end], [0, 0], ls=(0, (8, 3, 1, 3)), color="0.5", lw=0.6, zorder=0)
    ax.plot([x_dich, x_dich], [y_start, 0], ls=(0, (8, 3, 1, 3)), color="0.5", lw=0.6, zorder=0)


def band_v(ax, y, w, x=0.0, color=C_EXC, alpha=0.45):
    """Beam of half-width w(y) travelling along y at horizontal position x."""
    ax.fill_betweenx(y, x - w, x + w, color=color, alpha=alpha, lw=0)


def band_h(ax, x, w, y0=0.0, color=C_EXC, alpha=0.45):
    ax.fill_between(x, y0 - w, y0 + w, color=color, alpha=alpha, lw=0)


def cone(ax, x0, r0, x1, r1, color, alpha=0.4):
    ax.add_patch(Polygon([[x0, -r0], [x1, -r1], [x1, r1], [x0, r0]], fc=color, alpha=alpha, lw=0))


def hdim(ax, x0, x1, y, text, color="0.25"):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="<->", mutation_scale=6, color=color, lw=0.6))
    _txt(ax, (x0 + x1) / 2, y + 0.8, text, fontsize=6.5, color=color)


def vdim(ax, y0, y1, x, text, color="0.25"):
    ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="<->", mutation_scale=6, color=color, lw=0.6))
    _txt(ax, x + 1.2, (y0 + y1) / 2, text, fontsize=6.5, color=color, ha="left", va="center")


def focal_plane(ax, x, h, text):
    ax.plot([x, x], [-h, h], ls=":", color="0.3", lw=0.8)
    _txt(ax, x, -h - 1, text, fontsize=6.5, va="top", color="0.3")


def draw_system(ax, S):
    """Draw a configuration described by the dict S (built in the notebook).

    Required keys: x_optic_front, x_pupil, pupil_r, optic ('objective'|'asphere'),
    x_dich, x_felh, x_lens, x_det, r_det, arm (list of arm elements, see notebook),
    y_source, source ('laser'|'fibre'), exc_y, exc_w (arrays along the arm),
    w_exc_pupil, r_pl (collimated PL half-width), optional x_pinhole, r_pinhole."""
    x_end = S["x_det"] + 8
    axis_lines(ax, x_end, S["y_source"], S["x_dich"])
    diamond(ax)
    if S["optic"] == "objective":
        objective(ax, S["x_optic_front"], S["x_pupil"], S["pupil_r"])
    else:
        lens_v(ax, S["x_optic_front"], 12.7, t=14.0, kind="planoconvex")
        _txt(ax, S["x_optic_front"] + 7, -14.5, "ACL25416U-B\nf=16, NA 0.79", va="top")
    dichroic(ax, S["x_dich"])
    plate_v(ax, S["x_felh"], 12.5, t=3.5, fc="#e8a33d", label="FELH0550")
    lens_v(ax, S["x_lens"], 12.7, t=5.0, label="AC254-150-A")
    if S.get("x_pinhole") is not None:
        pinhole(ax, S["x_pinhole"], max(S["r_pinhole"], 0.25), label=S.get("pinhole_label", "pinhole"))
    detector(ax, S["x_det"], S["r_det"])
    # excitation arm
    xd = S["x_dich"]
    if S["source"] == "laser":
        laser(ax, S["y_source"], xd)
    else:
        fibre(ax, S["y_source"], xd)
    for el in S["arm"]:
        kind, y, lab = el[0], el[1], el[2]
        if kind == "filter":
            plate_h(ax, y, 6.25, xd, t=3.5, fc="#7ccf8a", label=lab)
        elif kind == "nd":
            plate_h(ax, y, 12.5, xd, t=2.0, fc="0.45", label=lab)
        elif kind == "pol":
            plate_h(ax, y, 12.5, xd, t=2.5, fc="#dddd99", hatch="////", label=lab)
        elif kind == "collimator":
            lens_h(ax, y, el[3] if len(el) > 3 else 6.0, xd, t=3.0, label=lab)
    band_v(ax, S["exc_y"], S["exc_w"], xd)
    # reflected excitation to the pupil, then the cone to the focus
    w = S["w_exc_pupil"]
    band_h(ax, np.array([S["x_pupil"], xd]), np.array([w, w]))
    cone(ax, 0.0, 0.02, S["x_pupil"], w, C_EXC, 0.45)
    # fluorescence: marginal cone into the optic, collimated to the lens, focus on detector
    r_pl = S["r_pl"]
    x_in = S["x_optic_front"]
    cone(ax, 0.0, 0.02, x_in, x_in * np.tan(np.arcsin(S["NA_coll"])), C_PL, 0.18)
    cone(ax, x_in, x_in * np.tan(np.arcsin(S["NA_coll"])), S["x_pupil"], r_pl, C_PL, 0.18)
    cone(ax, S["x_pupil"], r_pl, S["x_lens"], r_pl, C_PL, 0.18)
    x_focus = S.get("x_pinhole") or S["x_det"]
    cone(ax, S["x_lens"], r_pl, x_focus, 0.05, C_PL, 0.22)
    if S.get("x_pinhole") is not None:
        cone(ax, S["x_pinhole"], 0.05, S["x_det"], S["r_after_pinhole"], C_PL, 0.22)
    ax.set_aspect("equal")
    ax.set_ylim(top=27)
    ax.set_xlabel("position along collection axis (mm)")
    ax.set_ylabel("mm")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def legend_handles():
    from matplotlib.patches import Patch
    return [Patch(color=C_EXC, alpha=0.5, label="532 nm excitation (1/e$^2$ envelope, true scale)"),
            Patch(color=C_PL, alpha=0.3, label="NV fluorescence (marginal-ray envelope)")]


def sample_zoom(ax, z_um, w_um, NA_coll, n=2.42, depth_um=500, focus_um=None, title=None):
    """Cross-section of the diamond (x = transverse in um, y = depth in um, surface at 0)."""
    ax.axhspan(0, depth_um, color="#9ad0f5", alpha=0.35, lw=0)
    ax.fill_betweenx(z_um, -w_um, w_um, color=C_EXC, alpha=0.5, lw=0, label="excitation 1/e$^2$")
    th_c = np.degrees(np.arcsin(1 / n))
    th_na = np.arcsin(NA_coll / n)
    zf = focus_um if focus_um is not None else z_um[np.argmin(w_um)]
    for sgn in (-1, 1):
        ax.plot([0 + sgn * 0, sgn * zf * np.tan(th_na)], [zf, 0], color=C_PL, lw=1)
        ax.plot([0, sgn * zf * np.tan(np.radians(th_c))], [zf, 0], color="k", lw=0.7, ls="--")
    ax.plot([], [], color=C_PL, lw=1, label=f"collection cone in diamond ({np.degrees(th_na):.1f}°)")
    ax.plot([], [], color="k", lw=0.7, ls="--", label=f"TIR escape cone ({th_c:.1f}°)")
    ax.set_ylim(depth_um, -0.04 * depth_um)
    ax.set_xlabel("transverse position (µm)")
    ax.set_ylabel("depth below surface (µm)")
    ax.legend(fontsize=6.5, loc="lower right")
    if title:
        ax.set_title(title, fontsize=9)
