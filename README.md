# BudgetODMR

A budget optically-detected magnetic resonance (ODMR) rig for an NV-diamond sample.
Microwaves are swept across the NV resonance (~2.87 GHz) while a photodiode watches the
photoluminescence dip. The microwave source is either an ADF4351 board (driven over SPI
by a Red Pitaya STEMlab) or an R&S SMCV100B generator (controlled from a PC over LAN).
The Red Pitaya fast ADC reads the photodiode in both cases.

---

## Repository layout

```
experiments/
  common/          Shared PC-side code — every PC script puts this on sys.path
  low-cost/        ADF4351 path: Red Pitaya programs the synthesizer over SPI
  dc-odmr/         Unmodulated (DC) ODMR sweeps with the SMCV100B
  ac-odmr/         AM lock-in ODMR
  fm-odmr/         FM lock-in ODMR (magnitude and phase-sensitive)
  calibration/     Connectivity checks, laser/detector characterisation
  power-sweep/     ODMR vs MW power (power broadening)
  magnet-scan/     Zeeman studies vs magnet position
  sensitivity/     FM magnetometer sensitivity and field-lock loop
  self-oscillation/ Self-oscillating FM frequency-tracking loop

theory/            Simulations and calculators (run without hardware)
  nv_odmr_sim.py         NV Hamiltonian / 8-line spectrum fit
  nv_odmr.py             CW-ODMR line-shape calculator
  magnet_field_calc.py   On-axis field and NV Zeeman splitting vs distance
  coils/                 Helmholtz pair designer
  nqr/                   14N quadrupole / ODNMR physics
  lockin-tutorial/       Jupyter notebook + tutorial data
  proposal/              Funding-proposal work package (LaTeX, simulations)

procurement/       Hardware-upgrade notes and shopping-list generator
docs/              Datasheets and alignment notes
```

Each experiment folder holds both the **acquisition script(s)** and the
**plot/analysis scripts** for the data they produce.  New scripts go in the
folder matching the data they produce or analyse.

---

## How scripts run

### PC scripts (most of `experiments/`)

Run directly on the lab PC with plain Python (numpy, matplotlib, scipy).
No build step, no CLI arguments — configuration lives in constants at the top
of each file and in `experiments/common/config.json`.

```
python experiments/calibration/check_instruments.py   # connectivity check
python experiments/common/odmr_smcv100b_pc.py         # DC ODMR sweep
python experiments/calibration/plot_cal3_mw_laser_map.py  # analysis / figures
```

`experiments/common/expconfig.py` loads `config.json` and adds derived values
(`fs_hz`, `n_sub`, …).  Every PC script starts with:

```python
_EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_EXP, "common"))
from expconfig import load_config
```

so the script runs from any working directory.

### Red Pitaya scripts (`[RP]` in `low-cost/` and some in `calibration/`)

These run **on the Red Pitaya as root** (needs the `rp` and `spidev` modules).
Copy the whole `low-cost/` folder to the device — some scripts import
`odmr_redpitaya.py` from the same directory.  Output goes to a `data/`
subfolder relative to wherever the script is run.

---

## Talking to the instruments

### SMCV100B (R&S microwave generator)

Communication is plain SCPI over a TCP socket on port 5025.
`experiments/common/odmr_smcv100b_pc.py` provides the thin wrappers:

```python
src = SMCV100B("192.168.50.20", 5025)   # connect
src.set_freq_mhz(2870.0)               # set frequency
src.set_power_dbm(-25.0)               # enforces the chain power limit from config.json
src.output(True)                        # RF on
src.output(False)                       # RF off
src.close()
```

`set_power_dbm` always goes through `SMCV100B.set_power_dbm()` — never a raw
SCPI write — because it checks the amplifier damage limit stored in `config.json`.

To confirm the link is up before any experiment:

```
python experiments/calibration/check_instruments.py
```

### Red Pitaya ADC (fast photodiode digitiser)

The Red Pitaya runs its own SCPI server on port 5000.
`experiments/common/odmr_smcv100b_pc.py` provides `RedPitayaADC`:

```python
adc = RedPitayaADC("169.254.129.123", 5000)
voltage = integrate(adc)    # acquire one buffer, return mean voltage on IN1
adc.close()
```

