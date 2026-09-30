"""
Optical model shared by notebooks/Optical_Setup.ipynb.

Four levels of model, used where each is physically appropriate:

1. Gaussian beam propagation (paraxial, ABCD / complex-q).  Laser and fibre-mode
   beams between components, low-NA focusing, clipping on apertures.
2. Scalar Debye focusing integral.  High-NA focal spots (objective), truncated-
   Gaussian pupil fill, focusing through the air/diamond interface including the
   spherical aberration it causes, confocal detection PSF.  Scalar: polarisation
   and vectorial effects at NA 0.75 are ignored (they change FWHMs by ~5-10 %).
3. Geometric Monte-Carlo ray trace.  Collection of isotropic NV emission from an
   extended excited volume: exact Snell/Fresnel at the diamond surface, total
   internal reflection, ideal (aplanatic, sine-condition) collection lens, then
   paraxial propagation through the collimated space to the detector.
4. Closed-form estimates (etendue, NA, Airy unit, Malus law, plate shifts).

SI units throughout (metres, watts, radians).  Plot helpers convert for display.
"""

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.special import j0

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_DIAMOND = 2.42              # refractive index of diamond (2.425 @ 532 nm, 2.41 @ 700 nm)
C_ATOM_DENSITY = 1.763e29     # carbon atoms per m^3 in diamond
UM, MM = 1e-6, 1e-3

# ---------------------------------------------------------------------------
# 1. Gaussian beams (reduced complex-q: q_hat = q / n, so a flat interface is
#    the identity and w is independent of the medium)
# ---------------------------------------------------------------------------


def q_from_waist(w0, lam0, dz=0.0, n=1.0):
    """Reduced q at distance dz (in medium n) after a waist of 1/e^2 radius w0."""
    return dz / n + 1j * np.pi * w0 ** 2 / lam0


def q_propagate(qh, d, n=1.0):
    return qh + d / n


def q_lens(qh, f):
    return 1.0 / (1.0 / qh - 1.0 / f)


def q_radius(qh, lam0):
    """1/e^2 intensity radius."""
    return np.sqrt(-lam0 / (np.pi * np.imag(1.0 / qh)))


def q_waist(qh, lam0, n=1.0):
    """(waist radius, distance from here to the waist in medium n; >0 = ahead)."""
    return np.sqrt(lam0 * np.imag(qh) / np.pi), -np.real(qh) * n


def gauss_clip(w, a):
    """Power fraction of a centred Gaussian (1/e^2 radius w) through a circle of radius a."""
    return 1.0 - np.exp(-2.0 * a ** 2 / w ** 2)


def fibre_mode_divergence(mfd, lam0):
    """1/e^2 far-field half-angle of a single-mode fibre, Gaussian LP01 approximation."""
    return lam0 / (np.pi * mfd / 2)


def collimated_diameter(mfd, lam0, f):
    """1/e^2 beam diameter after a collimator of focal length f (D = 4 lam f / (pi MFD))."""
    return 4 * lam0 * f / (np.pi * mfd)


def mode_match(w1, w2):
    """Power overlap of two co-axial Gaussian waists (no tilt/offset)."""
    return (2 * w1 * w2 / (w1 ** 2 + w2 ** 2)) ** 2


def gaussian_focus(w_in, f, lam0, n=1.0):
    """Low-NA Gaussian focusing of a collimated beam of radius w_in by lens f.

    Returns dict: waist radius w0 (same in air and in medium n), Rayleigh range in
    the medium, far-field half-angle in the medium, effective NA in air (w_in/f).
    Valid while w_in/f << 1 (paraxial) and w_in well inside the lens aperture."""
    w0 = lam0 * f / (np.pi * w_in)
    return dict(w0=w0, zR=np.pi * w0 ** 2 * n / lam0,
                theta=lam0 / (np.pi * n * w0), NA_eff=w_in / f)


def beam_in_diamond(w_in, f, lam0, z_focus, depth, n=N_DIAMOND):
    """1/e^2 radius of a low-NA focused Gaussian inside the diamond at depths `depth`
    (array) when the waist sits at depth z_focus below the surface."""
    g = gaussian_focus(w_in, f, lam0, n)
    return g["w0"] * np.sqrt(1 + ((np.asarray(depth) - z_focus) / g["zR"]) ** 2)


