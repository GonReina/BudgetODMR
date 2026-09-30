# Can the APD430A do single-NV ODMR?

Technical note, 17 Sep 2026. All detector figures from the Thorlabs datasheet; the photon
budget from Rondin *et al.* 2012.

---

## Conclusion

**No — by a factor of about 10⁶ in measurement time.**

A single NV centre delivers **≈ 28 fW** to the detector. The APD430A's noise floor is
**0.14 pW/√Hz**, i.e. **5000× larger than the entire signal** in a 1 Hz bandwidth.
Recovering the ODMR dip at SNR = 10 would take **≈ 24 hours per frequency point**, against
**69 ms** for a photon-counting module. The setup would drift far more than the signal
during a single point.

The deeper issue is that the APD430A is the **wrong model within its own family**: its
DC–400 MHz bandwidth is bought at the cost of a NEP **40× worse** than the APD440A's, for
an experiment that runs at 5 kHz.

---

## 1. Inputs

### 1.1 Photon budget — from the literature

Rondin *et al.*, *Nanoscale magnetic field mapping with a single spin scanning probe
magnetometer*, [arXiv:1108.4438](https://arxiv.org/abs/1108.4438) (Appl. Phys. Lett. **100**,
153118). Measured on a single NV in a nanodiamond, NA 0.9 objective, 532 nm excitation:

| Quantity | Value | Source |
|---|---|---|
| Detected photon rate at saturation | **> 1 × 10⁵ s⁻¹** | quoted directly |
| Detected rate at 300 µW pump | 6 × 10⁴ s⁻¹ | Fig. 1(d) caption |
| ODMR contrast, C | **12 %** | Fig. 1(d) caption |
| ODMR linewidth | 9 MHz | Fig. 1(d) caption |
| Signal-to-background | > 10 | quoted directly |

We take **R = 10⁵ photons/s** and **C = 12 %**. Both are optimistic for us: that group used
NA 0.9 against our NA 0.75, and a nanodiamond on an AFM tip rather than bulk.

### 1.2 Detector — from the Thorlabs datasheet

[APD430A/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=APD430A/M), €1,417.69:

| Parameter | Value |
|---|---|
| Wavelength range | 400 – 1000 nm |
| Bandwidth (3 dB) | DC – 400 MHz |
| Active area diameter | 0.5 mm |
| Typical max responsivity | 53 A/W @ M = 100 (800 nm) |
| Transimpedance gain | 5 kV/A (50 Ω) · 10 kV/A (Hi-Z) |
| Max conversion gain | 5.3 × 10⁵ V/W |
| M factor adjustment range | **10 – 100** (cannot be reduced to 1) |
| Saturation power (CW) | 8.0 µW @ M = 100 · 80 µW @ M = 10 |
| **Minimum NEP** | **0.14 pW/√Hz** |

---

## 2. Optical power from one NV centre

NV emission runs from the 637 nm zero-phonon line through a broad phonon sideband peaking
near 680–700 nm. Take a mean detected wavelength λ = 700 nm:

$$E_\gamma = \frac{hc}{\lambda} = \frac{1.986\times10^{-25}\,\mathrm{J\,m}}{700\times10^{-9}\,\mathrm{m}} = 2.84\times10^{-19}\ \mathrm{J}$$

$$P = R\,E_\gamma = 10^{5}\,\mathrm{s^{-1}} \times 2.84\times10^{-19}\,\mathrm{J} = \boxed{2.84\times10^{-14}\ \mathrm{W} = 28.4\ \mathrm{fW}}$$

The quantity we actually have to detect is the **change** in that power on magnetic
resonance:

$$\Delta P = C\,P = 0.12 \times 28.4\ \mathrm{fW} = 3.40\ \mathrm{fW}$$

---

## 3. How long would it take?

Signal-to-noise for an optical power change ΔP against a detector of noise-equivalent
power NEP, in noise bandwidth B:

$$\mathrm{SNR} = \frac{\Delta P}{\mathrm{NEP}\sqrt{B}}$$

