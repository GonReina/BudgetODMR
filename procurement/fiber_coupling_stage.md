# Free-space → fibre coupling stage — parts list

All prices **ex-VAT**, read from thorlabs.com on 15 Sep 2026 (EUR, Bergkirchen DE warehouse).
Reviewed 30 Sep 2026 against the optical model in `notebooks/Optical_Setup.ipynb` (§2):
corrected beam path below, beam-size numbers recomputed for this fibre's 4.0 µm mode.

## Reviewed beam path — what goes where, and why

```
LAUNCH END (beam walk, alignment-critical)
DJ532-40 ─► M1 (KS1+BB1-E02P) ─► M2 (KS1+BB1-E02P) ─► [iris A] ─► λ/2 (RSP1/M) ─► [iris B] ─► F240APC-532 ─► fibre
 ~1.4 mm    150–300 mm apart      iris A just after M2, iris B just before the coupler, as far apart as possible

DELIVERY END (collimated, nothing here is alignment-critical)
fibre ─► F810APC-543 (confocal)  ─► LPVISE100-A ─► NE10A / NE20A ─► FBW5532-10 ─► DMLP550R ─► objective
      or F240APC-532 (ensemble)     fixed, on the    tilted 2–5°      fixed mount
                                    slow axis
```

Compared with the proposed order
`DJ532-40 → FBW5532-10 → polariser → iris → M1 → M2 → iris → collimator → fibre → collimator → ND → λ/2 → DMLP550R`,
five things move:

1. **λ/2 plate: launch side, after M2, before the coupler, not before the DMLP550R.** Its job
   is to rotate the laser's linear polarisation onto the fibre's slow axis. That is what
   makes the PM fibre polarisation-maintaining. It goes *after* the mirrors because it can
   rotate linear polarisation but cannot undo the ellipticity that 45° dielectric mirrors
   add. Keep the laser polarisation s or p on M1/M2 (the plate fixes the orientation
   afterwards). At the delivery end, a λ/2 in front of the DMLP550R would rotate the
   polarisation *at the dichroic*. 532 nm sits on its 533 nm reflection-band edge, where
   reflectance is polarisation-dependent, so it would change the excitation power and
   NV-orientation selectivity together. If you later want polarisation control at the
   sample, put a **second** λ/2 between the DMLP550R and the objective.
2. **Linear polariser: after the output collimator, fixed on the slow axis, not at the
   launch.** At the launch it is redundant if the DPSS output is already well polarised
   (check once: rotate it in front of the power meter). As a *rotating* attenuator it would
   also misalign the input polarisation from the PM axis. After the fibre, fixed, it acts as
   a clean-up polariser. The residual polarisation wander (≤ −15 dB extinction ratio) then
   becomes a ≤ 3 % power change instead of a polarisation change at the dichroic. **Do not
   rotate it for power control.** At 45° to the slow axis the fibre's thermal birefringence
   drift becomes ±17 % power wander (notebook §2). Step the power with the ND filters.
3. **FBW5532-10: after the fibre, not before.** Silica fibre generates weak Raman and
   fluorescence background above 540 nm. Part of it reaches the detector: it is reflected by
   the DMLP550R, bounces off the diamond (~17 %), and passes the FELH0550. The line filter
   has to sit after the fibre to remove it (and any residual pump IR with it). It is wedged
   (~30′ → 4 mrad deviation → **~20 µm focus shift** with the N40X-PF), so give it a fixed
   mount and align after it. Ø12.5 mm clips only ~0.3 % of a 5.9 mm beam.
4. **Irises: both after the mirrors.** An iris before M1 sees a beam whose position is fixed
   by the laser, so it adds nothing to the walk. It is still useful as a safety aperture.
   Beam walking needs two reference points *downstream* of M2 (steps 1–4 of the procedure
   below).
5. **ND filters: after the collimator (as proposed).** In the collimated beam a flat plate
   adds no aberration. A 3° tilt shifts the beam by ~36 µm, which is harmless. Tilting keeps
   their reflections out of the fibre. Between fibre and lens the same 2 mm plate would move
   the focus by 0.7 mm and ruin the collimation.