def trace_gaussian(w0, lam0, elements, dz0=0.0, n0=1.0, npts=60):
    """Propagate a Gaussian through a list of elements.

    elements: sequence of
        ("space", length, n)          free propagation
        ("lens", f, name)             thin lens
        ("aperture", radius, name)    record clipping (no truncation applied)
    Returns (z, w, table): cumulative geometric path z, radius w along it, and
    a list of dicts (name, z, w, clip) at every lens/aperture."""
    qh = q_from_waist(w0, lam0, dz0, n0)
    zs, ws, table, z = [0.0], [q_radius(qh, lam0)], [], 0.0
    for el in elements:
        kind = el[0]
        if kind == "space":
            L, n = el[1], el[2]
            for d in np.linspace(L / npts, L, npts):
                zs.append(z + d)
                ws.append(q_radius(q_propagate(qh, d, n), lam0))
            qh, z = q_propagate(qh, L, n), z + L
        elif kind == "lens":
            w = q_radius(qh, lam0)
            table.append(dict(name=el[2], z=z, w=w, clip=None))
            qh = q_lens(qh, el[1])
        elif kind == "aperture":
            w = q_radius(qh, lam0)
            table.append(dict(name=el[2], z=z, w=w, clip=1 - gauss_clip(w, el[1])))
    return np.array(zs), np.array(ws), table, qh


# ---------------------------------------------------------------------------
# 2. Scalar Debye focusing (with optional air -> medium interface)
# ---------------------------------------------------------------------------


def fresnel_T(cos_i, n1, n2):
    """Unpolarised power transmission n1 -> n2 at incidence cosine cos_i (0 beyond TIR)."""
    cos_i = np.asarray(cos_i, float)
    sin_t = n1 / n2 * np.sqrt(np.clip(1 - cos_i ** 2, 0, None))
    ok = sin_t < 1
    cos_t = np.sqrt(np.clip(1 - sin_t ** 2, 0, None))
    rs = (n1 * cos_i - n2 * cos_t) / (n1 * cos_i + n2 * cos_t)
    rp = (n2 * cos_i - n1 * cos_t) / (n2 * cos_i + n1 * cos_t)
    return np.where(ok, 1 - 0.5 * (rs ** 2 + rp ** 2), 0.0)


class Focus:
    """Scalar Debye focus of an aplanatic lens (sine condition), s = n1 sin(theta1).

    lam0     vacuum wavelength
    NA       lens NA in air
    f        lens focal length (sets the pupil scale for w_pupil)
    w_pupil  1/e^2 radius of a Gaussian beam at the pupil; None = uniform pupil
    n2       index of the medium containing the focus (1 = air sample)
    t_cg     cover-glass thickness the objective is corrected for (0 = none);
             with no cover glass present this leaves residual spherical aberration
    fresnel  include the unpolarised air/medium Fresnel amplitude
    """

    def __init__(self, lam0, NA, f, w_pupil=None, n2=1.0, t_cg=0.0, n_cg=1.523,
                 fresnel=True, nq=600):
        self.lam0, self.NA, self.f, self.n2 = lam0, NA, f, n2
        self.t_cg, self.n_cg = t_cg, n_cg
        self.k0 = 2 * np.pi / lam0
        x, w = leggauss(nq)
        self.s = 0.5 * NA * (x + 1)
        self.ws = 0.5 * NA * w
        c1 = np.sqrt(1 - self.s ** 2)
        A = np.ones_like(self.s) if w_pupil is None else np.exp(-(f * self.s) ** 2 / w_pupil ** 2)
        P = A / np.sqrt(c1)
        if fresnel and n2 != 1.0:
            P = P * np.sqrt(fresnel_T(c1, 1.0, n2))
        self.P = P
        self.kz1 = c1
        self.kz2 = np.sqrt(n2 ** 2 - self.s ** 2)
        self.psi = -self.k0 * t_cg * (np.sqrt(n_cg ** 2 - self.s ** 2) - c1) if t_cg else 0.0
        # Parseval: integral |E|^2 dA over any plane
        self.total = 2 * np.pi / self.k0 ** 2 * np.sum(self.ws * np.abs(self.P) ** 2 * self.s)
        self.E0_ideal = np.sum(self.ws * self.P * self.s)   # aberration-free on-axis peak field

    def field(self, r, z, z_f=0.0):
        """Complex field on grid (len(z), len(r)).  z = depth in medium n2 below the
        interface (or defocus from nominal focus if n2 == 1 and z_f == 0); z_f = where
        the lens would focus in air measured from the interface (i.e. stage position)."""
        r, z = np.atleast_1d(r), np.atleast_1d(z)
        phase = self.k0 * (np.outer(z, self.kz2) - z_f * self.kz1) + self.psi
        M = np.exp(1j * phase) * (self.ws * self.P * self.s)
        return M @ j0(self.k0 * np.outer(self.s, r))

    def intensity(self, r, z, z_f=0.0):
        return np.abs(self.field(r, z, z_f)) ** 2

    def best_focus(self, depth):
        """Stage position z_f maximising on-axis intensity at a point `depth` into the
        medium.  Returns (z_f, Strehl) with Strehl relative to the aberration-free
        pupil.  Grid search then golden refinement (the SA landscape is multimodal)."""
        zf_par = depth / self.n2
        self_cg = self.t_cg * (1 - 1 / self.n_cg)     # paraxial shift from the missing cover glass
        grid = np.linspace(0.25 * zf_par - 3e-6, 1.3 * zf_par + self_cg + 3e-6, 1601)
        ph0 = self.k0 * depth * self.kz2 + self.psi
        amp = self.ws * self.P * self.s

        def I(zf):
            return np.abs(np.sum(amp * np.exp(1j * (ph0 - self.k0 * zf * self.kz1)))) ** 2
        vals = np.array([I(g) for g in grid])
        i = int(np.argmax(vals))
        a, b = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
        for _ in range(60):
            m1, m2 = a + 0.382 * (b - a), a + 0.618 * (b - a)
            if I(m1) > I(m2):
                b = m2
            else:
                a = m1
        zf = 0.5 * (a + b)
        return zf, I(zf) / np.abs(self.E0_ideal) ** 2

    def encircled(self, a, z, z_f=0.0, nr=400):
        """Fraction of the total focused power inside radius a at plane(s) z."""
        r = np.linspace(0, a, nr)
        I = self.intensity(r, z, z_f)
        return np.trapezoid(I * 2 * np.pi * r, r, axis=1) / self.total


