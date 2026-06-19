# BudgetODMR

A budget optically-detected magnetic resonance (ODMR) rig for an NV-diamond
sample. An ADF4351 synthesizer sweeps microwaves across the NV resonance
(~2.87 GHz) while a photodiode watches the photoluminescence dip. A RedPitaya
drives the ADF4351 over SPI and digitizes the photodiode on its fast ADC.

## Repository layout

```
redpitaya/   Scripts that run ON the RedPitaya (Python 3, needs `rp` + `spidev`, run as root)
  odmr_redpitaya.py     Single ODMR sweep: per point, lock the PLL then average IN1.  <- main experiment
  odmr_repeat_sweeps.py Run the sweep N times, one CSV per run (reuses odmr_redpitaya.py).
  record_photodiode.py  Log IN1 (photodiode) for a fixed duration, e.g. 10 minutes.
  test_500mhz_locktime.py  Bench test: program 500 MHz, time the PLL lock.
  outputsine.py         Quick OUT2 sine generator sanity check.

analysis/    Scripts that run ON YOUR PC after copying CSVs into data/ (needs matplotlib)
  plot_odmr.py          Plot one ODMR spectrum, mark the resonance dip.
  plot_photodiode.py    Plot a photodiode time series with a +/-1 sd band.
  average_sweeps.py     Average the repeated runs in data/odmr_runs/ and plot the result.

arduino/     Legacy Arduino control path (before the move to RedPitaya)
  adf4351_bridge.ino + odmr_sweep.py   PC owns the PLL math, Arduino latches registers.
  hard_code_registers/, odmr_sweep/, with_library.ino   earlier sketches.

docs/        ADF4351.pdf datasheet
data/        CSV/PNG outputs (analysis scripts read from here)
```

## Typical workflow

1. **Run a sweep** on the RedPitaya (edit the config block at the top first):
   ```bash
   python3 redpitaya/odmr_redpitaya.py        # writes odmr_spectrum.csv
   ```
2. **Copy results to the PC** into `data/`, then plot:
   ```bash
   scp root@rp-XXXXXXXX.local:/root/odmr_spectrum.csv data/
   python3 analysis/plot_odmr.py
   ```

### Averaging repeated sweeps (better SNR)
```bash
python3 redpitaya/odmr_repeat_sweeps.py        # writes odmr_runs/run_01.csv ...
scp -r root@rp-XXXXXXXX.local:/root/odmr_runs data/
python3 analysis/average_sweeps.py             # -> data/odmr_average.csv + .png
```

### Recording the photodiode over time
```bash
python3 redpitaya/record_photodiode.py         # 10 min by default -> photodiode_timeseries.csv
scp root@rp-XXXXXXXX.local:/root/photodiode_timeseries.csv data/
python3 analysis/plot_photodiode.py
```

All scripts are configured by editing the variables at the top of each file —
there are no command-line arguments by design. The `analysis/` scripts find the
`data/` folder automatically, so they can be run from anywhere.

## Wiring (RedPitaya E1/E2 -> ADF4351)

| RedPitaya            | ADF4351 / sensor   |
|----------------------|--------------------|
| E2 SPI SCK           | CLK                |
| E2 SPI MOSI          | DATA               |
| E2 SPI CS            | LE                 |
| P3V3                 | VDD and CE         |
| E1 DIO0_P            | LD (lock detect)   |
| IN1 (fast ADC)       | photodiode amp out |
| GND                  | common ground      |
