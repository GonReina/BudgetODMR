# Coils for the zero-field (microwave-free) NV experiment

The target is the experiment of Dhungel, ..., Budker, Gawlik, Wojciechowski,
*Near-zero-field microwave-free magnetometry with NV centers in nanodiamonds*
(arXiv:2401.08246, Opt. Express 32, 21936 (2024)). Numbers below come from
`helmholtz_designer.py` (edit `DESIGNS`, run it, read `out/`).

## 1. What field the experiment needs

| quantity (from the paper) | value |
|---|---|
| scanned field | ±40 G = **±4 mT**, along one axis |
| zero-field dip width (FWHM) | bulk ~2–5 G (0.2–0.5 mT); nanodiamonds 20–45 G (2–4.5 mT) |
| transverse bias | 0–14.7 G (≤ 1.5 mT) |
| their coils | X 16.94 G/A, Y 7.34 G/A, 0–3 A from a HAMEG HMP4040 |
| their scan | 110-point current ramp, polarity reversed by hand, 512 averages on a scope |
| laser | 0.2–10 mW on a 4 µm² spot (the dip depends strongly on intensity) |

**0.2 T is about 50× more than this experiment needs.** The zero-field feature
lives within ±5 mT. Fields of 0.1–0.2 T matter for the *other* microwave-free
method, which uses the ground-state level anti-crossing at 102.4 mT (ESLAC
51 mT). That is a different experiment (see §4).

The homogeneity requirement is mild. The field across the probed volume must
vary by much less than the dip width, i.e. ≪ 50 µT for bulk. Every design below
gives < 0.01 µT over a 2 mm cube. Two things matter more: **Earth's field
(~50 µT)** and stray lab fields. Both shift and broaden the zero-field dip, so
all three axes need coils that can null them.

## 2. Designs (still air, J ≈ 3.5 A/mm², 3D-printed PETG former)

| coil pair | field | bore Ø | wire | turns/coil | spacing | current | V | P (pair) | wire (pair) | winding T | L | f_3dB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Z: scan + modulation | ±6 mT | 60 mm | 1.0 mm | 9×9 = 81 | 35 mm | 2.9 A | 2.6 V | 7.5 W | 36 m | 58 °C | 1.5 mH | 97 Hz |
| X: transverse / Earth null | ±2 mT | 100 mm | 0.8 mm | 8×8 = 64 | 54 mm | 1.9 A | 3.0 V | 5.6 W | 43 m | 47 °C | 1.8 mH | 142 Hz |
| Y: transverse / Earth null | ±2 mT | 140 mm | 0.8 mm | 10×10 = 100 | 74 mm | 1.7 A | 5.9 V | 9.7 W | 94 m | 46 °C | 6.4 mH | 88 Hz |
| (optional) separate modulation | 0.5 mT | 40 mm | 0.5 mm | 4×4 = 16 | 21 mm | 0.7 A | 0.3 V | 0.2 W | 4 m | 29 °C | 0.05 mH | 1.3 kHz |

- **Buy about 50 m of 1.0 mm, 170 m of 0.8 mm and 5 m of 0.5 mm enamelled copper
  wire** (grade 2). That is the totals plus ~20 % for leads and mistakes. For Z
  alone, one 56 m reel of 1.0 mm (RS 779-0735, Block CUL 500/1,00) is enough.
- **"Spacing" is centre-to-centre of the two windings.** It is solved for
  d²B/dz² = 0, which is the true Helmholtz condition for a thick winding. It is
  not exactly the radius.
- **The three pairs have different bores so they nest around each other**, like
  the cube in tarciszera's simulator. X and Y were 90 / 120 mm; they are now
  100 / 140 mm because the printed formers and flanges collided at the smaller
  sizes (checked in `cad/`, §6). The Z bore clears the N40X-PF (Ø30 mm).
- **Use a non-metallic former** (PETG/ABS; PLA softens at ~55 °C). An aluminium
  former is a shorted turn: it adds eddy currents that delay and attenuate the
  modulation. If you use one, cut a slot along it.
- **The field-to-current ratios are calculated, not measured.** Calibrate each
  axis on the rig with ODMR. With a known current, the line splitting is
  2 · 28.0 MHz/mT · B∥. Along [100], all four NV orientations have
  cos θ = 1/√3, so they give a single pair of lines.

`out/coil_sweep.png` shows how power, temperature, wire length and voltage
scale with bore diameter and wire size. The power depends almost only on bore
and current density, not on the wire. A thinner wire means more turns, more
volts and fewer amps for the same power. Pick the wire that matches the driver.

## 3. Controlling the coils from Python

### Recommended: one bipolar current driver per axis

```
 RP OUT1 (DC + sine) ─┬─[summing amp]──► power op-amp ──► coil ──┬── R_s ── GND
 MOD IN (BNC, sig gen │                  (OPA548/549)    ▲        │
  or MFLI Sig Out) ───┘                                   └── feedback from R_s
                                                 I_coil = V_in / R_s   (e.g. R_s = 0.33 Ω → 3 A/V)
```

