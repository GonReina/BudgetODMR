
"""
nv_odmr.py — A calculator for NV-centre ground-state spin physics and CW-ODMR.

Physics follows the ground-state spin-1 Hamiltonian used in
  Doherty et al., Phys. Rep. 528, 1 (2013)  ("The NV colour centre in diamond")
  Maze et al., New J. Phys. 13, 025025 (2011) ("...group theoretic approach")

Ground-state spin Hamiltonian (in the NV frame, z along the N-V axis), in MHz:

    H/h = D (Sz^2 - 2/3)  +  E (Sx^2 - Sy^2)
          + gamma_e (Bx Sx + By Sy + Bz Sz)          [electron Zeeman]
          + A_par Sz Iz  (+ A_perp ... )              [hyperfine, secular part]

with S = 1. Units: frequencies in MHz, magnetic field in gauss (G).

Key constants (module-level, editable):
    D0        = 2870.0 MHz   zero-field splitting at 300 K
    dDdT      = -0.074 MHz/K temperature coefficient of D near 300 K
    GAMMA_E   = 2.8025 MHz/G electron gyromagnetic ratio (g ~ 2.003)
    A_PAR_14N = -2.16 MHz    axial hyperfine, 14N (I=1)
    A_PAR_15N =  3.03 MHz    axial hyperfine, 15N (I=1/2)
    P_14N     = -4.95 MHz    14N nuclear quadrupole (shifts, no 1st-order EPR split)
"""
import numpy as np

# ---- physical constants (edit if you use different reference values) ----
D0        = 2870.0     # MHz, zero-field splitting at ~300 K
dDdT      = -0.074     # MHz/K, dD/dT near room temperature
GAMMA_E   = 2.8025     # MHz/G  (=28.025 GHz/T)
A_PAR_14N = -2.16      # MHz
A_PAR_15N =  3.03      # MHz
P_14N     = -4.95      # MHz

# ---- spin-1 operators ----
Sz = np.diag([1.0, 0.0, -1.0])
Sx = (1/np.sqrt(2))*np.array([[0,1,0],[1,0,1],[0,1,0]], dtype=complex)
Sy = (1/np.sqrt(2))*np.array([[0,-1j,0],[1j,0,-1j],[0,1j,0]], dtype=complex)
I3 = np.eye(3)

# The four NV symmetry axes (unit vectors along <111>)
NV_AXES = {
    "[111]":   np.array([ 1, 1, 1])/np.sqrt(3),
    "[1-1-1]": np.array([ 1,-1,-1])/np.sqrt(3),
    "[-11-1]": np.array([-1, 1,-1])/np.sqrt(3),
    "[-1-11]": np.array([-1,-1, 1])/np.sqrt(3),
}

def D_of_T(T_kelvin, D_ref=D0, T_ref=300.0):
    """Zero-field splitting D(T) via linear coefficient near room temperature."""
    return D_ref + dDdT*(T_kelvin - T_ref)

def _rotation_to_axis(nhat):
    """Rotation matrix mapping lab z-hat onto NV axis nhat (so we can express B in the NV frame)."""
    z = np.array([0,0,1.0]); n = nhat/np.linalg.norm(nhat)
    v = np.cross(z, n); c = np.dot(z, n); s = np.linalg.norm(v)
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1,-1,-1.0])
    vx = np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3) + vx + vx@vx*((1-c)/s**2)

def hamiltonian(B_lab, axis="[111]", D=None, E=0.0, T=None):
    """
    Electron-spin 3x3 Hamiltonian (MHz) for one NV orientation.
    B_lab : magnetic field vector in gauss, lab frame (x,y,z) with z=[001].
    axis  : NV orientation key from NV_AXES, or a 3-vector.
    E     : transverse strain/electric-field splitting parameter (MHz).
    D,T   : give D directly, or give T (K) to compute D(T). Default D=D0.
    """
    if D is None:
        D = D0 if T is None else D_of_T(T)
    nhat = NV_AXES[axis] if isinstance(axis, str) else np.asarray(axis)/np.linalg.norm(axis)
    R = _rotation_to_axis(nhat)          # lab -> such that z_new = nhat
    Bnv = R.T @ np.asarray(B_lab, float) # components of B in the NV frame
    H = D*(Sz@Sz - (2/3)*I3) + E*(Sx@Sx - Sy@Sy) \
        + GAMMA_E*(Bnv[0]*Sx + Bnv[1]*Sy + Bnv[2]*Sz)
    return H

