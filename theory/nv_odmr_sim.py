"""
NV-centre ODMR physics: the 8-line spectrum of a diamond with all four NV
orientations in a magnetic field, plus field-magnitude estimators and a fit.

Ground-state spin-1 Hamiltonian (MHz units, ignoring strain E and hyperfine):
    H = D * Sz^2  +  gamma * (B . S)
D ~= 2870 MHz, gamma = 28.024 MHz/mT. Each of the four NV axes sees a different
projection of B, so a general field splits the line into up to 8 resonances
(4 orientations x 2 transitions ms=0 -> ms=+/-1).

Field-magnitude estimates provided:
  * from the TWO most prominent peaks (one orientation's pair): B_axial = df/(2*gamma)
    -- this is only the projection on that axis (a lower bound on |B|).
  * from all EIGHT peaks: pair them symmetrically about the centre to get the four
    axial splittings, then use  |B|^2 = (3/4) * sum_i B_par,i^2  (exact for the four
    tetrahedral NV axes) -- this recovers the true |B|.
  * (best) FIT the full 8-line Hamiltonian model to the spectrum for the field
    vector -> |B|. Needs scipy; falls back gracefully if scipy is absent.

numpy required; scipy optional (only for fit_field).
"""

import numpy as np

D_DEFAULT = 2870.0          # zero-field splitting, MHz
GAMMA = 28.024              # MHz/mT (electron gyromagnetic ratio, g~2.003)

# spin-1 operators
_S2 = np.sqrt(2.0)
SX = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=complex) / _S2
SY = np.array([[0, -1j, 0], [1j, 0, -1j], [0, 1j, 0]], dtype=complex) / _S2
SZ = np.array([[1, 0, 0], [0, 0, 0], [0, 0, -1]], dtype=complex)

# the four NV axes (crystal <111> directions), unit vectors
NV_AXES = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=float)
NV_AXES /= np.linalg.norm(NV_AXES, axis=1, keepdims=True)


def _axis_transitions(b_vec_mT, axis, D):
    """Two ms=0 -> ms=+/-1 transition frequencies for one NV axis (MHz)."""
    b_par = float(np.dot(b_vec_mT, axis))
    b_perp = float(np.linalg.norm(b_vec_mT - b_par * axis))
    H = D * (SZ @ SZ) + GAMMA * (b_par * SZ + b_perp * SX)
    ev = np.sort(np.linalg.eigvalsh(H).real)      # ms=0 state is lowest for our fields
    return ev[1] - ev[0], ev[2] - ev[0]


def eight_frequencies(b_vec_mT, D=D_DEFAULT):
    """Sorted list of the (up to) 8 NV transition frequencies for field vector b."""
    out = []
    for ax in NV_AXES:
        f1, f2 = _axis_transitions(np.asarray(b_vec_mT, float), ax, D)
        out += [f1, f2]
    return sorted(out)


def field_from_two_peaks(f_lo, f_hi):
    """Axial-projection field (mT) from one symmetric pair: |B_par| = df/(2 gamma)."""
    return abs(f_hi - f_lo) / (2 * GAMMA)


def field_from_eight_peaks(peaks_MHz):
    """|B| (mT) from 8 peaks: nested symmetric pairing -> 4 axial splittings ->
    |B| = sqrt(3/4 * sum B_par_i^2). Needs an even number of peaks (uses up to 8)."""
    p = sorted(peaks_MHz)
    m = len(p) // 2
    splits = [p[len(p) - 1 - k] - p[k] for k in range(m)]     # outer..inner pairs
    b_par = np.array(splits) / (2 * GAMMA)
    return float(np.sqrt(0.75 * np.sum(b_par ** 2))), splits


def lorentzian(f, c, fwhm):
    hw = fwhm / 2.0
    return hw * hw / ((f - c) ** 2 + hw * hw)


def model_am(f, b_vec_mT, D, fwhm, amp, baseline):
    """AM-ODMR spectrum: a positive Lorentzian peak at each of the 8 frequencies."""
    y = np.full_like(np.asarray(f, float), baseline)
    for c in eight_frequencies(b_vec_mT, D):
        y = y + amp * lorentzian(f, c, fwhm)
    return y


