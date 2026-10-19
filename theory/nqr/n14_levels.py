"""
14N in the NV- ground state: where are the nuclear (quadrupole) transitions, how
strongly does an RF field drive them, and how homogeneous is a magnet pair at the
excited-state level anticrossing (ESLAC, ~51 mT)? Companion to n14_quadrupole_odnmr.md.

Hamiltonian (MHz), basis |m_S> x |m_I>, S = 1, I = 1, field at angle TILT to the NV axis:

    H = D Sz^2 + gamma_e B.S + A_par Sz Iz + A_perp (Sx Ix + Sy Iy) + P Iz^2 - gamma_n B.I

RF field B1 cos(wt) along x: H_rf = B1 cos(wt) (gamma_e Sx - gamma_n Ix). The Rabi
frequency of a nuclear transition a<->b is |<a|gamma_e Sx - gamma_n Ix|b>| * B1. The
gamma_e Sx part (through the A_perp state mixing) makes it ~10-20x the bare 14N value:
the "hyperfine enhancement".

Run:  python theory/nqr/n14_levels.py      (numpy, scipy)
"""

import numpy as np
from scipy.optimize import brentq
from scipy.special import ellipe, ellipk

D, GAMMA_E, GAMMA_N = 2870.0, 28.024, 0.003077      # MHz, MHz/mT, MHz/mT (14N)
A_PAR, A_PERP, P = -2.16, -2.70, -4.945             # MHz (literature, ground state)
FIELDS_MT = [0.0, 5.0, 51.0]
TILT_DEG = 0.0

# magnet pair (two facing NdFeB cylinders, field at the centre = B_TARGET_MT)
B_TARGET_MT, BR_T = 51.0, 1.30                      # N42
MAGNETS_MM = [(20, 20), (25, 25), (40, 40)]         # (diameter, length)
OFFSETS_MM = [0.1, 0.25, 0.5]                       # distance from the centre

s = 1 / np.sqrt(2)
SX = np.array([[0, s, 0], [s, 0, s], [0, s, 0]])
SY = np.array([[0, -1j * s, 0], [1j * s, 0, -1j * s], [0, 1j * s, 0]])
SZ = np.diag([1.0, 0, -1])
E3 = np.eye(3)
K = np.kron
M_VALUES = [1, 0, -1]
MU0 = 4e-7 * np.pi


def hamiltonian(b, tilt):
    c, sn = np.cos(tilt), np.sin(tilt)
    return (D * K(SZ @ SZ, E3) + GAMMA_E * b * (c * K(SZ, E3) + sn * K(SX, E3))
            + A_PAR * K(SZ, SZ) + A_PERP * (K(SX, SX) + K(SY, SY)) + P * K(E3, SZ @ SZ)
            - GAMMA_N * b * (c * K(E3, SZ) + sn * K(E3, SX)))


def levels(b, tilt=0.0):
    w, v = np.linalg.eigh(hamiltonian(b, tilt))
    lab = {}
    for k in range(9):
        j = int(np.argmax(np.abs(v[:, k]) ** 2))
        lab[(M_VALUES[j // 3], M_VALUES[j % 3])] = k
    return w, v, lab


def report(b):
    w, v, lab = levels(b, np.radians(TILT_DEG))
    rf = GAMMA_E * K(SX, E3) - GAMMA_N * K(E3, SX)
    bare = GAMMA_N * s
    print(f"\nB = {b:g} mT ({TILT_DEG:g} deg from the NV axis)")
    print("  nuclear transitions (RF):")
    for ms in (0, -1):
        for a, c in ((1, 0), (0, -1)):
            i, j = lab[(ms, a)], lab[(ms, c)]
            me = abs(v[:, i].conj() @ rf @ v[:, j])
            print(f"    m_S={ms:+d}, m_I {a:+d}<->{c:+d}: {abs(w[i] - w[j]):7.4f} MHz   "
                  f"enhancement x{me / bare:4.1f}, Rabi {me * 1e3:5.1f} kHz per mT of B1")
    print("  electron transitions (MW), one per m_I:")
    for mi in (1, 0, -1):
        print(f"    m_I={mi:+d}:  0->-1 {w[lab[(-1, mi)]] - w[lab[(0, mi)]]:9.3f} MHz   "
              f"0->+1 {w[lab[(1, mi)]] - w[lab[(0, mi)]]:9.3f} MHz")


def loop_field(a, z0, r, z):
    r = max(r, 1e-9)
    zz = z - z0
    q = (a + r) ** 2 + zz ** 2
    m = 4 * a * r / q
    d = (a - r) ** 2 + zz ** 2
    pre = MU0 / (2 * np.pi * np.sqrt(q))
    return (pre * zz / r * (-ellipk(m) + (a * a + r * r + zz * zz) / d * ellipe(m)),
            pre * (ellipk(m) + (a * a - r * r - zz * zz) / d * ellipe(m)))


def magnet_field(rad, length, zc, r, z, n=300):
    """Axially magnetised cylinder = sheet current Br/mu0 per metre (n loops)."""
    k = BR_T / MU0 * length / n
    br = bz = 0.0
    for z0 in zc - length / 2 + (np.arange(n) + 0.5) / n * length:
        a, b = loop_field(rad, z0, r, z)
        br, bz = br + a * k, bz + b * k
    return br, bz


def magnet_pair():
    print(f"\nFacing magnet pair (N42), {B_TARGET_MT:g} mT at the centre:")
    for dia, ln in MAGNETS_MM:
        rad, length = dia / 2e3, ln / 1e3

        def field(r, z, gap):
            c = gap / 2 + length / 2
            a1, b1 = magnet_field(rad, length, c, r, z)
            a2, b2 = magnet_field(rad, length, -c, r, z)
            return np.hypot(a1 + a2, b1 + b2)

        gap = brentq(lambda g: field(0, 0, g) - B_TARGET_MT * 1e-3, 1e-3, 0.5)
        b0 = field(0, 0, gap)
        print(f"  {dia}x{ln} mm: gap {gap * 1e3:.1f} mm between the faces")
        for d in OFFSETS_MM:
            dz = abs(field(0, d / 1e3, gap) - b0)
            dr = abs(field(d / 1e3, 0, gap) - b0)
            print(f"    +-{d:.2f} mm: along the axis {dz * 1e6:5.1f} uT "
                  f"({dz * 1e3 * GAMMA_E:.3f} MHz), across {dr * 1e6:5.1f} uT "
                  f"({dr * 1e3 * GAMMA_E:.3f} MHz)")


if __name__ == "__main__":
    for b in FIELDS_MT:
        report(b)
    magnet_pair()
