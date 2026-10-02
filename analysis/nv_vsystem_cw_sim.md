# `nv_vsystem_cw_sim.py`: physics, equations and numerics

Companion note to [`nv_vsystem_cw_sim.py`](nv_vsystem_cw_sim.py). Run it with
`python analysis/nv_vsystem_cw_sim.py` (no hardware needed). Figures and `summary.txt` go to
`analysis/vsystem_sim_out/`.

## 1. The question

At zero (or small) axial field the NV ground-state transitions $m_s=0\to+1$ and
$m_s=0\to-1$ overlap. A microwave field then drives a **V system**: one ground level $|0\rangle$
coupled to two upper levels $|\pm1\rangle$. The two transitions can act as independent
(incoherent) transitions, or the drive can create a **coherent superposition** of $|+1\rangle$ and
$|-1\rangle$. The script asks whether a CW ODMR measurement can tell these cases apart. It compares:

* a **coherent** model: the full density-matrix (Lindblad) steady state, which keeps the
  $\rho_{+1,-1}$ coherence, and
* an **incoherent** model: the same levels and rates, but each transition is driven by a
  classical Lorentzian pumping rate, so no $\rho_{+1,-1}$ can form.

Any difference between the two models therefore comes from the $|+1\rangle/|-1\rangle$ coherence.

## 2. Spin Hamiltonian

### 2.1 Lab frame

The NV$^-$ ground state is a spin triplet ($S=1$). The standard Hamiltonian, in frequency units
($H/h$) and with $z$ along the NV axis, is [1–3]:

$$
\frac{H_0}{h} = D\,S_z^2 \;+\; \gamma_e B_\parallel S_z \;+\; E\,(S_x^2 - S_y^2) \;+\; A_\parallel S_z I_z
$$

| term | meaning | value used / typical | source |
|---|---|---|---|
| $D S_z^2$ | zero-field splitting from the spin–spin interaction of the two unpaired electrons | $D \approx 2870$ MHz at room temperature | [1, 2] |
| $\gamma_e B_\parallel S_z$ | Zeeman term for the field component along the NV axis | $\gamma_e = g\mu_B/h = 28.024$ MHz/mT ($g\approx2.003$) | [1, 2] |
| $E(S_x^2-S_y^2)$ | transverse zero-field splitting from strain or electric field (lowers $C_{3v}$ symmetry) | `E`, default 0 | [1, 4, 5] |
| $A_\parallel S_z I_z$ | axial hyperfine coupling to the $^{14}$N nucleus ($I=1$, $m_I\in\{-1,0,+1\}$) | `A` $=-2.16$ MHz (Felton et al. give $-2.14(7)$ MHz) | [6] |

The code uses the basis $\{|+1\rangle,|0\rangle,|-1\rangle\}$ (indices 0, 1, 2). In this basis,

* $S_z = \mathrm{diag}(1,0,-1)$, so the Zeeman and hyperfine terms shift $|\pm1\rangle$ by
  $\pm\delta$, with
  $$\delta = \gamma_e B_\parallel + A_\parallel m_I .$$
  For a fixed nuclear state, $A_\parallel S_z I_z$ acts as an extra axial field, which is why the
  code folds it into $\delta$.
* $S_x^2 - S_y^2 = \tfrac12(S_+^2 + S_-^2)$ has a single nonzero matrix element,
  $\langle +1|S_x^2-S_y^2|-1\rangle = 1$. The $E$ term therefore couples $|+1\rangle$ and $|-1\rangle$
  directly. Its eigenstates are $(|+1\rangle \pm |-1\rangle)/\sqrt2$ at $D\pm E$, and with a field present
  the lines sit at $D \pm\sqrt{\delta^2+E^2}$.

Terms that are left out on purpose. The full ¹⁴N ground-state Hamiltonian adds [6, 20]

$$
\frac{H_N}{h} = A_\perp (S_x I_x + S_y I_y) + P\,(I_z^2 - \tfrac23) - \gamma_n B_\parallel I_z ,
$$

and each of these is either exactly zero for an ESR line or tiny:

* **Nuclear Zeeman** $-\gamma_n B_\parallel I_z$, with $\gamma_n(^{14}\mathrm{N}) = 3.077$ kHz/mT, and the
  **quadrupole** $P I_z^2$ ($P\approx-4.95$ MHz). For a given $m_I$ both shift $|0\rangle$, $|+1\rangle$ and
  $|-1\rangle$ by the *same* amount, because they act only on the nucleus. An ESR transition keeps $m_I$, so
  both cancel exactly from every line position. The nuclear Zeeman term would matter for NMR
  ($\Delta m_I = \pm1$) or for nuclear polarisation, but neither is modelled here.
* **Transverse hyperfine** $A_\perp(S_+I_- + S_-I_+)/2$ ($A_\perp\approx-2.7$ MHz). This mixes
  $|0, m_I\rangle$ with $|\pm1, m_I\mp1\rangle$, which lie about $D$ away. The line shift is therefore of order
  $A_\perp^2/D \sim$ kHz.
* **Transverse magnetic field** ($B_\perp S_x$, etc.). The model assumes the field is along the NV axis.

The script checks this directly (`check_nuclear`). It diagonalises the full 9-level electron ⊗ ¹⁴N
Hamiltonian and compares every ESR line with the model's $D \pm (\gamma_e B + A_\parallel m_I)$:

| $B_\parallel$ | max deviation | with $A_\perp = 0$ | change from the nuclear Zeeman term alone |
|---|---|---|---|
| 0.2 mT | 7.6 kHz | $5\times10^{-10}$ kHz | $6\times10^{-7}$ kHz |
| 10 mT | 7.9 kHz | $9\times10^{-10}$ kHz | $4\times10^{-5}$ kHz |

The only residual is the ~8 kHz second-order shift from $A_\perp$. That is about 300× smaller than
the 2.16 MHz hyperfine splitting and far below any linewidth here. The nuclear Zeeman term is
invisible at the 10⁻⁵ kHz level.

### 2.2 Microwave drive, rotating frame, RWA

