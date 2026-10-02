"""
Can CW ODMR show that the ms=0 -> +1 and ms=0 -> -1 transitions of an NV are driven
COHERENTLY (i.e. that a |+1>,|-1> superposition is created) when the two resonances overlap?

Runs without hardware:   python analysis/nv_vsystem_cw_sim.py
Writes figures + summary.txt to analysis/vsystem_sim_out/.

MODEL
-----
Ground-state spin triplet {|+1>, |0>, |-1>} (index 0, 1, 2), rotating frame at the
microwave frequency f (all frequencies in MHz, times in us):

    H/2pi = (delta - df)|+1><+1| + (-delta - df)|-1><-1| + E(|+1><-1| + h.c.)
            + (Omega/2) (c+ |+1><0| + c- |-1><0| + h.c.)

    df = f - D, delta = gamma*B_par (+ A_hf * m_I), E = transverse strain/electric term.
    Linear MW polarisation at angle phi to the strain (E) axis: c+ = exp(-i phi),
    c- = exp(+i phi) (Omega = Rabi frequency of EACH transition); circular sigma+ at the
    same power: c+ = sqrt2, c- = 0. phi only matters when E != 0: phi = 0 drives the
    upper strain eigenstate (|+1>+|-1>)/sqrt2 at D+E, phi = 90 deg the lower one at D-E.
    The 14N nuclear Zeeman and quadrupole terms shift all three m_s levels of a given m_I
    equally, so they cancel from every ESR line; the transverse hyperfine is a ~kHz
    correction. Both are checked against the full 9-level Hamiltonian in main().
    The rotating-wave approximation drops the counter-rotating (2f) terms and any MW field
    component along the NV axis (a longitudinal term oscillating at f); both are checked
    against the full lab-frame time evolution in main().

Laser and relaxation as Lindblad operators (rates in 1/us):
    sqrt(gamma_p) |0><+-1|   optical repolarisation into ms=0 (via the singlet)
    sqrt(gamma_exc) |0><0|   optical cycling of ms=0: dephases 0 vs +-1 coherences
    sqrt(gamma_exc_pm) (|+1><+1| + |-1><-1|)
                             optical cycling of ms=+-1 (spin-conserving): dephases 0 vs +-1
                             coherences but NOT the +1/-1 coherence (default 0 = off)
    sqrt(2/T2) Sz            magnetic noise: SQ coherences decay at 1/T2, the DQ
                             (+1,-1) coherence at 4/T2
PL = p0 + (1 - C0)(p+1 + p-1)   (the readout is diagonal: it never sees rho_{+1,-1}).

INCOHERENT reference: rate equations between |0> and the EIGENSTATES a, b of the undriven
+-1 block [[delta, E], [E, -delta]] (energies +-sqrt(delta^2 + E^2)): the secular
approximation, which keeps populations and drops every coherence between eigenstates.
Each transition is driven at W = (Omega_k^2/2) G2/(G2^2 + Delta_k^2) (G2 = decay rate of the
0/a, 0/b coherence), and the Sz noise moves population a <-> b at (2/T2) |<a|Sz|b>|^2.
At E = 0 the eigenstates are |+1>, |-1> and this is the plain two-transition rate model.
For an isolated transition it reproduces the full Lindblad steady state exactly (checked
below), so any difference between the two models is due to coherence between the
(near-)degenerate upper states.

ENSEMBLE: average over a Gaussian spread of gamma*B_par (sigma, MHz rms; field
gradients + spin bath), over the three 14N hyperfine classes (m_I = -1, 0, +1), and,
with sigma_E > 0, over a random transverse E (Gaussian Ex, Ey with rms sigma_E per axis:
random size AND direction relative to the MW, as from nearby charges in a dense sample).

FIGURES
-------
fig1_spectra       coherent vs incoherent CW spectra as the two lines merge (single NV, ensemble)
fig2_ratio_test    R = peak contrast at degeneracy / peak of one isolated line vs MW power.
                   Ideal single NV, saturating drive: R = 1 (coherent) vs 4/3 (incoherent),
                   because coherent linear driving couples |0> only to (|+1>+|-1>)/sqrt2
                   and leaves (|+1>-|-1>)/sqrt2 dark.
fig3_washout       how that signature disappears: (a) static spread sigma (protected by the
                   drive, halves near sigma ~ 0.35 Omega); (b) fast DQ dephasing (halves when
                   4/T2 ~ gamma_p, independent of the drive)
fig4_lineshape     fitting a coherent ensemble spectrum with the incoherent model: the fit
                   absorbs the difference into Omega, sigma, C0 (residual ~1 % of peak)
fig5_time_domain   what does work: Rabi frequency sqrt2 larger at degeneracy, and
                   double-quantum Ramsey oscillating at 2*gamma*B (single NV and ensemble)
fig6_pl_vs_rabi    PL spectra for increasing MW power, coherent vs incoherent
fig7_strain        strain / electric field: (a) fixed E at several MW angles, (b) random E
                   spread sigma_E (single NV dynamics and a dense ensemble)

ASSUMPTIONS (edit below): rates are order-of-magnitude values for moderate laser power,
not measured for this rig; PL contrast C0 only scales the signals; optical cycling is
assumed NOT to destroy the +1/-1 coherence (the most favourable case for coherence);
transverse magnetic field components, the excited state and NV0 are not modelled.
"""