def fwhm(x, y):
    """Full width at half maximum of a single-peaked profile (linear interpolation)."""
    y = np.asarray(y) / np.max(y)
    i = int(np.argmax(y))
    left = np.where(y[:i] < 0.5)[0]
    right = np.where(y[i:] < 0.5)[0]
    if len(left) == 0 or len(right) == 0:
        return np.nan
    l, r = left[-1], i + right[0]
    xl = np.interp(0.5, [y[l], y[l + 1]], [x[l], x[l + 1]])
    xr = np.interp(0.5, [y[r], y[r - 1]], [x[r], x[r - 1]])
    return xr - xl


def radial_fwhm(r, I):
    """FWHM of a radial profile I(r), r >= 0."""
    I = np.asarray(I) / I[0]
    j = np.where(I < 0.5)[0]
    if len(j) == 0:
        return np.nan
    j = j[0]
    return 2 * np.interp(0.5, [I[j], I[j - 1]], [r[j], r[j - 1]])


def airy_unit(lam0, NA):
    """Airy disc diameter (first zero), 1.22 lam / NA, in object space."""
    return 1.22 * lam0 / NA


def pinhole_detection_map(focus, r, z, a_obj, z_f=0.0, half=10e-6, N=256):
    """D(r, z): fraction of the light from a point emitter at (r, z) that passes a
    pinhole whose back-projection into object space has radius a_obj (reciprocity:
    detection PSF convolved with the pinhole disc).  Returns array (len(z), len(r))."""
    x = np.linspace(-half, half, N)
    dx = x[1] - x[0]
    X, Y = np.meshgrid(x, x)
    R = np.hypot(X, Y)
    rr = np.linspace(0, half * np.sqrt(2) * 1.01, 600)
    disc = (R <= a_obj).astype(float)
    Fd = np.fft.rfft2(np.fft.ifftshift(disc))
    out = np.empty((len(z), len(r)))
    for i, zz in enumerate(np.atleast_1d(z)):
        prof = focus.intensity(rr, zz, z_f)[0]
        img = np.interp(R, rr, prof)
        conv = np.fft.irfft2(np.fft.rfft2(img) * Fd, s=img.shape) * dx * dx
        out[i] = np.interp(r, x[N // 2:], conv[N // 2, N // 2:]) / focus.total
    return out


# ---------------------------------------------------------------------------
# 3. Monte-Carlo collection of isotropic emission from inside the diamond
# ---------------------------------------------------------------------------


def sample_gaussian_column(n, w_of_depth, thickness, alpha=0.0, rng=None):
    """Emitter positions for linear (unsaturated) excitation by a beam whose 1/e^2
    radius at depth z is w_of_depth(z); Beer-Lambert absorption alpha [1/m].
    Every depth slice carries the same beam power (x exp(-alpha z)), so depth is
    sampled from exp(-alpha z) and radius from the Gaussian profile at that depth."""
    rng = np.random.default_rng(rng)
    if alpha > 0:
        u = rng.random(n)
        z = -np.log(1 - u * (1 - np.exp(-alpha * thickness))) / alpha
    else:
        z = rng.random(n) * thickness
    w = w_of_depth(z)
    r = w * np.sqrt(-np.log(1 - rng.random(n)) / 2)
    ph = 2 * np.pi * rng.random(n)
    return np.column_stack([r * np.cos(ph), r * np.sin(ph), z])


def mc_collect(emitters, *, f, NA, z_f, stops=(), f2, L2, d2, det, n=N_DIAMOND,
               rng=None, return_rays=False):
    """Trace one isotropic ray per emitter through the collection path.

    Geometry (collimated-space coordinates measured from the collection lens pupil):
      diamond surface -> ideal aplanatic lens (focal length f, NA): a ray leaving the
      front focal plane at transverse position x' with direction cosines (u, v)
      exits at pupil height f*(u, v) with angle -x'/f.  The front focal plane sits at
      air-distance z_f below the diamond surface (= where the lens is focused).
      stops: list of (distance, shape) with shape ("circle", r) or ("rect", hx, hy)
      f2, L2: detector lens and its distance from the pupil; d2: lens -> detector.
      det: ("circle", r) detector or pinhole aperture.
    Returns dict of fractions of ALL emitted photons (4 pi) surviving each stage."""
    rng = np.random.default_rng(rng)
    N = len(emitters)
    x0, y0, zd = emitters.T
    cth = rng.random(N)                        # upward hemisphere, isotropic
    sth = np.sqrt(1 - cth ** 2)
    ph = 2 * np.pi * rng.random(N)
    xs = x0 + zd * sth / cth * np.cos(ph)       # point on the surface
    ys = y0 + zd * sth / cth * np.sin(ph)
    sa = n * sth                                # sin(theta) in air
    esc = sa < 1
    T = np.where(esc, fresnel_T(cth, n, 1.0), 0.0)
    ca = np.sqrt(np.clip(1 - sa ** 2, 1e-12, None))
    u, v = sa * np.cos(ph), sa * np.sin(ph)
    xf = xs - z_f * u / ca                      # back-extend to the front focal plane
    yf = ys - z_f * v / ca
    px, py = f * u, f * v
    ax, ay = -xf / f, -yf / f
    ok = esc & (np.hypot(px, py) <= f * NA)
    stages = {"escape (no TIR)": esc.copy(), "within lens NA": ok.copy()}
    for dist, shape in stops:
        X, Y = px + ax * dist, py + ay * dist
        ok &= _inside(X, Y, shape)
    stages["through filters/dichroic/lens stops"] = ok.copy()
    pre = ok.copy()
    X2, Y2 = px + ax * L2, py + ay * L2
    bx, by = ax - X2 / f2, ay - Y2 / f2
    Xd, Yd = X2 + bx * d2, Y2 + by * d2
    ok &= _inside(Xd, Yd, det)
    stages["on detector"] = ok
    res = {k: 0.5 * np.sum(T * m) / N for k, m in stages.items()}
    res["escape (no TIR)"] = 0.5 * np.sum(T * esc) / N
    if return_rays:
        res["rays"] = dict(Xd=Xd, Yd=Yd, px=px, py=py, ax=ax, ay=ay, z=zd, T=T,
                           in_na=stages["within lens NA"], pre=pre, hit=ok)
    return res


def _inside(X, Y, shape):
    if shape[0] == "circle":
        return np.hypot(X, Y) <= shape[1]
    return (np.abs(X) <= shape[1]) & (np.abs(Y) <= shape[2])


def escape_cone_fraction(NA_air, n=N_DIAMOND):
    """Fraction of isotropic emission (4 pi) inside the diamond that reaches air
    within NA_air through a flat face, without Fresnel loss: (1 - cos theta_d)/2."""
    th = np.arcsin(np.minimum(NA_air, 1.0) / n)
    return (1 - np.cos(th)) / 2


def escape_cone_fraction_fresnel(NA_air, n=N_DIAMOND, nq=2000):
    th_max = np.arcsin(np.minimum(NA_air, 1.0) / n)
    th = np.linspace(0, th_max, nq)
    return np.trapezoid(fresnel_T(np.cos(th), n, 1.0) * np.sin(th), th) / 2


# ---------------------------------------------------------------------------
# 4. Small closed-form helpers
# ---------------------------------------------------------------------------


def plate_lateral_shift(t, n, aoi):
    """Lateral displacement of a ray by a tilted plane-parallel plate."""
    return t * np.sin(aoi) * (1 - np.cos(aoi) / np.sqrt(n ** 2 - np.sin(aoi) ** 2))


def plate_focal_shift(t, n):
    """Paraxial longitudinal focus shift from a plate placed in a converging beam."""
    return t * (1 - 1 / n)


def wedge_deviation(alpha, n):
    """Thin-wedge beam deviation (n - 1) alpha."""
    return (n - 1) * alpha


def nv_per_volume(ppm, volume):
    return ppm * 1e-6 * C_ATOM_DENSITY * volume
