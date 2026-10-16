# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A budget ODMR (optically detected magnetic resonance) rig for an NV-diamond sample: microwaves are swept across the NV resonance (~2870 MHz, gamma = 28.024 MHz/mT) while a photodiode watches the photoluminescence. This is lab/experiment code, not a packaged application: there is no build system, test suite, linter, or requirements file. Scripts are plain Python (numpy, matplotlib) run directly, and most of them need live instruments.

`README.md` covers the repo layout, the lock-in methods, and data backup. `TROUBLESHOOTING_GUIDE.md` is the ADF4351 + Red Pitaya hardware debugging roadmap. Read them before changing acquisition behaviour.

## Running things

- Scripts are configured by editing constants at the top of each file or `experiments/common/config.json`. By design there are no CLI arguments. The few exceptions take an optional positional arg: a data dir for `power-sweep/plot_power_sweep_*.py` and `self-oscillation/plot_selfosc_*.py`, or a mode for `experiments/calibration/laser_rin_pc.py` (`acquire` / `selftest`).
- Nothing can be tested without hardware except the plot/analysis scripts, the simulations (`theory/nv_odmr_sim.py`, `theory/proposal/autonomous_nv_sim.py`), and `python experiments/calibration/laser_rin_pc.py selftest`. To check a hardware script's changes, use `python -m py_compile <file>`; do not run acquisition scripts, because they drive real instruments.
- `python experiments/common/expconfig.py` prints the resolved config. `python experiments/calibration/check_instruments.py` is the first thing to run on the rig (it checks connectivity to the SMCV and the Red Pitaya SCPI server).

## Repository layout

Scripts are grouped by experiment under `experiments/<experiment>/`. Each folder holds both the acquisition scripts and the plotters/analysis for that data: `low-cost` (ADF4351), `dc-odmr`, `ac-odmr` (AM lock-in), `fm-odmr`, `calibration` (connectivity, noise, laser), `power-sweep`, `magnet-scan`, `sensitivity`, `self-oscillation`. Shared PC instrument code lives in `experiments/common/`. Simulations, calculators and notebooks live in `theory/`, including `theory/proposal/` (the funding-proposal work package: LaTeX report, figures, simulation) and `theory/lockin-tutorial/` (notebook plus `tutorial_data/`, written by the `acq_*.py` scripts in the experiment folders). `procurement/` holds hardware-upgrade notes and the shopping-list generator (`build_shopping.py`). New scripts go in the folder of the experiment whose data they produce or analyse.

## Architecture: three control generations

1. **`experiments/low-cost/arduino/`**: legacy. An Arduino latches ADF4351 registers and the PC does the PLL math.
2. **RedPitaya-side scripts** (most of `experiments/low-cost/`, plus `record_photodiode.py`, `pd_vs_laser_current.py` and `outputsine.py` in `calibration/` and `odmr_smcv100b.py` in `dc-odmr/`): these run **on the Red Pitaya** as root (`rp`, `spidev` modules). The Red Pitaya programs the ADF4351 over SPI and reads the photodiode on IN1. Output goes to a `data/` dir relative to the CWD. The robust path uses a fixed settle time rather than waiting on the flaky LD (lock detect) pin; see the troubleshooting guide for why. Some `low-cost/` scripts import `odmr_redpitaya.py`, so copy that folder together.
3. **SMCV PC scripts** (everything else in `experiments/`): the current main path, run **on the PC**. They drive an R&S SMCV100B generator over LAN SCPI (port 5025) and read the Red Pitaya fast ADC through the Red Pitaya's SCPI server (port 5000).

Key shared modules in `experiments/common/`:
- `config.json` + `expconfig.load_config()`: the single source of instrument IPs, sweep range, power, lock-in params, and data paths. `load_config()` also adds derived values (`fs_hz`, `n_subread`, `n_sub`). Override the file with the `BUDGETODMR_CONFIG` env var. `paths.data_dir` points at a Windows lab-PC path.
- `odmr_smcv100b_pc.py`: holds the `Scpi`, `SMCV100B`, `RedPitayaADC` classes and `frange`. Other scripts import these, so it is both a script (the stepped DC sweep) and a library. Always change the MW level through `SMCV100B.set_power_dbm()`, never with a raw SCPI write. It enforces the limit from `config.json` `mw_chain` (−16.4 dBm with the ZHL-16W-43-S+ amplifier, whose damage limit is +9 dBm at its input) and also sets that limit in the instrument.
- `redpitaya_scope.py`: `RedPitayaScope`, the correct fill-synchronised Red Pitaya acquisition sequence (pre-fill, trigger, wait for `ACQ:TRIG:FILL?`). The naive sequence returns stale or zero half-buffers, so use this for any new acquisition.
- `lockin_common.py`: the software lock-in engine (numpy demodulation, SMCV internal AM/FM modulation setup and teardown). It is used by the `odmr_lockin_{am,fm,fm_deriv}_pc.py` thin wrappers and the magnet-scan variants. AM gives a peak, FM magnitude gives |derivative| with a null at the centre, and FM phase-sensitive gives a signed zero-crossing (this needs the LF reference on IN2 with the HV jumper).

Other shared modules sit with their experiment:
- `power-sweep/powersweep_acq.py`: shared by the DC and FM power sweeps. It provides tiered averaging per power band and sweep-level resume: each sweep is written atomically to its own file, and the combined mean+std CSV is regenerated after every sweep.
- `sensitivity/odmr_sensitivity_fm_pc.py`: also a helper library (`take_spectrum`, `find_working_point`, `welch_asd`, `moving_average`, ...) imported by calibration, fm-odmr and self-oscillation scripts.
- `self-oscillation/selfosc_common.py`: helpers for the self-oscillating FM loop experiments (`odmr_selfosc_*`). The loop is `f_{k+1} = f_k - (G/D_cal)(R(f_k) - R_0)` and the sensor signal is the period-doubling onset at G_eff = 2. The theory is in `theory/proposal/autonomous_nv_sim.py` and `theory/proposal/autonomous_nv_demo.md`.
- `theory/nv_odmr_sim.py`: NV Hamiltonian/fit, imported by the magnet-scan plotters.

Modules import each other as top-level modules (`from expconfig import load_config`). Every script in `experiments/<x>/` starts with `_EXP = dirname(dirname(abspath(__file__)))` and `sys.path.insert(0, join(_EXP, "common"))`, plus extra inserts for cross-folder helpers (`join(_EXP, "sensitivity")`, or `<repo>/theory`). Keep that pattern in new scripts so they run from any CWD.

## Analysis and data conventions

- Each `plot_*.py` is paired with specific acquisition scripts in the same folder, for example `ac-odmr/plot_lockin.py` with `odmr_lockin_*` (it also analyses the fm-odmr runs) and `power-sweep/plot_power_sweep_{dc,fm}.py` (which share `powersweep_common.py`) with `odmr_power_sweep_{dc,fm}_pc.py`. When you change an acquisition script's output format, update its plotter too.
- The CSV format is `freq_MHz,signal[,std]` with `#`-prefixed `key=value` metadata header lines. `powersweep_common.read_sweep` treats the std column as optional for backward compatibility with older files.