import os
import time

import matplotlib.pyplot as plt
import numpy as np
from numpy.polynomial.hermite_e import hermegauss
from numpy.polynomial.laguerre import laggauss
from scipy.linalg import expm
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "vsystem_sim_out")

# ---------------------------------------------------------------------------
# Parameters (MHz, us)
# ---------------------------------------------------------------------------
BASE = dict(
    Omega=1.0,        # single-transition Rabi frequency Omega/2pi with linear MW (MHz)
    gamma_p=0.2,      # optical repolarisation rate ms=+-1 -> 0 (1/us)
    gamma_exc=1.0,    # optical cycling rate of ms=0 (1/us)
    gamma_exc_pm=0.0, # optical cycling rate of ms=+-1 (1/us); physically ~gamma_exc, 0 = off
    T2=2.0,           # homogeneous SQ dephasing time (us)
    sigma=0.0,        # inhomogeneous rms spread of gamma*B_par (MHz)
    hf=False,         # include 14N hyperfine classes
    A=-2.16,          # 14N axial hyperfine (MHz)
    E=0.0,            # transverse strain/electric term (MHz), fixed (used when sigma_E = 0)
    phi=0.0,          # linear-MW polarisation angle to the strain axis (rad); only matters if E != 0
    sigma_E=0.0,      # random E: rms per axis of (Ex, Ey) (MHz); > 0 replaces E and phi
    nqE=10,           # quadrature nodes for |E| (Rayleigh distributed) when sigma_E > 0
    nphiE=8,          # quadrature nodes for the E direction when sigma_E > 0
    C0=0.3,           # PL contrast ms=+-1 vs 0
    pol="linear",
    nq=31,            # quadrature points over the Gaussian spread
)
IDEAL_SINGLE = dict(sigma=0.0, hf=False, T2=1000.0)                # isolated NV, no dephasing
ENSEMBLE = dict(sigma=0.5, hf=True, T2=2.0)                        # DNVB14-like (assumed)

POL = {"linear": (1.0, 1.0), "sigma+": (np.sqrt(2), 0.0), "sigma-": (0.0, np.sqrt(2))}
TWO_PI = 2 * np.pi
I3 = np.eye(3)
SZ = np.diag([1.0, 0.0, -1.0]).astype(complex)


def P(**kw):
    p = dict(BASE)
    p.update(kw)
    return p


def op(i, j):
    m = np.zeros((3, 3), complex)
    m[i, j] = 1.0
    return m


def bkron(A, B):
    """Batched Kronecker product over leading axes."""
    out = np.einsum("...ij,...kl->...ikjl", A, B)
    return out.reshape(out.shape[:-4] + (9, 9))


def dissipator(p, laser=True):
    Ls = [np.sqrt(2.0 / p["T2"]) * SZ]
    if laser:
        Ls += [np.sqrt(p["gamma_p"]) * op(1, 0), np.sqrt(p["gamma_p"]) * op(1, 2),
               np.sqrt(p["gamma_exc"]) * op(1, 1),
               np.sqrt(p["gamma_exc_pm"]) * (op(0, 0) + op(2, 2))]
    D = np.zeros((9, 9), complex)
    for L in Ls:
        LdL = L.conj().T @ L
        D += bkron(L.conj(), L) - 0.5 * bkron(I3, LdL) - 0.5 * bkron(LdL.T, I3)
    return D


def gamma2(p):
    return 0.5 * (p["gamma_p"] + p["gamma_exc"] + p["gamma_exc_pm"] + 2.0 / p["T2"])


def ensemble(p, delta0):
    """Ensemble members -> (delta, |E|, phi, weight), flat arrays of equal length.

    delta: Gaussian spread sigma (Gauss-Hermite) x 14N classes.
    E: fixed (p['E'], p['phi']) when sigma_E = 0; otherwise Ex, Ey ~ N(0, sigma_E^2), i.e.
    |E| Rayleigh (Gauss-Laguerre in |E|^2) and a uniform direction. The spectrum depends on
    the strain direction only through 2*phi, so phi is sampled uniformly over [0, pi).
    """
    if p["sigma"] > 0:
        x, w = hermegauss(p["nq"])
        w = w / w.sum()
    else:
        x, w = np.zeros(1), np.ones(1)
    mI = np.array([-1, 0, 1]) if p["hf"] else np.array([0])
    d = (delta0 + p["A"] * mI[:, None] + p["sigma"] * x[None, :]).ravel()
    wd = (np.ones(len(mI))[:, None] / len(mI) * w[None, :]).ravel()

    if p["sigma_E"] > 0:
        u, wu = laggauss(p["nqE"])                      # u = |E|^2 / (2 sigma_E^2) ~ Exp(1)
        ph = (np.arange(p["nphiE"]) + 0.5) * np.pi / p["nphiE"]
        Em, Ph = np.meshgrid(p["sigma_E"] * np.sqrt(2 * u), ph, indexing="ij")
        wE = np.outer(wu / wu.sum(), np.full(len(ph), 1.0 / len(ph)))
        Em, Ph, wE = Em.ravel(), Ph.ravel(), wE.ravel()
    else:
        Em, Ph, wE = np.array([float(p["E"])]), np.array([float(p["phi"])]), np.ones(1)

    n_d, n_e = len(d), len(Em)
    return (np.repeat(d, n_e), np.tile(Em, n_d), np.tile(Ph, n_d), np.outer(wd, wE).ravel())