For any acquisition that needs the full waveform buffer,
`experiments/common/redpitaya_scope.py` provides `RedPitayaScope` with the
correct fill-synchronised sequence (pre-fill → trigger → wait for
`ACQ:TRIG:FILL?`).  The naive approach returns stale or half-empty buffers;
use `RedPitayaScope` for any new waveform work.

### ADF4351 (low-cost path, runs on the Red Pitaya)

The Red Pitaya programs the ADF4351 board over SPI (`spidev`).  The PLL math
runs in Python on the Red Pitaya.  See `experiments/low-cost/odmr_sweep_robust.py`
for the main experiment script and `TROUBLESHOOTING_GUIDE.md` for the full
hardware/software debugging roadmap.

---

## How a sweep works (DC example)

`experiments/common/odmr_smcv100b_pc.py` (also a runnable script) shows the
pattern used by almost every acquisition script:

```python
for freq in frange(F_START_MHZ, F_STOP_MHZ, F_STEP_MHZ):
    src.set_freq_mhz(freq)
    src.output(True);  time.sleep(SETTLE_S)
    pl_on  = integrate(adc)
    src.output(False); time.sleep(SETTLE_S)
    pl_off = integrate(adc)
    signal[i] = pl_on / pl_off          # ODMR ratio: dips below 1 at resonance
```

The lock-in scripts (`ac-odmr/odmr_lockin_am_pc.py`, `fm-odmr/odmr_lockin_fm_pc.py`)
follow the same loop but tell the SMCV to modulate itself (AM or FM, at `f_mod` from
`config.json`) and demodulate the Red Pitaya buffer against that frequency in software
(`experiments/common/lockin_common.py`).

---

## Data format

Every acquisition script writes **CSV files with `#`-prefixed metadata headers**:

```
# experiment=odmr_smcv100b
# f_start_MHz=2850.0
# f_stop_MHz=2890.0
# ...
freq_MHz,signal
2850.000,0.9987
2850.200,0.9991
...
```

Multi-sweep scripts add a `std` column and one `sweep_NN` column per sweep.
`experiments/common/expconfig.py`'s `read_table()` function parses this format
into a metadata dict and a column dict — used by every plotter.

The data directory is set in `config.json` (`paths.data_dir`), and each run
gets a timestamped subfolder, e.g.:
```
C:\Users\qute\Downloads\rsattempt\16-10-2026\calibration\mw_laser_map_20261016_142528\
```

---

## How plotters work

Each plotter is a standalone script in the same folder as its acquisition script.
It finds data automatically (newest matching folder by default) or takes an
optional path argument.  Example:

```
python experiments/calibration/plot_cal3_mw_laser_map.py
python experiments/calibration/plot_cal3_mw_laser_map.py path\to\specific\run
```

Plotters read the index CSV, load individual spectrum files on demand via a
helper like `spectrum_file(run, filename)`, compute fits (Lorentzian,
saturation curve, power broadening), and save figures as PNGs into the same
run folder.  `plot_cal3_mw_laser_map.py` is a good worked example: it reads
`index.csv`, fits contrast and FWHM across the laser × MW power grid, and
writes several figures (`mw_laser_map.png`, `mw_laser_map_cuts.png`, per-level
spectra, etc.).

---

## Key scripts to read first

| Purpose | Script |
|---------|--------|
| Connectivity check | `experiments/calibration/check_instruments.py` |
| DC ODMR sweep (PC) | `experiments/common/odmr_smcv100b_pc.py` |
| AM lock-in sweep | `experiments/ac-odmr/odmr_lockin_am_pc.py` |
| FM lock-in sweep | `experiments/fm-odmr/odmr_lockin_fm_pc.py` |
| Config / derived values | `experiments/common/expconfig.py` |
| Lock-in engine | `experiments/common/lockin_common.py` |
| Waveform acquisition | `experiments/common/redpitaya_scope.py` |
| Multi-level calibration | `experiments/calibration/cal3_mw_laser_map.py` |
| Analysis example | `experiments/calibration/plot_cal3_mw_laser_map.py` |
| NV simulation | `theory/nv_odmr_sim.py` |

See `TROUBLESHOOTING_GUIDE.md` for the ADF4351 + Red Pitaya hardware debugging
roadmap, and `experiments/calibration/CALIBRATION_PROTOCOL.md` for the
step-by-step laser and detector calibration sequence.