- **Current mode, not voltage mode.** The coil resistance rises ~15 % as it
  warms (0.78 → 0.89 Ω for Z). A voltage-driven coil would drift by that much
  in field. A current driver keeps B ∝ V_in.
- **It is bipolar, so the scan goes smoothly through zero.** The paper used a
  unipolar supply and swapped polarity by hand, then stitched the two halves
  together. A bipolar driver needs no relay and has no stitch at zero field.
- **One input can carry DC and modulation together.** For Z at 1 kHz,
  |Z| = |R + jωL| ≈ 9 Ω, i.e. 4.5 V per mT of modulation amplitude. A 0.25 mT
  amplitude (half a bulk dip width) needs ~1.1 V on top of the 2.6 V DC, so
  **±8–12 V rails are enough**. The modulation can go on the scan coil itself;
  the separate modulation pair is only needed with a bench supply (below).
- **Build notes:**
  - The OPA548 (3 A, ±30 V) or OPA549 (8 A) is an easy part to start with.
  - With an inductive load, add a Zobel network (≈ 10 Ω + 100 nF) across the
    coil and follow the datasheet compensation.
  - Heatsink for (V_rail − V_coil) · I ≈ 15–30 W per axis.
  - Commercial equivalent: a Kepco BOP (it has an analog programming input),
    if the budget allows.

Driving it from the **Red Pitaya over the SCPI server** (port 5000, already used
by the rig). The fast outputs are ±1 V, 14 bit (122 µV per step). With
R_s = 0.33 Ω (3 A/V) and 2.08 mT/A, that is ≈ 0.8 µT per step on Z, which is
plenty against a 200–500 µT wide dip:

```python
scpi.tx_txt("SOUR1:FUNC SINE")         # or DC for a pure bias
scpi.tx_txt("SOUR1:FREQ:FIX 1000")     # modulation frequency
scpi.tx_txt("SOUR1:VOLT 0.04")         # modulation amplitude (V) -> I = V / R_s
scpi.tx_txt("SOUR1:VOLT:OFFS 0.30")    # DC part = the field set-point of the scan
scpi.tx_txt("OUTPUT1:STATE ON")
# step OFFS through the scan; |amplitude| + |offset| must stay <= 1 V
```

**Output allocation:**
- **Z (scan + modulation):** OUT1.
- **X and Y (slow, DC only):**
  - OUT2 for one of them;
  - the slow analog outputs `ANALOG:PIN AOUT0..3, 0–1.8 V` for the other(s),
    with a 0.9 V offset subtracted in the driver input to make them bipolar.
- **Lock-in reference:** feed the voltage across R_s (it is the real coil
  current, including the L/R phase lag) into IN2. That is the same "reference
  on IN2" scheme the FM phase-sensitive lock-in in `lockin_common.py` uses.
  IN2 currently reads the PM101A, so plan which one gets it.

**With the MFLI:**
- Its Signal Output (sine + offset) drives MOD IN, and it demodulates the
  photodiode on Sig In 1, so the reference is internal and phase-locked.
- Its auxiliary outputs (±10 V, set from `zhinst`) can be the DC set-points for
  X/Y/Z. Then the whole scan and lock-in is one Python program on the PC.
- This is the cleanest option and reuses the `Mfli` class in
  `experiments/fm-odmr/odmr_fm_mfli_phase_pc.py`.
- Check the aux-output count and range in the MFLI manual before wiring.

### Cheapest: programmable bench supply (the paper's way)

- **The supply:** a 3-channel SCPI supply such as the Rigol DP832 (LAN/USB,
  2×30 V/3 A + 5 V/3 A) in constant-current mode, one channel per axis,
  controlled with `pyvisa`.
- **Polarity:** a DPDT relay per axis, switched by a Red Pitaya digital pin.
- **Modulation:** use the separate small modulation pair (0.05 mH, 1.3 kHz
  bandwidth), driven by a signal generator or the MFLI through any DC-coupled
  amplifier.
- **Drawbacks:**
  - no smooth zero crossing;
  - the CC loop of a bench supply is slow and noisy;
  - the Z scan coil and the modulation coil are coaxial, so they act as a
    transformer and some modulation couples into the supply.
- It is fine for a first look at the dip, but not for magnetometry.

**Avoid PWM H-bridge drivers.** The 20 kHz ripple is a field ripple right in the
lock-in band.

## 4. If you really want 0.2 T (the 102.4 mT level anti-crossing)

An air-core Helmholtz pair is the wrong tool here (design `bias_200mT`,
30 mm bore):
- 2 × 3721 turns of 1.5 mm wire, 3 km of wire, 48 kg of copper;
- **~800 W at 155 V even if kept at 20 °C**; in still air it runs away
  thermally, so it needs water cooling;