def hamiltonian(df, d, E, phi, p):
    """Rotating-frame H (rad/us), shape (len(df), len(d), 3, 3); d, E, phi per member."""
    cp, cm = POL[p["pol"]]
    F, Dl = np.meshgrid(df, d, indexing="ij")
    H = np.zeros(F.shape + (3, 3), complex)
    H[..., 0, 0] = Dl - F
    H[..., 2, 2] = -Dl - F
    H[..., 0, 2] = H[..., 2, 0] = E[None, :]
    # <+-1| (cos(phi) Sx + sin(phi) Sy) |0> = exp(-+i phi)/sqrt2: in-plane MW angle -> relative phase
    vp = 0.5 * p["Omega"] * cp * np.exp(-1j * phi)[None, :]
    vm = 0.5 * p["Omega"] * cm * np.exp(1j * phi)[None, :]
    H[..., 0, 1], H[..., 1, 0] = vp, np.conj(vp)
    H[..., 2, 1], H[..., 1, 2] = vm, np.conj(vm)
    return TWO_PI * H


def contrast_coherent(df, delta0, p, max_batch=60000):
    """Ensemble-averaged CW contrast from the full Lindblad steady state."""
    d, E, ph, wt = ensemble(p, delta0)
    df = np.atleast_1d(np.asarray(df, float))
    Dm = dissipator(p)
    out = np.zeros(len(df))
    step = max(1, max_batch // len(df))              # members per chunk (bounds memory)
    for s in range(0, len(d), step):
        sl = slice(s, s + step)
        H = hamiltonian(df, d[sl], E[sl], ph[sl], p)
        L = -1j * (bkron(I3, H) - bkron(np.swapaxes(H, -1, -2), I3)) + Dm
        L[..., 0, :] = 0.0
        L[..., 0, [0, 4, 8]] = 1.0                   # trace(rho) = 1 replaces one equation
        b = np.zeros(L.shape[:-1] + (1,), complex)
        b[..., 0, 0] = 1.0
        x = np.linalg.solve(L, b)[..., 0]
        pp, p0, pm = x[..., 0].real, x[..., 4].real, x[..., 8].real
        out += (1 - (p0 + (1 - p["C0"]) * (pp + pm))) @ wt[sl]
    return out


def contrast_incoherent(df, delta0, p):
    """Secular rate model: |0> <-> eigenstates a (+r), b (-r) of [[delta, E], [E, -delta]]."""
    d, E, ph, wt = ensemble(p, delta0)
    cp, cm = POL[p["pol"]]
    g2, gp = gamma2(p), p["gamma_p"]
    F = np.atleast_1d(np.asarray(df, float))[:, None]

    r = np.hypot(d, E)
    th = np.arctan2(E, d)                            # a = (cos th/2, sin th/2), b = (-sin, cos)
    c, s = np.cos(th / 2), np.sin(th / 2)
    vp = 0.5 * p["Omega"] * cp * np.exp(-1j * ph)
    vm = 0.5 * p["Omega"] * cm * np.exp(1j * ph)
    ga, gb = c * vp + s * vm, -s * vp + c * vm       # <a|V|0>, <b|V|0>
    kab = (2.0 / p["T2"]) * np.sin(th) ** 2          # (2/T2) |<a|Sz|b>|^2

    def W(g, e):                                     # drive rate, Rabi frequency 2|g|
        return 0.5 * (TWO_PI * 2 * np.abs(g)) ** 2 * g2 / (g2 ** 2 + (TWO_PI * (e - F)) ** 2)

    Wa, Wb = W(ga, r), W(gb, -r)
    A, B = Wa + gp + kab, Wb + gp + kab
    det = A * B - kab ** 2
    xa, xb = (Wa * B + kab * Wb) / det, (Wb * A + kab * Wa) / det   # p_a/p0, p_b/p0
    p0 = 1.0 / (1.0 + xa + xb)
    pl = p0 + (1 - p["C0"]) * p0 * (xa + xb)
    return (1 - pl) @ wt


def span(p, delta0):
    return (abs(delta0) + (3 * abs(p["A"]) if p["hf"] else 0) + 5 * p["sigma"] + 3 * p["Omega"]
            + abs(p["E"]) + 4 * p["sigma_E"] + 2)


def peak_ratio(p, n=241, iso=25.0):
    """R = peak contrast with the two transitions degenerate / peak of one isolated line."""
    s0 = span(p, 0.0)
    df0 = np.linspace(-s0, s0, n)
    dfi = np.linspace(iso - s0, iso + s0, n)       # only the +1 line of the isolated pair
    iso_peak = contrast_incoherent(dfi, iso, p).max()   # coherent == incoherent when isolated
    return (contrast_coherent(df0, 0.0, p).max() / iso_peak,
            contrast_incoherent(df0, 0.0, p).max() / iso_peak)


def peak_signature(p, delta0=0.0, n=161):
    """(peak coherent / peak incoherent - 1, max |coherent - incoherent| / peak incoherent)."""
    s0 = span(p, delta0)
    df = np.linspace(-s0, s0, n)
    c, i = contrast_coherent(df, delta0, p), contrast_incoherent(df, delta0, p)
    return c.max() / i.max() - 1, np.max(np.abs(c - i)) / i.max()


# ---------------------------------------------------------------------------
# Time domain (no laser during the MW sequence)
# ---------------------------------------------------------------------------
def rabi(p, delta0, df, t):
    """Ensemble-averaged P0(t) for a MW pulse at offset df, starting in |0>."""
    d, E, ph, wt = ensemble(p, delta0)
    H = hamiltonian(np.array([df]), d, E, ph, p)[0]
    Dm = dissipator(p, laser=False)
    rho0 = np.zeros(9, complex)
    rho0[4] = 1.0
    out = np.zeros(len(t))
    dt = t[1] - t[0]
    for Hk, w in zip(H, wt):
        L = -1j * (np.kron(I3, Hk) - np.kron(Hk.T, I3)) + Dm
        U = expm(L * dt)
        r = rho0.copy()
        for i in range(len(t)):
            out[i] += w * r[4].real
            r = U @ r
    return out


def dominant_freq(t, y, pad=64, fmin=0.3):
    """Peak of the zero-padded, windowed spectrum above fmin (MHz for t in us).
    fmin skips the slow drift that the hyperfine classes add in the ensemble."""
    n = pad * len(t)
    yd = y - np.polyval(np.polyfit(t, y, 3), t)
    spec = np.abs(np.fft.rfft(yd * np.hanning(len(t)), n))
    f = np.fft.rfftfreq(n, t[1] - t[0])
    spec[f < fmin] = 0
    return f[np.argmax(spec)]


def ramsey(p, delta0, t, dq):
    """Ensemble-averaged P0(t) for ideal Ramsey with hard pulses, frame at D.

    SQ: pi/2 pulses on the upper eigen-transition |0> <-> a (= |+1> at E = 0), which precesses
        at r = sqrt(delta^2 + E^2):  P0 = [1 + e^{-t/T2} cos(2 pi r t)] / 2.
    DQ: pi pulses |0> <-> (|+1>+|-1>)/sqrt2 (Fang 2013, Mamin 2014). Free evolution under
        [[delta, E], [E, -delta]] returns to that state with probability
        1 - (delta/r)^2 sin^2(2 pi r t), i.e. P0 = 1 - (delta/r)^2 [1 - e^{-4t/T2} cos(4 pi r t)]/2,
        which is [1 + e^{-4t/T2} cos(2 pi 2 delta t)]/2 at E = 0. Strain (E along the MW axis
        here) both raises the frequency and reduces the visibility.
    """
    d, E, _, wt = ensemble(p, delta0)
    r = np.hypot(d, E)
    if not dq:
        osc = np.exp(-t / p["T2"])[:, None] * np.cos(TWO_PI * np.outer(t, r))
        return 0.5 * (1 + osc @ wt)
    vis = np.where(r > 0, (d / np.where(r > 0, r, 1.0)) ** 2, 1.0)
    osc = np.exp(-4 * t / p["T2"])[:, None] * np.cos(2 * TWO_PI * np.outer(t, r))
    return (1 - 0.5 * vis[None, :] * (1 - osc)) @ wt


# ---------------------------------------------------------------------------
# Validity checks of the model itself (Hamiltonian terms and the rotating-wave approximation)
# ---------------------------------------------------------------------------
D_ZFS = 2870.0          # MHz
GAMMA_E = 28.024        # MHz/mT
GAMMA_N14 = 3.077e-3    # MHz/mT (14N nuclear gyromagnetic ratio; H = -gamma_n B Iz)
A_PERP = -2.70          # MHz, 14N transverse hyperfine (Felton 2009)
P_QUAD = -4.945         # MHz, 14N quadrupole


def spin1():
    sx = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], complex) / np.sqrt(2)
    sy = np.array([[0, -1j, 0], [1j, 0, -1j], [0, 1j, 0]], complex) / np.sqrt(2)
    return sx, sy, SZ.copy()