A linearly polarised MW field at frequency $f$, making an angle $\varphi$ with the strain $x$
axis in the plane transverse to the NV axis, adds
$h\,\Omega_\text{lab}\cos(2\pi f t)\,(\cos\varphi\,S_x + \sin\varphi\,S_y)$. Its matrix elements are

$$
\langle\pm1|\cos\varphi S_x + \sin\varphi S_y|0\rangle = \tfrac{1}{\sqrt2}\,e^{\mp i\varphi}.
$$

Both $|\pm1\rangle$ lie about $D$ above $|0\rangle$. Moving to the frame
$U = \exp[i2\pi f t\,(|{+1}\rangle\langle{+1}| + |{-1}\rangle\langle{-1}|)]$ and dropping the
terms that oscillate at $2f$ (the rotating-wave approximation, valid for $\Omega \ll D$) gives the
Hamiltonian in the code (`hamiltonian()`):

$$
\frac{H}{h} = (\delta - \Delta f)\,|{+1}\rangle\langle{+1}| + (-\delta - \Delta f)\,|{-1}\rangle\langle{-1}|
+ E\,\big(|{+1}\rangle\langle{-1}| + \text{h.c.}\big)
+ \frac{\Omega}{2}\big(c_+\,|{+1}\rangle\langle 0| + c_-\,|{-1}\rangle\langle 0| + \text{h.c.}\big),
$$

where $\Delta f = f - D$. The coefficients $c_\pm$ come from the polarisation (`POL` and `phi`):

| `pol` | $c_+$ | $c_-$ | comment |
|---|---|---|---|
| `linear` | $e^{-i\varphi}$ | $e^{+i\varphi}$ | $\Omega$ is the Rabi frequency of **each** transition |
| `sigma+` | $\sqrt2$ | 0 | the same MW power in one circular component drives only $0\to+1$ [7, 8] |
| `sigma-` | 0 | $\sqrt2$ | |

The $\sqrt2$ is a power normalisation. A circular field with the same total power as the
linear one has $\sqrt2$ larger amplitude on the one transition it drives.

The code multiplies $H/h$ by $2\pi$ so that it is in rad/µs (with frequencies in MHz). The
dissipative rates below are already in 1/µs.

### 2.2.1 Is the rotating frame valid? Longitudinal and counter-rotating terms

The antenna field generally has a component along the NV axis as well as across it. For a
given NV orientation the full lab-frame drive is

$$
\frac{H_\text{MW}}{h} = \Omega_L\cos(2\pi f t)\,(\cos\varphi\,S_x + \sin\varphi\,S_y)
\;+\; \Omega_z \cos(2\pi f t)\,S_z ,
\qquad \Omega_L = \sqrt2\,\Omega,\quad \Omega_z = \gamma_e B_{1,\parallel}.
$$

Going to the rotating frame $U = \exp[i2\pi f t\,S_z^2]$ is an **exact** unitary change of picture,
not an approximation. Three things happen:

1. **The static terms are unchanged.** $D S_z^2$ becomes the detuning. $\delta S_z$ and the strain
   term both commute with $S_z^2$ ($S_z^2$ is the identity on the ±1 pair), so they are unaffected.
2. **The transverse drive** gives the time-independent couplings $\Omega/2$ plus *counter-rotating*
   terms oscillating at $2f$. Dropping those is the rotating-wave approximation (RWA). They cause
   the Bloch–Siegert shift, of order $\Omega^2/(4f)$ [21], and small wiggles of relative size
   about $\Omega/f$.
3. **The longitudinal term** $\Omega_z\cos(2\pi f t)S_z$ also commutes with $U$, so it survives
   unchanged as a *longitudinal, time-dependent* term. That is exactly the concern: it is not
   in the RWA model. A second exact transformation $\exp[i(\Omega_z/f)\sin(2\pi f t)S_z]$ removes it,
   turning it into frequency modulation of the ±1 levels with modulation index $\beta = \Omega_z/f$.
   Expanding in Bessel functions [22], the resonant couplings are rescaled by
   $J_0(\beta) \approx 1-\beta^2/4$, and all other terms sit at multiples of $f$, i.e. ~2.9 GHz off
   resonance. For $\Omega_z = 42$ MHz, $\beta = 0.015$ and the rescaling is $6\times10^{-5}$. A longitudinal
   drive would only matter if something were resonant at $f$ itself, for example a ±1 splitting
   of $2r \approx f$. That needs fields of about 50 mT, nothing like this rig.

The Lindblad terms are unaffected by the change of frame. A jump operator $|0\rangle\langle\pm1|$
only picks up a phase $e^{\pm i2\pi f t}$, which cancels in $L\rho L^\dagger$, and $S_z$ and the
projectors commute with $U$.

The script checks this numerically (`check_rwa`). It propagates the full lab-frame Hamiltonian,
$D = 2870$ MHz, counter-rotating terms and an optional longitudinal component, exactly over one MW
period (400 steps), then stroboscopically for 2 µs. It compares $P_0(t)$ with the RWA model for a
resonant, degenerate Rabi pulse:

| $\Omega/2\pi$ | max $|\Delta P_0|$, transverse MW | MW at 45° to the NV axis ($B_{1z} = B_{1\perp}$) |
|---|---|---|
| 1 MHz | $9\times10^{-5}$ | $9\times10^{-5}$ |
| 10 MHz | $1.0\times10^{-3}$ | $1.2\times10^{-3}$ |
| 30 MHz | $4.5\times10^{-3}$ | $1.2\times10^{-2}$ |

The error grows like $\Omega/f$, as expected for terms at $f$ and $2f$, and it is mostly fast
wiggles that CW measurements average away. The RWA is fine for everything in this note. It would
need revisiting only for Rabi frequencies of hundreds of MHz.

### 2.3 Bright and dark states

With linear drive and $\varphi=0$, $|0\rangle$ couples only to the **bright** state
$|B\rangle = (|{+1}\rangle+|{-1}\rangle)/\sqrt2$, with coupling $\sqrt2\,\Omega/2$. The orthogonal
**dark** state $|D\rangle = (|{+1}\rangle-|{-1}\rangle)/\sqrt2$ is not driven. This is the
V-system analogue of coherent population trapping [9]. In the $\{B, D\}$ basis:

