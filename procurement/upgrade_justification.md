# NV magnetometer upgrade — justification for €5,000

**Requested:** €2,995.75 (core, 3 k tranche) + €1,999.49 (extension, 2 k tranche) = **€4,995.24, ex-VAT.**
Itemised list with vendor links: `NV_upgrade_shopping_list.xlsx`.

## 1. The problem this money solves

The optical and microwave hardware is in place, but the **transduction chain is a factor of ~50 weaker than it should be**, and this single deficiency currently limits every measurement we make:

| Measured on our setup | Value | Consequence |
|---|---|---|
| CW ODMR contrast (PL_on/PL_off) | 0.8 % | weak signal at source |
| FM lock-in lobe amplitude at the working point | ≈ 0.10 mV | ~1 LSB of the Red Pitaya ADC |
| Lock-in slope / field transduction | 0.103 mV/MHz → 2.9 mV/mT | 15 µV of ordinary electronic noise reads as ≈ 5 µT |
| Per-reading SNR | ≈ 5 | thousands of nT of apparent "field noise" |

The headline result is that our reported field noise is **not** magnetic: it is an ordinary noise floor divided by a very small slope. Sensitivity, the WP3 threshold measurements and any attempt at single-NV work all inherit this. Two further blockers are practical: **fibre coupling has never been achieved** (we have the fibre and collimators but no stage that can translate the fibre tip), and **the room is too bright** — light still enters through cable holes and small apertures despite the fabric panels.

## 2. What the core tranche buys (€2,996)

**Fluorescence collection and detection — €678.** A large-area switchable-gain detector (PDA100A2, 75.4 mm² vs the 0.8 mm² we use now) fed by a NA = 0.79 aspheric condenser placed close to the diamond, behind a 650 nm longpass. For *ensemble* work the 40× objective is a poor collector; a condenser plus large detector captures far more of the 4π emission, and eight selectable gains let us trade bandwidth we do not need for transimpedance we do. This is the most direct attack on the 0.1 mV problem, for well under a quarter of the tranche.

**Stray-light control — €622.** Rigid black hardboard panels, blackout fabric and — the part that matters for our specific failure — mouldable matte black foil to seal cable holes and apertures, plus a beam trap for the transmitted green. This is the precondition for any low-light measurement and is cheap.

**Fibre coupling — €681.** A FiberPort provides the integrated five-axis launch (x, y, focus and two tilts) that our kinematic-mount attempt structurally cannot: without translation of the fibre tip, coupling is a matter of luck. *Action before ordering: measure the collimated beam diameter and choose the matching focal length — the variants all cost the same.*

**Microwave power characterisation — €681.** A 20 W 30 dB attenuator and an RF power detector let us measure the amplifier output safely. This matters more than it sounds: with +16 dBm drive into a 16 W, ~45 dB-gain amplifier we are almost certainly deep in compression, which means the MW power we *set* is not the power at the antenna — a systematic error that would silently corrupt the linewidth-vs-power and G_c-vs-power experiments. A TTL RF switch, flexible cables and connectors for a resonant antenna complete the chain; stronger B₁ is the cheapest available route to better contrast.

**Temperature, cleaning, consumables — €334.** Logger, heaters and thermistors to separate thermal from magnetic drift; standard optics-cleaning supplies.

## 3. What the extension tranche buys (€1,999) — new measurements

- **Balanced detection (€472).** A second identical detector on a beam pick-off, differenced in the MFLI, cancels common-mode laser intensity noise — the term our noise-budget script is most likely to identify as dominant in a DPSS-pumped setup.
- **Laser power control (€315).** A rotating polariser plus ND filters give continuous, repeatable optical power steps without changing diode current (which changes both noise and mode). Required for clean power-dependence series.
- **Sample and fibre infrastructure (€662).** A precision rotation platform for reproducible diamond/antenna orientation (vector magnetometry, NV-orientation studies) and a spare PM fibre better matched to 532 nm.
- **Field calibration coil (€80).** A coil of known geometry turns our nT/√Hz figures from *relative* into *traceable*, and supplies a known AC field for the WP3 statistics test.
- **Environment and contingency (€433).** Dust control plus a modest allowance for adapters, fasteners and carriage.

These enable four experiments we cannot presently do: **Rabi frequency from CW power broadening** (resolve the ¹⁴N triplet at low power, fit linewidth vs calibrated MW power to extract Ω); **diamond thermometry** (measure dD/dT ≈ −74 kHz/K and quantify laser-induced heating); **calibrated AC magnetometry**; and **orientation-resolved measurements**.

## 4. Notes for the reviewer

- **Prices are ex-VAT**, as displayed by Thorlabs and DigiKey ES on 10 Sep 2026; the spreadsheet carries a VAT-inclusive memo line (€6,044). Please confirm which basis the awards are quoted on — at 21 % this is the difference between fitting and not fitting.
- **Deliberately excluded** (detailed in the workbook's second sheet): a single-photon counting module (≈ €6–8 k, the only real route to single-NV work — proposed separately); a second lower-density diamond; and a turnkey Helmholtz pair.
- **Software licences are not requested.** Our acquisition and analysis stack is Python-based, already written and tested. The only licences worth considering are Zurich Instruments MFLI options — MF-MD (simultaneous 1f/2f demodulation) and MF-PID (moving the WP3 feedback loop into hardware) — both quote-only; we will obtain a quote before proposing them.
- **Sequencing.** Run the existing noise-budget diagnostic first, then install collection and enclosure, then fibre and MW calibration. The diagnostic decides whether the balanced-detection pair is needed, so Tier B can be adjusted before committing.