The output collimator **is** an asphere acting as a collimator (a point source, the 4 µm
mode, at its focus). Use a fixed-focus APC package rather than an ACL condenser: the
package sets the fibre–lens spacing at the factory, compensates the 8° APC facet, and is
AR-coated at 532 nm.

## The fibre has two ends, and they want different collimators

This is the thing to hold onto, because the two requirements pull in opposite directions:

| End | Job | Beam diameter needed | Set by |
|---|---|---|---|
| **Launch** (laser → fibre) | focus the laser onto the fibre core | match the **laser's** beam, ≈ 1.3–1.5 mm | `F240APC-532` |
| **Delivery, confocal** (fibre → microscope) | collimate for the objective pupil | fill the **7.5 mm** back aperture | `F810APC-543` |
| **Delivery, ensemble** | reproduce today's beam | ≈ 1.3 mm (effective NA 0.13, ~2.5 µm spot, no saturation) | a second `F240APC-532` |

The two delivery options are different experiments, not better and worse. For ensemble
ODMR a pupil-filling beam makes a ~0.4 µm spot that saturates the NVs at mW powers.
Mount the delivery collimator in an SM1 adapter so that swapping them is a two-minute job.

> **APC, not PC** — see the connector section below. Both collimators you own are the
> FC/**PC** variant and your fibre is FC/**APC**. This is probably not a detail.

Both focus to the same spot at the fibre tip. They have to, since it is the same fibre
mode (MFD ≈ 4.0 µm at 532 nm for this fibre), so either *could* sit at either end. What
differs is the free-space beam diameter on the other side of the lens, D = 4λf/(π·MFD).
That diameter is chosen by what the lens has to talk to: a ~1.4 mm laser beam at one end,
a 7.5 mm objective pupil at the other.

---

## The connector mismatch — check this before anything else

Your fibre, [`P3-405BPM-FC-1`](https://www.thorlabs.com/thorproduct.cfm?partnumber=P3-405BPM-FC-1),
is **FC/APC** (8° angled ferrule). Your parts list records both collimators as
`F240FC-532`, which is the **FC/PC** (flat) variant. An APC ferrule will screw happily
into a PC receptacle — and then misbehave.

Light leaving an 8° silica facet is refracted **3.70°** off the fibre axis
(sin θ_air = 1.4573 × sin 8°). Thorlabs compensate for this by angling the receptacle in
the APC versions, so that "light exiting the fiber enters the collimator perpendicular to
the focal plane." In a PC receptacle there is no compensation, and the cone strikes the
lens off-centre by f·tan(3.70°):

| Collimator | f | Lateral offset at the lens |
|---|---|---|
| `F240` | 7.86 mm | **0.51 mm** |
| `F810` | 34.74 mm | **2.25 mm** |

At the launch end that is a large fraction of a 1.48 mm beam — enough to vignette the
coupling cone, wreck the mode overlap, and make the alignment behave in ways that no
amount of beam-walking explains. **This is a strong candidate for why the coupling never
worked.**

**Action: read the engraving on the two collimators before ordering anything.** If they
say `F240FC-532`, the fix is below. If they say `F240APC-532`, ignore this section and my
apologies for the detour.

### Corrected optics (net €233.16)

| # | Part | Description | Qty | Unit | Total |
|---|---|---|---|---|---|
| O1 | [F240APC-532](https://www.thorlabs.com/thorproduct.cfm?partnumber=F240APC-532) | 532 nm FC/**APC** collimation pkg, f = 7.86 mm, NA = 0.51 — **launch** | 1 | 238,55 € | 238,55 € |
| O2 | [F810APC-543](https://www.thorlabs.com/thorproduct.cfm?partnumber=F810APC-543) | 543 nm FC/**APC** collimation pkg, f = 34.74 mm, NA = 0.26 — **delivery** | 1 | 311,47 € | 311,47 € |
| O3 | [AD15F](https://www.thorlabs.com/thorproduct.cfm?partnumber=AD15F) | SM1-threaded adapter for the Ø15 mm F810 body | 1 | 35,24 € | 35,24 € |
| | *credit:* return 2 × `F240FC-532` | | 2 | −176,05 € | −352,10 € |
| | | | | **Net** | **233,16 €** |

Note the F810 body is **Ø15 mm**, so your `KAD12NT` adapters (Ø12 mm) do not fit it.
`AD15F` is SM1-threaded and drops into a cage plate; `KAD15NT` (€78.13) is the kinematic
alternative but needs a Ø1.5" mount.

## Design decision: you do NOT need a focusing lens

The F240 collimator (as the APC version, see above) **is** the coupling lens. Run in reverse it takes a
collimated beam and focuses it onto the fibre tip; the lens-to-tip spacing is fixed at the
factory, which is exactly why it works. Adding a separate focusing lens would give you a
second, conflicting focus condition and make the alignment harder, not easier.

Two steering mirrors give exactly the degrees of freedom the problem needs:

| What must be controlled at the fibre | Set by |
|---|---|
| spot position on the core (x, y) | input beam **angle** into the coupler |
| cone axis direction (θx, θy) | input beam **position** on the coupler |

Four unknowns, four adjusters (2 mirrors × pitch/yaw). This is the standard beam-walking
launch. Your original attempt failed because a single kinematic mount gives only 2 of the 4.

The one thing mirrors **cannot** fix is beam diameter — see the gate below.

---

## Gate before ordering: measure your beam diameter (LAUNCH end only)

`F240FC-532` specs (verified): waist diameter **1.48 mm**, waist distance 6.96 mm,
NA = 0.51, f = 7.86 mm, housing Ø12 mm / M12 × 0.5. Thorlabs quote the 1.48 mm with their
reference fibre. With *this* fibre's 4.0 µm mode the matched beam is **1.33 mm**.

Mismatch costs coupling efficiency as η = [2w₁w₂/(w₁²+w₂²)]². A 2× mismatch already throws
away ~36 %, but ±30 % costs only ≤ 9 %. The gate is forgiving.

**Status (30 Sep 2026): provisionally passed.** A viewing-card estimate gives the laser
beam as "just below 1.5 mm". Taking 1.4 mm, the ideal mode match to the F240 is 99.7 %,
so no collimator swap is needed. Real coupling will be limited by M², astigmatism and
alignment (expect 50–80 %), not by diameter. Confirm it properly with the ID25 iris: the
iris diameter at which **86.5 % of the power is transmitted** is the 1/e² diameter. Only
if it comes out far from 1.3–1.5 mm, **do not build a telescope**: swap the launch
collimator instead (FC prices shown; the APC equivalents are needed for this fibre):

| Part | Waist diameter | Use if your beam is |
|---|---|---|
| `F110FC-532` | 1.14 mm | ~1.1 mm |
| `F240FC-532` (owned) | 1.48 mm | ~1.5 mm |
| `F220FC-532` | 2.1 mm | ~2.1 mm |

This gate applies **only to the launch end**. The delivery end is fixed by the objective
pupil, not by anything you measure — see below.

---

## The fibre itself — keep it

`P3-405BPM-FC-1`, PANDA PM, fibre type **PM-S405-XP**, €289.61. Verified specs:

| | |
|---|---|
| Operating wavelength | **400 – 680 nm** — 532 is inside |
| Cutoff | 380 ± 20 nm — **single mode at 532** |
| Mode field diameter | 3.3 µm @ 405, 4.6 µm @ 630 → **≈ 4.0 µm @ 532** |
| Extinction ratio | 15 dB min / 17 dB typ |
| Connector | **FC/APC** — 60 dB typical return loss |

It is single-mode at your wavelength, it is polarisation-maintaining, and the angled
connector already suppresses back-reflection into the diode. **Nothing here needs
replacing.** (This also retracts a warning I gave earlier about FC/PC Fresnel
back-reflection into the DJ532-40 — that concern does not apply; your fibre is APC.)

PM is worth keeping rather than downgrading to plain single-mode. Your `DMLP550R` sits at
45° and is polarisation-sensitive: 532 nm is right at the edge of its 380–533 nm
reflection band. A drifting output polarisation would therefore convert directly into
excitation-power drift in the ODMR baseline.

### Optional fibre swap — better, and it refunds you €37

| Part | Fibre | MFD @ 532 | Beam from F810APC-543 | Pupil fill | ER | Price |
|---|---|---|---|---|---|---|
| `P3-405BPM-FC-1` (owned) | PM-S405-XP | ≈ 4.0 µm | 5.84 mm | 78 % | 15/17 dB | 289,61 € |
| [`P3-488PM-FC-1`](https://www.thorlabs.com/thorproduct.cfm?partnumber=P3-488PM-FC-1) | PM460-HP | ≈ 3.4 µm | 6.92 mm | **92 %** | **18/20 dB** | **252,58 €** |

Beam diameter out of a collimator is D = 4λf/(π·MFD) — a *smaller* mode diverges more and
therefore fills more of the lens. The 488 cable has a tighter mode at 532, so it fills the
objective pupil better, has a better extinction ratio, is specified over 460–700 nm, and
costs €37.03 **less** than the one you have. Thorlabs also quote collimator beam diameters
using 460HP, which PM460-HP closely matches, so the published numbers become trustworthy.

This is a genuine but modest gain — 78 % fill is already a workable truncation, and the
spot-size difference is ~18 %. Do it if returns are easy; do not hold up the build for it.

**Not recommended:** `P3-630PM-FC-1` (620–850 nm) — 532 is below its operating range.

---

## Why the delivery end matters at all

Your `N40X-PF` has NA = 0.75 and f = 5 mm, so its back aperture is 2·NA·f = **7.5 mm**.
An `F240` delivers 1.33 mm there (as does today's free-space beam): an 18 % pupil fill,
which drops the *effective excitation* NA to ~0.13. The spot is then ~2.5 µm (1/e²)
instead of ~0.4 µm FWHM, with a ~20 µm Rayleigh range in the diamond. In a confocal
arrangement (30 µm pinhole) the F810 shrinks the effective detection volume ~7×, from
~31 to ~5 µm³ (notebook §4). The fibre choice then tunes the fill from 78 % to 92 %. For
**ensemble** work the under-filled F240 beam is the better choice (see the table at the top).

**On the 11 nm wavelength offset (543 design, 532 use):** the AR coating is 350–700 nm and
Thorlabs quote the damage threshold "measured at 532 nm", so transmission is a non-issue.
The doublet is chromatic with no adjustment, so at 532 you sit ~80 µm off the design focus
— about 0.2 mrad of residual divergence and a ~2 µm shift of the objective's focal plane,
which the stage refocuses away. It does not degrade the spot.

---

## Core list — build the stage (€641.44)

| # | Part | Description | Qty | Unit | Total |
|---|---|---|---|---|---|
| 1 | [BB1-E02P](https://www.thorlabs.com/thorproduct.cfm?partnumber=BB1-E02P) | Ø1" broadband dielectric mirror, 400–750 nm, **back side polished** | 2 | 106,44 € | 212,88 € |
| 2 | [KS1](https://www.thorlabs.com/thorproduct.cfm?partnumber=KS1) | Ø1" precision kinematic mount, 3 adjusters, 1/4"-80 | 2 | 96,84 € | 193,68 € |
| 3 | [TR75/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=TR75/M) | Ø12.7 mm post, L = 75 mm (mirrors + coupler) | 3 | 5,98 € | 17,94 € |
| 4 | [PH75/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=PH75/M) | Ø12.7 mm post holder, L = 75 mm (mirrors, coupler, irises) | 5 | 9,35 € | 46,75 € |
| 5 | [BA1/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=BA1/M) | Slotted base, 25 × 75 × 10 mm | 5 | 5,89 € | 29,45 € |
| 6 | [ID25/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=ID25/M) | Mounted iris, Ø25 mm max aperture, **TR75/M post included** | 2 | 68,25 € | 136,50 € |
| 7 | [LMR1/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=LMR1/M) | Ø1" lens mount w/ retaining ring — holds the KAD12NT | 1 | 16,02 € | 16,02 € |
| | | | | **Core** | **641,44 €** |

Note on #1: the "P" suffix means back side polished. It costs €27.44 more each than the
plain [BB1-E02](https://www.thorlabs.com/thorproduct.cfm?partnumber=BB1-E02) (79,00 €).
It is worth it **only** if you intend to pick off the ~0.1–1 % leakage through mirror 2
onto a reference photodiode for laser-power monitoring — back-side polishing removes the
ghost-fringe interference that makes an unpolished back face useless for that. If you are
not doing the leakage pickup, use BB1-E02 and **save €54.88**.

Note on #2: `KS1` is a *Universal* part (M4 / #8 counterbored holes). There is no `KS1/M`.

Note on #3/#4: TR75/M + PH75/M puts the KS1 optical axis at roughly 100–150 mm above the
table. **Check this against your existing beam height** — if your rail-mounted optics sit
lower, substitute TR50/M posts.

## Diagnostic — strongly recommended (€167.54)

| # | Part | Description | Qty | Unit | Total |
|---|---|---|---|---|---|
| 8 | [SI035P](https://www.thorlabs.com/thorproduct.cfm?partnumber=SI035P) | Shear plate, **1–3 mm** beam diameter | 1 | 167,54 € | 167,54 € |

A shear plate tells you in one look whether the beam is actually collimated. Guessing at
collimation by eye over a 2 m path is the single most common reason a coupling attempt
stalls at a few percent and nobody can say why. (The `SI050P` is the wrong size — it
starts at 2.5 mm.)

## Recommended — PM axis launch (€464,72)

| # | Part | Description | Qty | Unit | Total |
|---|---|---|---|---|---|
| 9 | [WPH10ME-532](https://www.thorlabs.com/thorproduct.cfm?partnumber=WPH10ME-532) | Ø1" mounted polymer zero-order λ/2 plate, 532 nm, SM1 | 1 | 347,77 € | 347,77 € |
| 10 | [RSP1/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=RSP1/M) | Continuous rotation mount, Ø1" optics, M4 tap | 1 | 95,73 € | 95,73 € |
| 11 | TR75/M + PH75/M + BA1/M | post assembly for the waveplate | 1 | 21,22 € | 21,22 € |

Your `P3-405BPM-FC-1` is **PM** fibre. Launched off its principal axis it stops being
polarisation-maintaining: the output polarisation then wanders with fibre temperature,
and because your `DMLP550R` dichroic is polarisation-sensitive, that wander converts
directly into **excitation-power drift** — which will show up in your ODMR baseline and
in the RIN measurement as spurious 1/f. The waveplate is not needed to *get* light down
the fibre; it is needed for the light to stay stable once you do. It is the only
continuous polarisation adjustment the launch has, so it belongs in the build, placed
**after M2, just before the coupler** (see the reviewed beam path at the top). It can be
added after the first successful coupling without disturbing the walk. The set-up
procedure is in the next section.

---

## Polarisation and filtering optics — the λ/2 plate, the polariser and the FBW5532-10

These three parts do not help get light into the fibre. They set the **polarisation**,
**power stability** and **spectral purity** of the light that comes out, and each has
exactly one correct place in the beam path.

| # | Part | Where | Job | Mount |
|---|---|---|---|---|
| 9 | `WPH10ME-532` λ/2 plate | launch: after M2, before iris B and the coupler | rotate the laser polarisation onto the fibre's slow axis | `RSP1/M` rotation mount (listed above) |
| 12 | `LPVISE100-A` linear polariser | delivery: first element after the output collimator | clean-up polariser, **fixed** on the slow axis | rotation mount, set once and locked |
| 13 | `NE10A`, `NE20A` absorptive ND | delivery: after the polariser | discrete power steps (×0.1, ×0.01, ×0.001) | SM1-threaded, tilted 2–5° |
| — | `FBW5532-10` (owned) | delivery: after the NDs, last element before the DMLP550R | 532 nm laser-line clean-up | fixed; Ø12.5 mm → needs an SM05-to-SM1 thread adapter in a 1″ cage |

### λ/2 plate: matching the laser polarisation to the PM fibre

**What it does.** A half-wave plate turns linear polarisation into linear polarisation,
mirrored about its fast axis. Rotating the plate by θ rotates the polarisation by **2θ**,
so 45° of plate rotation covers the full 90° range. The DPSS output is already linear. The
plate only has to *turn* it to lie along the fibre's slow axis, and it does so without any
power loss.

**Why the fibre needs this.** A PANDA PM fibre maintains polarisation only for light
launched along one of its two stress axes. Launched at an angle, the light splits between
the slow and fast axes. These travel at different speeds, so their relative phase drifts
with fibre temperature and bending, and the output polarisation wanders. After the
polarisation-sensitive DMLP550R (532 nm sits on its 533 nm band edge), that wander becomes
excitation-power noise in the ODMR baseline.

**Why after the mirrors.** The BB1-E02P dielectric mirrors at 45° shift the s and p phases
differently. Linear light that is neither pure s nor pure p comes off them slightly
elliptical, and a λ/2 plate cannot remove ellipticity. So: keep the laser polarisation s or
p on M1/M2 (it usually is when the beam stays in a horizontal plane), and rotate it with
the plate *after* the last mirror.

**Why not at the delivery end** (in front of the DMLP550R). There it would rotate the
polarisation at the dichroic's band edge, and change the NV-orientation selectivity at the
same time. Excitation power and NV response would then vary together, and you could not
separate them. If you ever want polarisation control *at the sample*, add a **second** λ/2
between the DMLP550R and the objective.

### Linear polariser: clean-up, not attenuator

**What it does.** Passes only the polarisation component along its axis. It is fixed on the
fibre's slow axis, so it removes the small fraction of light in the fast axis. With the
fibre's 15 dB minimum extinction ratio that fraction is ≤ 3 %. The light reaching the
dichroic then always has the same polarisation direction. Any residual launch imperfection
shows up as a ≤ 3 % power change, which a reference photodiode can normalise, instead of a
polarisation change, which nothing downstream can correct.

**Why not rotate it for power control** (Malus law, as the shopping list originally
proposed). Behind a PM fibre the output always contains a small, phase-drifting
fast-axis component. With the polariser at angle θ to the slow axis, the transmitted power
swings by up to ±2√(ε(1−ε))·sinθ·cosθ as that phase drifts, where ε = 10^(−ER/10). At
15 dB and θ = 45° that is **±17 %**. On the slow axis (θ = 0) the swing vanishes. Use the
NDs for power steps. For *continuous* power control, the right tool is a second λ/2 +
polariser pair *before* the fibre, so the fibre always receives the same polarisation.

**Why after the output collimator, not before it or at the launch.**
- *Between the fibre and the collimator lens:* the beam diverges at ±4.9° and there is no
  room inside a collimator package. Any plate there also moves the focus (≈ 0.7 mm for 2 mm
  of glass) and spoils the collimation.
- *At the launch:* it is redundant if the DPSS is already well polarised (check once, see
  Open items). As a rotating element it would misalign the input from the PM axis.
- *In the collimated delivery beam:* it simply transmits.

### FBW5532-10: laser-line filter after the fibre

**What it does.** A hard-coated 532 nm bandpass, 10 nm FWHM, ≥ 90 % transmission and
OD > 5 blocking outside the band. It removes everything in the excitation beam that is not
532 nm.

**Why it moves from the laser to after the fibre.** The silica fibre itself produces a weak
broadband Raman and fluorescence background above 540 nm, in the NV emission band. That
light takes a path to the detector: part is reflected by the DMLP550R towards the sample,
~17 % is back-reflected by the diamond surface, and it then passes the dichroic and the
FELH0550 like real PL. A filter before the fibre cannot remove light the fibre creates.
One filter after the fibre removes the fibre background *and* anything the laser emits
outside 532 nm, so a second one before the fibre is unnecessary.

**Why a fixed mount, and why last.** The FBW series is **wedged** (≈ 30′ per the vendor
text) to suppress etalon fringes. That tilts the transmitted beam by (n − 1)·α ≈ 4 mrad.
At the objective pupil a beam *angle* becomes a *lateral focus shift* of f·δ: **≈ 20 µm**
with the N40X-PF and ≈ 64 µm with the ACL25416U. Rotating, removing or re-seating the
filter therefore moves the focus on the sample. Put it in a fixed mount, never touch it,
and do the final pointing into the objective after it. Placed last, nothing downstream has
to be re-aligned when upstream NDs are swapped.

**Size and angle.** It is Ø12.5 mm. A 5.9 mm F810 beam loses ~0.3 % at an assumed ~Ø10 mm
clear aperture, and the 1.3 mm F240 beam loses nothing. Tilting it a few degrees to keep
its reflection out of the fibre shifts the passband by well under 1 nm, which is harmless
for a 10 nm band.

### ND filters (for completeness)

Absorptive, so they dissipate rather than reflect the blocked power (fine at ≤ 40 mW).
A 3° tilt shifts the beam by ~36 µm, which is irrelevant at a 7.5 mm pupil, and keeps
their ~4 % surface reflections out of the fibre. They are plane plates, not wedges, but
their parallelism is not specified. Check the focus position once when you swap them (a
0.1 mrad deviation moves the N40X-PF focus by 0.5 µm).

### Delivery-optics parts (€315.49; already in tier B of `NV_upgrade_shopping_list.xlsx`)

| # | Part | Description | Qty | Unit | Total |
|---|---|---|---|---|---|
| 12 | [LPVISE100-A](https://www.thorlabs.com/thorproduct.cfm?partnumber=LPVISE100-A) | Ø1″ linear polariser, 400–700 nm | 1 | 103,08 € | 103,08 € |
| 12a | [RSP1/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=RSP1/M) | rotation mount for the polariser (set once, then locked) | 1 | 95,73 € | 95,73 € |
| 13 | [NE10A](https://www.thorlabs.com/thorproduct.cfm?partnumber=NE10A) | absorptive ND, OD 1.0, SM1-mounted | 1 | 58,34 € | 58,34 € |
| 13a | [NE20A](https://www.thorlabs.com/thorproduct.cfm?partnumber=NE20A) | absorptive ND, OD 2.0, SM1-mounted | 1 | 58,34 € | 58,34 € |

Note that the λ/2 plate (#9) and the polariser each need their **own** rotation mount. The
single `RSP1/M` in the shopping list was meant for a rotating polariser. In this design it
holds the polariser, and the PM-launch tranche above supplies the second one for the plate.

---

## Already owned — do not re-order

| Part | Qty | Role in this stage |
|---|---|---|
| `F240FC-532` | 2 | FC/**PC** — wrong for the APC fibre; return both (€176,05 each) against the APC versions. If you want the ensemble delivery option, order **two** `F240APC-532` (+238,55 € over the table above) |
| `KAD12NT` | 2 | Ø1" kinematic pitch/yaw adapter for the Ø12 mm collimator body (€73,08) |
| `P3-405BPM-FC-1` | 1 | the fibre |
| `PM101A` + `S120C` | 1 | coupling-efficiency readout — essential during the walk |
| `VRC2` | 1 | beam visualisation |
| `FBW5532-10` | 1 | laser-line filter; **moves** from the free-space laser path to the delivery end, after the NDs |
| `CCHK/M`, `HW-KIT1/M`, `HW-KIT2/M` | — | hex keys and screws |

Verified compatible mounting adapters for the Ø12 mm / M12 × 0.5 `F240FC-532` body:
`AD12BA`, `AD12F`, `AD12NT`, `KAD12F`, `KAD12NT`.

---

## Totals

| Tranche | Cost | Running |
|---|---|---|
| Core launch stage (mirrors, mounts, irises, posts) | 641,44 € | 641,44 € |
| APC collimators + AD15F, net of returning 2 × F240FC-532 | 233,16 € | **874,60 €** |
| Shear plate SI035P | 167,54 € | 1 042,14 € |
| *credit:* swap fibre to P3-488PM-FC-1 | −37,03 € | 1 005,11 € |
| PM axis launch (recommended; can follow first coupling) | 464,72 € | 1 469,83 € |
| *option:* second F240APC-532 for ensemble delivery | 238,55 € | 1 708,38 € |
| Delivery optics: polariser + rotation mount + 2 ND (already in tier B) | 315,49 € | 2 023,87 € |
| *variant:* plain BB1-E02 instead of BB1-E02P | −54,88 € | |

The first two rows are what unblock work: **€874.60** gets you a correctly-connectorised,
fibre-coupled beam that actually fills the objective pupil.

For comparison, the `FiberPort` line currently in `NV_upgrade_shopping_list.xlsx` is
€681. Core + shear plate is €128 more. The honest trade: a FiberPort is the easier
*first* coupling (five axes in one factory-aligned body), but the mirror route gives you
two steering mirrors and two alignment irises that you will reuse for every subsequent
beam path on that table, and you already own the collimators. **If you swap, redirect the
FiberPort's €681 here and take the shear plate out of the difference.**

---

## Layout and procedure

See the reviewed beam path at the top for the full order, including the λ/2 plate,
polariser, NDs and line filter. The core of the launch:

```
LAUNCH END
DJ532-40 ──► M1 (KS1+BB1-E02P) ──► M2 (KS1+BB1-E02P) ──► [ID25/M A] ──► (λ/2) ──► [ID25/M B] ──► F240APC-532 ──► fibre
  ~1.4 mm                                                                                        (KAD12NT in LMR1/M)

DELIVERY END
fibre ──► F810APC-543 ──► 5.9 mm collimated ──► polariser ─► ND ─► FBW5532-10 ──► DMLP550R ──► N40X-PF ──► diamond
          (AD15F into cage plate)
```

Put M1 and M2 roughly 150–300 mm apart, and M2 roughly 150–300 mm before the coupler.
Too close together and the two mirrors become degenerate — you lose the independence
that makes walking converge.

1. **Set the axis.** With the coupler removed, place both irises at the intended beam
   height, closed down hard, one near M2 and one at the coupler position. Walk M1/M2
   until the beam passes both. This defines the axis the coupler must sit on.
2. **Verify collimation** with the SI035P. Fringes parallel to the reference line = collimated.
3. **Install the coupler** on the axis, fibre attached, power meter on the far end.
4. **Walk.** Adjust M2 for maximum power; then deliberately misadjust M1 slightly and
   re-peak with M2. If power went up, keep going that way on M1; if down, reverse. Repeat
   for both axes. This converges — random fiddling does not.
5. Expect **> 50 %** into the fibre once mode-matched. If you plateau below ~20 % and the
   shear plate says the beam is collimated, the beam diameter is wrong — revisit the gate.

Then the polarisation and filter optics, in this order (power meter at the delivery end):

6. **Output collimator + polariser.** Fit the delivery collimator, then the polariser in its
   rotation mount. Rotate the polariser for maximum transmission (P_max), then 90° away
   for minimum (P_min). The extinction ratio is 10·log(P_max/P_min).
7. **λ/2 plate (launch side).** Leave the polariser at the *minimum* (crossed) position.
   Warm a length of the fibre gently with your hand, or flex it slowly. If P_min
   fluctuates, the launch is off-axis. Rotate the λ/2 plate a few degrees at a time,
   re-find the polariser minimum, and repeat. Stop when P_min is smallest and steady;
   aim for ≥ 15 dB (the fibre's minimum spec). Inserting the plate does not disturb the
   coupling, so re-peak M2 only if the power dropped. Thorlabs align the PM slow axis to
   the connector key, which gives a first guess.
8. **Lock the polariser at maximum** (the slow axis). Record the angle.
9. **NDs and FBW5532-10.** Insert the NDs tilted 2–5°, then the FBW5532-10 in its fixed
   mount, then align into the DMLP550R and the objective *after* the FBW is in place.
   Check the power stability behind the whole chain for ~30 min while touching the fibre.
   The residual drift should be a few % or less.

## Open items

- Beam diameter of the `DJ532-40` + `LTC56A/M` assembly: viewing-card estimate "just
  below 1.5 mm" (30 Sep 2026). That provisionally passes the gate. Confirm with the iris
  (86.5 % transmission) and measure the divergence (diameter at two distances ≥ 1 m apart).
- Check the laser's polarisation ratio once (polariser in front of the power meter). If it
  is poor, a fixed polariser *before* M1 is justified as well.
- **Confirm the collimator engravings** (`F240FC-532` vs `F240APC-532`). The whole
  "corrected optics" tranche hangs on this. It is a two-minute check with a torch.
- Fibre swap to `P3-488PM-FC-1` is optional and refunds €37.03. Decide it independently
  of the connector question.