* The Zeeman/hyperfine term $\delta S_z$ appears as an **off-diagonal** element $\delta$
  between $|B\rangle$ and $|D\rangle$. A field, or an inhomogeneous spread of fields, rotates bright
  population into dark population.
* The strain term $E$ is **diagonal**: $|B\rangle$ is shifted to $+E$ and $|D\rangle$ to $-E$. Strain
  splits the line but does not mix the two states.
* $S_z$-type dephasing (Section 3) also converts $|B\rangle \leftrightarrow |D\rangle$.

All of the script's physical conclusions follow from this picture:

* **CW contrast.** With a saturating drive and no B↔D mixing, $|0\rangle$ and $|B\rangle$ end up equally populated
  (½ each), so the $m_s=0$ depletion is ½. In the incoherent model the three levels equalise at ⅓,
  so the depletion is ⅔. Relative to one isolated saturated line (depletion ½), the ratio is
  $R = 1$ (coherent) against $R = 4/3$ (incoherent).
* **Rabi frequency.** At degeneracy the $|0\rangle\leftrightarrow|B\rangle$ Rabi frequency is $\sqrt2\,\Omega$.
* **Double-quantum precession.** The $|B\rangle/|D\rangle$ superposition evolves at $2\delta$, the double-quantum frequency [10–12].

## 3. Open-system model: Lindblad master equation

Optical pumping and relaxation are included through a Lindblad (GKSL) master equation [13–15]:

$$
\dot\rho = -\frac{i}{\hbar}[H,\rho] + \sum_k \Big( L_k\rho L_k^\dagger - \tfrac12\{L_k^\dagger L_k,\rho\}\Big).
$$

Collapse operators (`dissipator()`):

| operator | physics | effect |
|---|---|---|
| $\sqrt{\Gamma_p}\,|0\rangle\langle{+1}|$, $\sqrt{\Gamma_p}\,|0\rangle\langle{-1}|$ | **optical repolarisation**: under green light, $m_s=\pm1$ population returns to $m_s=0$ through the excited state and the singlet (ISC) path [16, 17] | $p_{\pm1}\to p_0$ at $\Gamma_p$ (`gamma_p`); coherences with $\pm1$ decay at $\Gamma_p/2$ per $\pm1$ index |
| $\sqrt{\Gamma_\text{exc}}\,|0\rangle\langle 0|$ | **optical cycling of $m_s=0$**: each excitation/emission cycle of $|0\rangle$ is a "which-state" measurement | dephases $\rho_{0,\pm1}$ at $\Gamma_\text{exc}/2$ (`gamma_exc`) |
| $\sqrt{\Gamma_\text{exc}^{\pm}}\,(|{+1}\rangle\langle{+1}|+|{-1}\rangle\langle{-1}|)$ | **optical cycling of $m_s=\pm1$** (spin-conserving cycles; physically $\Gamma_\text{exc}^{\pm}\approx\Gamma_\text{exc}$ [16, 17]). A single projector onto the $\pm1$ manifold cannot tell $+1$ from $-1$ | dephases $\rho_{0,\pm1}$ at $\Gamma_\text{exc}^{\pm}/2$ but leaves $\rho_{+1,-1}$ intact, which is the most favourable case for the coherence (`gamma_exc_pm`, default 0 = off) |
| $\sqrt{2/T_2}\,S_z$ | **magnetic noise** (spin bath, field noise) as white-noise dephasing | $\rho_{ij}$ decays at $\tfrac{1}{T_2}(m_i-m_j)^2$: single-quantum (SQ) coherences at $1/T_2$, the double-quantum (DQ) coherence $\rho_{+1,-1}$ at $4/T_2$ |

The resulting coherence decay rates, checked numerically against the code, are:

$$
\Gamma_2 \equiv \Gamma_{0,\pm1} = \tfrac12(\Gamma_p + \Gamma_\text{exc} + \Gamma_\text{exc}^{\pm}) + \frac1{T_2}
\qquad(\texttt{gamma2()}),
\qquad
\Gamma_{+1,-1} = \Gamma_p + \frac4{T_2}.
$$

$T_1$ spin–lattice relaxation (ms timescale) is omitted because it is negligible next to $\Gamma_p$.

**Photoluminescence readout.** $m_s=\pm1$ is darker by the contrast $C_0$ (ISC to the singlet) [1, 2]:

$$
\text{PL} = p_0 + (1-C_0)(p_{+1}+p_{-1}),\qquad \text{contrast} = 1-\text{PL}.
$$

The readout only sees populations, so $\rho_{+1,-1}$ never enters PL directly. It acts only through
how it redistributes population. $C_0$ scales every signal and does not change the shapes.

### 3.1 Steady-state solution (`contrast_coherent`)

$\rho$ is vectorised by column stacking ($\mathrm{vec}(A\rho B) = (B^T\otimes A)\,\mathrm{vec}\,\rho$),
which turns the master equation into $\dot{\vec\rho} = \mathcal L\vec\rho$ with a $9\times9$ Liouvillian:

$$
\mathcal L = -i\,(I\otimes H - H^T\otimes I) + \sum_k\Big(L_k^*\otimes L_k - \tfrac12 I\otimes L_k^\dagger L_k - \tfrac12 (L_k^\dagger L_k)^T\otimes I\Big).
$$

The CW steady state solves $\mathcal L\vec\rho = 0$. That system is singular because trace is
conserved, so the code replaces the first row with the normalisation $\rho_{00}+\rho_{11}+\rho_{22}=1$
and solves the result with `np.linalg.solve`. `bkron` is a batched Kronecker product, so every MW
frequency and every ensemble member is solved in one vectorised call.

## 4. Incoherent reference model (`contrast_incoherent`)

### 4.1 Which states are "incoherent"?

"Incoherent driving" only means something in a particular basis. The natural basis is the
**eigenstates of the undriven Hamiltonian**: a rate model between them is the secular
approximation, which keeps populations and drops every coherence between non-degenerate
eigenstates [15]. For the ±1 pair, the undriven block