For simple averaging over time τ, the equivalent noise bandwidth is B ≈ 1/(2τ), so

$$\tau = \frac{1}{2B} = \frac{1}{2}\left(\frac{\mathrm{SNR}\cdot\mathrm{NEP}}{\Delta P}\right)^{2}$$

With NEP = 140 fW/√Hz and ΔP = 3.40 fW:

| Target | Integration time **per frequency point** |
|---|---|
| SNR = 1 | 848 s ≈ **14 minutes** |
| SNR = 10 | 84 800 s ≈ **23.6 hours** |

A 100-point ODMR sweep at SNR = 10 would take **270 days**. Even at the optimistic 30 %
contrast sometimes quoted for single NVs, it is 3.8 hours per point — 16 days per sweep.

### 3.1 A sanity check in volts

Conversion gain 5.3 × 10⁵ V/W at maximum M gives, for the whole single-NV signal:

$$V = 5.3\times10^{5}\ \mathrm{V/W} \times 2.84\times10^{-14}\ \mathrm{W} = 15\ \mathrm{nV}$$

and the ODMR dip is 12 % of that, **1.8 nV**. Our Red Pitaya is 14-bit over ±1 V, so one
LSB is 122 µV: **the entire single-NV signal is ~1/8000 of one ADC count.** The detector's
own noise density over the same gain is 74 nV/√Hz — five times the full signal.

---

## 4. Comparison: photon counting

A Geiger-mode module detects each photon as a discrete pulse well above the electronics
noise, so the measurement is limited only by counting statistics. In time τ it registers
N = Rτ counts with shot noise √N, and the dip is CN:

$$\mathrm{SNR} = \frac{C N}{\sqrt{N}} = C\sqrt{R\tau} \quad\Longrightarrow\quad \tau = \frac{1}{R}\left(\frac{\mathrm{SNR}}{C}\right)^{2}$$

$$\tau = \frac{1}{10^{5}}\left(\frac{10}{0.12}\right)^{2} = \boxed{69\ \mathrm{ms}}$$

**Ratio: 84 800 s / 0.069 s ≈ 1.2 × 10⁶.**

### 4.1 The same result from a different direction

The shot-noise-limited NEP for P watts of light on a detector of quantum efficiency η:

$$\mathrm{NEP_{shot}} = \sqrt{\frac{2h\nu P}{\eta}} = \sqrt{\frac{2(2.84\times10^{-19})(2.84\times10^{-14})}{0.7}} = 0.16\ \mathrm{fW/\sqrt{Hz}}$$

The APD430A's 140 fW/√Hz is **880× above the shot-noise floor** at this light level. Since
integration time scales as the square of the noise, that predicts a penalty of 880² ≈
7.7 × 10⁵ — agreeing with the direct calculation to within a factor of 1.6. The two routes
are independent, which is why the ~10⁶ figure is trustworthy.

---

## 5. Where the APD430A *does* belong

An APD only earns its keep while its own noise exceeds the shot noise of the light landing
on it. Setting NEP = NEP_shot:

$$P_\mathrm{cross} = \frac{\mathrm{NEP}^{2}\eta}{2h\nu} = \frac{(1.4\times10^{-13})^{2}(0.7)}{2(2.84\times10^{-19})} = 2.4\times10^{-8}\ \mathrm{W} = 24\ \mathrm{nW}$$

Above 24 nW you are shot-noise limited, the low NEP buys nothing, and the avalanche
process **adds** excess multiplication noise (F ≈ 2–5 for silicon), making the APD worse
than a plain PIN by √F ≈ 1.4–2.2.

At the low end, requiring SNR = 10 in 1 s per point at 12 % contrast needs P ≈ 8.2 pW.

| | Optical power | Equivalent NV count |
|---|---|---|
| Practical floor | 8.2 pW | ≈ 300 NVs |
| Shot-noise crossover | 24 nW | ≈ 850 000 NVs |
| Hard saturation (M = 100) | 8.0 µW | ≈ 2.8 × 10⁸ NVs |