def check_nuclear(b_mt, a_perp=A_PERP, gamma_n=GAMMA_N14, quad=P_QUAD, a_par=-2.16):
    """Max |ESR line position, full 9-level electron x 14N Hamiltonian - model| (kHz).

    Model: f(0 -> +-1, m_I) = D +- (gamma_e B + A_par m_I), i.e. no nuclear Zeeman,
    quadrupole or transverse hyperfine. Basis order |m_s> x |m_I>, both (+1, 0, -1).
    """
    sx, sy, sz = spin1()
    k = np.kron
    H = (D_ZFS * k(sz @ sz, I3) + GAMMA_E * b_mt * k(sz, I3) + a_par * k(sz, sz)
         + a_perp * (k(sx, sx) + k(sy, sy)) + quad * k(I3, sz @ sz - 2 / 3 * I3)
         - gamma_n * b_mt * k(I3, sz))
    ev, U = np.linalg.eigh(H)
    label = np.argmax(np.abs(U) ** 2, axis=0)        # basis index with the largest weight
    energy = {int(lb): e for lb, e in zip(label, ev)}
    dev = []
    for j, mI in enumerate((1, 0, -1)):
        e0 = energy[3 * 1 + j]                       # m_s = 0 block is index 1
        for i, ms in ((0, 1), (2, -1)):
            f_full = energy[3 * i + j] - e0
            f_model = D_ZFS + ms * (GAMMA_E * b_mt + a_par * mI)
            dev.append(f_full - f_model)
    return 1e3 * np.max(np.abs(dev))