$$
\begin{pmatrix}\delta & E\\ E & -\delta\end{pmatrix}
\;\Rightarrow\; |a\rangle = (\cos\tfrac\theta2,\ \sin\tfrac\theta2),\ \ |b\rangle = (-\sin\tfrac\theta2,\ \cos\tfrac\theta2),
\quad \epsilon_{a,b} = \pm r,\ \ r=\sqrt{\delta^2+E^2},\ \ \tan\theta = E/\delta ,
$$

has eigenstates $|a\rangle, |b\rangle$ in the $(|{+1}\rangle, |{-1}\rangle)$ basis.

* **$E = 0$:** the eigenstates are $|+1\rangle$ and $|-1\rangle$, and this is the familiar
  "two independent transitions" model.
* **$E \gg \delta$:** they are the strain states $(|{+1}\rangle\pm|{-1}\rangle)/\sqrt2$. These are superpositions of
  ±1, but that is a static property of a strained NV, not a sign of coherent driving.

The **coherence signature** is then defined basis-independently, as what the full Lindblad model
gives *beyond* this secular rate model.

### 4.2 The rate model

For a single two-level transition, setting the coherence's equation of motion to zero (it
relaxes at $\Gamma_2$, much faster than the populations change) gives the textbook Lorentzian
pumping rate [18]. Applied to each eigen-transition $|0\rangle\to|k\rangle$, $k = a, b$:

$$
W_k = \frac{\Omega_k^2}{2}\,\frac{\Gamma_2}{\Gamma_2^2+\Delta_k^2},
\qquad \Omega_k = 2\,|\langle k|V|0\rangle|,\quad \Delta_k = 2\pi(\epsilon_k - \Delta f)
\qquad (\text{rad/µs}),
$$

with $\langle a|V|0\rangle = \cos\tfrac\theta2\,v_+ + \sin\tfrac\theta2\,v_-$ and
$\langle b|V|0\rangle = -\sin\tfrac\theta2\,v_+ + \cos\tfrac\theta2\,v_-$, where $v_\pm = \tfrac\Omega2 c_\pm$ are the
drive couplings of Section 2.2. $\Gamma_2$ is the same as in Section 3, because every collapse operator
treats $|a\rangle$ and $|b\rangle$ alike.

The two remaining rates in the secular model are:

* **Repolarisation:** $|a\rangle, |b\rangle \to |0\rangle$ at $\Gamma_p$, since $\sum_\pm |\langle\pm1|k\rangle|^2 = 1$.
* **Noise-induced transfer:** the $S_z$ noise moves population $a\leftrightarrow b$ at
  $k_{ab} = (2/T_2)\,|\langle a|S_z|b\rangle|^2 = (2/T_2)\sin^2\theta$.

The steady state is then analytic:

$$
\frac{p_a}{p_0} = \frac{W_a B + k_{ab}W_b}{AB-k_{ab}^2},\quad
\frac{p_b}{p_0} = \frac{W_b A + k_{ab}W_a}{AB-k_{ab}^2},\quad
A = W_a+\Gamma_p+k_{ab},\ B = W_b+\Gamma_p+k_{ab},
$$

with $p_0 + p_a + p_b = 1$.

At $E=0$, $k_{ab}=0$ and this reduces to the two-transition model
$p_{\pm1} = a_\pm\,p_0$, $a_\pm=W_\pm/(W_\pm+\Gamma_p)$, $p_0 = 1/(1+a_++a_-)$, so every result at $E=0$ is
unchanged. For an isolated transition the elimination is **exact**, because the coherence's time
derivative really is zero in steady state. The script checks this to $10^{-16}$.

**A subtlety at exact degeneracy.** When $\delta = E = 0$, any basis of the ±1 pair is an
eigenbasis, so the "incoherent" reference is not unique. The script uses $|\pm1\rangle$, which asks
whether the $0\to+1$ and $0\to-1$ transitions act independently. Take the opposite extreme: a
tiny $E$ aligned with the MW ($\varphi = 0$) makes the bright and dark states themselves the
eigenstates. The secular model then also leaves the dark state undriven, and coherent and
incoherent agree exactly (the script checks this to $10^{-15}$; Figure 7a, $\varphi = 0$). The
dark-state "signature" therefore depends on the reference you compare against. That is one more
reason CW contrast is a weak witness of coherence.

For one isolated line this yields the standard power-broadened CW ODMR line [19]:

$$
\text{contrast} = \frac{C_0}{2}\,\frac{s}{1+s+\Delta^2/\Gamma_2^2},\qquad s = \frac{\Omega^2}{\Gamma_2\Gamma_p},
\qquad \text{FWHM} = \frac{\Gamma_2}{\pi}\sqrt{1+s}\ \text{(MHz)}.
$$

With the default parameters ($\Omega/2\pi = 1$ MHz, $\Gamma_2=1.1$/µs, $\Gamma_p=0.2$/µs), $s\approx180$:
the line is strongly saturated and about 4.7 MHz wide.

The incoherent model shares the same $|0\rangle$ population between both transitions but cannot
form a coherence between $|a\rangle$ and $|b\rangle$. Because it is built on the eigenstates, the
comparison remains meaningful at any $E$ (Section 10).

## 5. Ensemble averaging (`ensemble`)

An NV ensemble is modelled as a weighted average of single-NV steady states (or time traces) over
$\delta$:

* **Static inhomogeneity.** $\gamma_e B_\parallel$ has a Gaussian spread of rms `sigma` (field gradients,
  ¹³C/P1 spin bath). The average uses Gauss–Hermite quadrature with probabilists' weight
  $e^{-x^2/2}$ (`hermegauss`, `nq`=31 nodes), at nodes $\delta = \delta_0 + \sigma x_k$.
  For SQ Ramsey this corresponds to $T_2^* = 1/(\sqrt2\pi\sigma)$, about 0.45 µs at $\sigma=0.5$ MHz.
* **¹⁴N hyperfine.** The three $m_I$ classes are equally populated (no nuclear polarisation at
  low field), at $\delta_0 + A_\parallel m_I$.
