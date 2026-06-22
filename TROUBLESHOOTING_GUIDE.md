# ADF4351 + Red Pitaya ODMR — Troubleshooting Roadmap

A single, ordered procedure to get from "it locks every now and then" back to a
rig that (a) outputs any frequency continuously and (b) runs precise, repeatable,
averaged frequency sweeps while recording the photodiode.

Work top to bottom. Each step tells you **what to do**, **what a good result looks
like**, and **what a bad result means**. Don't skip ahead — the early steps split
the problem into "hardware" vs "software" so you stop chasing both at once.

---

## 0. The short version (read this first)

Three things almost certainly combined to break a setup that previously worked:

1. **Power quality regressed.** Last week's working config was *5 V battery →
   barrel jack, 3V3 pin unplugged*. That path runs the module's **on-board 3.3 V
   regulator** with its bulk decoupling — a clean, well-filtered supply. Powering
   the `3V3` pin directly **bypasses that regulator** and leans on the Red Pitaya's
   3.3 V rail, which is noisier and current-limited. The ADF4351 is extremely
   sensitive to supply noise; a marginal supply makes it pick the **wrong VCO band**
   and lock only intermittently. This matches your symptom exactly.

2. **A lock-detect register bug.** `test_500mhz_locktime.py` programs
   `R2 = 0x18005E42`. At 500 MHz the channel is **integer-N** (FRAC = 0), and the
   datasheet requires the **LDF bit (R2 DB8) = 1** for integer-N digital lock detect.
   It is currently 0. So even when the VCO *is* locked and outputting 500 MHz, the
   LD pin reports lock unreliably → "locks every now and then." Correct value is
   `0x18005F42`. (Your main `odmr_redpitaya.py` already sets this correctly; only the
   bench test was wrong.)

