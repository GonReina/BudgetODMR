# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A budget ODMR (optically detected magnetic resonance) rig for an NV-diamond sample: microwaves are swept across the NV resonance (~2870 MHz, gamma = 28.024 MHz/mT) while a photodiode watches the photoluminescence. This is lab/experiment code, not a packaged application: there is no build system, test suite, linter, or requirements file. Scripts are plain Python (numpy, matplotlib) run directly, and most of them need live instruments.

`README.md` covers the repo layout, the lock-in methods, and data backup. `TROUBLESHOOTING_GUIDE.md` is the ADF4351 + Red Pitaya hardware debugging roadmap. Read them before changing acquisition behaviour.

## Running things

- Scripts are configured by editing constants at the top of each file or `smcv/config.json`. By design there are no CLI arguments. The few exceptions take an optional positional arg: a data dir for `analysis/plot_power_sweep_*.py` and `plot_selfosc_*.py`, or a mode for `smcv/laser_rin_pc.py` (`acquire` / `selftest`) and `smcv/odmr_fm_mfli_phase_pc.py`.
- Nothing can be tested without hardware except the analysis scripts, the simulations (`analysis/nv_odmr_sim.py`, `proposal/autonomous_nv_sim.py`), and `python smcv/laser_rin_pc.py selftest`. To check a hardware script's changes, use `python -m py_compile <file>`; do not run acquisition scripts, because they drive real instruments.
- `python smcv/expconfig.py` prints the resolved config. `python smcv/check_instruments.py` is the first thing to run on the rig (it checks connectivity to the SMCV and the Red Pitaya SCPI server).

## Architecture: three control generations

1. **`arduino/`**: legacy. An Arduino latches ADF4351 registers and the PC does the PLL math.
2. **`redpitaya/`**: runs **on the Red Pitaya** as root (`rp`, `spidev` modules). The Red Pitaya programs the ADF4351 over SPI and reads the photodiode on IN1. Output goes to a `data/` dir relative to the CWD. The robust path uses a fixed settle time rather than waiting on the flaky LD (lock detect) pin; see the troubleshooting guide for why.
3. **`smcv/`**: current main path, runs **on the PC**. It drives an R&S SMCV100B generator over LAN SCPI (port 5025) and reads the Red Pitaya fast ADC through the Red Pitaya's SCPI server (port 5000).

Key shared modules in `smcv/`:
- `config.json` + `expconfig.load_config()`: the single source of instrument IPs, sweep range, power, lock-in params, and data paths. `load_config()` also adds derived values (`fs_hz`, `n_subread`, `n_sub`). Override the file with the `BUDGETODMR_CONFIG` env var. `paths.data_dir` points at a Windows lab-PC path.
- `odmr_smcv100b_pc.py`: holds the `Scpi`, `SMCV100B`, `RedPitayaADC` classes and `frange`. Other scripts import these, so it is both a script and a library. Always change the MW level through `SMCV100B.set_power_dbm()`, never with a raw SCPI write. It enforces the limit from `config.json` `mw_chain` (−16.4 dBm with the ZHL-16W-43-S+ amplifier, whose damage limit is +9 dBm at its input) and also sets that limit in the instrument.
- `redpitaya_scope.py`: `RedPitayaScope`, the correct fill-synchronised Red Pitaya acquisition sequence (pre-fill, trigger, wait for `ACQ:TRIG:FILL?`). The naive sequence returns stale or zero half-buffers, so use this for any new acquisition.
- `lockin_common.py`: the software lock-in engine (numpy demodulation, SMCV internal AM/FM modulation setup and teardown). It is used by the `odmr_lockin_{am,fm,fm_deriv}_pc.py` thin wrappers and the magnet-scan variants. AM gives a peak, FM magnitude gives |derivative| with a null at the centre, and FM phase-sensitive gives a signed zero-crossing (this needs the LF reference on IN2 with the HV jumper).
- `powersweep_acq.py`: shared by the DC and FM power sweeps. It provides tiered averaging per power band and sweep-level resume: each sweep is written atomically to its own file, and the combined mean+std CSV is regenerated after every sweep.
- `selfosc_common.py`: helpers for the self-oscillating FM loop experiments (`odmr_selfosc_*`). The loop is `f_{k+1} = f_k - (G/D_cal)(R(f_k) - R_0)` and the sensor signal is the period-doubling onset at G_eff = 2. The theory is in `proposal/autonomous_nv_sim.py` and `proposal/autonomous_nv_demo.md`.

`smcv/` modules import each other as top-level modules (`from expconfig import load_config`), so run them from inside `smcv/` or with it on `sys.path`. `analysis/` and `notebooks/acq_*.py` scripts do `sys.path.insert(0, <repo>/smcv)` to reach `expconfig`. Keep that pattern in new analysis scripts.

## Analysis and data conventions

- `analysis/plot_*.py` are paired with specific acquisition scripts, for example `plot_lockin.py` with `odmr_lockin_*` and `plot_power_sweep_{dc,fm}.py` (which share `powersweep_common.py`) with `odmr_power_sweep_{dc,fm}_pc.py`. When you change an acquisition script's output format, update its plotter too.
- The CSV format is `freq_MHz,signal[,std]` with `#`-prefixed `key=value` metadata header lines. `powersweep_common.read_sweep` treats the std column as optional for backward compatibility with older files.
- `proposal/` holds a funding-proposal work package (LaTeX report, figures, simulation). `procurement/` holds hardware-upgrade notes and the shopping-list generator (`build_shopping.py`). `notebooks/` holds tutorials plus `tutorial_data/`.