def _sph_to_vec(b, theta, phi):
    return b * np.array([np.sin(theta) * np.cos(phi),
                         np.sin(theta) * np.sin(phi), np.cos(theta)])


def frequencies_for_axes(b_vec_mT, axes_idx=(0, 1), D=D_DEFAULT):
    """Sorted transition frequencies for a SUBSET of the four NV axes. `axes_idx`
    selects which of NV_AXES (0..3) contribute, so (0, 1) models only two
    orientations (4 lines) instead of the full eight."""
    b = np.asarray(b_vec_mT, float)
    out = []
    for i in axes_idx:
        f1, f2 = _axis_transitions(b, NV_AXES[i], D)
        out += [f1, f2]
    return sorted(out)


def model_am_axes(f, b_vec_mT, axes_idx, D, fwhm, amp, baseline):
    """Positive-Lorentzian AM-ODMR spectrum using only the chosen NV axes."""
    y = np.full_like(np.asarray(f, float), baseline)
    for c in frequencies_for_axes(b_vec_mT, axes_idx, D):
        y = y + amp * lorentzian(f, c, fwhm)
    return y


def fit_field_axes(freq_MHz, signal, axes_idx=(0, 1), b_mag_guess_mT=1.0,
                   D=D_DEFAULT, fwhm=1.5):
    """Fit the spin-1 Hamiltonian for only the chosen NV axes (e.g. two
    orientations -> 4 lines) to a positive-going spectrum. Same (|B|, theta, phi)
    parameterisation as fit_field, with a coarse direction grid + bounded refine.

    NOTE: two orientations constrain |B| less tightly than the full 8-line fit --
    prefer fit_field() when all four orientations are visible. Returns a dict with
    |B|, the per-axis axial projections, the line positions and the fitted curve,
    or None if scipy is unavailable."""
    try:
        from scipy.optimize import least_squares
    except Exception:
        return None
    f = np.asarray(freq_MHz, float)
    y = np.asarray(signal, float)
    base0 = float(np.median(y))
    amp0 = float(np.max(y) - base0) or 1.0

    def resid(p):
        b, th, ph, d, w, a, base = p
        return model_am_axes(f, _sph_to_vec(b, th, ph), axes_idx, d,
                             max(abs(w), 0.05), a, base) - y

    b_hi = b_mag_guess_mT * 3 + 5
    lo = [0.0, 0.0, 0.0, D - 15, 0.1, 0.0, base0 - abs(amp0)]
    hi = [b_hi, np.pi, 2 * np.pi, D + 15, 20.0, amp0 * 10 + 1, base0 + abs(amp0)]

    # Target axial splittings from the data. Reduced symmetry with <4 axes creates a
    # "symmetric" local minimum that collapses the lines onto one splitting; matching
    # only the outer pair doesn't break it. So detect the peaks, pair them symmetrically
    # about D (nested outer..inner) to get the target axial projections, and seed each
    # trial DIRECTION with the |B| that best reproduces BOTH projections -- only the
    # correct geometry then scores well. Refine the best several seeds (multi-start).
    h = y - base0
    cand = sorted((i for i in range(1, len(f) - 1)
                   if h[i] > 0 and h[i] >= h[i - 1] and h[i] > h[i + 1]),
                  key=lambda i: -h[i])
    pk = []
    for i in cand:
        if all(abs(f[i] - f[j]) >= 1.5 for j in pk):
            pk.append(i)
        if len(pk) >= 2 * len(axes_idx):
            break
    fpk = sorted(f[i] for i in pk)
    npair = max(len(fpk) // 2, 1)
    targ = sorted(((fpk[len(fpk) - 1 - k] - fpk[k]) / (2 * GAMMA)
                   for k in range(npair)), reverse=True) if len(fpk) >= 2 \
        else [b_mag_guess_mT]
    targ = np.array(targ, float)

    # For each direction pick the |B| that best matches BOTH target splittings, then
    # score by the FULL model residual: matching projections fixes the axial structure,
    # while the residual rejects degenerate directions whose transverse field (b_perp)
    # shifts the exact eigenvalue lines away from the data.
    grid = []
    for th in np.linspace(0.05, np.pi, 20):
        for ph in np.linspace(0.0, 2 * np.pi, 20, endpoint=False):
            u = _sph_to_vec(1.0, th, ph)
            proj = np.sort([abs(float(np.dot(u, NV_AXES[i]))) for i in axes_idx])[::-1]
            p = proj[:len(targ)]
            denom = float(np.dot(p, p)) or 1e-9
            b_dir = float(np.clip(np.dot(p, targ) / denom, 0.0, b_hi))
            m = model_am_axes(f, b_dir * u, axes_idx, D, fwhm, amp0, base0)
            grid.append((float(np.sum((m - y) ** 2)), th, ph, b_dir))
    grid.sort(key=lambda t: t[0])

    best = None
    for _, th0, ph0, b0 in grid[:12]:
        p0 = [b0, th0, ph0, D, fwhm, amp0, base0]
        try:
            res = least_squares(resid, p0, bounds=(lo, hi), max_nfev=20000)
        except Exception:
            continue
        cost = float(np.sum(res.fun ** 2))
        if best is None or cost < best[0]:
            best = (cost, res)
    res = best[1]
    b, th, ph, d, w, a, base = res.x
    bvec = _sph_to_vec(b, th, ph)
    axial = [float(np.dot(bvec, NV_AXES[i])) for i in axes_idx]
    return {
        "B_mT": float(b),
        "B_vec_mT": bvec,
        "D_MHz": float(d),
        "fwhm_MHz": abs(float(w)),
        "axes_idx": tuple(axes_idx),
        "axial_projections_mT": axial,
        "peaks_MHz": frequencies_for_axes(bvec, axes_idx, d),
        "fit_curve": model_am_axes(f, bvec, axes_idx, d, abs(w), a, base),
        "success": bool(res.success),
    }


def fit_field(freq_MHz, signal, b_mag_guess_mT=1.0, D=D_DEFAULT, fwhm=1.5):
    """Fit the 8-line NV model to an AM spectrum for the field magnitude/direction.
    Parameterised by (|B|, theta, phi) with a coarse direction grid for the initial
    guess and bounded refinement so it can't diverge. Returns a dict with |B| (mT),
    the field vector, D, fwhm and the fitted curve, or None if scipy is absent."""
    try:
        from scipy.optimize import least_squares
    except Exception:
        return None
    f = np.asarray(freq_MHz, float)
    y = np.asarray(signal, float)
    base0 = float(np.median(y))
    amp0 = float(np.max(y) - base0) or 1.0

    # coarse grid over one octant to seed the direction (NV axes are symmetric)
    best = None
    for th in np.linspace(0.05, np.pi / 2, 10):
        for ph in np.linspace(0.0, np.pi / 2, 10):
            m = model_am(f, _sph_to_vec(b_mag_guess_mT, th, ph), D, fwhm, amp0, base0)
            r = float(np.sum((m - y) ** 2))
            if best is None or r < best[0]:
                best = (r, th, ph)
    _, th0, ph0 = best

    def resid(p):
        b, th, ph, d, w, a, base = p
        return model_am(f, _sph_to_vec(b, th, ph), d, max(abs(w), 0.05), a, base) - y

    p0 = [b_mag_guess_mT, th0, ph0, D, fwhm, amp0, base0]
    lo = [0.0, 0.0, 0.0, D - 15, 0.1, 0.0, base0 - abs(amp0)]
    hi = [b_mag_guess_mT * 3 + 5, np.pi, 2 * np.pi, D + 15, 20.0, amp0 * 10 + 1, base0 + abs(amp0)]
    res = least_squares(resid, p0, bounds=(lo, hi), max_nfev=20000)
    b, th, ph, d, w, a, base = res.x
    bvec = _sph_to_vec(b, th, ph)
    return {
        "B_mT": float(b),
        "B_vec_mT": bvec,
        "D_MHz": float(d),
        "fwhm_MHz": abs(float(w)),
        "peaks_MHz": eight_frequencies(bvec, d),
        "fit_curve": model_am(f, bvec, d, abs(w), a, base),
        "success": bool(res.success),
    }


# ===========================================================================
# Extended model: transverse strain / electric field (E) + 14N hyperfine,
# restricted to a chosen SUBSET of NV axes (the "complex" two-orientation model).
# ===========================================================================
A_N14_MHZ = 2.16       # 14N axial hyperfine: each electronic line -> triplet, ~2.16 MHz spacing
E_DEFAULT = 0.0        # transverse strain / electric-field splitting parameter (MHz)

# Sx^2 - Sy^2 for spin 1 couples ms=+1 <-> ms=-1; the strain term is E*(Sx^2 - Sy^2),
# which splits the ms=+/-1 doublet by 2E at zero field.
SX2_MINUS_SY2 = np.array([[0, 0, 1], [0, 0, 0], [1, 0, 0]], dtype=complex)


def _axis_transitions_ext(b_vec_mT, axis, D, E):
    """Two transition frequencies for one NV axis, including strain E (transverse
    principal axis taken along the transverse-field direction -- a scalar-E model)."""
    b_par = float(np.dot(b_vec_mT, axis))
    b_perp = float(np.linalg.norm(b_vec_mT - b_par * axis))
    H = D * (SZ @ SZ) + E * SX2_MINUS_SY2 + GAMMA * (b_par * SZ + b_perp * SX)
    ev = np.sort(np.linalg.eigvalsh(H).real)
    return ev[1] - ev[0], ev[2] - ev[0]


def frequencies_for_axes_ext(b_vec_mT, axes_idx=(0, 1), D=D_DEFAULT, E=E_DEFAULT):
    """Electronic transition frequencies (no hyperfine) for the chosen NV axes,
    including strain E."""
    b = np.asarray(b_vec_mT, float)
    out = []
    for i in axes_idx:
        f1, f2 = _axis_transitions_ext(b, NV_AXES[i], D, E)
        out += [f1, f2]
    return sorted(out)


def model_am_axes_ext(f, b_vec_mT, axes_idx, D, E, fwhm, amp, baseline, a_hf=A_N14_MHZ):
    """Positive-Lorentzian spectrum for the chosen NV axes, with strain E and (if
    a_hf > 0) the 14N hyperfine triplet -- each electronic line becomes three equal
    lines at f + m*a_hf, m in {-1, 0, +1}. Setting E=0 and a_hf=0 reduces exactly to
    model_am_axes (the simple Zeeman-only model)."""
    y = np.full_like(np.asarray(f, float), baseline)
    ms = (-1, 0, 1) if a_hf > 0 else (0,)
    w = amp / len(ms)
    for c in frequencies_for_axes_ext(b_vec_mT, axes_idx, D, E):
        for m in ms:
            y = y + w * lorentzian(f, c + m * a_hf, fwhm)
    return y


def fit_field_axes_ext(freq_MHz, signal, axes_idx=(0, 1), b_mag_guess_mT=1.0,
                       D=D_DEFAULT, fwhm=1.0, a_hf=A_N14_MHZ, E=0.0, fit_E=False,
                       e_max=15.0):
    """Two-orientation fit with the COMPLEX model: the 14N hyperfine triplet (a_hf, a
    KNOWN constant, ~2.16 MHz) plus transverse strain E.

    Identifiability: hyperfine adds real, resolvable structure and is always included.
    Strain, however, is NOT separable from the transverse magnetic field with only two
    orientations at low field -- both split the lines the same way, so a free per-point
    E just trades off against |B|. Therefore E is held FIXED at `E` by default (measure
    it once from a near-zero-field spectrum, where the split is 2E, and pass it in). Set
    fit_E=True to let E float anyway, but treat the resulting |B|/E split with caution.

    Fits (|B|, theta, phi, D, [E], fwhm, amp, baseline). Returns a dict adding E_MHz,
    a_hf_MHz and fit_E, or None if scipy is unavailable."""
    try:
        from scipy.optimize import least_squares
    except Exception:
        return None
    f = np.asarray(freq_MHz, float)
    y = np.asarray(signal, float)
    base0 = float(np.median(y))
    amp0 = float(np.max(y) - base0) or 1.0
    E0 = abs(float(E))

    if fit_E:
        def resid(p):
            b, th, ph, d, Ev, w, a, base = p
            return model_am_axes_ext(f, _sph_to_vec(b, th, ph), axes_idx, d, abs(Ev),
                                     max(abs(w), 0.05), a, base, a_hf) - y
    else:
        def resid(p):
            b, th, ph, d, w, a, base = p
            return model_am_axes_ext(f, _sph_to_vec(b, th, ph), axes_idx, d, E0,
                                     max(abs(w), 0.05), a, base, a_hf) - y

    b_hi = b_mag_guess_mT * 3 + 5

    # --- robust seeding: target splittings -> direction grid scored by the simple
    #     (Zeeman) model, scaling |B| per direction to match. Group the hyperfine
    #     triplet (peak separation >= ~1.5*a_hf) so its sub-lines aren't mistaken for
    #     separate orientations. ---
    sep = max(1.5, 1.5 * a_hf) if a_hf > 0 else 1.5
    h = y - base0
    cand = sorted((i for i in range(1, len(f) - 1)
                   if h[i] > 0 and h[i] >= h[i - 1] and h[i] > h[i + 1]),
                  key=lambda i: -h[i])
    pk = []
    for i in cand:
        if all(abs(f[i] - f[j]) >= sep for j in pk):
            pk.append(i)
        if len(pk) >= 2 * len(axes_idx):
            break
    fpk = sorted(f[i] for i in pk)
    npair = max(len(fpk) // 2, 1)
    targ = sorted(((fpk[len(fpk) - 1 - k] - fpk[k]) / (2 * GAMMA)
                   for k in range(npair)), reverse=True) if len(fpk) >= 2 \
        else [b_mag_guess_mT]
    targ = np.array(targ, float)

    grid = []
    for th in np.linspace(0.05, np.pi, 20):
        for ph in np.linspace(0.0, 2 * np.pi, 20, endpoint=False):
            u = _sph_to_vec(1.0, th, ph)
            proj = np.sort([abs(float(np.dot(u, NV_AXES[i]))) for i in axes_idx])[::-1]
            p = proj[:len(targ)]
            b_dir = float(np.clip(np.dot(p, targ) / (float(np.dot(p, p)) or 1e-9), 0.0, b_hi))
            m = model_am_axes_ext(f, b_dir * u, axes_idx, D, E0, fwhm, amp0, base0, a_hf)
            grid.append((float(np.sum((m - y) ** 2)), th, ph, b_dir))
    grid.sort(key=lambda t: t[0])

    if fit_E:
        lo = [0.0, 0.0, 0.0, D - 15, 0.0, 0.1, 0.0, base0 - abs(amp0)]
        hi = [b_hi, np.pi, 2 * np.pi, D + 15, e_max, 20.0, amp0 * 10 + 1, base0 + abs(amp0)]
        seed = lambda b0, th0, ph0: [b0, th0, ph0, D, E0, fwhm, amp0, base0]
    else:
        lo = [0.0, 0.0, 0.0, D - 15, 0.1, 0.0, base0 - abs(amp0)]
        hi = [b_hi, np.pi, 2 * np.pi, D + 15, 20.0, amp0 * 10 + 1, base0 + abs(amp0)]
        seed = lambda b0, th0, ph0: [b0, th0, ph0, D, fwhm, amp0, base0]

    best = None
    for _, th0, ph0, b0 in grid[:12]:
        try:
            res = least_squares(resid, seed(b0, th0, ph0), bounds=(lo, hi), max_nfev=20000)
        except Exception:
            continue
        cost = float(np.sum(res.fun ** 2))
        if best is None or cost < best[0]:
            best = (cost, res)
    res = best[1]
    if fit_E:
        b, th, ph, d, Ev, w, a, base = res.x
        E_out = abs(float(Ev))
    else:
        b, th, ph, d, w, a, base = res.x
        E_out = E0
    bvec = _sph_to_vec(b, th, ph)
    axial = [float(np.dot(bvec, NV_AXES[i])) for i in axes_idx]
    return {
        "B_mT": float(b),
        "B_vec_mT": bvec,
        "D_MHz": float(d),
        "E_MHz": E_out,
        "a_hf_MHz": float(a_hf),
        "fit_E": bool(fit_E),
        "fwhm_MHz": abs(float(w)),
        "axes_idx": tuple(axes_idx),
        "axial_projections_mT": axial,
        "peaks_MHz": frequencies_for_axes_ext(bvec, axes_idx, d, E_out),
        "fit_curve": model_am_axes_ext(f, bvec, axes_idx, d, E_out, abs(w), a, base, a_hf),
        "success": bool(res.success),
    }
