# What detectors NV groups actually use

Literature survey, 15 Sep 2026. Sources at the bottom. Marked **[primary]** where I read
the paper's own methods text, **[secondary]** where it comes from a search summary only.

## Summary

The field splits cleanly into two regimes, with **nothing in between**:

| Work | Detector class | Typical part |
|---|---|---|
| Single NV, scanning, g⁽²⁾ | **Geiger-mode single-photon counting module** | Excelitas/Perkin-Elmer `SPCM-AQR(H)-14` |
| Ensembles | **Plain Si PIN photodiode**, often balanced | Thorlabs `DET025AFC`, `PDA36A2`, `PDB450A`, Newport Nirvana |

**No paper I found uses a linear-mode APD** of the `APD430A` type for NV work. That
absence is the most useful result of this survey: the regime the APD430A occupies is not
one anybody publishes in. Above ~17 nW a PIN is better (no excess multiplication noise);
below ~1 nW you want photon counting. The linear APD falls in the gap.

---

## Single-NV and scanning work

### Rondin et al. 2012, scanning single-NV magnetometer **[primary]**

*Nanoscale magnetic field mapping with a single spin scanning probe magnetometer*,
[arXiv:1108.4438](https://arxiv.org/abs/1108.4438) (APL **100**, 153118).

Detection chain, quoted from their supplementary methods:

- Objective: Olympus `MPLFLN100X`, **NA 0.9**, 1 mm working distance
- Dichroic + bandpass: Semrock **697/75** BP
- **"focused onto a 50-µm diameter pinhole and directed to silicon avalanche photodiodes
  (Perkin-Elmer, `SPCM-AQR-14`) operating in the single-photon counting regime"**
- Two such APDs on a 50/50 beamsplitter for the HBT g⁽²⁾ measurement, with a Picoquant
  `TimeHarp 300`
- Laser: Spectra-Physics Excelsior, 532 nm

Their photon budget — worth committing to memory:

| | |
|---|---|
| Detected rate, single NV at saturation | **> 1 × 10⁵ photons/s** |
| Detected rate at 300 µW pump | 6 × 10⁴ counts/s |
| Signal-to-background | > 10 |
| ODMR contrast | 12 % |
| ODMR linewidth | 9 MHz |
| Sensitivity achieved | ≈ 10 µT/√Hz |

This confirms the 10⁵ photons/s figure used in our APD430A calculation — from a group
using an NA 0.9 objective, i.e. close to the best case.

### Modern equivalents **[secondary]**

`SPCM-AQRH-14` and `SPCM-AQRH-14-FC` (Excelitas) recur across the recent literature —
e.g. single-NV fabrication work ([arXiv:1911.12429](https://arxiv.org/abs/1911.12429),
two units in an HBT with a Picoquant PicoHarp 300) and scanning magnetometry
([arXiv:2503.04244](https://arxiv.org/abs/2503.04244)). Quoted detection efficiency
≈ 65–68 % at 650 nm over a 180 µm active diameter, > 20 Mcounts/s.

---

## Ensemble work

### Sewani et al. 2020, teaching-lab NV setup **[primary]**

*Coherent control of NV⁻ centers in diamond in a quantum teaching lab*,
[arXiv:2004.02643](https://arxiv.org/abs/2004.02643) (Am. J. Phys. **88**, 1156).

This is the closest published analogue to our situation — a deliberately low-cost
ensemble setup with a full costed parts list. Their detection path:

- Dichroic: Thorlabs **`DMLP550`** — the same one we have
- Filters: **`FEL0600`** 600 nm longpass **+ `FES0900`** 900 nm shortpass
- Two silver mirrors (`PF10-03-P01`) on `KM100` kinematic mounts
- Aspheric `C260TMD-B` into a **50 µm multimode fibre (`M42L01`)**
- Fibre alignment: **`ST1XY-D/M`** XY translator + `SM1Z` Z translator
- Detector: **Thorlabs `DET025AFC/M`, a plain Si PIN photodetector, €306**

Two things to steal from this:

1. **The 50 µm multimode fibre core *is* the confocal pinhole.** Light is spatially
   filtered by the fibre and then guided to the detector, which removes the need to align
   a physical pinhole *and* a detector separately. We already own `ST1XY-S/M`.
2. They use a **600 nm longpass**, not 550. Reinforces moving off our `FELH0550`.

### Balanced detection for laser-noise rejection **[secondary]**

- Thorlabs **`PDB450A`** balanced detector with ~1 % of the laser picked off into the
  reference arm to cancel intensity noise
- Thorlabs **`PDA36A2`** in a fiberised vector magnetometer
- **Newport Nirvana** balanced receiver; some groups instead sample the laser and subtract
  digitally

All PIN. Ensemble NV sensing is shot-noise-limited on a large fluorescence background
with 1–3 % contrast — exactly the regime where a PIN wins and an APD's excess
multiplication noise hurts.

---

## Two incidental findings relevant to us

**Microwave drive.** Rondin et al. drive a *single* NV through a 20 µm copper wire
spanned across the sample using a **Mini-Circuits `ZHL-42`** (~+29 dBm). We have a
`ZHL-16W-43-S+` (16 W, ~+45 dB gain). This is a second independent indication — alongside
Opaluch et al. running the same amplifier at −15 dBm CW — that our +16 dBm drive level is
far into compression.

**Their lock-in is our lock-in.** Rondin's ESR tracking applies two microwave frequencies
ν± = ν̄ ± Δν/2 consecutively and uses D = S(ν₊) − S(ν₋) as the error signal, with
Δν = 5 MHz and ~100–110 ms per point. That is exactly the two-point dither scheme in
`smcv/odmr_fieldlock_fm_pc.py`. Our closed-loop approach is the published one.

---

## Sources

- [Rondin et al., arXiv:1108.4438](https://arxiv.org/abs/1108.4438) — scanning single-NV magnetometer, SPCM-AQR-14
- [Sewani et al., arXiv:2004.02643](https://arxiv.org/abs/2004.02643) — teaching-lab ensemble setup, DET025AFC/M
- [arXiv:1911.12429](https://arxiv.org/abs/1911.12429) — single-NV fabrication, SPCM-AQRH-14-FC in HBT
- [arXiv:2503.04244](https://arxiv.org/abs/2503.04244) — scanning NV magnetometry (QZabre QSM commercial instrument)
- [arXiv:2004.02279](https://arxiv.org/abs/2004.02279) — NV magnetometer for biological signals, balanced detection
- [arXiv:2002.08255](https://arxiv.org/abs/2002.08255) — sub-nT fibre-coupled diamond sensor
- [Excelitas SPCM-AQRH](https://www.excelitas.com/product/spcm-aqrh) — detector datasheet
- [Thorlabs balanced amplified photodetectors](https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=1299)