3. **The software trusts LD too much.** The sweep arms the ADC on the LD **rising
   edge** for every point. If LD is flaky (see #1, #2), the whole sweep stalls or
   times out. For a rudimentary rig, gating acquisition on a fixed settle delay is
   far more robust than edge-triggering on a marginal lock pin.

**Fastest path to working:** restore the 5 V-barrel-jack power scheme, run
`diag_spi_alive.py` (proves SPI without needing a lock), then `set_frequency.py`
(continuous output you can watch on the scope), then `odmr_sweep_robust.py` (fixed
settle, many averaged sweeps). The new scripts and the fixes are described below.

---

## 1. Mental model — what each part is doing

```
Red Pitaya  --SPI(CLK,MOSI,CS=LE)-->  ADF4351 module  --RFOUT-->  SPF5189 amp --> coil/antenna
   |  3V3? / GND                          | LD (lock detect)          (own PSU)
   |  IN1 (fast ADC) <-- photodiode amp   |
   +--- DIO0_P / ext-trig  <--------------+
```

- The Red Pitaya writes 6 registers (R5→R0) over SPI. **R0 written last** triggers
  a VCO band-select + lock.
- **LD** goes low during re-acquisition, then high when locked. It's only a *status
  output* — it does not affect whether RF comes out.
- The photodiode PL is digitized on **IN1**. Averaging many captures (and many
  sweeps) beats down the noise of this budget setup.

Key consequence: **RF output and lock-detect reporting are separate failure modes.**
You can have good RF with bad LD (the LDF bug), or bad RF with whatever LD says
(power/band-select problems). Always confirm RF on the scope independently of LD.

---

## 2. Triage — hardware or software? (~30 min)

Do these in order. Stop at the first one that fails and go to the matching section.

| # | Test | Tool / script | Good result | If bad → |
|---|------|---------------|-------------|----------|
| 2.1 | Module powered correctly | multimeter on VDD pin | 3.0–3.6 V, steady | §3 Power |
| 2.2 | SPI reaches the chip | `diag_spi_alive.py` | LD pin follows forced HIGH/LOW commands | §5 SPI/wiring |
| 2.3 | RF actually comes out | `set_frequency.py` 500 MHz + scope on RFOUT | clean ~500 MHz tone | §4 Ref / §3 Power |
| 2.4 | Lock detect asserts | same script, watch LD / D-LED | LD high, stable | §6 Lock detect |
| 2.5 | ADC sees the photodiode | `record_photodiode.py` | sensible voltage, responds to laser block | §7 Acquisition |

If 2.1–2.4 all pass, your hardware is fine and the problem is purely in the sweep
software — jump to §7.

---

## 3. Power (most likely root cause)

The ADF4351 needs **3.0–3.6 V**, with **AVDD = DVDD**, and **decoupling caps as
close to the supply pins as possible** (datasheet, Pin Function / Power sections).
Field reports of "sometimes doesn't lock" overwhelmingly trace back to **supply
noise or a weak/disturbed supply**, which causes wrong VCO band selection — worse at
higher frequencies.

**Do this:**

1. **Go back to the known-good scheme:** 5 V into the **barrel jack**, **`3V3` pin
   disconnected**, `CE` tied high (to the module's own 3V3, not the Pitaya's).
   This uses the on-board LDO + its decoupling — the configuration that worked.
2. **Never feed two supplies at once.** If the barrel jack is powered, the `3V3`
   pin must be **unplugged**. Driving the Pitaya's 3.3 V into the `3V3` pin *while*
   the barrel jack feeds the LDO makes the rail fight the regulator — exactly the
   kind of change that "broke it after iterating."
3. **Measure under load** (multimeter at the VDD pin while RF is on):
   - DC level **3.0–3.6 V**. Below ~3.0 V → brownout → no/intermittent lock.
   - Put the scope (AC coupled, 20 MHz BW limit) on the same pin. Want
     **< ~20–30 mV ripple**. Lots of ripple → add a 10 µF + 100 nF cap right at the
     pin, and prefer a **linear** supply (a clean 5 V battery is good; cheap
     switching "wall wart" 5 V supplies inject noise and are a known lock-killer).
4. **Current:** the module draws on the order of a couple hundred mA. A nearly-dead
   battery sags under load even if it reads 5 V open-circuit. **Try a fresh
   battery / a bench linear PSU set to 5 V with a current meter** and watch that the
   voltage holds when RF turns on.
5. **Power-on order:** bring up the **ADF module first, then** start the Red Pitaya
   script. (Community guidance for these modules; avoids programming during an
   unsettled supply.) With the battery-on-barrel-jack scheme this happens naturally.
6. **Keep the SPF5189 on its own PSU** (you already do). Just make sure its **ground
   is common** with the Pitaya and the ADF module (§5.4).

**Pass criterion:** VDD holds 3.0–3.6 V with low ripple while RF is on, using a
single supply. Then re-test §2.3/§2.4.

---

## 4. Reference clock

These modules have an **on-board 25 MHz TCXO** (your register math assumes
REF = 25 MHz, and 500 MHz came out right, so 25 MHz is confirmed). The classic
EngineerZone "sometimes doesn't lock" case was a **disturbed/loaded reference** that
distorted the clock and caused wrong-band selection. On an integrated-TCXO module
the equivalent failure is the TCXO's own supply sagging (i.e. it's really a power
problem, §3), or a cracked solder joint on the TCXO.

**Check:** if you have the TCXO pin/test point broken out, scope it — you should see
a clean ~25 MHz square/sine. If output frequency comes out **slightly high** (e.g.
asking 500 gets ~508) with a **VCO tune voltage pinned near a rail**, that's
wrong-band selection from a bad ref or supply — recheck §3 first.

---

## 5. SPI and wiring

5.1 **Correct SPI device.** Red Pitaya **Gen 2** boards expose the E2 SPI as
`/dev/spidev2.0` (the header is labelled SPI1 on the schematic but enumerates as
bus 2). Gen 1 / older OS images used `/dev/spidev1.0`. Your code uses
`spi.open(2, 0)` → bus 2, which is right for Gen 2. If `diag_spi_alive.py` errors
with "No such file or directory," list what exists:
```bash
ls -l /dev/spidev*
```
and set the bus number to match.