* **Random strain / electric field** (`sigma_E` > 0). In a dense sample the transverse $E$ comes
  mostly from the electric fields of nearby charges, with random size and direction [5]. The model
  takes $E_x, E_y \sim N(0, \sigma_E^2)$. Then $|E|$ is Rayleigh distributed, integrated with
  Gauss–Laguerre quadrature in $|E|^2$ (`nqE` nodes), and its direction is uniform, integrated
  over `nphiE` angles. Only the relative angle $\varphi$ between the strain axis and the MW matters,
  and only through $2\varphi$. `sigma_E` > 0 replaces the fixed `E`, `phi`.

This is a **static** average: each member keeps its own $\delta$ for the whole measurement. The
script contrasts it with the **dynamic**, Markovian dephasing $\propto 1/T_2$ described in Section 3.

## 6. Time domain (no laser during MW)

* **Rabi** (`rabi`). Starting from $|0\rangle$, the code propagates $\vec\rho(t+dt) = e^{\mathcal L\,dt}\vec\rho(t)$
  with only the $S_z$ dephasing (laser off) and records $p_0(t)$. At degeneracy with linear MW the
  Rabi frequency is $\sqrt2\,\Omega$; for an isolated line it is $\Omega$. `dominant_freq` extracts the
  frequency from a windowed, zero-padded FFT after removing a cubic trend.
* **Ramsey** (`ramsey`). The code evaluates analytic ideal hard-pulse expressions in the frame at $D$,
  with $r=\sqrt{\delta^2+E^2}$:
  $$P_0^\text{SQ} = \tfrac12\big[1 + e^{-t/T_2}\langle\cos 2\pi r t\rangle\big],\qquad
    P_0^\text{DQ} = \Big\langle 1 - \tfrac{\delta^2}{r^2}\,\tfrac12\big[1 - e^{-4t/T_2}\cos 2\pi(2r) t\big]\Big\rangle .$$
  SQ uses π/2 pulses on the upper eigen-transition. DQ uses π pulses between $|0\rangle$ and
  $(|{+1}\rangle+|{-1}\rangle)/\sqrt2$: the return probability after free evolution is
  $1-(\delta/r)^2\sin^2(2\pi r t)$. At $E=0$ these reduce to
  $\tfrac12[1 + e^{-t/T_2}\cos 2\pi\delta t]$ and $\tfrac12[1 + e^{-4t/T_2}\cos 2\pi(2\delta) t]$.
  DQ precesses at twice the field-sensitive frequency and is immune to common-mode shifts of $D$
  (temperature, axial strain) [10–12]. Strain raises the DQ frequency to $2r$ and cuts its
  visibility to $(\delta/r)^2$, which is why DQ magnetometry needs $\gamma_e B \gg E$. The decay factors
  are the $E=0$ ones.

## 7. What the figures show (default run, `summary.txt`)

| figure | content | key result |
|---|---|---|
| `fig1_spectra` | coherent vs incoherent spectra as $\gamma B_\parallel$ goes 3 → 0.5 → 0 MHz, for a single NV and an ensemble | differences appear only where the lines overlap |
| `fig2_ratio_test` | $R$ = (peak contrast at degeneracy)/(peak of one isolated line) against $\Omega$ | ideal single NV: $R_\text{coh}=1.00$ vs $R_\text{inc}=1.33$; ensemble without ¹⁴N: 1.31 vs 1.33; with ¹⁴N the hyperfine classes are themselves partially overlapping V systems and $R$ is not a clean test (1.41 vs 1.36) |
| `fig3_washout` | signature $S = 1 - R_\text{coh}/R_\text{inc}$ (ideal ¼) against (a) static spread σ, (b) $T_2$ | (a) the drive protects the dark/bright structure (Autler–Townes splitting $\sim\Omega$ against B↔D mixing $\delta$), so $S$ halves at $\sigma\approx0.35\,\Omega$; (b) DQ dephasing feeds $|D\rangle$ at a rate set by $4/T_2$ independent of drive, so $S$ halves at $4/T_2\approx\Gamma_p$ |
| `fig4_lineshape_ambiguity` | fit of a coherent ensemble spectrum with the incoherent model (free $\Omega,\sigma,C_0$) | residual about 0.7 % of peak: the lineshape alone cannot reveal the coherence |
| `fig5_time_domain` | Rabi (degenerate vs isolated) and SQ vs DQ Ramsey | Rabi ratio 1.41 ≈ √2 even in the ensemble; DQ Ramsey at $2\gamma B$ |
| `fig6_pl_vs_rabi` | PL spectra for $\Omega/2\pi$ = 0.1–3 MHz, coherent vs incoherent, at $\gamma B$ = 0.5 and 0 MHz | single NV: min PL 0.849 vs 0.800 at degeneracy and saturation; ensemble: 0.844 vs 0.848 at 1 MHz, i.e. < 0.5 % of the PL |
| `fig7_strain` | coherence signature (peak coherent / peak incoherent − 1) against (a) fixed $E$ at three MW angles, (b) a random $E$ spread $\sigma_E$ | the signature survives only while $E \lesssim 0.3\,\Omega$; a random $E$ spread washes it out like a static field spread; dense ensemble +2.0 % → +0.35 % at $\sigma_E$ = 1 MHz (Section 10) |

Conclusion: CW ODMR on a realistic ensemble is a weak and ambiguous probe of the $\pm1$ coherence.
The $\sqrt2$ Rabi enhancement and DQ Ramsey are the robust signatures.

## 8. Review of the Hamiltonian, and changes made

I checked the rotating-frame Hamiltonian numerically against the lab-frame
$D S_z^2 + \delta S_z + E(S_x^2-S_y^2)$, so its eigenvalues match the ODMR line positions
$D\pm\sqrt{\delta^2+E^2}$. I also checked the dissipator's coherence decay rates against
Section 3. **The Hamiltonian is standard.** The signs, the $E$ matrix element, the hyperfine
folding into $\delta$, the RWA, and the σ± power normalisation are all correct. Two further
checks now run every time the script runs:

* **Omitted nuclear terms** (nuclear Zeeman, quadrupole, transverse hyperfine): at most an
  ~8 kHz line shift, all of it from $A_\perp$ (Section 2.1).
* **RWA and the longitudinal MW component:** $|\Delta P_0| \lesssim 10^{-3}$ up to
  $\Omega/2\pi = 10$ MHz (Section 2.2.1).

There was one **hidden, non-generic assumption**. The linear-drive couplings were hard-coded as
$c_+=c_-=1$. That fixes the MW polarisation along the strain axis ($\varphi=0$), so the drive
couples only to the upper strain eigenstate. With $E\neq0$ this would make the $D-E$ line
completely invisible at zero field. In reality the relative angle is arbitrary, and for an
ensemble it is spread over the four NV orientations and random strain directions [4, 5, 7]. The
fix was a `phi` parameter (default 0, so every existing result is unchanged), with
$c_\pm \to c_\pm e^{\mp i\varphi}$. Check at $E=2$ MHz, $\delta=0$:
$\varphi=0$ gives line contrasts (D−E, D+E) = (0.04, 0.15), $\varphi=45°$ gives (0.16, 0.16), and
$\varphi=90°$ gives (0.15, 0.04).

A second addition is in the dissipator, not the Hamiltonian. **Optical cycling of $m_s=\pm1$**
is now an optional term (`gamma_exc_pm`, default 0, so every existing result is unchanged); see
Section 3. Turning it on ($\Gamma_\text{exc}^{\pm}=\Gamma_\text{exc}=1$/µs) only broadens the lines.
At $\Omega/2\pi = 2.5$ MHz, $R_\text{coh}/R_\text{inc}$ changes from 1.003/1.331 to 1.002/1.329
(ideal single NV) and from 1.405/1.364 to 1.376/1.352 (¹⁴N ensemble).

Further caveats:

* The rates ($\Gamma_p$, $\Gamma_\text{exc}$, $T_2$, $\sigma$) are assumed, not measured on this rig.
* The excited state, NV⁰ charge dynamics, transverse fields and the four NV orientations are not modelled.

## 9. Why ¹⁴N makes the R test unclean, and what would fix it

### 9.1 What goes wrong

At $B=0$ the three ¹⁴N classes sit at $\delta = A_\parallel m_I = 0, \pm2.16$ MHz. Only the
$m_I=0$ class (⅓ of the NVs) is a **degenerate** V system. The $m_I=\pm1$ classes each have
their two lines at $D\pm2.16$ MHz. When the hyperfine structure is not resolved, the peak at $f=D$ mixes three
things that the $R$ test cannot separate. All numbers below are for $\Omega/2\pi=2.5$ MHz with the
`ENSEMBLE` parameters.

1. **The lines are far wider than the hyperfine spacing.** The homogeneous FWHM
   $(\Gamma_2/\pi)\sqrt{1+s}$ is 4.7 MHz at $\Omega/2\pi=1$ MHz and 11.8 MHz at 2.5 MHz, against a
   2.16 MHz spacing. Both "degenerate" and "isolated" peaks are blends of hyperfine components, and the
   blending depends on power differently in the two cases.
2. **The $m_I=\pm1$ classes are non-degenerate V systems driven between their lines.** Each one
   is driven 2.16 MHz off both transitions at once, with $\Omega \gtrsim \delta$. Here the
   independent-Lorentzian rate model is no longer exact: the drive creates a $|0\rangle$–$|B\rangle$
   dressed state, which $\delta$ then rotates into $|D\rangle$. In this regime the coherent model gives **more**
   contrast than the rate model. For a clean single V at $\delta=2.16$ MHz and $f=D$, contrast is
   0.187 coherent vs 0.172 incoherent at $\Omega/2\pi=2.5$ MHz. This sign is opposite to the
   degenerate signature.
3. **The degenerate class's own signature is already gone.** With $T_2=2$ µs, the DQ dephasing
   $4/T_2 = 2$/µs is 10× $\Gamma_p$, so the dark state is continuously refilled (Figure 3b). The
   $m_I=0$ class contributes 0.065 coherent vs 0.066 incoherent at $f=D$.

The net result is that the residue of (3) is outweighed by (2), so $R_\text{coh} > R_\text{inc}$.
The sign flip tells you nothing about the degenerate coherence. The model is not wrong; the
observable simply mixes several effects.

### 9.2 A cleaner CW observable: centre/side line ratio at B = 0

With the hyperfine **resolved**, a single $B=0$ spectrum contains its own reference, so no
second measurement at a different field is needed:

* **Centre line** ($f=D$): the degenerate $m_I=0$ class, ⅓ of the NVs. Saturated depletion is
  ½ (coherent) or ⅔ (incoherent).
* **Side lines** ($f=D\pm2.16$ MHz): one $m_I=+1$ transition plus one $m_I=-1$ transition, from
  different NVs. They are therefore incoherent, and each class's depletion is ½.

$$
\frac{\text{centre}}{\text{side}} \;\xrightarrow{\ \text{resolved, saturated}\ }\;
\frac{\tfrac13\cdot\tfrac12}{2\cdot\tfrac13\cdot\tfrac12} = \frac12\ \text{(coherent)}
\quad\text{vs}\quad
\frac{\tfrac13\cdot\tfrac23}{2\cdot\tfrac13\cdot\tfrac12} = \frac23\ \text{(incoherent)},
$$

and both tend to 1 in the linear (unsaturated) regime. Simulated (`gamma_exc_pm = gamma_exc`):

| parameters | $\Omega/2\pi$ (MHz) | FWHM (MHz) | centre/side coherent | incoherent |
|---|---|---|---|---|
| rig-like ensemble ($\sigma$ 0.5 MHz, $T_2$ 2 µs, $\Gamma_p$ 0.2/µs) | 0.2 | 1.7 | 0.879 | 0.872 |
| same | 1.0 | 5.8 | 1.067 | 1.045 |
| clean ($\sigma$ 0.02 MHz, $T_2$ 200 µs, $\Gamma_p$ 0.02/µs, $\Gamma_\text{exc}$ 0.1/µs) | 0.1 | 0.5 | **0.632** | **0.685** |
| clean, $T_2$ 20 µs | 0.1 | 0.6 | 0.679 | 0.691 |
| clean, $\sigma$ 0.2 MHz | 0.1 | 0.7 | 0.735 | 0.742 |
| ideal ($\sigma$ 0, $T_2$ 10 ms) | 0.1 | 0.5 | 0.521 | 0.683 |

