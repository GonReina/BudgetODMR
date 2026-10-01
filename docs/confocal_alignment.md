# Confocal alignment procedure

Step-by-step alignment of the confocal configuration (N40X-PF + AC254-150 + pinhole) and how
to find the diamond surface. Numbers marked *(notebook §n)* come from the optical model in
`notebooks/Optical_Setup.ipynb`.

Written 1 Oct 2026.

## Geometry recap

```
fibre/laser ─► (polariser, ND, FBW5532-10) ─► DMLP550R ─► N40X-PF (f = 5 mm, NA 0.75, WD 0.66 mm) ─► diamond on NanoMax
                                                 │
                                                 └─► FELH0550 ─► AC254-150 ─► pinhole at 150 mm ─► detector (≤ 20 mm behind)
```

| Quantity | Value |
|---|---|
| Magnification at the pinhole | M = 150/5 = 30 |
| Airy unit at the pinhole (700 nm) | ≈ 34 µm *(notebook §4)* |
| Recommended pinhole | 30 µm (≈ 0.9 AU); 50 µm for more signal |
| Lateral pinhole tolerance (−10 % signal, 30 µm pinhole) | ≈ ±6 µm at the pinhole |
| Axial pinhole tolerance (−10 %) | ≈ ±0.3 mm |
| Cone after the pinhole | NA 0.025, so a Ø1 mm detector catches it all within ~20 mm |
| Diamond surface reflectance at 532 nm | ≈ 17 % |
| Stage travel per µm of depth in diamond | ≈ 0.4 µm *(notebook §4)* |
| Sharpest focus with this objective | ≈ 200 µm deep (the 0.17 mm cover-glass correction is cancelled by the diamond) *(notebook §4)* |

## Before starting

- **Laser power:** reduce to ~0.1–0.5 mW at the sample with the ND filters, and wear goggles.
- **Photon counter:** **disconnected or capped** until step 8. All alignment is done with
  the **PDA10A2**. A reflected laser beam or room light can damage a photon counter.
- **Sample:** start with **DNVB14**, whose bright PL makes everything easy to find. The
  electronic-grade plate comes last.
- **Tools:** VRC2 card, irises, PKIT1K pinholes, ST1XY-S/M translator (+ Z adjustment),
  NanoMax, PM101A + S120C power meter.

## Step 1: Put the excitation beam on the objective axis

1. Remove the objective. Thread an iris or cage alignment plate into the objective's mount
   position, and place a second target further along the same axis (e.g. at the sample position).
2. Steer the excitation beam (last mirror before the dichroic, or the dichroic mount) until it
   passes through the centre of both targets.
3. **Back-reflection check:** put a flat mirror at the sample position. The reflected beam
   must retrace its path onto the iris centre. That confirms normal incidence.
4. Check that the beam is centred on the 7.5 mm pupil. An iris closed to ~7.5 mm should clip a
   pupil-filling (F810, ~5.9 mm) beam symmetrically.

## Step 2: Fit the objective and check the output

1. Thread in the N40X-PF. On a card a few cm below the focus, the diverging beam should be
   a **round, uniformly lit disc**. A lopsided or clipped disc means the beam is off-centre or
   tilted at the pupil: go back to step 1.
2. Put the DNVB14 on the NanoMax and **approach from far away**. The working distance is only
   0.66 mm, so start with ~2 mm clearance and come down slowly, watching from the side.
   A crash damages the objective front lens.

## Step 3: Centre the collection path (no pinhole yet)

1. With the focus somewhere inside the DNVB14, the PL leaves the objective as a collimated
   ~7 mm beam. Centre the FELH0550 and the AC254-150 on it. On the VRC2 card it should be a round
   red disc.
2. Put the **PDA10A2 at the AC254 focal plane** (150 mm) and maximise its signal laterally.
   The useful window is only about ±0.25 mm *(notebook §1)*.

## Step 4: Find the diamond surface

### Method A: PL edge (DNVB14, filters in)

Step the NanoMax Z in ~2 µm steps from "focus above the diamond" to "focus inside" and record the
PDA signal. The PL rises from near zero to a plateau as the focus enters the crystal.
**The surface is at the half-rise point.** Without a pinhole the edge is broad (tens of µm);
it sharpens after step 5, which is the confocality check in step 6.

