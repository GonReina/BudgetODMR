# Quadrupole resonance, the NV centre, and measuring the ¹⁴N quadrupole P

Numbers in this note come from `n14_levels.py` in this folder. It diagonalises the
9-level NV + ¹⁴N ground-state Hamiltonian and models a magnet pair.

---

## 1. Nuclear quadrupole resonance (NQR) in one page

**The moment.** Any nucleus with spin I ≥ 1 has a non-spherical charge distribution,
either a stretched "cigar" or a flattened "pancake". This is its *electric quadrupole
moment* eQ. Nuclei with spin I = 1/2 (¹H, ¹³C, ¹⁵N) are spherical and have none.

**The field it feels.** In a solid, the nucleus sits in the electric field of its
neighbours. A uniform field only pushes the nucleus as a whole. The *gradient* of the
field does something more: it torques the cigar and favours some orientations over
others. That gradient is a 3×3 tensor, the electric field gradient (EFG),
V_ij = ∂²V/∂x_i∂x_j. In its own axes it is described by:
- the largest component, V_zz = eq;
- the asymmetry parameter η = (V_xx − V_yy)/V_zz, between 0 and 1.

At a site with cubic symmetry the EFG is zero, so there is no quadrupole splitting.
A lower-symmetry site is needed.

**The Hamiltonian.**

    H_Q = e²qQ / (4I(2I−1)) · [ 3I_z² − I(I+1) + η (I_x² − I_y²) ]

It depends on I_z², so states +m and −m have the same energy. The levels split *with
no magnet at all*. NQR means driving transitions between these levels with an RF
coil, in zero field. It is NMR without the magnet. The frequencies are fingerprints of
the chemical bonding and are very temperature dependent, which is why NQR has been used
for thermometry and for detecting explosives (¹⁴N lines at a few MHz).

**For I = 1 (¹⁴N)**, with axial symmetry (η = 0):
- the levels are m = 0 and a degenerate pair m = ±1, separated by P = 3e²qQ/4;
- there is one NQR line at |P|;
- η ≠ 0 splits it into two lines;
- a small magnetic field B splits it into |P| ± γ_n B, where γ_n(¹⁴N) = 3.077 kHz/mT.

**Why NQR is hard.** The thermal population difference at a few MHz and room
temperature is about hν/kT ≈ 10⁻⁶. The signal is tiny, so conventional NQR needs large
samples. The NV trick below replaces thermal polarisation with *optical pumping*
(about 90 % or more) and replaces the pickup coil with *photons*.

---

## 2. The NV⁻ centre: two different "quadrupoles"

### 2a. The electron spin is not a quadrupole, but it obeys the same equation

The NV⁻ ground state is an electron spin triplet, S = 1:

    H_e = D [S_z² − S(S+1)/3] + E (S_x² − S_y²)

This has *exactly* the form of H_Q above:

| NQR term | electron-spin term | value |
|---|---|---|
| splitting P | D | 2.87 GHz |
| asymmetry η | E | ~2.7 MHz in your sample |

But the physics is different. D comes from the *magnetic* dipole–dipole interaction
between the two unpaired electrons, not from an electric quadrupole. Electrons have no
quadrupole moment. E comes from strain and local electric fields, just as η comes
from a distorted EFG.

So your zero-field ODMR is the electron-spin analogue of an NQR spectrum. The
5.3 MHz doublet at 2870 MHz is the "η-split NQR line" of this analogue. Like real NQR
lines, D shifts with temperature, by about −74 kHz/K.

### 2b. The real nuclear quadrupole: the NV's own ¹⁴N

The nitrogen of the NV is ¹⁴N (I = 1, 99.6 % abundant). It sits in the steep EFG of
the defect, on the symmetry axis, so η = 0. The full ground-state Hamiltonian is:

    H = D S_z² + γ_e B·S + A∥ S_z I_z + A⊥ (S_x I_x + S_y I_y) + P I_z² − γ_n B·I

| parameter | value | what it is |
|---|---|---|
| D | 2870 MHz | electron zero-field splitting |
| A∥ | −2.16 MHz | hyperfine coupling along the NV axis |
| A⊥ | −2.70 MHz | transverse hyperfine coupling |
| **P** | **−4.945 MHz** | **¹⁴N quadrupole: the quantity to measure** |
| γ_e, γ_n | 28.024 MHz/mT, 3.077 kHz/mT | electron and ¹⁴N gyromagnetic ratios |