def check_rwa(Omega, bz_ratio=0.0, phi=0.0, t_max=2.0, n_sub=400):
    """Max |P0(t), full lab-frame evolution - rotating-wave model| for a resonant Rabi pulse
    at B = 0 (degenerate V system), no dissipation.

    Lab frame:  H/h = D Sz^2 + Omega_L cos(2 pi f t) (cos phi Sx + sin phi Sy)
                      + bz_ratio * Omega_L cos(2 pi f t) Sz,       f = D,
    with Omega_L = sqrt2 * Omega so that each RWA coupling is Omega/2. bz_ratio is the MW field
    component along the NV axis relative to the transverse one: it keeps the counter-rotating
    (2f) terms AND the longitudinal term that the RWA model drops. Evolved exactly over one
    period (n_sub midpoint steps) and then stroboscopically, where the rotating and lab frames
    coincide.
    """
    sx, sy, sz = spin1()
    f = D_ZFS
    om_l = np.sqrt(2) * Omega
    T = 1.0 / f
    dt = T / n_sub
    U_T = np.eye(3, dtype=complex)
    for k in range(n_sub):
        c = np.cos(TWO_PI * f * (k + 0.5) * dt)
        H = (D_ZFS * sz @ sz + om_l * c * (np.cos(phi) * sx + np.sin(phi) * sy)
             + bz_ratio * om_l * c * sz)
        U_T = expm(-1j * TWO_PI * H * dt) @ U_T
    n = int(t_max / T)
    psi = np.array([0, 1, 0], complex)
    p_lab = np.empty(n)
    for i in range(n):
        p_lab[i] = abs(psi[1]) ** 2
        psi = U_T @ psi
    H_rwa = hamiltonian(np.array([0.0]), np.array([0.0]), np.array([0.0]), np.array([phi]),
                        P(Omega=Omega))[0, 0]
    ev, V = np.linalg.eigh(H_rwa)
    tt = np.arange(n) * T
    amp = (V[1, :] * V[1, :].conj())[None, :] * np.exp(-1j * np.outer(tt, ev))
    p_rwa = np.abs(amp.sum(axis=1)) ** 2
    return np.max(np.abs(p_lab - p_rwa))


