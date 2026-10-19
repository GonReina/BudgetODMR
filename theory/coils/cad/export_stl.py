"""
Render the coil-former CAD (v1 / v2 / v3) to STL and preview PNGs, and check the
assemblies for collisions.

    python theory/coils/cad/export_stl.py            STLs -> cad/stl/<version>/, PNGs -> cad/preview/
    python theory/coils/cad/export_stl.py check      pairwise collision check of every assembly

Needs OpenSCAD (a 2024+ build with the Manifold backend is much faster). It is found in
the OPENSCAD env var, on PATH, or in the default Windows install folder. Re-run
helmholtz_designer.py first if you changed a coil design: it rewrites coil_dims.scad.
"""

import itertools
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

VERSIONS = {
    "v1_single_axis": dict(
        print=["z_former", "base", "sample_arm"],
        parts=["base", "z_former", "sample_arm", "objective"]),
    "v2_single_axis_mod": dict(
        print=["mod_insert"],                       # the rest are the v1 parts
        parts=["base", "z_former", "mod_insert", "sample_arm", "objective"]),
    "v3_three_axis": dict(
        print=["base", "x_hoop", "y_hoop", "x_spacer", "y_spacer"],
        parts=["base", "z_former", "mod_insert", "x_hoop_p", "x_hoop_n", "y_hoop_t",
               "y_hoop_b", "x_spacers", "y_spacers", "sample_arm", "objective"]),
}
# parts that are meant to touch (shared faces) give zero-volume intersections, so a
# collision is an intersection with more than this volume
MIN_OVERLAP_MM3 = 0.5
CAMERA = "--camera=-260,-330,170,0,0,-20"


def find_openscad():
    for c in (os.environ.get("OPENSCAD"), shutil.which("openscad"),
              r"C:\Program Files\OpenSCAD\openscad.com",
              r"C:\Program Files\OpenSCAD (Nightly)\openscad.com"):
        if c and os.path.exists(c):
            return c
    sys.exit("OpenSCAD not found: install it or set OPENSCAD=<path to openscad(.com)>")


def run(osc, scad, out, defines, extra=()):
    cmd = [osc, "--backend=Manifold", "-o", out, *extra]
    for k, v in defines.items():
        cmd += ["-D", f'{k}="{v}"']
    cmd.append(scad)
    return subprocess.run(cmd, capture_output=True, text=True)


def export(osc):
    for ver, spec in VERSIONS.items():
        scad = os.path.join(HERE, ver + ".scad")
        odir = os.path.join(HERE, "stl", ver)
        os.makedirs(odir, exist_ok=True)
        for p in spec["print"]:
            out = os.path.join(odir, p + ".stl")
            r = run(osc, scad, out, {"part": p}, ["--export-format=binstl"])
            print(("ok   " if r.returncode == 0 else "FAIL ") + os.path.relpath(out, HERE))
            if r.returncode:
                print(r.stderr)
        pdir = os.path.join(HERE, "preview")
        os.makedirs(pdir, exist_ok=True)
        png = os.path.join(pdir, ver + ".png")
        r = run(osc, scad, png, {"part": "assembly"},
                [CAMERA, "--autocenter", "--viewall", "--imgsize=1400,1000",
                 "--colorscheme=Tomorrow"])
        print(("ok   " if r.returncode == 0 else "FAIL ") + os.path.relpath(png, HERE))


def stl_volume(path):
    """Enclosed volume (mm3) of a binary STL, by the divergence theorem."""
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack_from("<I", data, 80)[0]
    v = 0.0
    for i in range(n):
        x = struct.unpack_from("<9f", data, 84 + 50 * i + 12)
        a, b, c = x[0:3], x[3:6], x[6:9]
        v += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
              + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
    return abs(v)


def check(osc):
    bad = 0
    tmp = os.path.join(HERE, "_collide.stl")
    for ver, spec in VERSIONS.items():
        scad = os.path.join(HERE, ver + ".scad")
        for a, b in itertools.combinations(spec["parts"], 2):
            if os.path.exists(tmp):
                os.remove(tmp)
            r = run(osc, scad, tmp, {"part": "collide", "a": a, "b": b},
                    ["--export-format=binstl"])
            vol = stl_volume(tmp) if r.returncode == 0 and os.path.exists(tmp) else 0.0
            if vol > MIN_OVERLAP_MM3:
                bad += 1
                print(f"COLLISION  {ver}: {a} x {b}  ({vol:.1f} mm3)")
    if os.path.exists(tmp):
        os.remove(tmp)
    print("no collisions" if not bad else f"{bad} collision(s)")
    return bad


if __name__ == "__main__":
    osc = find_openscad()
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        sys.exit(1 if check(osc) else 0)
    export(osc)