### 9.3 Conditions for the test to be clean

All of the following must hold together:

| requirement | why | condition |
|---|---|---|
| resolved hyperfine | the centre line must be the $m_I=0$ class only | FWHM $\approx\sqrt{(\Gamma_2/\pi)^2(1+s) + (2.35\sigma)^2} \ll 2.16$ MHz, i.e. ≲ 0.7 MHz |
| saturation | the ½ vs ⅔ difference only appears for $s\gg1$ | $s=\Omega^2/(\Gamma_2\Gamma_p)\gtrsim 10$ |
| slow DQ dephasing | otherwise $|D\rangle$ is refilled (Figure 3b) | $4/T_2 \ll \Gamma_p$ |
| small static spread | otherwise $\delta$ mixes $B\leftrightarrow D$ (Figure 3a) | $\sigma \ll 0.35\,\Omega$ |
| $E\approx0$, $B_\parallel\approx0$ for the probed orientation | strain or charge fields split the centre line [5] | $E,\ \gamma_e B_\parallel \ll \Omega$ |

Because $\Gamma_p$ has to be small for narrow lines, these conditions point to low laser power and
$T_2 \gtrsim 100$ µs, i.e. a single NV or a dilute, ¹²C-enriched, low-N ensemble. A 13 ppm N
(DNV-B14-type) ensemble has $T_2^* \sim 0.1$–1 µs from the P1 bath, so it fails the dephasing and
spread conditions by one to two orders of magnitude. For such a sample the robust coherence test
is the time-domain one: the √2 Rabi enhancement at degeneracy, or DQ Ramsey at $2\gamma_e B$
(Figure 5).

### 9.4 Why the hyperfine triplet may not show up on this rig

With the current `smcv/config.json`, several settings each blur the triplet:

* **FM lock-in deviation `fm_deviation_khz` = 2000.** A ±2 MHz FM excursion is as large as the
  2.16 MHz spacing, so the demodulated signal averages over the triplet. Use ≲ 0.2–0.3 MHz deviation
  (with a correspondingly smaller signal), or use DC/AM ODMR for this check.
* **MW power `power_dbm` = 16.** Power broadening scales as $\sqrt{1+s}$. Step the power down
  (the power-sweep scripts do this) until the FWHM stops shrinking. That floor is the
  optical/inhomogeneous width.
* **Laser power.** $\Gamma_p$ and $\Gamma_\text{exc}$ add directly to $\Gamma_2$. Reduce the power at low MW power
  and compare.
* **Inhomogeneous width of the sample and the field.** P1/¹³C bath, field gradients across the laser
  spot from a nearby magnet, and several NV orientations with slightly different $B_\parallel$ all
  add to the width. With $\sigma \gtrsim 0.7$ MHz the triplet cannot be resolved by any choice of
  power. Align $B$ so one orientation is isolated, keep the spot small, and keep the magnet far
  away or remove it.
* **Step size.** ≤ 0.3 MHz is needed. The amplifier power sweep uses exactly 0.3 MHz (chosen
  for the wide window), which is just enough. Use 0.1 MHz in a narrow window to look for the triplet.

A quick diagnostic is the FWHM of a single line at the lowest usable MW power and laser power.
If it stays above about 1.5 MHz, the triplet (and the centre/side test) is out of reach for this
sample. `analysis/plot_power_sweep_dc.py` already fits a 2.16 MHz triplet and can be used to
check.

## 10. Strain and electric fields in a dense sample (`fig7_strain`)

A high-density sample does not have $E=0$. Charged defects (N⁺, NV⁻) produce local electric
fields, and there is local strain. Both enter as the transverse term $E$, with a size and
direction that vary from NV to NV [5]. With the eigenstate reference of Section 4 the
coherent/incoherent comparison is valid at any $E$. The results below are at $B=0$ and
$\Omega/2\pi = 1$ MHz.

**(a) One ideal NV, fixed $E$.** The MW is linearly polarised at angle $\varphi$ to the strain axis.

| $E$ (MHz) | 0.01 | 0.06 | 0.3 | 1.8 | 10 |
|---|---|---|---|---|---|
| $\varphi$ = 22.5° | −24.4 % | −23.4 % | −1.7 % | +2.7 % | 0.0 % |
| $\varphi$ = 45° | −24.5 % | −22.8 % | −1.3 % | +1.9 % | +0.1 % |
| $\varphi$ = 0 | 0 | 0 | 0 | 0 | 0 |

* **Small $E$:** coherence changes the PL only while the strain splitting $2E$ is unresolved. In
  practice that means $E \lesssim 0.3\,\Omega$, where the drive's dressing protects the bright/dark
  structure, exactly as for the field spread in Figure 3a.
* **Large $E$:** for $E \gg \Omega$ each strain eigenstate is an ordinary, separately resolved
  two-level line.
* **$\varphi = 0$:** the drive's bright state *is* a strain eigenstate. Coherent and incoherent
  models then agree exactly (Section 4.1).

**(b) Random $E$, as in an ensemble.** $E_x, E_y \sim N(0,\sigma_E^2)$, so both size and
direction are random.

| $\sigma_E$ (MHz rms per axis) | 0 | 0.03 | 0.1 | 0.3 | 1 | 3 |
|---|---|---|---|---|---|---|
| ideal single-NV dynamics | −24.6 % | −23.6 % | −18.7 % | −1.3 % | +3.6 % | 0.0 % |
| dense ensemble (σ 0.5 MHz, ¹⁴N, $T_2$ 2 µs, ±1 cycling on) | +2.0 % | +2.1 % | +1.9 % | +1.1 % | +0.35 % | −0.1 % |