# ---------------------------------------------------------------------------
def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    # ---- validation --------------------------------------------------------------
    df = np.linspace(20, 30, 401)
    p = P(**IDEAL_SINGLE, pol="sigma+")
    err = np.max(np.abs(contrast_coherent(df, 25.0, p) - contrast_incoherent(df, 25.0, p)))
    say(f"[check] single driven transition, Lindblad vs rate model: max |difference| = {err:.1e} (exact)")
    p = P(**IDEAL_SINGLE)
    err = np.max(np.abs(contrast_coherent(df, 25.0, p) - contrast_incoherent(df, 25.0, p)))
    say(f"[check] same with linear MW (other transition 50 MHz away): {err:.1e} "
        "(off-resonant light shift only)")
    ps = P(**IDEAL_SINGLE, Omega=20.0)
    c_coh = contrast_coherent([0.0], 0.0, ps)[0] / ps["C0"]
    c_inc = contrast_incoherent([0.0], 0.0, ps)[0] / ps["C0"]
    say(f"[check] single NV, degenerate, saturating linear drive: ms=0 depletion "
        f"coherent {c_coh:.3f} (theory 1/2), incoherent {c_inc:.3f} (theory 2/3)")
    e2 = np.max(np.abs(contrast_coherent(df - 25, 0.0, P(**IDEAL_SINGLE, pol="sigma+"))
                       - contrast_incoherent(df, 25.0, P(**IDEAL_SINGLE, pol="sigma+"))))
    say(f"[check] sigma+ at degeneracy == isolated line with sqrt2*Omega: max |diff| = {e2:.1e}")
    pa = P(**IDEAL_SINGLE, E=3.0, phi=0.0)
    dfa = np.linspace(-8, 8, 321)
    e3 = np.max(np.abs(contrast_coherent(dfa, 0.0, pa) - contrast_incoherent(dfa, 0.0, pa)))
    say(f"[check] strain E = 3 MHz along the MW axis, B = 0: Lindblad vs eigenstate rate model "
        f"max |diff| = {e3:.1e} (the drive addresses one strain eigenstate only)")

    say("\n[check] terms left out of the Hamiltonian: full 9-level electron x 14N model vs the "
        "model's ESR line positions")
    for b in (0.2, 10.0):
        full = check_nuclear(b)
        no_perp = check_nuclear(b, a_perp=0.0)
        no_gn = check_nuclear(b, gamma_n=0.0)
        say(f"    B = {b:5.1f} mT: max deviation {full:6.3f} kHz | without A_perp {no_perp:.1e} kHz "
            f"(nuclear Zeeman + quadrupole cancel exactly) | nuclear Zeeman alone moves it by "
            f"{abs(full - no_gn):.1e} kHz")
    say("[check] rotating-wave approximation: full lab-frame evolution (counter-rotating terms, "
        "MW component along the NV axis) vs the RWA model, resonant degenerate Rabi, 2 us")
    for om in (1.0, 10.0, 30.0):
        e_t = check_rwa(om, 0.0)
        e_l = check_rwa(om, 1.0)
        say(f"    Omega/2pi = {om:4.0f} MHz: max |dP0| transverse MW {e_t:.1e}, "
            f"MW at 45 deg to the NV axis (B1z = B1perp) {e_l:.1e}")

    # ---- figure 1: spectra ----------------------------------------------------------
    scen = [("Ideal single NV (no dephasing)", P(**IDEAL_SINGLE)),
            ("DNVB14-like ensemble (sigma 0.5 MHz, 14N, T2 2 us)", P(**ENSEMBLE))]
    deltas = [3.0, 0.5, 0.0]
    fig, axs = plt.subplots(2, 3, figsize=(13, 6.4), sharey="row")
    for r, (name, p) in enumerate(scen):
        for c, d0 in enumerate(deltas):
            s = span(p, d0)
            df = np.linspace(-s, s, 501)
            ch = contrast_coherent(df, d0, p)
            ic = contrast_incoherent(df, d0, p)
            ax = axs[r, c]
            ax.plot(df, 100 * ch, "C3", label="coherent (Lindblad)")
            ax.plot(df, 100 * ic, "k--", label="incoherent (rate model)")
            ax.plot(df, 100 * (ch - ic), "C0", lw=0.9, label="difference")
            ax.set_title(f"{name}\n$\\gamma B_\\parallel$ = {d0} MHz", fontsize=8.5)
            ax.set_xlabel("f - D (MHz)")
            if c == 0:
                ax.set_ylabel("ODMR contrast (%)")
            ax.grid(alpha=0.3)
    axs[0, 0].legend(fontsize=7)
    fig.suptitle(f"CW spectra, linear MW, Omega/2pi = {BASE['Omega']} MHz", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_spectra.png"), dpi=150)
    plt.close(fig)

    # ---- figure 2: normalisation-free test R vs MW power -------------------------------
    Om = np.geomspace(0.03, 10, 22)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    say("\nR = peak contrast at degeneracy / peak of one isolated line (linear MW):")
    scen2 = scen[:1] + [("Ensemble without 14N (sigma 0.5 MHz, T2 2 us)", P(sigma=0.5, hf=False, T2=2.0))] + scen[1:]
    for (name, base), col in zip(scen2, ["C3", "C2", "C0"]):
        R = np.array([peak_ratio(P(**{**base, "Omega": o})) for o in Om])
        ax.semilogx(Om, R[:, 0], color=col, label=f"{name}: coherent")
        ax.semilogx(Om, R[:, 1], color=col, ls="--", label=f"{name}: incoherent")
        say(f"  {name}: at Omega={Om[-6]:.2f} MHz  R_coh={R[-6,0]:.3f}  R_inc={R[-6,1]:.3f}")
    ax.axhline(4 / 3, color="0.6", lw=0.7, ls=":")
    ax.axhline(1.0, color="0.6", lw=0.7, ls=":")
    ax.set_xlabel("Rabi frequency $\\Omega/2\\pi$ per transition (MHz)  ~ sqrt(MW power)")
    ax.set_ylabel("R")
    ax.set_title("CW observable that coherence changes: degenerate vs isolated peak contrast", fontsize=9)
    ax.legend(fontsize=6.5)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig2_ratio_test.png"), dpi=150)
    plt.close(fig)

    # ---- figure 3: wash-out of the signature by inhomogeneity ---------------------------
    sig = np.geomspace(1e-3, 3, 16)
    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    say("\nSignature S = 1 - R_coh/R_inc (ideal value 1 - 3/4 = 0.25), no hyperfine:")
    say("  (a) static spread sigma, T2 = 1 ms  -> sigma at which S halves:")
    for om, col in zip([0.3, 1.0, 3.0], ["C0", "C1", "C3"]):
        S = np.array([1 - np.divide(*peak_ratio(P(sigma=s, hf=False, T2=1000.0, Omega=om, nq=21))) for s in sig])
        axs[0].semilogx(sig, S, color=col, marker="o", ms=3, label=f"$\\Omega/2\\pi$ = {om} MHz")
        half = sig[np.argmax(S < S[0] / 2)]
        say(f"      Omega {om:.1f} MHz: S(0) = {S[0]:.3f}, halves near sigma ~ {half:.2f} MHz")
    axs[0].set_xlabel("static spread of $\\gamma B_\\parallel$, $\\sigma$ (MHz rms)")
    axs[0].set_title("(a) static inhomogeneity: a stronger drive protects the signature", fontsize=9)
    T2s = np.geomspace(0.3, 1000, 16)
    say("  (b) homogeneous T2, sigma = 0, Omega = 1 MHz -> T2 at which S halves (compare 4/gamma_p):")
    for gp, col in zip([0.05, 0.2, 1.0, 5.0], ["C0", "C1", "C2", "C3"]):
        S = np.array([1 - np.divide(*peak_ratio(P(sigma=0.0, hf=False, T2=T2, gamma_p=gp))) for T2 in T2s])
        axs[1].semilogx(T2s, S, color=col, marker="o", ms=3, label=f"$\\Gamma_p$ = {gp} /us")
        half = T2s[np.argmax(S > S[-1] / 2)]
        say(f"      gamma_p {gp:4.2f}/us: halves near T2 ~ {half:.1f} us  (4/gamma_p = {4/gp:.0f} us)")
    axs[1].set_xlabel("homogeneous dephasing time $T_2$ (us)")
    axs[1].set_title("(b) fast dephasing: no protection from the drive; need $4/T_2 \\ll \\Gamma_p$", fontsize=9)
    for a in axs:
        a.set_ylabel("coherence signature  S = 1 - R$_{coh}$/R$_{inc}$")
        a.legend(fontsize=7)
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig3_washout.png"), dpi=150)
    plt.close(fig)

    # ---- figure 4: lineshape ambiguity (fit coherent ensemble with incoherent model) ------
    pe = P(**ENSEMBLE)
    s = span(pe, 0.0)
    df = np.linspace(-s, s, 401)
    data = contrast_coherent(df, 0.0, pe)

    def resid(x):
        return contrast_incoherent(df, 0.0, P(**{**ENSEMBLE, "Omega": x[0], "sigma": x[1], "C0": x[2]})) - data

    fit = least_squares(resid, [pe["Omega"], pe["sigma"], pe["C0"]],
                        bounds=([0.01, 0.01, 0.01], [20, 5, 1]))
    best = data + fit.fun
    rms = np.sqrt(np.mean(fit.fun ** 2)) / data.max()
    say(f"\nLineshape test (ensemble, degenerate): fitting the COHERENT spectrum with the INCOHERENT model")
    say(f"  free Omega, sigma, C0 -> Omega {fit.x[0]:.2f} (true {pe['Omega']}), sigma {fit.x[1]:.2f} "
        f"(true {pe['sigma']}), C0 {fit.x[2]:.3f} (true {pe['C0']})")
    say(f"  rms residual = {100*rms:.2f} % of the peak contrast")
    fig, axs = plt.subplots(2, 1, figsize=(7, 5), sharex=True, gridspec_kw=dict(height_ratios=[2, 1]))
    axs[0].plot(df, 100 * data, "C3", label="coherent model ('data')")
    axs[0].plot(df, 100 * best, "k--", label="best incoherent fit (Omega, sigma, C0 free)")
    axs[0].set_ylabel("contrast (%)")
    axs[0].legend(fontsize=7)
    axs[1].plot(df, 100 * fit.fun / data.max(), "C0")
    axs[1].set_ylabel("residual (% of peak)")
    axs[1].set_xlabel("f - D (MHz)")
    axs[0].set_title("Lineshape alone: incoherent model absorbs the coherence into fitted parameters",
                     fontsize=9)
    for a in axs:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig4_lineshape_ambiguity.png"), dpi=150)
    plt.close(fig)

    # ---- figure 5: time domain -------------------------------------------------------------
    t = np.linspace(0, 6.0, 601)
    tr = np.linspace(0, 4.0, 801)
    fig, axs = plt.subplots(2, 2, figsize=(12, 6.4))
    say("\nTime domain (no laser during MW):")
    for r, (name, base) in enumerate(scen):
        p = P(**base)
        deg = rabi(p, 0.0, 0.0, t)
        iso = rabi(p, 25.0, 25.0, t)
        ax = axs[r, 0]
        ax.plot(t, deg, "C3", label="degenerate, linear MW (both transitions)")
        ax.plot(t, iso, "k--", label="isolated transition")
        ax.set_title(f"Rabi: {name}", fontsize=8.5)
        ax.set_xlabel("pulse length (us)")
        ax.set_ylabel("P(ms=0)")
        f_deg, f_iso = dominant_freq(t, deg), dominant_freq(t, iso)
        say(f"  {name}: Rabi frequency degenerate/isolated = {f_deg:.2f}/{f_iso:.2f} MHz "
            f"(ratio {f_deg/f_iso:.2f}, sqrt2 = 1.41)")
        ax = axs[r, 1]
        d0 = 1.0
        ax.plot(tr, ramsey(p, d0, tr, dq=False), "k", lw=0.9, label="single-quantum (0<->+1)")
        ax.plot(tr, ramsey(p, d0, tr, dq=True), "C3", lw=0.9, label="double-quantum (+1,-1 superposition)")
        ax.set_title(f"Ramsey at $\\gamma B_\\parallel$ = {d0} MHz: {name}", fontsize=8.5)
        ax.set_xlabel("free evolution (us)")
        ax.set_ylabel("P(ms=0)")
        for a in axs[r]:
            a.legend(fontsize=6.5)
            a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig5_time_domain.png"), dpi=150)
    plt.close(fig)

    # ---- figure 6: PL spectra vs Rabi frequency, coherent vs incoherent ----------------------
    oms = [0.1, 0.3, 1.0, 3.0]
    cols = ["C0", "C2", "C1", "C3"]
    fig, axs = plt.subplots(2, 2, figsize=(12, 7.5), sharex="col")
    say("\nPL spectra vs Rabi frequency: minimum PL (normalised to MW off), coherent / incoherent:")
    for r, (name, base) in enumerate(scen):
        for c, d0 in enumerate([0.5, 0.0]):
            ax = axs[r, c]
            s = span(P(**{**base, "Omega": max(oms)}), d0)
            df = np.linspace(-s, s, 501)
            msg = []
            for om, col in zip(oms, cols):
                p = P(**{**base, "Omega": om})
                pl_c = 1 - contrast_coherent(df, d0, p)
                pl_i = 1 - contrast_incoherent(df, d0, p)
                ax.plot(df, pl_c, color=col, lw=1.4, label=f"$\\Omega/2\\pi$ = {om} MHz, coherent")
                ax.plot(df, pl_i, color=col, lw=1.1, ls="--", label=f"$\\Omega/2\\pi$ = {om} MHz, incoherent")
                msg.append(f"{om}: {pl_c.min():.3f}/{pl_i.min():.3f}")
            say(f"  {name}, gamma*B = {d0} MHz -> " + "  ".join(msg))
            ax.set_title(f"{name}\n$\\gamma B_\\parallel$ = {d0} MHz "
                         f"({'lines degenerate' if d0 == 0 else 'lines overlapping'})", fontsize=8.5)
            ax.set_ylabel("PL / PL(MW off)")
            ax.grid(alpha=0.3)
            if r == 1:
                ax.set_xlabel("f - D (MHz)")
    h, lab = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=4, fontsize=7.5)
    fig.suptitle("Photoluminescence spectra for increasing MW power: solid = coherent (Lindblad), "
                 "dashed = incoherent (rate model)", fontsize=10)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(os.path.join(OUT, "fig6_pl_vs_rabi.png"), dpi=150)
    plt.close(fig)

    # ---- figure 7: strain / electric field ---------------------------------------------------
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
    say("\nStrain / electric field E, B = 0, Omega/2pi = 1 MHz. Signature = peak coherent / peak "
        "incoherent (eigenstate rate model) - 1:")
    Es = np.geomspace(0.01, 10, 13)
    say("  (a) single ideal NV, fixed E, MW at angle phi to the strain axis:")
    for phi_deg, col in zip([0.0, 22.5, 45.0], ["C0", "C1", "C3"]):
        S = np.array([peak_signature(P(**IDEAL_SINGLE, E=e, phi=np.deg2rad(phi_deg)))[0] for e in Es])
        axs[0].semilogx(Es, 100 * S, color=col, marker="o", ms=3, label=f"phi = {phi_deg:g} deg")
        say(f"      phi {phi_deg:4.1f} deg: " + "  ".join(
            f"E={e:.2g}:{100*v:+.1f}%" for e, v in zip(Es[::3], S[::3])))
    axs[0].axhline(0, color="0.5", lw=0.8)
    axs[0].set_xlabel("transverse strain / electric term E (MHz)")
    axs[0].set_title("(a) single NV, fixed E: coherence matters only while E < Omega", fontsize=9)

    sEs = np.array([0.03, 0.1, 0.3, 1.0, 3.0])
    say("  (b) random E (Ex, Ey ~ N(0, sigma_E^2): random size and direction):")
    for (name, base), col in zip(
            [("ideal single-NV dynamics", P(**IDEAL_SINGLE)),
             ("dense ensemble (sigma 0.5, 14N, T2 2 us, +-1 cycling on)",
              P(**ENSEMBLE, nq=15, gamma_exc_pm=BASE["gamma_exc"]))], ["C3", "C0"]):
        s0 = peak_signature(base)
        S = np.array([peak_signature(P(**{**base, "sigma_E": se})) for se in sEs])
        axs[1].semilogx(sEs, 100 * S[:, 0], color=col, marker="o", ms=3, label=name)
        axs[1].axhline(100 * s0[0], color=col, ls=":", lw=1)
        say(f"      {name}: sigma_E = 0: {100*s0[0]:+.2f} %  | " + "  ".join(
            f"{se:g}: {100*v:+.2f} %" for se, v in zip(sEs, S[:, 0])))
        say(f"          max |coh - inc| / peak at the same sigma_E: " + "  ".join(
            f"{100*v:.1f} %" for v in S[:, 1]))
    axs[1].axhline(0, color="0.5", lw=0.8)
    axs[1].set_xlabel("random E spread $\\sigma_E$ (MHz rms per axis)")
    axs[1].set_title("(b) random E in an ensemble (dotted: same model at $\\sigma_E$ = 0)", fontsize=9)
    for a in axs:
        a.set_ylabel("peak coherent / peak incoherent - 1 (%)")
        a.legend(fontsize=7)
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig7_strain.png"), dpi=150)
    plt.close(fig)

    say(f"\n(run time {time.time()-t0:.0f} s; figures in {OUT})")
    with open(os.path.join(OUT, "summary.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
