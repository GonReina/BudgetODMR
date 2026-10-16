# Laser / detector calibration protocol

Run order for the `cal*` scripts in this folder. Each script prompts you step by step.
The laser current (LDC200C) and the TEC temperature are typed in by hand. Outputs go
to `<paths.data_dir>/calibration/` (`config.json`). Every plotter also takes that
folder as an optional argument, so you can re-analyse a copy elsewhere.

**Power meter wiring.** The PM101A is read through its **analog output on Red Pitaya
IN2**, not over USB. The IN2 jumper and `config.json` `redpitaya.in2_gain` must match
(LV, ±1 V, is ~20× finer than HV). Set the meter to 532 nm and the analog output to
**responsivity mode**: V = P × "AO responsivity". Choose it so the highest power gives
~0.7–0.9 V on LV (15 V/W for 50 mW), put it in `redpitaya.pm_ao_responsivity_v_per_w`,
and keep it for the whole calibration. The volts → mW factor (nominally 1000 /
responsivity mW/V) is measured against a Thorlabs Optical Power Monitor reading
(step 0), checked against the nominal value, and saved in `pm101a_analog_cal.csv`.
Later scripts offer to reuse it as long as the responsivity, wavelength and IN2 jumper
stay the same. If any of them change, measure it again.

Before starting, edit `I_MAX_MA` and the `CURRENTS_MA` lists at the top of each script
to match your laser. The scripts refuse any current above `I_MAX_MA`.

| # | Script | Instrument | What it gives |
|---|---|---|---|
| 0 | `cal0_check_power_meter.py` | PM101A → IN2 | Live IN2 level (check it follows the beam and does not clip), zero, and the **mW/V factor** measured against Optical Power Monitor. |
| 1a | `cal1_loss_budget.py` | PM101A + S120C | Power at the laser output, before and after the objective (add `after_fibre` once a fibre is fitted). The 532 nm bandpass stays in the beam, so the readings exclude IR. |
| 1b | `cal1_power_vs_current.py` | PM101A + S120C | Up/down sweep with settling, 30–60 s logs and TEC temperature. Run with `POSITION = "before_objective"`; optionally again at `"laser_output"` (path transmission vs current). |
| 1c | `plot_cal1_power.py` | – | **`power_calibration.csv`** (current → power at the sample), hysteresis, path transmission vs current. |
| 2a | `cal2_noise_floors.py` | Red Pitaya IN1 | Terminated-input and blocked-beam floors. |
| 2b | `cal2_rin_vs_current.py` | PDA10A2 (+ PM101A monitor on IN2) | RIN vs current at a constant DC level (ND filters). Finds the quiet current. |
| 2c | `cal2_noise_vs_photocurrent.py` | PDA10A2 (+ PM101A monitor on IN2) | Stage 0c: at the quiet current, vary only the attenuation. |
| 2d | `plot_cal2_noise.py` | – | RIN at the candidate f_mod values, log-log slopes (0 electronics, ½ shot, 1 laser). |
| 3a | `cal3_pl_vs_power.py`, `MODE = "nv"` | APD + SMCV (+ PM101A readings typed in) | PL and a quick CW ODMR (contrast, FWHM, centre) at every current. |
| 3b | `cal3_pl_vs_power.py`, `MODE = "background"` | APD (+ PM101A readings typed in) | Same currents with the focus off the diamond. |
| 3c | `cal3_pl_vs_power.py`, `MODE = "nd_check"` | APD | APD linearity with a known ND at the top power. |
| 3d | `plot_cal3_pl_saturation.py` | – | Fit PL = A·P/(P+P_sat) + b·P, sensitivity Δν/(C·√PL) vs P, heating from the centre shift (−74 kHz/K). |
| 3e | `cal3_mw_laser_map.py` → `plot_cal3_mw_laser_map.py` | APD + SMCV | ODMR contrast map vs laser power × MW power (adaptive averaging, shuffled MW order, start/end reference). Gives MW saturation power and C_max per laser level, optical (W0) vs MW broadening, and the best (laser, MW) operating point. Fine 0.1 MHz spectra at low laser/MW power. The laser axis is converted with `power_calibration.csv` at plot time. |
| 3f | `cal3_rabi_transient.py` → `plot_cal3_rabi.py` | fast detector + SMCV pulse modulation (gate on IN2) | CW-laser transient nutation: Rabi frequency vs MW power (f_R = κ√P → `rabi_calibration.csv`, used as an extra MW axis on the 3e map) and the optical pumping time vs laser power. |

Notes:
- **S120C safety:** never put the sensor at the focus. Measure 2–3 mm past it. The
  sensor reads up to 50 mW.
- **Consistent settings:** use the same IN1 jumper (LV/HV) and decimation for 2a–2c. Keep
  the APD gain, pinhole and filters fixed for 3a–3c.
- **Power monitor (2b, 2c, 3a, 3b; `MONITOR_POWER`):** put the S120C on a pick-off of
  the excitation beam, before the ND filters, and leave it there. It records whether the
  laser power drifts or fails to repeat step 1. In 2b and 2c it is read on IN2; it is
  zeroed when you block the beam, and without a saved mW/V factor only its volts are
  recorded. In step 3 the meter is not wired to the Red Pitaya, so you type its reading
  in at every current (before the PL reading and after the ODMR sweep; blank skips).
  Set `MONITOR_POWER = False` if no pick-off is fitted.
- **Step 3 x-axis:** step 3 needs `power_calibration.csv` from step 1.
- **After the run:** set `lockin.f_mod_hz` in `config.json` from the quiet band in 2d. Pick
  the operating laser power from the sensitivity minimum in 3d, not from the PL maximum.
