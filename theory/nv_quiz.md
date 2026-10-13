# NV-Centre ODMR & Sensitivity — Self-Test

*Work each problem, then check against the worked solution. Constants:
D₀=2870 MHz, γ_e=2.8025 MHz/G, A_∥(¹⁴N)=2.16 MHz, A_∥(¹⁵N)=3.03 MHz,
dD/dT=−0.074 MHz/K. Verify any numeric answer with `nv_odmr.py`.*

---

## A. Conceptual (short answer)

**A1.** Why does the m_s=0 sublevel fluoresce more brightly than m_s=±1? Name the
level responsible for the contrast.

**A2.** In CW-ODMR you park the microwave on the *steepest* part of a dip, not
its centre. Why?

**A3.** You change the temperature of your diamond. Do the two dips move *apart*,
*together*, or *in the same direction*? Contrast this with what a magnetic field
does, and explain how one measurement separates B from T.

**A4.** Why does raising NV density to gain the √N sensitivity advantage tend to
*degrade* the linewidth? Name the two microscopic culprits.

**A5.** Why is NV magnetometry intrinsically a *projective* (axial) field
measurement? What happens to the levels under a purely transverse field, and to
what order in B_⊥?

---

## B. Spectrum arithmetic

**B1.** Zero applied field, an unstrained sample, ¹⁴N. How many ODMR dips, and at
what frequencies?

**B2.** Same sample, now with transverse strain giving E=4 MHz, still B=0, ignore
hyperfine. Where are the dips and what is their splitting?

**B3.** A field of 30 G lies **along** one NV axis. For *that* orientation, where
are the two electronic lines? What is the dip-to-dip splitting in MHz, and how
would you back out B_∥ from a measured splitting of 168.15 MHz?

**B4.** Ensemble, ¹⁴N, generic field direction. How many resolvable dips in
total? Now the field is rotated to lie along [100] — how many? Along [111]?

**B5.** You switch to a ¹⁵N-enriched sample. Re-answer B4 for the generic case.

---

## C. Linewidth & temperature

**C1.** Your ensemble has T₂* = 250 ns. What is the intrinsic (unbroadened) CW
FWHM? What T₂* would you need to reach a 100 kHz line?

**C2.** With optical saturation s_opt=2 and MW broadening β_MW=3 on that same
250 ns sample, estimate the CW linewidth. By what factor is it broadened?

**C3.** Your zero-field line sits at 2867.8 MHz instead of 2870.0. Assuming the
shift is purely thermal, what is the sample temperature?

---

## D. Sensitivity

**D1.** A CW device has contrast C=2 %, linewidth Δν=0.8 MHz, photon rate
R=5×10¹¹ counts/s. Estimate the shot-noise DC sensitivity in pT/√Hz. Which single
change helps most: halving Δν, doubling C, or 4× more light?

**D2.** An ensemble has N=10¹¹ spins and T₂*=1.5 µs. What is the (ideal) SQL
Ramsey sensitivity? Why is the real device far above this?

---

# WORKED SOLUTIONS

**A1.** The spin-dependent intersystem crossing: m_s=±1 cross more readily into
the metastable **singlet (¹A₁/¹E)**, which is dark and decays back to m_s=0. So
±1 is dimmer and the singlet is the "shelving" level that creates both the
polarization and the contrast.

**A2.** Sensitivity ∝ slope dPL/df of the discriminant. Field shifts the
resonance; the PL change you read is (slope)×(shift). The slope is maximal on the
flanks, zero at the dip minimum — so you lock where the response to a field is
largest. (Lock-in FM detection makes this the zero-crossing of the derivative.)

**A3.** **Together / same direction.** D(T) shifts both f₊ and f₋ by the same
amount and sign, so the *sum* f₊+f₋ = 2D(T) tracks temperature. A magnetic field
shifts them **apart** (f_±=D±γ_eB_∥), so the *difference* f₊−f₋ = 2γ_eB_∥ tracks
field. Sum → thermometry, difference → magnetometry; measuring both lines
separates them.

