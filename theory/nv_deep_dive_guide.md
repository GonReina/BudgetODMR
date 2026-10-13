# NV-Centre Ensemble ODMR & Sensitivity — A Deep-Dive Study Guide

*A companion to Doherty et al., Phys. Rep. **528**, 1 (2013) and Maze et al.,
New J. Phys. **13**, 025025 (2011). Sensitivity/hardware sections cross-referenced
to Barry et al., Rev. Mod. Phys. **92**, 015004 (2020) ("Sensitivity optimization
for NV-diamond magnetometry"). Numbers you can plug in live in the companion
calculator `nv_odmr.py`; test yourself with `nv_quiz.md` / the interactive quiz.*

---

## Part 1 — How ensemble ODMR sensing works at the hardware level

### 1.1 The measurement chain

A continuous-wave (CW) ODMR magnetometer is, at its core, five elements:

1. **Optical pump (green, 515–532 nm).** Off-resonant excitation drives NV⁻
   through its spin-conserving optical cycle. The key asymmetry: from the excited
   ³E state, the m_s=±1 sublevels have a substantially higher probability of
   intersystem-crossing (ISC) into the metastable singlet (¹A₁→¹E) than m_s=0.
   The singlet decays preferentially back to the m_s=0 ground sublevel. Two
   consequences follow, and they are the whole basis of the technique:
   (i) **optical spin polarization** — after a few µs of pumping the ensemble is
   ~80–95 % in m_s=0; (ii) **spin-dependent photoluminescence (PL)** — m_s=0 is
   ~20–30 % brighter than m_s=±1 because the ±1 population is shelved in the dark
   singlet.

2. **Microwave drive (~2.87 GHz).** A wire, loop, stripline, or resonator
   delivers a microwave field B₁ perpendicular to the NV axis. When the MW
   frequency hits a ground-state spin resonance, it drives m_s=0 ↔ ±1, moving
   population into the darker states → **the PL drops**. Sweeping the MW
   frequency and recording PL traces out the ODMR spectrum: a set of Lorentzian
   dips at the spin transition frequencies.

3. **Photodetection.** A photodiode (ensemble, high flux) or APD/camera
   collects the red PL (637–800 nm) through a dichroic + long-pass filter.
   Ensembles emit enough light to use a simple amplified photodiode — this is
   why your Thorlabs-component setup works.

4. **Lock-in / modulation.** CW-ODMR is almost always run with lock-in
   detection: either the MW frequency is modulated (FM, giving a dispersive
   derivative lineshape whose zero-crossing is the resonance) or the MW is
   square-wave gated. This rejects laser-intensity 1/f noise and is what turns a
   shallow dip into a steep, zero-baseline discriminant.

5. **Field readout.** You park the MW on the steepest point of a chosen dip
   (max dPL/df). A small external field B shifts the resonance by γ_e·B_∥
   (2.8 MHz/G along the NV axis). The resulting PL change, divided by the slope,
   is your field estimate. Locking to opposite slopes of the +1 and −1 lines and
   subtracting cancels temperature/strain drift (common-mode) while doubling the
   magnetic (differential-mode) signal.

### 1.2 Why an ensemble, and the orientation trick

A bulk diamond hosts NV centres along **all four** ⟨111⟩ axes in equal
populations. Each family projects an external field differently
(B_∥ = **B**·**n̂**), so a single vector field produces up to **eight** electronic
resonances (four axes × two m_s transitions). Measuring three or more of these
projections lets you reconstruct the **full vector** **B** — this is vector
magnetometry, and it needs no moving parts. If you apply a modest bias field
along one axis you can spectrally isolate that family and work with a clean pair
of lines.

Ensemble √N advantage: signal (contrast) scales with N, shot noise with √N, so
sensitivity improves as √N — the central reason ensembles beat single NVs for
field sensing (single NVs win on spatial resolution).

### 1.3 Regimes: CW-ODMR vs pulsed

- **CW-ODMR** (your setup): simplest; laser and MW on continuously. Limited
  because the optical pumping that polarizes the spin **also** broadens the line
  (power broadening, §2.3). Best DC sensitivity typically ~few nT/√Hz to ~100
  pT/√Hz.
- **Pulsed ODMR:** separate the pump, the MW π-pulse, and the readout in time so
  the line is not power-broadened; linewidth → 1/(πT₂*). Better.
- **Ramsey (pulsed DC magnetometry):** free precession for time τ≈T₂*; approaches
  the T₂*-limited standard quantum limit (SQL).
- **AC magnetometry (Hahn echo / CPMG / XY-N):** dynamical decoupling extends the
  coherence used for sensing from T₂* to T₂ (often 100–1000× longer), giving the
  best AC field sensitivities. The trade is you sense narrowband AC fields, not DC.

---

## Part 2 — Current sensitivity & performance "world records"

*(Order-of-magnitude anchors; consult the cited works for exact conditions.
Records move — treat these as the landscape, not gospel.)*

| Regime | Benchmark sensitivity | Notes / source |
|---|---|---|
| **DC, broadband ensemble** | ~**0.9 pT/√Hz** (sub-pT) | Wolf et al., *Phys. Rev. X* **5**, 041001 (2015), "Subpicotesla diamond magnetometry" — the canonical DC record. |
| **DC, practical CW devices** | ~**1–100 pT/√Hz** | Barry et al. RMP 2020; typical optimized ensemble CW/pulsed devices. |
| **AC magnetometry** | **~1 pT/√Hz and below**; projected fT/√Hz with large volumes | dynamical-decoupling protocols; large sensing volumes lower normalized noise. |
| **Volume-normalized** | ~**few pT·µm³ᐟ²/√Hz** frontier | relevant when comparing sensors of different size. |
| **Broadband/laser-threshold schemes** | projected **~fT/√Hz** | laser-threshold magnetometry and intracavity absorption proposals. |
| **Diamond T₂ (isotopically pure ¹²C)** | up to **~1–2 ms** (ensemble) / seconds (single, low T) | ¹²C purification removes the ¹³C nuclear-spin bath. |
| **Zero-field / GHz AC** | active frontier | concatenated continuous dynamical decoupling for GHz-range AC sensing (2025 preprints). |

**What sets the ceiling.** The shot-noise-limited CW sensitivity is

$$\eta_B \;\approx\; \mathcal{P}_F\,\frac{4}{3\sqrt3}\,\frac{h}{g\mu_B}\,\frac{\Delta\nu}{C\sqrt{R}}$$

so you win by **narrowing the linewidth Δν**, **raising the contrast C**, and
**collecting more photons R**. The √N (spin number) and √T₂*(coherence) levers
appear explicitly in the SQL (Ramsey) limit
$\eta \approx 1/(\gamma_e C\sqrt{N\,T_2^*})$. Every hardware improvement —
better light collection (parabolic lenses, diamond nano-structuring, light
trapping), higher NV density with preserved coherence, isotopic ¹²C
purification, preferential N-to-NV conversion — is an attack on one of these
four factors.

---

## Part 3 — The mathematics: the ground-state spin Hamiltonian

Everything you see in an ODMR spectrum comes from the **electronic ground-state
spin-1 Hamiltonian** (energies in frequency units, S=1):

$$\boxed{\;\frac{H}{h} = D\!\left(S_z^2-\tfrac{2}{3}\right) + E\,(S_x^2-S_y^2)
+ \gamma_e\,\mathbf{B}\!\cdot\!\mathbf{S} + \mathbf{S}\!\cdot\!\mathbb{A}\!\cdot\!\mathbf{I}
+ H_Q \;}$$

with z along the N-V symmetry axis. Term by term:

### 3.1 Zero-field splitting D — the 2.87 GHz you always see
The dipolar spin–spin interaction of the two unpaired electrons splits m_s=0
from the degenerate m_s=±1 pair by **D ≈ 2.87 GHz** even at B=0. Group-theoretically
(Maze et al.), the ground state is a ³A₂ triplet; D is the axial fine-structure
constant. The −2/3 in (S_z²−2/3) just recentres the energy trace to zero — it
does not affect transition frequencies. **At B=0, E=0 both transitions sit
exactly at D.**

### 3.2 Electron Zeeman — how you measure a field
$\gamma_e\,\mathbf B\!\cdot\!\mathbf S$ with $\gamma_e = g_e\mu_B/h = 2.8025$
MHz/G (g_e ≈ 2.003). A field **along the axis** (B_∥) splits the ±1 pair
linearly and **symmetrically about D**:

$$f_\pm \approx D \pm \gamma_e B_\parallel \qquad(\text{axial, } E,B_\perp \text{ small})$$

So the **splitting between the two dips is 2γ_e B_∥ = 5.605 MHz per gauss** — read
the splitting, divide by 5.605, get B_∥ in gauss. A **transverse** field B_⊥
mixes the states and only shifts the levels at **second order**
(∝ B_⊥²/D), which is why NV magnetometry is naturally a *projective, axial*
measurement — a feature you exploit for vector sensing and a nuisance if your
bias is misaligned.

### 3.3 Transverse strain / electric field E — splitting at zero field
$E(S_x^2-S_y^2)$ lifts the ±1 degeneracy **even at B=0**, producing two dips at

$$f_\pm = D \pm \sqrt{E^2 + (\gamma_e B_\parallel)^2}\;\;\to\;\; D\pm E \text{ at } B=0.$$

E bundles together crystal **strain** and transverse **electric field** (they
enter the Hamiltonian identically via the ³A₂ ↔ E' coupling; Doherty §on
electric-field/strain). A stressed or implanted diamond shows a **zero-field
splitting of 2E** — often several MHz in an ensemble, and the reason your B=0
spectrum may show a doublet rather than one line. Different NV sites see
different local strain → a **distribution of E → inhomogeneous broadening** of
the ensemble line.

### 3.4 Hyperfine coupling A — the triplet (¹⁴N) or doublet (¹⁵N)
$\mathbf S\!\cdot\!\mathbb A\!\cdot\!\mathbf I$ couples the electron spin to the
**nitrogen nuclear spin**. The secular (dominant) part is $A_\parallel S_z I_z$.

- **¹⁴N (I=1, 99.6 % natural):** three nuclear projections m_I = −1,0,+1 →
  **each electronic line splits into 3**, spaced by **|A_∥|≈2.16 MHz**. This is
  the triplet you see on every ¹⁴N ODMR dip.
- **¹⁵N (I=½, isotopically labelled):** two lines spaced by **|A_∥|≈3.03 MHz**.
- The ¹⁴N **nuclear quadrupole** P≈−4.95 MHz (H_Q = P I_z²) shifts levels but
  does **not** itself add first-order EPR splittings (it is diagonal in m_I).
- A nearby **¹³C** (1.1 % natural abundance, I=½) adds *further* satellite
  splittings; the ¹³C nuclear-spin **bath** is the dominant T₂ limiter in
  natural diamond — hence ¹²C purification.

### 3.5 Temperature — D(T) and thermometry
D depends on temperature through thermal-expansion / electron–phonon coupling.
Near room temperature the dependence is approximately linear:

$$\frac{dD}{dT} \approx -74\ \text{kHz/K} \quad(-0.074\ \text{MHz/K}).$$

Both dips move **together** (same sign) when T changes, whereas a magnetic field
moves them **apart**. That is exactly how a single NV does simultaneous
thermometry + magnetometry: the **sum** f₊+f₋ ∝ 2D(T) tracks temperature; the
**difference** f₊−f₋ ∝ 2γ_e B_∥ tracks field. Over wide ranges D(T) is nonlinear
(polynomial fits in the literature); the linear coefficient is the room-T
working value.

### 3.6 Putting it together — the line positions
For one orientation, to a good approximation in the axial regime:

$$f_\pm(T,B_\parallel,E,m_I) \;=\; D(T)\;\pm\;\sqrt{E^2+(\gamma_e B_\parallel)^2}\;+\;A_\parallel\,m_I.$$

Diagonalize the full 3×3 (the calculator does this exactly, including transverse
terms) when B_⊥ or E is not small.

---

## Part 4 — Linewidths: what sets Δν

The ODMR **contrast** and **linewidth** together set your sensitivity, so
understanding Δν is understanding your noise floor.

1. **Intrinsic / T₂*-limit.** A CW line's minimum FWHM is
   $\Delta\nu_{\min} = 1/(\pi T_2^*)$. For T₂* = 1 µs → 0.32 MHz; for 100 ns →
   3.2 MHz. T₂* (inhomogeneous dephasing) is set by the static spread of local
   fields.

2. **Inhomogeneous broadening (the ensemble tax).** In an ensemble T₂* is
   dominated by (a) the **¹³C nuclear-spin bath**, (b) **paramagnetic N (P1)
   centres** — substitutional nitrogen not converted to NV, whose electron spins
   produce a magnetic-noise bath scaling with [N], and (c) **strain/E-field
   spread** (§3.3). This couples density to linewidth: pushing NV density up to
   gain √N raises [N] and broadens the line — the central engineering tension in
   ensemble sensors.

3. **Power broadening.** CW pumping and CW MW drive both broaden:
   $\Delta\nu \approx \frac{1}{\pi T_2^*}\sqrt{1+s_\text{opt}+\beta_\text{MW}}$,
   with s_opt the optical saturation (∝ laser intensity) and β_MW ∝ Ω_R²
   (∝ MW power). There is an **optimum**: too little power → weak contrast; too
   much → broad line. Optimizing C/√Δν over laser & MW power is the standard
   CW-ODMR tune-up, and is exactly why pulsed schemes (which remove power
   broadening) do better.

4. **Magnetic-gradient / bias-inhomogeneity broadening.** A non-uniform bias
   field across the sensing volume smears the resonance.

The calculator exposes `linewidth_from_T2star`, `power_broadened_linewidth`, and
folds Δν and C into `sensitivity_cw`, so you can see each lever numerically.

---

## Part 5 — Counting the dips (a worked mental model)

For an ensemble in a **generic** field with **¹⁴N**:

$$N_\text{dips} = \underbrace{4}_{\text{orientations}}\times
\underbrace{2}_{m_s=\pm1}\times \underbrace{3}_{^{14}\!N\ m_I} = 24.$$

Symmetry collapses this:
- **B ∥ [100]:** all four axes make equal angles → the four families are
  degenerate → 2×3 = **6 dips**.
- **B ∥ [111]:** one family axial + three equivalent off-axis → 4 electronic
  lines × 3 = **12 dips**.
- **Generic B:** all distinct → **24 dips**.
- **¹⁵N** replaces the ×3 by ×2 (so 16 generic); **zero N hyperfine resolved**
  (or ¹²C-only counting) gives the bare 8 / 2 / 4.
Use `nv_odmr.n_dips(B, axes, isotope, resolve_MHz)` to get the exact resolvable
count for any field and linewidth.

---

## Part 6 — Using the calculator

```python
import sys; sys.path.insert(0, ".")   # if needed
import nv_odmr as nv, numpy as np

# 1) Splitting from an axial field (read B from a spectrum)
nv.transitions((np.array([1,1,1])/np.sqrt(3))*50, "[111]")   # -> [2729.9, 3010.1] MHz

# 2) How many dips will I see? (ensemble, 14N, 0.3 MHz resolution)
nv.n_dips(np.array([12.,8.,25.]), "all", isotope="14N")      # -> (24, [freqs...])

# 3) Zero-field strain doublet
nv.transitions([0,0,0], "[111]", E=6.0)                      # -> D-6, D+6

# 4) Temperature shift of D
nv.D_of_T(310)                                               # -> 2870 - 0.74 MHz

# 5) Linewidth and CW sensitivity
nv.linewidth_from_T2star(1.0)                                # 0.318 MHz FWHM
nv.sensitivity_cw(contrast=0.03, linewidth_MHz=0.5,
                  photon_rate_per_s=1e12)                    # T/sqrt(Hz)

# 6) Standard-quantum-limit (Ramsey) sensitivity
nv.sensitivity_sql(N_spins=1e12, T2star_us=1.0)             # T/sqrt(Hz)
```

All constants (D0, dD/dT, γ_e, A_∥, P) are module-level — override them to match
your sample or a different reference.

---

## Key references
- **Doherty, Manson, Delaney, Jelezko, Wrachtrup, Hollenberg**, "The
  nitrogen-vacancy colour centre in diamond," *Phys. Rep.* **528**, 1 (2013).
- **Maze, Gali, Togan, Chu, Trifonov, Kaxiras, Lukin**, "Properties of
  nitrogen-vacancy centers in diamond: the group theoretic approach," *New J.
  Phys.* **13**, 025025 (2011).
- **Barry, Schloss, Bauch, Turner, Hart, Pham, Walsworth**, "Sensitivity
  optimization for NV-diamond magnetometry," *Rev. Mod. Phys.* **92**, 015004
  (2020).
- **Wolf, Neumann, Nakamura, Sumiya, Ohshima, Isoya, Wrachtrup**,
  "Subpicotesla diamond magnetometry," *Phys. Rev. X* **5**, 041001 (2015).