5.2 **SPI settings:** mode 0 (CPOL = 0, CPHA = 0), MSB-first, ~1 MHz. The Pitaya's
CS line is the ADF **LE** — it pulses high at the end of each 32-bit transfer, which
is the latch edge. One register per transfer. (All already correct in your code.)

5.3 **Logic levels:** ADF4351 inputs accept up to VDD; the Pitaya's 3.3 V CMOS is
fine. LD/MUXOUT swing to ~DVDD (3.3 V), fine for a Pitaya DIO input.

5.4 **Grounds — check this carefully.** Every module that "worked when I unplugged a
wire" is usually a grounding story. You need **one common ground** between Red
Pitaya, ADF module, photodiode amp, and the SPF5189 PSU. When the ADF was floating
on a battery, its only ground reference to the Pitaya was through the SPI cable
ground — fine if that wire is solid, flaky if it isn't. **Confirm continuity
(multimeter beep) from Pitaya GND to ADF GND to amp GND.** A missing/intermittent
ground makes SPI levels and LD readings unreliable.

5.5 **Lead length / probing.** Long, unshielded SPI jumpers + 1 MHz is usually OK,
but if SPI is marginal, shorten leads and keep CLK away from RFOUT.

**Pass criterion:** `diag_spi_alive.py` toggles the LD pin HIGH then LOW on command.
That proves the Pitaya → ADF SPI path end-to-end **without needing the PLL to lock.**

---

## 6. Lock detect — why it's flaky, and how to stop depending on it

6.1 **Fix the integer-N LDF bug.** For any FRAC = 0 (integer-N) channel — which
includes **500 MHz**, and every 25 MHz point in your 2700–3000 sweep — set
**R2 DB8 (LDF) = 1**. The bench test currently uses `0x18005E42` (LDF = 0); it should
be `0x18005F42`. This alone will make 500 MHz lock detect far more reliable. (Fix
already applied to `test_500mhz_locktime.py` — see §8.)

6.2 **Confirm lock independently of LD.** The honest test of "did it lock" is the
**VCO tune voltage** (VTUNE / charge-pump output). On a good lock it sits somewhere
in the **mid-range (~0.5–2.5 V)**, not pinned at 0 V or at the top rail. If you can
reach the VTUNE/CP test point, scope it: rail-pinned = wrong band / not locked, even
if LD twitches high. Combined with "clean tone at the right frequency on RFOUT,"
that's ground truth.

6.3 **Try analog lock detect** if digital LD stays unreliable: set MUXOUT to analog
LD (R2 MUXOUT = 0b101) — it shows a train of pulses that go to steady-high on lock,
sometimes easier to judge on a scope.

6.4 **Stop gating acquisition on the LD edge.** For a budget averaging experiment,
the robust approach is: program the frequency, **wait a fixed settle time** (a few ms
— far longer than the sub-ms lock time), then acquire. Optionally *read* LD as a
quality flag and log it, but don't *block* on it. `odmr_sweep_robust.py` does exactly
this, so a single flaky point can't stall the whole run.

---

## 7. Acquisition / the photodiode path

- `record_photodiode.py` with the laser on, then blocked, should show the mean
  voltage move — confirms IN1, the LV/HV jumper, and the amp.
- Decimation `RP_DEC_64` ≈ 8 ms per 16384-sample block. Averaging N blocks per point
  and repeating M sweeps reduces noise ∝ 1/√(N·M). For a rudimentary rig, prefer
  **many fast sweeps** (good against slow laser drift) over few slow ones — drift
  between the start and end of a long single sweep shows up as a sloped baseline,
  whereas averaging many quick sweeps averages the drift out.

---

## 8. The working software set

All scripts are self-contained, run **on the Red Pitaya as root**, and write under
`data/`. Edit the CONFIG block at the top of each; there are no CLI args (matches
your existing convention).