**A4.** More NV needs more substitutional **nitrogen (P1 centres)**, whose
electron spins form a paramagnetic **magnetic-noise bath** that shortens T₂*
(broadens the line); and the associated **¹³C nuclear-spin bath** / strain spread
add inhomogeneous broadening. Density buys √N in signal but costs you in Δν —
the core ensemble trade-off.

**A5.** The Zeeman term along the axis (γ_eB_∥S_z) shifts levels **linearly**; a
transverse field B_⊥ only **mixes** m_s=±1 and shifts energies at **second
order** (∝ B_⊥²/D) because D≫γ_eB_⊥. So to first order the NV responds only to
the **projection** B_∥ = **B·n̂** — the basis for vector reconstruction from the
four orientations.

**B1.** Both transitions coincide at D → a single electronic line at 2870, split
by ¹⁴N into **3 dips** at **2867.84, 2870.00, 2872.16 MHz** (±2.16).

**B2.** f_± = D±E = **2866 and 2874 MHz**, splitting **2E = 8 MHz**.

**B3.** f_± = 2870 ± 2.8025×30 = **2785.9 and 2954.1 MHz**; splitting
2γ_eB = **168.15 MHz**. From a measured 168.15 MHz: B_∥ = 168.15/(2×2.8025) =
**30.0 G**.

**B4.** Generic: 4 orientations × 2 × 3 = **24**. Along **[100]** all four axes
equivalent → 2×3 = **6**. Along **[111]** one axial + three equivalent → 4×3 =
**12**.

**B5.** ¹⁵N replaces the ×3 hyperfine by ×2 → generic = 4×2×2 = **16 dips**.

**C1.** FWHM = 1/(πT₂*) = 1/(π·0.25 µs) = **1.27 MHz**. For 0.1 MHz you need
T₂* = 1/(π·0.1 MHz) = **3.18 µs**.

**C2.** FWHM = (1/πT₂*)·√(1+s_opt+β_MW) = 1.27·√(1+2+3) = 1.27·√6 =
**3.12 MHz**, i.e. broadened by **√6 ≈ 2.45×**.

**C3.** ΔD = 2867.8−2870.0 = −2.2 MHz; ΔT = ΔD/(dD/dT) = −2.2/−0.074 ≈ **+29.7 K**
above the 300 K reference → T ≈ **330 K**.

**D1.** η ≈ P_F·(4/3√3)·(1/γ)·Δν/(C√R). With γ=2.8025×10¹⁰ Hz/T, Δν=8×10⁵ Hz,
C=0.02, R=5×10¹¹, P_F≈0.7:
η ≈ 0.7·0.7698·(3.57×10⁻¹¹)·(8×10⁵)/(0.02·7.07×10⁵) ≈ **1.1 nT/√Hz**
(≈1090 pT/√Hz). Halving Δν → ÷2; doubling C → ÷2; 4× light → ÷2. All three give
the same factor of 2 here, because η ∝ Δν/(C√R) — √R means you need **4×** light
to match a **2×** gain in C or Δν. So per unit effort, improving C or narrowing
Δν beats scaling light. (Check with `nv.sensitivity_cw(0.02,0.8,5e11)`.)

**D2.** η_SQL = 1/(γ_rad·√(N·T₂*)), γ_rad=2π·2.8025×10¹⁰ rad/s/T,
√(10¹¹·1.5×10⁻⁶)=√(1.5×10⁵)=387. η ≈ 1/(1.76×10¹¹·387) ≈ **1.5×10⁻¹⁴ T/√Hz =
0.015 pT/√Hz = 15 fT/√Hz**. The real device is far worse because of finite
readout fidelity (optical contrast ≪1, few photons per shot), dead time, power
broadening in CW, and inhomogeneity — the SQL is the ceiling, not the achieved
value.