- L ≈ 2 H, so it cannot be modulated.

Power scales as B² × size, so the field is the problem, not the design.
Practical routes:
- **Iron-yoke electromagnet with a small gap.** For a 10 mm gap,
  NI ≈ B·g/μ₀ ≈ 1600 ampere-turns in total: e.g. 2 × 400 turns at 2 A, a few
  tens of W. Homogeneity comes from the pole-face size, and the sample sits in
  the gap.
- **NdFeB magnets on a translation stage** (what you already have, further
  away for homogeneity), plus the Z coil above for fine scanning and
  modulation around the anti-crossing.

## 5. Order of work

1. Wind Z first and build one current driver. Calibrate mT/A with ODMR.
2. Scan Z across ±6 mT with the existing PD/Red Pitaya readout and look for
   the dip at zero. Then null Earth's field with X/Y: maximise the dip depth
   and minimise its width.
3. Add modulation and lock-in (Red Pitaya reference on IN2, or the MFLI) for
   the derivative signal, which is the actual magnetometer.

## 6. 3D-printed formers (`cad/`)

Three OpenSCAD versions, each a superset of the one before, so nothing gets reprinted:

| version | file | new parts to print |
|---|---|---|
| v1: Z scan only (the quick test) | `v1_single_axis.scad` | `z_former`, `base`, `sample_arm` |
| v2: + modulation pair | `v2_single_axis_mod.scad` | `mod_insert` (slides into the Z bore) |
| v3: three axes | `v3_three_axis.scad` | `base` (bigger), 2× `x_hoop`, 2× `y_hoop`, 2× `x_spacer`, 4× `y_spacer` |

**Geometry**
- The Z pair is coaxial with the optical axis, so B is normal to the [100] face of
  the DNVB14 and all four NV orientations see the same B∥ = B/√3.
- The objective enters the bore from the front and the sample arm from the back.
  The arm bolts to the translation stage, so focusing moves only the diamond and
  the coil stays put.
- The diamond is glued (a dab of CA or crystalbond) onto a 2.4 mm square pedestal
  that stands 2 mm proud of the arm's end face. The 3 mm diamond overhangs it, so
  at 0.66 mm WD the objective can only meet the diamond, never plastic.
- Free bore: 55 mm in v1, 36 mm through the mod insert (the N40X-PF is Ø30 mm).

**Rig parameters** (top of `coil_lib.scad`, check them before printing)
- `BEAM_H = 75`: optical axis above the table.
- `STAGE_TOP = 40`: top of the sample stage above the table. This one is a guess;
  measure your stage.
- `ARM_REACH = 120`: riser behind the sample, chosen to clear the v3 base.

**Table mounting**
- M6 slots on the 25 mm grid run across the beam, so any lateral position is
  reachable.
- There are two slot pairs, 50 and 75 mm apart, so along the beam the coil centre
  always lands within 6.25 mm of the focus. That is inside its 0.1 % region.
- Bolt the base down first; the Z former then screws onto the pedestal from inside
  the bore.

**Regenerating**
- The winding sizes come from `cad/coil_dims.scad`, which `helmholtz_designer.py`
  writes, so a design change flows into the CAD.
- `python cad/export_stl.py` writes `cad/stl/<version>/*.stl` (print orientation)
  and `cad/preview/*.png`.
- `python cad/export_stl.py check` intersects every pair of parts in each assembly,
  including a ghost N40X-PF with its 30 mm cage plate. It reports any overlap
  above 0.5 mm³; touching faces are allowed.

**Printing**
- PETG, 4 walls, ≥ 40 % infill.
- The formers, hoops and mod insert print axis-vertical. The underside of each
  channel's upper flange needs supports ("everywhere", tree supports clean out
  easily).
- The sample arm needs supports under the beam. The bases and spacers need none.
- The Y hoop is 162 mm across, so it needs a ≥ 180 mm bed.

**Hardware** (all non-magnetic near the sample: nylon or brass)

| version | items |
|---|---|
| v1 | 2× M3×16 countersunk + 2 M3 nuts (former to pedestal); 2× M6×16 for the base and 4× M6×16 for the arm foot (steel is fine that far out) |
| v2 | 2× M3 nylon thumbscrews + 2 M3 nuts (collar lock); 4 m of 0.5 mm wire |
| v3 | M4 brass/nylon threaded rod: 4 × 130 mm (Y) and 4 × 90 mm (X); 16 M4 nuts |

**Winding**
- Start leads exit through the Ø1.8 mm holes at the channel floor and finish leads
  through the rim notches, all on top (or at the back for the Y hoops).
- Wire each pair in series aiding (the end of coil 1 to the start of coil 2, same
  winding sense; see §3 / the schematic) and check the polarity with a compass
  before you mount the sample.