### Method B: confocal reflection (any sample; required for electronic grade)

1. **Remove the FELH0550**, which blocks 532 nm at OD > 5, and put OD 2–3 in front of the
   PDA10A2. Only the PDA, never the photon counter.
2. Use a large pinhole (100 µm) at the AC254 focus, or just the PDA's 1 mm active area.
3. Scan Z. The reflected 532 nm signal shows a **sharp peak when the top surface is in focus**.
   Near the surface the objective's cover-glass correction makes the peak weaker and broader
   than ideal, but it is easy to find.
4. Continue deeper: a **second, broader peak from the bottom surface** appears roughly
   0.2 mm of stage travel later for a 0.5 mm plate. Dividing the travel between the peaks by the
   plate thickness calibrates the stage-to-depth ratio on your own sample.
5. **Refit the FELH0550 before any fluorescence measurement.**

## Step 5: Insert the pinhole (100 → 50 → 30 µm)

1. Mount the **100 µm** pinhole on the ST1XY-S/M at the AC254 focus, with the PDA10A2 directly
   behind it (within ~20 mm).
2. Focus 20–50 µm below the DNVB14 surface, where the PL is steady.
3. Peak the signal in **X and Y**, then in **Z** (along the axis, ±mm). Iterate.
4. Swap to **50 µm** and re-peak XY (and Z), then to **30 µm** and re-peak. Each step loses some
   signal; expect ~0.78 in-focus transmission at 30 µm *(notebook §4)*.
5. From now on, **do not touch the excitation path.** Swapping the collimator, or disturbing
   the wedged FBW5532-10 (≈ 20 µm focus shift), moves the spot, and the pinhole must be
   re-peaked.

## Step 6: Verify confocality

- **Z scan through the surface** (Method A again). With the 30 µm pinhole and a pupil-filling
  beam the edge should sharpen to **~5 µm** (4.9 µm FWHM thin-layer sectioning predicted,
  ~10 µm with the current under-filled 1.4 mm beam). If it stays at tens of µm, the pinhole is
  off in X/Y or Z.
- **XY scan across a sharp feature:** a surface scratch, dust, or the diamond edge. Expect
  ~0.4 µm lateral resolution with the F810 beam, ~0.8 µm with the current beam.

## Step 7: Go to the working depth

Raise the sample towards the objective by **≈ 0.4 × the target depth** from where the
surface was in focus: ≈ 85 µm of travel for ≈ 210 µm depth, where the focus is sharpest
(Strehl ≈ 0.99, notebook §4). Check the clearance to the objective; about 0.5 mm remains.

## Step 8: Switch to single-NV mode (photon counter)

1. Swap to the **electronic-grade** plate and find its surface with **Method B** (FELH out,
   PDA + ND).
2. Refit the FELH0550 (or a 650 nm longpass if available), and put OD 2–3 in front of the
   detector position.
3. Connect the photon counter with the room lights off and the enclosure closed. Check the
   count rate first, then remove ND step by step while staying well below saturation.
4. Check: even without NVs in focus, the diamond's first-order **Raman line at 573 nm**
   passes the FELH0550 and gives a weak, uniform bulk signal. The surface edge (Method A) is
   visible in it with the photon counter.
5. Go to ~200 µm depth and raster-scan XY. Isolated ~0.4 µm bright spots on a dark background
   are single-NV candidates (confirm with g⁽²⁾). A uniform glow means the NV density is too
   high to resolve single centres.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Asymmetric disc below the objective (step 2) | beam off-centre or tilted at the pupil |
| Surface edge stays broad after inserting the pinhole | pinhole off in Z, or not centred in X/Y |
| No reflection peak in Method B | FELH0550 still in, or the reflected beam misses the pinhole (tilted excitation) |
| Signal drifts over minutes | thermal drift: let the laser and stage warm up; add a periodic XYZ refocus |
| Focus jumps after touching the filters | wedged FBW5532-10 moved; re-peak the pinhole |
| Photon-counter rate pinned at maximum | dense sample or stray light; add ND, check the enclosure |
