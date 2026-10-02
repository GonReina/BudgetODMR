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

Terms that are left out on purpose:

* The nuclear quadrupole term $P I_z^2$ ($P\approx-5$ MHz) shifts all three $m_s$ levels by the
  same amount for a given $m_I$, so it cancels from every ESR transition.
* The transverse hyperfine term $A_\perp(S_+I_- + S_-I_+)/2$ ($A_\perp\approx-2.7$ MHz) mixes states
  that differ in energy by about $D$. Its effect is of order $A_\perp^2/D \sim$ kHz, which is negligible here.
* Transverse magnetic field ($B_\perp S_x$, etc.). The model assumes the field is along the NV axis.

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

For a single two-level transition, setting the coherence's equation of motion to zero (it
relaxes at $\Gamma_2$, much faster than the populations change) gives the textbook Lorentzian
pumping rate [18]:

$$
W(\Delta) = \frac{\Omega^2}{2}\,\frac{\Gamma_2}{\Gamma_2^2+\Delta^2}
\qquad (\Omega,\Delta\ \text{in rad/µs}),\quad \Delta_\pm = 2\pi(\Delta f \mp \delta).
$$

In steady state this elimination is **exact**, because the coherence's time derivative really is
zero. The script checks this to $10^{-16}$. Each transition is then a pair of rate equations
($0\to\pm1$ at $W_\pm$; $\pm1\to0$ at $W_\pm+\Gamma_p$), which gives

$$
p_{\pm1} = a_\pm\,p_0,\quad a_\pm=\frac{W_\pm}{W_\pm+\Gamma_p},\quad p_0 = \frac1{1+a_++a_-}.
$$

For one isolated line this yields the standard power-broadened CW ODMR line [19]:

$$
\text{contrast} = \frac{C_0}{2}\,\frac{s}{1+s+\Delta^2/\Gamma_2^2},\qquad s = \frac{\Omega^2}{\Gamma_2\Gamma_p},
\qquad \text{FWHM} = \frac{\Gamma_2}{\pi}\sqrt{1+s}\ \text{(MHz)}.
$$

With the default parameters ($\Omega/2\pi = 1$ MHz, $\Gamma_2=1.1$/µs, $\Gamma_p=0.2$/µs), $s\approx180$:
the line is strongly saturated and about 4.7 MHz wide.

The incoherent model shares the same $|0\rangle$ population between both transitions but cannot
form $\rho_{+1,-1}$. It also ignores $E$. The comparison is therefore only meaningful at $E=0$,
which is the default in every figure.

## 5. Ensemble averaging (`ensemble`)

An NV ensemble is modelled as a weighted average of single-NV steady states (or time traces) over
$\delta$:

* **Static inhomogeneity.** $\gamma_e B_\parallel$ has a Gaussian spread of rms `sigma` (field gradients,
  ¹³C/P1 spin bath). The average uses Gauss–Hermite quadrature with probabilists' weight
  $e^{-x^2/2}$ (`hermegauss`, `nq`=31 nodes), at nodes $\delta = \delta_0 + \sigma x_k$.
  For SQ Ramsey this corresponds to $T_2^* = 1/(\sqrt2\pi\sigma)$, about 0.45 µs at $\sigma=0.5$ MHz.
* **¹⁴N hyperfine.** The three $m_I$ classes are equally populated (no nuclear polarisation at
  low field), at $\delta_0 + A_\parallel m_I$.

This is a **static** average: each member keeps its own $\delta$ for the whole measurement. The
script contrasts it with the **dynamic**, Markovian dephasing $\propto 1/T_2$ described in Section 3.

## 6. Time domain (no laser during MW)

* **Rabi** (`rabi`). Starting from $|0\rangle$, the code propagates $\vec\rho(t+dt) = e^{\mathcal L\,dt}\vec\rho(t)$
  with only the $S_z$ dephasing (laser off) and records $p_0(t)$. At degeneracy with linear MW the
  Rabi frequency is $\sqrt2\,\Omega$; for an isolated line it is $\Omega$. `dominant_freq` extracts the
  frequency from a windowed, zero-padded FFT after removing a cubic trend.
* **Ramsey** (`ramsey`). The code evaluates analytic ideal-pulse expressions in the frame at $D$:
  $$P_0^\text{SQ} = \tfrac12\big[1 + e^{-t/T_2}\langle\cos 2\pi\delta t\rangle\big],\qquad
    P_0^\text{DQ} = \tfrac12\big[1 + e^{-4t/T_2}\langle\cos 2\pi(2\delta) t\rangle\big].$$
  DQ precesses at twice the field-sensitive frequency and is immune to common-mode shifts of $D$
  (temperature, axial strain) [10–12].

## 7. What the figures show (default run, `summary.txt`)

| figure | content | key result |
|---|---|---|
| `fig1_spectra` | coherent vs incoherent spectra as $\gamma B_\parallel$ goes 3 → 0.5 → 0 MHz, for a single NV and an ensemble | differences appear only where the lines overlap |
| `fig2_ratio_test` | $R$ = (peak contrast at degeneracy)/(peak of one isolated line) against $\Omega$ | ideal single NV: $R_\text{coh}=1.00$ vs $R_\text{inc}=1.33$; ensemble without ¹⁴N: 1.31 vs 1.33; with ¹⁴N the hyperfine classes are themselves partially overlapping V systems and $R$ is not a clean test (1.41 vs 1.36) |
| `fig3_washout` | signature $S = 1 - R_\text{coh}/R_\text{inc}$ (ideal ¼) against (a) static spread σ, (b) $T_2$ | (a) the drive protects the dark/bright structure (Autler–Townes splitting $\sim\Omega$ against B↔D mixing $\delta$), so $S$ halves at $\sigma\approx0.35\,\Omega$; (b) DQ dephasing feeds $|D\rangle$ at a rate set by $4/T_2$ independent of drive, so $S$ halves at $4/T_2\approx\Gamma_p$ |
| `fig4_lineshape_ambiguity` | fit of a coherent ensemble spectrum with the incoherent model (free $\Omega,\sigma,C_0$) | residual about 0.7 % of peak: the lineshape alone cannot reveal the coherence |
| `fig5_time_domain` | Rabi (degenerate vs isolated) and SQ vs DQ Ramsey | Rabi ratio 1.41 ≈ √2 even in the ensemble; DQ Ramsey at $2\gamma B$ |

Conclusion: CW ODMR on a realistic ensemble is a weak and ambiguous probe of the $\pm1$ coherence.
The $\sqrt2$ Rabi enhancement and DQ Ramsey are the robust signatures.

## 8. Review of the Hamiltonian, and a change made

I checked the rotating-frame Hamiltonian numerically against the lab-frame
$D S_z^2 + \delta S_z + E(S_x^2-S_y^2)$, so its eigenvalues match the ODMR line positions
$D\pm\sqrt{\delta^2+E^2}$. I also checked the dissipator's coherence decay rates against
Section 3. **The Hamiltonian is standard.** The signs, the $E$ matrix element, the hyperfine
folding into $\delta$, the RWA, and the σ± power normalisation are all correct.

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
* **Step size.** `f_step_mhz` = 0.1 is fine; ≤ 0.3 MHz is needed.

A quick diagnostic is the FWHM of a single line at the lowest usable MW power and laser power.
If it stays above about 1.5 MHz, the triplet (and the centre/side test) is out of reach for this
sample. `analysis/plot_power_sweep_dc.py` already fits a 2.16 MHz triplet and can be used to
check.

## 10. Parameters (`BASE`)

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