**Why CW ODMR cannot see P.** A microwave photon flips the electron spin
(Δm_S = ±1) and leaves the nucleus alone (Δm_I = 0). The quadrupole energy P·m_I² is
the same before and after, so it cancels in the transition frequency. What ODMR *does*
show is A∥, as the hyperfine triplet: three lines 2.16 MHz apart, one per m_I.

**To see P you must drive the nucleus itself** (Δm_I = ±1, Δm_S = 0) with RF. That is
optically detected NMR (ODNMR), also called ENDOR. The nuclear transitions
(`n14_levels.py`):

| field along the NV axis | m_S = 0: m_I 0 ↔ ±1 | m_S = −1: m_I +1↔0, 0↔−1 |
|---|---|---|
| 0 mT | 4.943 MHz (twofold) | 2.788, 7.108 MHz |
| 51 mT | 5.097, 4.786 MHz | 2.942, 6.953 MHz |

Reading the table:
- **In m_S = 0, the line sits at ≈ |P| ± γ_n B.** That is pure NQR of the nitrogen,
  with a small second-order hyperfine shift: 4.943 MHz instead of 4.945 MHz.
- **In m_S = −1, the hyperfine coupling adds:** the lines are at ≈ |P| ∓ |A∥|. Their
  mean is |P| again, and their difference is 2|A∥|.

---

## 3. How the measurement works (ODNMR)

Three ingredients are needed. Each has a matching hurdle in §4.

### Ingredient 1: resolved hyperfine lines

The microwaves must address one nuclear state at a time. You park the MW frequency on
the line belonging to, say, m_I = +1. That only works if the three hyperfine lines,
2.16 MHz apart, are resolved: each must be narrower than about 1.5 MHz. **This is the
gate for the whole experiment.**

### Ingredient 2: a nuclear population difference, from the ESLAC

The thermal polarisation (10⁻⁶) is useless. The NV *excited state* is also a triplet,
with D_es ≈ 1.42 GHz. At B ≈ D_es/γ_e ≈ **51 mT along the NV axis**, the excited-state
levels |m_S = 0⟩ and |m_S = −1⟩ cross. This is the excited-state level anticrossing
(ESLAC).

Near the crossing, the transverse hyperfine term A⊥ mixes |0, m_I⟩ with
|−1, m_I+1⟩. The electron spin flips back to m_S = 0 at every optical cycle, while the
nuclear spin keeps getting pushed one step. After many cycles the ¹⁴N piles up in one
outer state. Jacques et al. measured about 98 % polarisation for this
(PRL 102, 057403, 2009).

**How to see it with no RF:** the hyperfine-resolved ODMR triplet turns into one
dominant line, and this happens only within a few mT of 51 mT. That observation is
already a nice experiment in its own right (step 2 in §5).

**Alignment matters.** A field component transverse to the NV axis mixes the electron
states and destroys the effect. The magnet has to be aligned with one NV axis to
better than about 1°. In an ensemble only that one orientation class, ¼ of the NVs,
takes part. The other three classes see a 109.5° field, are strongly mixed, and only
add background PL.

### Ingredient 3: the RF drive and how it shows up in the PL

The detection logic:

1. **Polarise:** the laser pumps the nuclei into, say, m_I = +1 (ingredient 2).
2. **Park the MW:** set it on the |0, +1⟩ → |−1, +1⟩ line. Because almost all NVs are
   in m_I = +1, this gives the *full* ODMR dip.
3. **Drive the nucleus:** apply RF at the |0, +1⟩ ↔ |0, 0⟩ nuclear frequency (~5.1 or
   ~4.8 MHz at 51 mT, depending on which state is polarised). It moves population into
   m_I = 0, whose MW line is 2.16 MHz away from where the MW is parked.
4. **Read the PL:** fewer NVs are now resonant with the MW, so the dip gets shallower
   and **the PL goes up**.
5. **Sweep:** step the RF frequency, toggling the RF on and off at each step, and
   record PL_on/PL_off. The nuclear line shows up as a peak above 1.

**Extracting P.**
- From the m_S = 0 line at ν₀: |P| ≈ ν₀ ∓ γ_n B. B is known very precisely from the
  electron line itself (γ_e B to about 0.1 %), so γ_n B ≈ 0.157 MHz at 51 mT is known
  to better than 1 kHz.