| Script | Purpose |
|--------|---------|
| `redpitaya/diag_spi_alive.py` | **Proves the SPI path** by forcing the LD pin HIGH then LOW via R5 (DB23:22). No PLL/lock needed. First thing to run when "nothing works." |
| `redpitaya/set_frequency.py` | **Continuously output any frequency.** Correct integer-N/fractional-N register math (incl. the LDF fix), holds the tone, polls LD as a *status* flag, prints the VTUNE check reminder. Use for §2.3/§2.4 and any time you just want a tone. |
| `redpitaya/odmr_sweep_robust.py` | **Precise, repeatable, averaged sweeps** recording the photodiode. Fixed settle time (LD optional/logged, never blocking), N captures/point, M repeated sweeps accumulated into a running average + per-run CSVs. This is the main experiment. |
| `redpitaya/test_500mhz_locktime.py` | Patched: `R2` now `0x18005F42` (LDF = 1) so the 500 MHz lock-time test is meaningful. |

Typical bring-up sequence after a power fix:
```bash
sudo python3 redpitaya/diag_spi_alive.py        # SPI path OK?  (LD follows commands)
sudo python3 redpitaya/set_frequency.py         # 500 MHz tone on the scope? LD high?
sudo python3 redpitaya/odmr_sweep_robust.py     # run the averaged sweep
python3 analysis/average_sweeps.py              # (on the PC) plot the averaged result
```

---

## 9. One-page decision tree

```
Nothing works
  └─ diag_spi_alive.py: does LD follow forced HIGH/LOW?
       NO  → SPI/wiring/ground (§5) or power dead (§3). Fix, retry.
       YES → SPI is fine. set_frequency.py @500 MHz, scope RFOUT:
              Clean tone?
                NO  → Power quality / wrong VCO band (§3, §4). Check VDD level+ripple,
                      single supply, fresh battery, VTUNE not rail-pinned.
                YES → Is LD high & steady?
                        NO  → LDF bug fixed? (§6.1) VTUNE mid-range? If tone is right,
                              trust RF over LD; run sweeps with fixed settle (§6.4).
                        YES → Hardware good. Run odmr_sweep_robust.py (§7,§8).
```

---

## 10. Bench checklist (tick before each session)

- [ ] Single supply only (5 V → barrel jack; `3V3` pin **unplugged**).
- [ ] VDD at the pin = 3.0–3.6 V **under RF load**, ripple < ~30 mV.
- [ ] Common ground: Pitaya ↔ ADF ↔ photodiode amp ↔ SPF5189 PSU (multimeter beep).
- [ ] `/dev/spidev2.0` present (Gen 2); `diag_spi_alive.py` passes.
- [ ] 500 MHz tone confirmed on scope, independent of LD.
- [ ] LDF = 1 on integer-N points (use the provided scripts).
- [ ] Photodiode responds to blocking the laser.

---

## Sources

- [ADF4351 Data Sheet (Analog Devices, Rev. A)](https://www.analog.com/media/en/technical-documentation/data-sheets/adf4351.pdf) — power supply 3.0–3.6 V, AVDD=DVDD, decoupling near pins; initialization sequence R5→R0; double-buffering and the R0-last rule; integer-N requires LDF (R2 DB8)=1; LD pin / MUXOUT options; RF divider and band-select.
- [ADF4351 sometimes doesn't lock — Analog Devices EngineerZone](https://ez.analog.com/rf/f/q-a/75651/adf4351-sometimes-doesn-t-lock) — intermittent lock from a disturbed/loaded reference → wrong VCO band, worse at higher frequencies.
- [ADF4351 module guidance — use a linear (not switching) supply, decouple near the pins, power the module before the controller](https://www.alibaba.com/product-insights/adf4351-module.html)
- [Red Pitaya SPI bus enumeration — E2 SPI is /dev/spidev2.0 on Gen 2 (labelled SPI1 on the schematic)](https://github.com/pavel-demin/red-pitaya-notes/issues/321)
- [Red Pitaya SPI documentation](https://redpitaya.readthedocs.io/en/latest/appsFeatures/remoteControl/command_list/commands-spi.html)