A random $E$ acts as one more static inhomogeneity: each NV gets a different amount of
bright↔dark mixing. For the dense ensemble the signature starts small. At $\sigma_E = 0$ it is
+2 %, and that comes mostly from the ¹⁴N effect of Section 9.1, not from degenerate coherence.
Realistic $E$ then shrinks it to a few tenths of a percent of the ODMR peak. The full lineshape
difference stays at 1–3 % of the peak, and Figure 4 shows a fitted rate model absorbs it into
$\Omega$, $\sigma$ and $C_0$.

Measured against the noise on this rig (≥ 8 % of the signal per averaged FM power-sweep point,
SNR ≈ 10), these effects are one to two orders of magnitude too small to see in CW. Strain does
not open a loophole; it closes it further. To estimate $E$ for this sample, take a zero-field ODMR
spectrum without the magnet: the width of the central split/dip structure gives the $E$ scale.

## 11. Parameters (`BASE`)

| name | default | unit | meaning |
|---|---|---|---|
| `Omega` | 1.0 | MHz | Rabi frequency $\Omega/2\pi$ per transition (linear MW) |
| `gamma_p` | 0.2 | 1/µs | optical repolarisation $\pm1\to0$ |
| `gamma_exc` | 1.0 | 1/µs | optical cycling of $m_s=0$ |
| `gamma_exc_pm` | 0.0 | 1/µs | optical cycling of $m_s=\pm1$ (physically ≈ `gamma_exc`; 0 = off) |
| `T2` | 2.0 | µs | homogeneous (Markovian) dephasing time |
| `sigma` | 0.0 | MHz | static rms spread of $\gamma_e B_\parallel$ |
| `hf`, `A` | False, −2.16 | –, MHz | include ¹⁴N classes; axial hyperfine |
| `E` | 0.0 | MHz | transverse strain/electric splitting |
| `phi` | 0.0 | rad | linear-MW angle to the strain axis (only matters if $E\neq0$) |
| `sigma_E` | 0.0 | MHz | random $E$: rms of $E_x$, $E_y$; > 0 replaces `E` and `phi` |
| `nqE`, `nphiE` | 10, 8 | – | quadrature nodes for $|E|$ and its direction |
| `C0` | 0.3 | – | PL contrast of $\pm1$ vs 0 |
| `pol` | `linear` | – | `linear`, `sigma+`, `sigma-` |
| `nq` | 31 | – | Gauss–Hermite nodes |

Presets: `IDEAL_SINGLE` (σ=0, no hf, $T_2$=1 ms) and `ENSEMBLE` (σ=0.5 MHz, ¹⁴N, $T_2$=2 µs,
"DNVB14-like", assumed).

## References

1. M. W. Doherty et al., "The nitrogen-vacancy colour centre in diamond", *Phys. Rep.* **528**, 1 (2013).
2. L. Rondin et al., "Magnetometry with nitrogen-vacancy defects in diamond", *Rep. Prog. Phys.* **77**, 056503 (2014).
3. J. F. Barry et al., "Sensitivity optimization for NV-diamond magnetometry", *Rev. Mod. Phys.* **92**, 015004 (2020).
4. F. Dolde et al., "Electric-field sensing using single diamond spins", *Nat. Phys.* **7**, 459 (2011).
5. T. Mittiga et al., "Imaging the local charge environment of nitrogen-vacancy centers in diamond", *Phys. Rev. Lett.* **121**, 246402 (2018).
6. S. Felton et al., "Hyperfine interaction in the ground state of the negatively charged nitrogen vacancy center in diamond", *Phys. Rev. B* **79**, 075203 (2009).
7. T. P. M. Alegre et al., "Polarization-selective excitation of nitrogen vacancy centers in diamond", *Phys. Rev. B* **76**, 165205 (2007).
8. P. London et al., "Strong driving of a single spin using arbitrarily polarized fields", *Phys. Rev. A* **90**, 012302 (2014).
9. E. Arimondo, "Coherent population trapping in laser spectroscopy", *Prog. Opt.* **35**, 257 (1996).
10. K. Fang et al., "High-sensitivity magnetometry based on quantum beats in diamond nitrogen-vacancy centers", *Phys. Rev. Lett.* **111**, 130802 (2013).
11. H. J. Mamin et al., "Multipulse double-quantum magnetometry with near-surface nitrogen-vacancy centers", *Phys. Rev. Lett.* **113**, 030803 (2014).
12. E. Bauch et al., "Ultralong dephasing times in solid-state spin ensembles via quantum control", *Phys. Rev. X* **8**, 031025 (2018).
13. G. Lindblad, "On the generators of quantum dynamical semigroups", *Commun. Math. Phys.* **48**, 119 (1976).
14. V. Gorini, A. Kossakowski, E. C. G. Sudarshan, *J. Math. Phys.* **17**, 821 (1976).
15. H.-P. Breuer and F. Petruccione, *The Theory of Open Quantum Systems* (Oxford University Press, 2002).
16. L. Robledo et al., "Spin dynamics in the optical cycle of single nitrogen-vacancy centres in diamond", *New J. Phys.* **13**, 025013 (2011).
17. J.-P. Tetienne et al., "Magnetic-field-dependent photodynamics of single NV defects in diamond", *New J. Phys.* **14**, 103033 (2012).
18. L. Allen and J. H. Eberly, *Optical Resonance and Two-Level Atoms* (Wiley, 1975; Dover, 1987).
19. A. Dréau et al., "Avoiding power broadening in optically detected magnetic resonance of single NV defects for enhanced dc magnetic field sensitivity", *Phys. Rev. B* **84**, 195204 (2011).
20. M. W. Doherty et al., "Theory of the ground-state spin of the NV⁻ center in diamond", *Phys. Rev. B* **85**, 205203 (2012).
21. F. Bloch and A. Siegert, "Magnetic resonance for nonrotating fields", *Phys. Rev.* **57**, 522 (1940).
22. J. H. Shirley, "Solution of the Schrödinger equation with a Hamiltonian periodic in time", *Phys. Rev.* **138**, B979 (1965).