- To include the small second-order terms exactly, adjust P in `n14_levels.py` until
  the computed line matches the measured one.
- The m_S = −1 lines (~2.94, ~6.95 MHz) give A∥ as a cross-check. To see them, the MW
  must keep some population in m_S = −1.

**Driving strength.** The bare ¹⁴N is very weakly driven: γ_n = 3 kHz/mT, i.e. only
about 2.2 kHz of nuclear Rabi frequency per mT of RF field. But A⊥ mixes in a little
electron spin, and γ_e is about 9000× larger. This *hyperfine enhancement* raises the
drive by a factor of 16–22 at these fields:

| transition (51 mT) | enhancement | nuclear Rabi frequency per mT of B₁ |
|---|---|---|
| m_S = 0, m_I ±1 ↔ 0 | ×21.8 | 47 kHz |
| m_S = −1 | ×18 | 39 kHz |

The B₁ field must be **perpendicular to the NV axis**, i.e. to the magnet field. The
RF has to depolarise the nucleus faster than the laser repolarises it. So the nuclear
Rabi frequency (tens of kHz with B₁ ≈ 0.3–1 mT) has to compete with the optical
pumping rate. That means **low laser power**, and the laser power is the main knob to
scan.

---

## 4. Can your rig do it? (Red Pitaya + coil + magnet)

**Short answer: yes in principle, with three real hurdles.** In order of how
likely each is to stop you: the linewidth, the magnet homogeneity, and the MW
amplifier band.

| need | your rig | verdict |
|---|---|---|
| RF source, 2.5–7.5 MHz, switchable | Red Pitaya OUT2: 125 MS/s DAC, ±1 V, SCPI `SOUR2:FREQ:FIX`, `OUTPUT2:STATE` | **yes** |
| RF power for B₁ ≈ 0.3 mT | RP gives ≤ 20 mA into 50 Ω (≈ 0.02 mT) | **buy** an HF power amplifier (1–30 MHz, 1–5 W) |
| RF coil | not yet | **wind one** (below) |
| PL readout with on/off ratio | RP IN1, same as the MW on/off code | **yes** |
| MW at the aligned class's 0 → −1 line, 1.44 GHz | SMCV100B covers it; the ZHL-16W-43-S+ amplifier is specified for 1.8–4.0 GHz | **hurdle**: run without the amplifier or get one that covers 1.4 GHz; change the `config.json` `mw_chain` limit to match; check the antenna response at 1.44 GHz |
| 0 → +1 line instead (4.30 GHz) | above the amplifier band, and above 3 GHz needs the SMCV frequency option | probably no |
| 51 mT, homogeneous, aligned to < 1° | the magnet behind the antenna gave a ~100 MHz smear | **hurdle**: needs a facing magnet pair (below) |
| lines narrower than ~1.5 MHz | ~4.5 MHz FWHM per line at the powers used so far | **gate**: test first (step 0) |

### The magnet: why one magnet fails and two work

A single magnet has a steep gradient where its field is 51 mT. Across the probed
depth, the line moves by:

| single N42 magnet | gradient | line shift across 0.1 mm |
|---|---|---|
| 10×10 mm | 10 mT/mm | 29 MHz |
| 25×25 mm | 4 mT/mm | 11 MHz |
| 50×50 mm | 2 mT/mm | 6 MHz |

That smears the hyperfine lines completely, which is what you saw in the wide sweep.

**Two identical magnets facing each other** (attracting, N facing S) cancel the
gradient at the midpoint, exactly like a Helmholtz pair:

| facing pair, N42 | gap for 51 mT | spread at ±0.25 mm | spread at ±0.5 mm |
|---|---|---|---|
| 20×20 mm | 55 mm | 0.39 MHz | 1.5 MHz |
| **25×25 mm** | **68 mm** | **0.25 MHz** | **1.0 MHz** |
| 40×40 mm | 109 mm | 0.10 MHz | 0.39 MHz |

**A 25×25 mm pair with a 68 mm gap works if the probed volume sits within about
±0.25 mm of the midpoint.** The field is set by the gap: roughly 1–2 mT per mm of gap
change near 51 mT, so a screw-adjusted gap is your field knob. The 68 mm gap also
leaves room for the antenna and the objective.

The magnets attract each other with a large force. Use a rigid aluminium or brass
frame and keep steel tools away.