**A single NV sits 290× below the practical floor.** The APD430A's genuine window is
roughly 300 to 10⁶ centres — real, but not where single-NV physics lives.

---

## 6. The sharper point: wrong model, right family

| | **APD440A** | APD410A | **APD430A** (ours) |
|---|---|---|---|
| Bandwidth | DC–100 kHz | DC–10 MHz | DC–400 MHz |
| Active area Ø | 1.0 mm | 1.0 mm | 0.5 mm |
| Max conversion gain | 2.65 × 10⁹ V/W | 26.5 × 10⁶ V/W | 5.3 × 10⁵ V/W |
| **Minimum NEP** | **3.5 fW/√Hz** | 0.04 pW/√Hz | 0.14 pW/√Hz |
| Saturation @ M = 100 | 1.54 nW | 0.15 µW | 8.0 µW |
| Price | €1,264.73 | €1,417.69 | €1,417.69 |

The APD430A's NEP is **40× worse than the APD440A's**, and that is the price of 400 MHz of
bandwidth we will never use — our lock-in runs at 5 kHz, four orders of magnitude below.

Repeating the calculation of §3 with the APD440A's 3.5 fW/√Hz gives **53 s per point** at
SNR = 10 — 1600× better, and marginally usable. So the honest statement is not "analogue
APDs cannot see single NVs"; it is that **this** APD cannot, by a wide margin, and it costs
€153 more than the sibling that nearly can.

---

## 7. Consequence for the purchase

1. **The APD430A cannot support single-NV work.** Not marginal — off by ~10⁶ in time.
2. **It is also not the right detector for our ensemble work.** At µW-level bulk PL we are
   far above the 24 nW crossover, where a large-area PIN (PDA100A2, 75.4 mm² versus
   0.5 mm) wins outright and the APD's excess noise actively hurts.
3. **Its real window — 300 to 10⁶ NVs — is one we cannot reach yet**, because it needs a
   working confocal and a dark room, which is what the €1,417.69 would otherwise buy.
4. It is a catalogue stock item, so returning it is reversible.

**Recommendation: return it.** If low-light confocal work later proves necessary, the
APD440A is the correct model and is cheaper. Genuine single-NV work needs a photon counter
(Thorlabs SPDMA, Ø500 µm, €4,781.34; or Excelitas SPCM-AQRH, the literature standard).

---

## 8. Assumptions and caveats

- **λ = 700 nm** as the mean detected NV emission wavelength. Using 650 or 750 nm changes P
  by ±7 %, and the conclusion by nothing.
- **R = 10⁵ s⁻¹** is Rondin's saturated rate at NA 0.9. Our NA 0.75 — and, until the pupil
  fill is fixed, an effective excitation NA nearer 0.14 — would give substantially less.
  This makes the estimate optimistic.
- **C = 12 %** is Rondin's measured value. Single-NV CW contrast is reported between ~10 %
  and ~30 %; the 10⁶ *ratio* in §4 is independent of C, since contrast cancels.
- **B = 1/(2τ)** assumes simple boxcar averaging. A lock-in with a well-chosen filter can
  do somewhat better, but not by four orders of magnitude.
- **η = 0.7** for silicon at 700 nm, used only in §4.1 and §5.
- Thorlabs quote "minimum NEP", presumably at peak responsivity. Using a worse
  wavelength-specific value would only strengthen the conclusion.
- Excess multiplication noise (F) is neglected throughout, which again favours the APD.

## Sources

- [Rondin et al., arXiv:1108.4438](https://arxiv.org/abs/1108.4438) — single-NV photon rate, contrast, linewidth
- [Thorlabs APD430A/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=APD430A/M) — price and summary specs
- [Thorlabs Free-Space Si Avalanche Photodetectors](https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=5255) — full comparison table, NEP, saturation, conversion gain
- [Thorlabs Single Photon Detectors](https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=5255) — SPDMA / SPDMHx alternatives
