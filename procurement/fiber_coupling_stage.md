# Free-space → fibre coupling stage

Updated 7 Oct 2026. Supersedes the 15 Sep / 30 Sep versions, which assumed FC/PC
collimators, post + post-holder mounting and a free-standing delivery end. Prices are in
the Thorlabs cart, not here.

## What is already in the lab

| Item | Qty | Role |
|---|---|---|
| `F240APC-532` | 2 | one **launch** coupler, one **delivery** collimator (ensemble work). FC/**APC**, matching the fibre. The connector problem in earlier versions of this file is resolved. |
| `KAD12NT` | 2 | Ø1″ pitch/yaw adapters for the Ø12 mm collimator bodies (one per end) |
| `P3-405BPM-FC-1` | 1 | PM fibre, PANDA, FC/APC, single mode at 532 nm, MFD ≈ 4.0 µm, ER 15 dB min / 17 dB typ |
| `FBW5532-10` | 1 | 532/10 nm wedged laser-line filter, already on the dichroic cube face |
| 30 mm cage system | — | DMLP550R cube, N40X-PF (excitation + collection), FELH0550, ACL25416U-B detector lens |
| Pillar post kit, M4/M6 hardware | — | launch-side mounting |
| `PM101A` + `S120C`, `VRC2` | 1 | coupling-efficiency readout, beam visualisation |

## Beam path

```
LAUNCH (pillar posts; alignment-critical)
DJ532-40 ─► M1 ─► M2 ─► [iris A] ─► λ/2 (RSP1/M) ─► [iris B] ─► F240APC-532 in KAD12NT/LMR1/M ─► fibre
 ~1.4 mm   KS1 + BB1-E02P, 150–300 mm apart

DELIVERY (30 mm cage extension of the dichroic cube; coaxial by construction)
fibre ─► F240APC-532 ─► LPVISE100-A ─► NE10A-A ─► NE20A-A ─► (lens L, optional) ─► FBW5532-10 ─► DMLP550R cube ─► N40X-PF ─► diamond
         KAD12NT in      CRM1T/M,        KC1T/M,    KC1T/M,     CP33T/M              cube face
         CP33T/M         locked on       tilted     tilted
                         slow axis       2–3°       2–3°

DETECTION (unchanged): diamond ─► N40X-PF ─► DMLP550R ─► FELH0550 ─► ACL25416U-B ─► PDA10A2
```

## Why each element sits where it does

**λ/2 plate (launch, after M2, before the coupler).** The DJ532-40 output is already
linearly polarised; the plate rotates it onto the fibre's slow axis (plate angle θ rotates
the polarisation by 2θ). PM fibre maintains polarisation only when launched on a stress
axis. Off-axis, the output polarisation drifts with temperature and handling, and since
532 nm sits on the DMLP550R's 533 nm reflection edge, that drift becomes excitation-power
drift. The plate goes *after* the mirrors because 45° dielectric mirrors add a little
ellipticity to light that is not pure s or p, and a λ/2 plate cannot remove it. Rotating
the laser module instead also works, but it moves the beam and is hard to set finely.

**Linear polariser (delivery, first after the collimator, fixed on the slow axis).** It is
not for power control.
1. *Clean-up:* the fibre's ≤ 3 % fast-axis leakage becomes a ≤ 3 % power change (which a
   reference detector can normalise) instead of a polarisation change at the dichroic and
   on the NV axes.
2. *Alignment tool:* crossed, it shows whether the λ/2 launch is on-axis (procedure below).
3. *Defined polarisation* at the sample, for later NV-orientation-selective work.

Do not rotate it to attenuate. At 45° to the slow axis, the fibre's thermal birefringence
drift becomes ±17 % power wander at 15 dB extinction ratio (`notebooks/Optical_Setup.ipynb` §2).

**ND filters (after the polariser), AR-coated, in tilted kinematic cage mounts.** In a cage
every plate is square to the beam. A surface normal to a collimated beam reflects straight
back into the collimator, perfectly mode-matched into the fibre and on to the laser. An
uncoated face (~4 %) can return ~2–3 % of the power to the DJ532-40 and adds weak etalon
fringes. Two measures:
- `NE10A-A` / `NE20A-A` (AR 350–700 nm, < 0.5 % per surface) instead of the uncoated versions;
- `KC1T/M` kinematic cage mounts (±5° tip/tilt), set 2–3° off normal.

A 3° tilt shifts the beam by ~36 µm, which is irrelevant. Combinations give OD 1, 2 or 3.

**FBW5532-10 (stays on the cube face, last before the dichroic).** The silica fibre makes a
weak Raman/fluorescence background above 540 nm. Part of it reaches the detector via the
DMLP550R and the diamond-surface reflection (~17 %), and it passes the FELH0550. Only a
filter *after* the fibre removes it, and it also removes anything else that isn't 532 nm.
It is wedged (~4 mrad deviation): disturbing it moves the focus sideways (≈ 64 µm with the
ACL, ≈ 20 µm with the N40X-PF), so it stays fixed where it is.

**Delivery collimator.** Use the second `F240APC-532` (1.33 mm beam) for ensemble work. For a
pupil-filling confocal beam later, add `F810APC-543` (5.9 mm, 78 % fill of the N40X-PF pupil)
in an `AD15F`. The F810 body is Ø15 mm, so it does not fit a KAD12NT.

## Launch-end notes

- **Beam diameter.** With this fibre's 4.0 µm mode, the F240's matched beam is 1.33 mm
  (Thorlabs' 1.48 mm spec uses a different reference fibre). A viewing-card estimate puts
  the laser at ~1.4 mm, an ideal mode match of 99.7 %. Mismatch is forgiving (±30 % costs
  ≤ 9 %). Confirm with an iris: the diameter that transmits 86.5 % is the 1/e² diameter.
- **No focusing lens.** The F240 *is* the coupling lens, with a factory-set fibre distance.
  Two mirrors give the four degrees of freedom needed (spot x, y on the core via input angle;
  cone direction via input position).
- **Pillar posts.** Every optic's centre height = pillar length + that mount's axis height,
  and KS1, RSP1/M, LMR1/M and the iris differ. Check each mount's axis height and choose
  pillar lengths or spacers so they share one beam height. The KS1 takes an M4 cap screw
  through a counterbore, so the pillar top needs an M4 thread (or an M6→M4 adapter).
- **BB1-E02P vs BB1-E02.** The polished back (P) is only worth it if you will pick off the
  leakage through M2 for a power-monitor photodiode. Otherwise use BB1-E02.

## Procedure

1. **Set the launch axis.** Coupler removed, both irises closed down hard (A just after M2,
   B at the coupler position). Walk M1/M2 until the beam passes both.
2. **Check collimation** with the SI035 shearing interferometer (fringes parallel to the reference line). Its
   path difference is ~1.9 mm, well inside the coherence length of the DPSS laser.
3. **Install the coupler**, fibre attached, power meter on the far end.
4. **Walk:** peak with M2, deliberately offset M1 slightly, re-peak with M2. Keep going in the
   direction that raised the power. Expect > 50 % once mode-matched. Below ~20 % with a
   collimated beam means the beam diameter or the collimator is wrong.
5. **Build the delivery cage** on the cube: CP33T/M with KAD12NT + F240APC-532, then
   CRM1T/M with the polariser. NDs out for now.
6. **Extinction ratio.** Rotate the polariser to maximum (P_max) and to minimum (P_min);
   ER = 10·log(P_max/P_min).
7. **λ/2 alignment (launch).** Polariser crossed (minimum). Warm or flex the fibre gently: if
   P_min fluctuates, the launch is off-axis. Rotate the λ/2 a few degrees, re-find the
   minimum, repeat until P_min is smallest and steady (aim ≥ 15 dB). The slow axis is
   aligned to the connector key, which gives a first guess. Re-peak M2 only if the power fell.
8. **Lock the polariser at maximum** (the slow axis) and record the angle.
9. **NDs:** screw into the KC1T/M mounts, tilt 2–3°. Check that the laser noise does not
   change with them in (`smcv/laser_rin_pc.py`). Then check the power stability behind the
   chain for ~30 min while touching the fibre: a few % or less.

## Optional: larger excitation spot (lens L)

Current geometry: the N40X-PF delivers the laser **and** collects the PL; an ACL25416U-B
focuses the PL onto the PDA10A2. Ray-trace result (`notebooks/optics_model.py`): the
objective delivers **2.03 %** of all emitted PL to the detector, i.e. everything inside its
NA 0.75. An ACL25416U-B in its place delivers 1.67 %, because its Ø25 mm beam is clipped by
the 1″ downstream optics. After the objective's own (unmeasured, ~85–90 %) transmission the
two are about equal. Swapping the objective for a condenser buys working distance (7.3 mm vs
0.66 mm), not PL. Lower-NA objectives collect less (NA 0.5: 0.88 %).

With the 1.33 mm F240 beam the objective makes a ~2.4 µm spot, which reaches NV saturation
at ~20 mW. To light a larger area with the sample still at focus, add a lens L in the
delivery cage that focuses the beam at the back focal plane of the focusing optic. L and
that optic form a telescope, and the diamond sees a **collimated** beam of diameter

    D_spot = D_in · f_optic / f_L      (D_in = 1.33 mm; f_optic = 5 mm objective, 16 mm ACL)

| L | f_L | D_spot, N40X-PF | D_spot, ACL |
|---|---|---|---|
| AC254-050-A | 50 mm | 0.13 mm | 0.43 mm |
| AC254-100-A | 100 mm | 0.07 mm | 0.21 mm |

The optical path from L to the back focal plane (inside the objective, near its shoulder;
≈ 16 mm in front of the ACL's curved face) must equal f_L, which sets where L sits on the
rods. Slide it until the beam after the objective/ACL stays the same size over a few cm.
The FBW in the converging beam only shifts the focus by ~0.6 mm. Collimated excitation is
uniform through the 0.5 mm thickness.

**Choose the spot with three limits in mind:**
- **Collection:** with the objective + ACL detector lens (magnification 3.2), the PDA10A2
  sees a ~0.3 mm diameter field, so keep the spot ≲ 0.2 mm.
- **Magnet gradient:** a 10 mm N42 magnet at 3 cm gives ~0.33 mT/mm, i.e. ~4.6 MHz of line
  broadening across 0.5 mm (~0.75 MHz at 5 cm). Helmholtz coils remove this limit.
- **Optical pumping rate:** at 30–40 mW the intensity at a 0.3–0.5 mm spot gives
  repolarisation rates of only ~10³ /s (order of magnitude). The ODMR response then cannot
  follow the 5 kHz FM lock-in modulation, so f_mod must drop. Measure lock-in amplitude
  vs f_mod.

## Open items

- Confirm the laser beam diameter (iris) and divergence (two distances ≥ 1 m apart).
- Check the laser polarisation ratio once (polariser in front of the power meter).
- Measure the distance from the cube face to the ACL's curved face before choosing f_L.
- Optional fibre swap to `P3-488PM-FC-1` (MFD ≈ 3.4 µm at 532, ER 18/20 dB): fills the
  N40X-PF pupil better with an F810 (92 % vs 78 %). Only relevant for confocal work.

## Shopping list (Thorlabs)

**Launch (pillar posts)**
- KS1 ×2
- BB1-E02P ×2 (or BB1-E02 ×2 without the leakage pick-off)
- ID20/M ×2
- WPH10ME-532 ×1
- RSP1/M ×1
- LMR1/M ×1
- SI035 ×1 (complete shearing interferometer: base, shear plate, diffuser screen; recommended. SI035P is only the replacement plate)

**Delivery (30 mm cage)**
- CP33T/M ×1 (holds the KAD12NT + F240APC-532)
- CRM1T/M ×1
- LPVISE100-A ×1
- KC1T/M ×2
- NE10A-A ×1
- NE20A-A ×1
- ER6 ×4 (cage rods; ER8 ×4 if adding a long-focal-length lens L)

**Optional: larger spot + more PL**
- AC254-050-A ×1 (≈ 0.13 mm spot with the objective) + CP33T/M ×1
- BB1-E02 ×1 (dielectric back-reflector under the diamond; estimated up to ~2× PL, not modelled)

**Later, for confocal work:** F810APC-543 ×1, AD15F ×1