**Alignment.** For a (100)-cut plate, the NV axes are 54.7° from the plate normal, so
the magnet axis must be tilted by that angle and rotated to lie along a ⟨111⟩
direction. For a (111)-cut plate, one class lies along the normal.

Check alignment with ODMR. When the field is exactly along one axis:
- the other three classes become equivalent and their lines merge into one;
- the aligned class's 0 → −1 line is at its lowest frequency.

### The RF coil

Make a small loop as close to the laser spot as possible, with its field perpendicular
to the magnet axis. For example, 3 turns of 0.3 mm wire, 3 mm diameter, around or next
to the spot:
- **field:** B₁ ≈ μ₀N/(2r) ≈ 1.26 mT per amp;
- **target:** 0.25 A peak gives B₁ ≈ 0.3 mT, a nuclear Rabi frequency of about
  15 kHz in m_S = 0;
- **impedance:** the loop is a fraction of a µH. At 5 MHz that is a few ohms, so put a
  ~50 Ω power resistor in series (away from the sample) to load the amplifier
  broadband;
- **power:** 0.25 A peak into 50 Ω is about 1.6 W, i.e. a +32 dBm amplifier.

Watch for two side effects:
- **Heating.** D shifts by −74 kHz/K, and a warm sample walks the parked MW line off
  resonance. Toggling RF on and off at every point cancels slow drifts, but keep the
  average power low.
- **RF pickup in the photodiode electronics.** Measure the on/off ratio with the laser
  blocked: it must stay at 1.

### Expected signal

At most, the RF can remove the dip of the aligned class at the parked MW frequency.
With ¼ of the NVs taking part and a few % contrast, expect a PL change of about
0.1–0.5 %. Your on/off ODMR already reaches noise levels of a few 10⁻⁴ per point, so
this is detectable once the first three hurdles are cleared.

---

## 5. Step-by-step plan

0. **Linewidth check (no new hardware).** Run the FINE spectra of
   `cal3_mw_laser_map.py` (0.1 MHz steps, low laser and MW power). The hyperfine
   triplet should appear as three dips 2.16 MHz apart, or at least as a flat-bottomed
   or shouldered line.
   - If each line stays wider than about 2 MHz even at the lowest powers, the
     diamond's intrinsic linewidth (nitrogen content / T₂*) rules out this experiment
     with this sample.
   - One thing in your favour: at 51 mT the strain doublet (E) is suppressed, because
     γ_e B ≫ E. So the lines may be cleaner there than at zero field.
1. **Field.**
   - Build the magnet pair on a gap-adjustable rail.
   - Find the aligned class's 0 → −1 line near 1.44 GHz. Sort out the MW amplifier
     and antenna at this frequency.
   - Align the field using the three merged lines of the other classes.
   - Centre the sample between the magnets by minimising the linewidth.
2. **Nuclear polarisation (no RF).**
   - Take hyperfine-resolved ODMR of the 0 → −1 line at gaps giving 40–60 mT.
   - The triplet should become one dominant line near 51 mT. That shows the ESLAC
     pumping, and it tells you which m_I is polarised.
3. **ODNMR.**
   - Park the MW on the dominant hyperfine line.
   - With the Red Pitaya, sweep the RF over 4.6–5.3 MHz in ~5 kHz steps, toggling the
     RF on and off at each step. Record PL_on/PL_off.
   - Expect one peak, at ~5.10 or ~4.79 MHz.
   - Then try 2.8–3.1 MHz and 6.8–7.1 MHz for the m_S = −1 lines.
   - Scan the laser power to trade polarisation against RF saturation.
4. **Extract P (and A∥).** Fit the line centres. Compute γ_n B from the measured
   electron line. Adjust P (and A∥) in `n14_levels.py` until the computed transitions
   match the measured ones.

The software needs are small: an RF on/off sweep is the existing MW on/off loop with
`SOUR2:FREQ:FIX` in place of the SMCV frequency, and it can live in a new
`experiments/` folder when you get there.

---

## References

- V. Jacques et al., *Dynamic polarization of single nuclear spins by optical pumping
  of NV color-center spins in diamond at room temperature*, PRL **102**, 057403 (2009).
  ESLAC nuclear polarisation.
- M. W. Doherty et al., *The nitrogen-vacancy colour centre in diamond*, Phys. Rep.
  **528**, 1 (2013). NV Hamiltonian, hyperfine and quadrupole parameters, ESLAC.
- `theory/nv_deep_dive_guide.md` covers the electron-spin side of the NV in this repo.