def transitions(B_lab, axis="[111]", D=None, E=0.0, T=None):
    """Return the two ms=0 -> ms=+/-1 ODMR transition frequencies (MHz), sorted.

    The ms=0-like state is identified as the eigenvector with the largest
    overlap on the |ms=0> basis ket (middle row in the [+1,0,-1] basis),
    which is robust to the -2/3 D offset and to strain/field mixing.
    """
    H = hamiltonian(B_lab, axis, D, E, T)
    w, v = np.linalg.eigh(H)
    w = w.real
    overlap0 = np.abs(v[1, :])**2          # |<ms=0 | eigenstate>|^2
    i0 = int(np.argmax(overlap0))          # the ms=0-like level
    others = [j for j in range(3) if j != i0]
    f = np.array([w[j] - w[i0] for j in others])
    return np.sort(f)

def hyperfine_lines(f_center, isotope="14N"):
    """Split an electronic ODMR line into hyperfine components (MHz positions)."""
    if isotope == "14N":
        A = abs(A_PAR_14N); return [f_center - A, f_center, f_center + A]   # 3 lines
    if isotope == "15N":
        A = abs(A_PAR_15N); return [f_center - A/2, f_center + A/2]         # 2 lines
    if isotope in ("none", "12C"):
        return [f_center]
    raise ValueError("isotope in {'14N','15N','none'}")

def odmr_spectrum(B_lab, axes="all", E=0.0, T=None, isotope="14N", D=None):
    """
    Full ensemble CW-ODMR dip list.
    axes : "all" (four orientations), or a list of axis keys, or one key.
    Returns sorted list of dip frequencies (MHz) with (axis, transition, mI) tags.
    """
    if axes == "all":
        keys = list(NV_AXES)
    elif isinstance(axes, str):
        keys = [axes]
    else:
        keys = list(axes)
    dips = []
    for k in keys:
        for f in transitions(B_lab, k, D=D, E=E, T=T):
            for fl in hyperfine_lines(f, isotope):
                dips.append((round(fl, 4), k, round(f,4)))
    dips.sort()
    return dips

def n_dips(B_lab, axes="all", E=0.0, T=None, isotope="14N", D=None, resolve_MHz=0.3):
    """Count distinct (resolvable) ODMR dips; lines closer than resolve_MHz merge."""
    freqs = sorted(d[0] for d in odmr_spectrum(B_lab, axes, E, T, isotope, D))
    merged = []
    for f in freqs:
        if not merged or f - merged[-1] > resolve_MHz:
            merged.append(f)
    return len(merged), merged

# ---------------- linewidths ----------------
def linewidth_from_T2star(T2star_us):
    """Intrinsic (unbroadened) FWHM of a Lorentzian CW-ODMR line, MHz.
       FWHM = 1/(pi*T2*)."""
    return 1.0/(np.pi*T2star_us)     # us -> MHz

def power_broadened_linewidth(T2star_us, s_opt=0.0, beta_mw=0.0):
    """
    Approximate CW-ODMR FWHM (MHz) including optical + MW power broadening:
        FWHM = (1/pi T2*) * sqrt(1 + s_opt + beta_mw)
    s_opt   : optical saturation parameter (I/I_sat)
    beta_mw : microwave broadening parameter ~ (Omega_R * T2*)^2 style term
    """
    return linewidth_from_T2star(T2star_us)*np.sqrt(1.0 + s_opt + beta_mw)

# ---------------- sensitivity ----------------
def sensitivity_cw(contrast, linewidth_MHz, photon_rate_per_s, P_F=0.70):
    """
    Shot-noise-limited DC magnetic sensitivity of CW-ODMR (T / sqrt(Hz)).
        eta ~ P_F * (4/(3 sqrt3)) * (h/(g muB)) * (Delta_nu)/(C sqrt(R))
    Here (g muB / h) = GAMMA_E; contrast C is fractional (0-1); R in counts/s.
    Returns eta in tesla / sqrt(Hz).
    """
    gamma_Hz_per_T = GAMMA_E*1e6*1e4     # MHz/G -> Hz/T
    dnu_Hz = linewidth_MHz*1e6
    R = photon_rate_per_s
    eta = P_F*(4/(3*np.sqrt(3)))*(1.0/gamma_Hz_per_T)*dnu_Hz/(contrast*np.sqrt(R))
    return eta

def sensitivity_sql(N_spins, T2star_us, contrast=1.0, readout_fidelity=1.0):
    """
    Standard-quantum-limit (Ramsey) DC sensitivity (T/sqrt(Hz)):
        eta ~ 1/(gamma_e * C * sqrt(N * T2*))
    with an optional readout-fidelity factor (1 = ideal spin-projection limit).
    """
    gamma_rad = 2*np.pi*GAMMA_E*1e6*1e4    # rad/s/T
    T2 = T2star_us*1e-6
    return 1.0/(gamma_rad*contrast*readout_fidelity*np.sqrt(N_spins*T2))
