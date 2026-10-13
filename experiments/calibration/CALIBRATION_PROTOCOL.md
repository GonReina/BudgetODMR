# Laser / detector calibration protocol

Run order for the `cal*` scripts in this folder. Each script prompts you step by step.
The laser current (LDC200C) and the TEC temperature are typed in by hand. Outputs go
to `<paths.data_dir>/calibration/` (`config.json`). Every plotter also takes that
folder as an optional argument, so you can re-analyse a copy elsewhere.

Before starting, edit `I_MAX_MA` and the `CURRENTS_MA` lists at the top of each script
to match your laser. The scripts refuse any current above `I_MAX_MA`.

| # | Script | Instrument | What it gives |
|---|---|---|---|
| 0 | `cal0_check_power_meter.py` | PM101A | Whether Python can read the meter over USB. If not, the cal1 scripts ask you to type readings in. |
| 1a | `cal1_loss_budget.py` | PM101A + S120C | Power at the laser output, before and after the objective (add `after_fibre` once a fibre is fitted); 532 nm bandpass check for IR. |
| 1b | `cal1_power_vs_current.py` | PM101A + S120C | Up/down sweep with settling, 30–60 s logs and TEC temperature. Run with `POSITION = "before_objective"`; optionally again at `"laser_output"` (path transmission vs current). |
| 1c | `plot_cal1_power.py` | – | **`power_calibration.csv`** (current → power at the sample), hysteresis, path transmission vs current. |
| 2a | `cal2_noise_floors.py` | Red Pitaya IN1 | Terminated-input and blocked-beam floors. |
| 2b | `cal2_rin_vs_current.py` | PDA10A2 | RIN vs current at a constant DC level (ND filters). Finds the quiet current. |
| 2c | `cal2_noise_vs_photocurrent.py` | PDA10A2 | Stage 0c: at the quiet current, vary only the attenuation. |
| 2d | `plot_cal2_noise.py` | – | RIN at the candidate f_mod values, log-log slopes (0 electronics, ½ shot, 1 laser). |
| 3a | `cal3_pl_vs_power.py`, `MODE = "nv"` | APD + SMCV | PL and a quick CW ODMR (contrast, FWHM, centre) at every current. |
| 3b | `cal3_pl_vs_power.py`, `MODE = "background"` | APD | Same currents with the focus off the diamond. |
| 3c | `cal3_pl_vs_power.py`, `MODE = "nd_check"` | APD | APD linearity with a known ND at the top power. |
| 3d | `plot_cal3_pl_saturation.py` | – | Fit PL = A·P/(P+P_sat) + b·P, sensitivity Δν/(C·√PL) vs P, heating from the centre shift (−74 kHz/K). |

Notes:
- **S120C safety:** never put the sensor at the focus. Measure 2–3 mm past it. The
  sensor reads up to 50 mW.
- **Consistent settings:** use the same IN1 jumper (LV/HV) and decimation for 2a–2c. Keep
  the APD gain, pinhole and filters fixed for 3a–3c.
- **Step 3 x-axis:** step 3 needs `power_calibration.csv` from step 1.
- **After the run:** set `lockin.f_mod_hz` in `config.json` from the quiet band in 2d. Pick
  the operating laser power from the sensitivity minimum in 3d, not from the PL maximum.
