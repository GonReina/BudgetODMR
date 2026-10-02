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

Laser and relaxation as Lindblad operators (rates in 1/us):
    sqrt(gamma_p) |0><+-1|   optical repolarisation into ms=0 (via the singlet)
    sqrt(gamma_exc) |0><0|   optical cycling of ms=0: dephases 0 vs +-1 coherences
    sqrt(gamma_exc_pm) (|+1><+1| + |-1><-1|)
                             optical cycling of ms=+-1 (spin-conserving): dephases 0 vs +-1
                             coherences but NOT the +1/-1 coherence (default 0 = off)
    sqrt(2/T2) Sz            magnetic noise: SQ coherences decay at 1/T2, the DQ
                             (+1,-1) coherence at 4/T2
PL = p0 + (1 - C0)(p+1 + p-1)   (the readout is diagonal: it never sees rho_{+1,-1}).

INCOHERENT reference: the same levels, the same rates, the same shared ms=0 population,
but each transition driven by an incoherent rate W = (Omega^2/2) G2/(G2^2 + Delta^2)
(G2 = decay rate of the 0/+-1 coherence). For an isolated transition this rate model
reproduces the full Lindblad steady state exactly (checked below), so any difference
between the two models near degeneracy is entirely due to the +1/-1 coherence.

ENSEMBLE: average over a Gaussian spread of gamma*B_par (sigma, MHz rms; field
gradients + spin bath) and over the three 14N hyperfine classes (m_I = -1, 0, +1).

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

ASSUMPTIONS (edit below): rates are order-of-magnitude values for moderate laser power,
not measured for this rig; PL contrast C0 only scales the signals; optical cycling is
assumed NOT to destroy the +1/-1 coherence (the most favourable case for coherence);
transverse field components, the excited state and NV0 are not modelled. The
incoherent reference ignores E, so the coherent/incoherent comparison is only
meaningful for E = 0 (the default everywhere below).
"""

import os
import time

import matplotlib.pyplot as plt
import numpy as np
from numpy.polynomial.hermite_e import hermegauss
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
    E=0.0,            # transverse strain/electric term (MHz)
    phi=0.0,          # linear-MW polarisation angle to the strain axis (rad); only matters if E != 0
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
    """Nodes (delta values, MHz) and weights for the ensemble average."""
    if p["sigma"] > 0:
        x, w = hermegauss(p["nq"])
        w = w / w.sum()
    else:
        x, w = np.zeros(1), np.ones(1)
    mI = np.array([-1, 0, 1]) if p["hf"] else np.array([0])
    d = delta0 + p["A"] * mI[:, None] + p["sigma"] * x[None, :]
    wt = np.ones(len(mI))[:, None] / len(mI) * w[None, :]
    return d.ravel(), wt.ravel()


def hamiltonian(df, d, p):
    cp, cm = POL[p["pol"]]
    F, Dl = np.meshgrid(df, d, indexing="ij")
    H = np.zeros(F.shape + (3, 3), complex)
    H[..., 0, 0] = Dl - F
    H[..., 2, 2] = -Dl - F
    H[..., 0, 2] = H[..., 2, 0] = p["E"]
    # <+-1| (cos(phi) Sx + sin(phi) Sy) |0> = exp(-+i phi)/sqrt2: in-plane MW angle -> relative phase
    vp = 0.5 * p["Omega"] * cp * np.exp(-1j * p["phi"])
    vm = 0.5 * p["Omega"] * cm * np.exp(1j * p["phi"])
    H[..., 0, 1], H[..., 1, 0] = vp, np.conj(vp)
    H[..., 2, 1], H[..., 1, 2] = vm, np.conj(vm)
    return TWO_PI * H


def contrast_coherent(df, delta0, p):
    """Ensemble-averaged CW contrast from the full Lindblad steady state."""
    d, wt = ensemble(p, delta0)
    H = hamiltonian(np.atleast_1d(df), d, p)
    L = -1j * (bkron(I3, H) - bkron(np.swapaxes(H, -1, -2), I3)) + dissipator(p)
    L[..., 0, :] = 0.0
    L[..., 0, [0, 4, 8]] = 1.0                       # trace(rho) = 1 replaces one equation
    b = np.zeros(L.shape[:-1] + (1,), complex)
    b[..., 0, 0] = 1.0
    x = np.linalg.solve(L, b)[..., 0]
    pp, p0, pm = x[..., 0].real, x[..., 4].real, x[..., 8].real
    pl = p0 + (1 - p["C0"]) * (pp + pm)
    return (1 - pl) @ wt


def contrast_incoherent(df, delta0, p):
    """Same levels and rates, both transitions as incoherent Lorentzian rates."""
    d, wt = ensemble(p, delta0)
    cp, cm = POL[p["pol"]]
    g2 = gamma2(p)
    F, Dl = np.meshgrid(np.atleast_1d(df), d, indexing="ij")

    def W(c, det):
        return 0.5 * (TWO_PI * p["Omega"] * c) ** 2 * g2 / (g2 ** 2 + (TWO_PI * det) ** 2)

    ap = W(cp, F - Dl) / (W(cp, F - Dl) + p["gamma_p"])
    am = W(cm, F + Dl) / (W(cm, F + Dl) + p["gamma_p"])
    p0 = 1.0 / (1.0 + ap + am)
    pl = p0 + (1 - p["C0"]) * p0 * (ap + am)
    return (1 - pl) @ wt


def span(p, delta0):
    return abs(delta0) + (3 * abs(p["A"]) if p["hf"] else 0) + 5 * p["sigma"] + 3 * p["Omega"] + 2


def peak_ratio(p, n=241, iso=25.0):
    """R = peak contrast with the two transitions degenerate / peak of one isolated line."""
    s0 = span(p, 0.0)
    df0 = np.linspace(-s0, s0, n)
    dfi = np.linspace(iso - s0, iso + s0, n)       # only the +1 line of the isolated pair
    iso_peak = contrast_incoherent(dfi, iso, p).max()   # coherent == incoherent when isolated
    return (contrast_coherent(df0, 0.0, p).max() / iso_peak,
            contrast_incoherent(df0, 0.0, p).max() / iso_peak)


# ---------------------------------------------------------------------------
# Time domain (no laser during the MW sequence)
# ---------------------------------------------------------------------------
def rabi(p, delta0, df, t):
    """Ensemble-averaged P0(t) for a MW pulse at offset df, starting in |0>."""
    d, wt = ensemble(p, delta0)
    H = hamiltonian(np.array([df]), d, p)[0]
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
    """Ensemble-averaged P0(t) for ideal SQ (0<->+1) or DQ (0<->(+1,-1)) Ramsey, frame at D."""
    d, wt = ensemble(p, delta0)
    k = 2.0 if dq else 1.0
    decay = np.exp(-(4.0 if dq else 1.0) * t / p["T2"])
    return 0.5 * (1 + decay * (np.cos(TWO_PI * k * np.outer(t, d)) @ wt))


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

    say(f"\n(run time {time.time()-t0:.0f} s; figures in {OUT})")
    with open(os.path.join(OUT, "summary.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
