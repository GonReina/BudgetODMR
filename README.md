# BudgetODMR

A budget optically-detected magnetic resonance (ODMR) rig for an NV-diamond
sample. An ADF4351 synthesizer sweeps microwaves across the NV resonance
(~2.87 GHz) while a photodiode watches the photoluminescence dip. A RedPitaya
drives the ADF4351 over SPI and digitizes the photodiode on its fast ADC.

## Repository layout

Scripts are grouped by the experiment they perform. Each experiment folder holds
its acquisition script(s) **and** the analysis/plot scripts for the data they
produce. Files marked **[RP]** run ON the RedPitaya (Python 3, needs `rp` +
`spidev`, run as root); everything else runs on the PC.

```
experiments/
  common/        Shared PC-side instrument code. Every PC script puts this folder on sys.path.
    config.json           All experiment settings (IPs, sweep range, power, lock-in params, data paths).
    expconfig.py          Loads config.json (used by every PC script and plotter).
    odmr_smcv100b_pc.py   Scpi / SMCV100B / RedPitayaADC classes, and runnable as the stepped DC ODMR
                          sweep (SMCV sets freq, RedPitaya reads IN1, MW on/off ratio).
    lockin_common.py      Shared software lock-in engine (AM / FM / FM-derivative).
    redpitaya_scope.py    Fill-synchronised RedPitaya acquisition (use for any new acquisition).

  low-cost/      ADF4351 synthesizer path (RedPitaya SPI, legacy Arduino)
    diag_spi_alive.py     [RP] Prove the SPI path by forcing LD high/low via R5 (no lock needed). Run first.
    diag_reference.py     [RP] Reference-clock / feedback diagnostic for a VCO that won't lock.
    set_frequency.py      [RP] Continuously output any single frequency; LD read as a status flag only.
    odmr_sweep_robust.py  [RP] Averaged repeated sweeps using a FIXED settle time.  <- main experiment
    odmr_redpitaya.py     [RP] Original single sweep: per point, wait for the LD lock edge then average IN1.
    odmr_repeat_sweeps.py [RP] Run odmr_redpitaya.py's sweep N times, one CSV per run.
    lock_diagnostic_sweep.py  [RP] Dwell at each frequency so a human can watch the scope + D3 LED.
    test_500mhz_locktime.py   [RP] Bench test: program 500 MHz, time the PLL lock.
    average_sweeps.py     Average repeated runs and plot the result (lock filter + normalize + median).
    arduino/              Legacy Arduino path: adf4351_bridge.ino + odmr_sweep.py (PC owns the PLL math),
                          plus earlier sketches.

  dc-odmr/       Unmodulated SMCV sweeps (the main DC sweep itself is common/odmr_smcv100b_pc.py)
    odmr_smcv100b.py      [RP] SMCV-driven sweep with the script running on the RedPitaya.
    acq_dc_integration_sweep.py  DC sweep at several integration times (data for the lock-in tutorial).
    plot_odmr.py          Plot one ODMR spectrum, mark the resonance dip.

  ac-odmr/       AM lock-in
    odmr_lockin_am_pc.py  Lock-in AM -> line appears as a PEAK.
    acq_am_tutorial.py    AM demo data for the lock-in tutorial.
    plot_lockin.py        Analyse lock-in runs (AM peak / FM null / FM-derivative zero-crossing)
                          -> centre(s), splitting, B. Also used for the fm-odmr runs.
    plot_lockin_envelope.py   Hilbert-envelope view of each lock-in run.

  fm-odmr/       FM lock-in
    odmr_lockin_fm_pc.py        Lock-in FM (magnitude) -> |derivative|, NULL at centre.
    odmr_lockin_fm_deriv_pc.py  Lock-in FM (phase-sensitive) -> signed derivative, ZERO-CROSSING at centre.
    odmr_fm_mfli_phase_pc.py    Signed FM detection with the MFLI lock-in (experimental).
    acq_fm_tutorial.py          FM demo data for the lock-in tutorial.

  calibration/   Connectivity checks, detector / laser noise and characterisation
    check_instruments.py  Prove you can talk to the SMCV and the RedPitaya SCPI server. Run first.
    diag_lockin_raw.py    Park on a resonance and inspect the raw modulated photodiode waveform.
    laser_rin_pc.py       Laser relative intensity noise (`selftest` mode runs without hardware).
    odmr_noise_budget_pc.py   Noise budget of the FM lock-in magnetometer.
    acq_noise_photodiode.py, acq_noise_vs_integration.py   Noise data for the lock-in tutorial.
    record_photodiode.py  [RP] Log IN1 (photodiode) for a fixed duration  -> plot_photodiode.py
    pd_vs_laser_current.py    [RP] Photodiode vs laser current  -> plot_laser_calibration.py
    outputsine.py         [RP] Quick OUT2 sine generator sanity check.
    LaserChar.py, LaserIntensityThreshold.py (+ CSVs)   Laser power / threshold characterisation.
    cal0_*..cal3_*, plot_cal*.py, calib_common.py   Step-by-step laser/detector calibration:
                          power at the sample vs current, RIN vs current and vs photocurrent,
                          PL saturation + contrast/linewidth/heating. Run order and outputs:
                          CALIBRATION_PROTOCOL.md.

  power-sweep/   DC and FM sweeps across MW power (power broadening)
    odmr_power_sweep_{dc,fm}_pc.py, powersweep_acq.py      acquisition
    plot_power_sweep_{dc,fm}.py, powersweep_common.py      analysis

  magnet-scan/   Zeeman studies vs magnet position
    odmr_magnet_scan.py (DC), odmr_magnet_scan_{am,fm,fm_deriv}.py (lock-in), odmr_watch_magnet_pc.py
    plot_magnet_scan.py, plot_magnet_lockin*.py, plot_magnet_two_orientation.py, plot_fm_two_orientations.py

  sensitivity/   FM magnetometer sensitivity and closed-loop field lock
    odmr_sensitivity_fm_pc.py (also a helper library for other folders), odmr_sensitivity_fm_wb_pc.py,
    odmr_fieldlock_fm_pc.py, and their plot_*.py

  self-oscillation/   Self-oscillating FM loop (WP3 measurements)
    odmr_selfosc_{fm,power,cycletime,precision}_pc.py, selfosc_common.py, plot_selfosc_*.py

theory/          Simulations, calculators, notebooks (most run without hardware)
  nv_odmr_sim.py        8-line NV spectrum + field fit (imported by the magnet-scan plotters).
  nv_odmr.py            NV ground-state spin / CW-ODMR calculator.
  nv_vsystem_cw_sim.py  Coherent V-system CW-ODMR simulation (+ .md write-up, vsystem_sim_out/).
  magnet_field_calc.py  Estimate on-axis magnet field & NV splitting vs distance.
  nv_deep_dive_guide.md, nv_quiz.md
  lockin-tutorial/      lockin_odmr_tutorial.ipynb + tutorial_data/ (filled by the acq_*.py scripts above)
  optics/               Optical_Setup.ipynb + optics_model.py, optics_draw.py
  proposal/             Funding-proposal work package: LaTeX report, WorkPackage3.ipynb,
                        autonomous_nv_sim.py, figures, selfosc_data/

procurement/     Hardware-upgrade notes and the shopping-list generator
docs/            ADF4351.pdf datasheet, confocal alignment notes
data/            CSV/PNG outputs (analysis scripts read from here)
```

See TROUBLESHOOTING_GUIDE.md for the full ADF4351 hardware/software debugging
roadmap. To use the **[RP]** scripts, copy them to the RedPitaya (the scripts in
`low-cost/` must stay together, since some import `odmr_redpitaya.py`). The
data-producing ones write under a `data/` subfolder relative to wherever they're
run (e.g. `/root/data/...`), so one Task Scheduler job on the PC can sync
everything at once -- see "Backing up data" below.

## Lock-in ODMR methods (SMCV100B)

The stepped DC sweep (`experiments/common/odmr_smcv100b_pc.py`) dwells and averages at each
frequency -- it works but is slow at fine resolution and limited by laser 1/f and
mains noise. The lock-in scripts instead modulate the microwaves at `f_mod` (a few
kHz, set in `config.json`) and detect the photodiode's response at that frequency,
where the noise floor is far lower -- so each point takes ~8 ms instead of ~100 ms
and the resonance stands out cleanly. The SMCV modulates itself with its internal
LF generator (K197 option); for AM and FM nothing extra is wired (photodiode ->
IN1 only). The Red Pitaya demodulates against the known `f_mod`. Test in this order:

1. **AM** -- `experiments/ac-odmr/odmr_lockin_am_pc.py`
   The microwave AMPLITUDE is switched sinusoidally at `f_mod`. On resonance the PL
   is modulated at `f_mod`; off resonance it is not. The magnitude lock-in
   `R = sqrt(X^2 + Y^2)` therefore traces the ODMR line as a **peak**. Simplest and
   most robust -- start here to confirm the whole chain end to end.

2. **FM, magnitude** -- `experiments/fm-odmr/odmr_lockin_fm_pc.py`
   The microwave FREQUENCY is dithered by ~a linewidth at `f_mod`. The PL is then
   modulated in proportion to the SLOPE of the line, so the magnitude lock-in gives
   the **|derivative|**: two lobes with a null exactly at the line centre. A sharper
   centre feature than AM, still phase-independent (no reference cable).

3. **FM, phase-sensitive (derivative)** -- `experiments/fm-odmr/odmr_lockin_fm_deriv_pc.py`
   Same FM dither, but demodulated IN PHASE with the modulation reference. This
   yields the **signed derivative** -- a dispersive curve that crosses zero at the
   centre, the most precise centre estimate (best for tracking small Zeeman
   shifts). It needs a real phase reference: route the SMCV LF-generator output to
   Red Pitaya **IN2** (set the IN2 jumper to HV). If your SMCV cannot output its LF
   generator, use the FM-magnitude script instead -- its null still locates centre.

All three save `freq_MHz,signal` CSVs (+ a running average) under `data_dir`. Analyse
them with `experiments/ac-odmr/plot_lockin.py`: set `MODE` to `am`, `fm`, or `fm_deriv` and it
picks the right centre-finder for that lineshape (AM = peak, FM = null between lobes,
FM-derivative = zero-crossing via integration), then reports the resonance centre(s),
and for a Zeeman pair the splitting and implied axial field B = df / (2*gamma).

## Typical workflow

1. **Run a sweep** on the RedPitaya (edit the config block at the top first):
   ```bash
   python3 experiments/low-cost/odmr_redpitaya.py        # writes data/odmr_spectrum_2.csv
   ```
2. Data backs up to the PC automatically (see below) — or copy it manually:
   ```bash
   scp -r root@rp-XXXXXXXX.local:/root/data ./
   python3 experiments/dc-odmr/plot_odmr.py
   ```

### Averaging repeated sweeps (better SNR)
```bash
python3 experiments/low-cost/odmr_repeat_sweeps.py        # writes data/odmr_runs/run_01.csv ...
python3 experiments/low-cost/average_sweeps.py             # -> data/odmr_average.csv + .png
```

### Recording the photodiode over time
```bash
python3 experiments/calibration/record_photodiode.py         # 10 min by default -> data/photodiode_*.csv
python3 experiments/calibration/plot_photodiode.py
```

All scripts are configured by editing the variables at the top of each file —
there are no command-line arguments by design. The plot/analysis scripts find the
`data/` folder automatically, so they can be run from anywhere.

## Backing up data automatically

The RedPitaya's kernel has no CIFS module and apt can't fetch `cifs-utils` on
this image, so mounting a Windows share from the Pitaya is a dead end. Instead
the chain is **Windows Task Scheduler pulls via scp <-- RedPitaya**, then
**Windows D: --robocopy--> Samba server**. Nothing in the experiment scripts
needs to know about backups at all — they just write under `data/`.

### Hop 1: Windows Task Scheduler pulls from the RedPitaya

1. **Set up passwordless SSH key auth** (Task Scheduler can't type a
   password). In PowerShell on the Windows PC:
   ```powershell
   ssh-keygen -t ed25519 -f $HOME\.ssh\id_ed25519   # Enter twice for no passphrase
   Get-Content $HOME\.ssh\id_ed25519.pub
   ```
   Copy that output, then on the RedPitaya (logged in with your usual password):
   ```bash
   mkdir -p ~/.ssh && chmod 700 ~/.ssh
   echo "<pasted public key>" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```
   From Windows, run `ssh root@rp-XXXXXXXX.local` once manually and accept the
   host key prompt (`yes`) — this caches it so the scheduled task never hits
   that prompt. Confirm it logs in with no password.

2. **Create a Scheduled Task**: Action tab ->
   - Program/script: `C:\Windows\System32\OpenSSH\scp.exe`
   - Add arguments:
     ```
     -o BatchMode=yes -o ConnectTimeout=10 -r root@rp-XXXXXXXX.local:/root/data/ D:\BudgetODMR_Data\
     ```

   Triggers tab -> On a schedule -> Daily -> check **Repeat task every: 30
   minutes**, for a duration of **Indefinitely**.

   `BatchMode=yes` makes it fail fast (instead of hanging) if the key setup
   ever breaks; `-r` pulls the whole `data/` folder recursively every time, so
   it always catches output from any script.

### Hop 2: Windows D: drive mirrors to the Samba server

`robocopy` is built into Windows (`C:\Windows\System32\Robocopy.exe`), so this
is a second Scheduled Task, same shape as Hop 1.

**Gotcha:** a `Z:\` drive letter mapped from Explorer only exists in *your*
logged-on session. A task set to "Run whether user is logged on or not" runs
in a separate, non-interactive session and won't see `Z:\` at all -- it'll
fail silently. Avoid this entirely by pointing robocopy at the share's UNC
path instead of the drive letter:

1. **Create a Scheduled Task**: Action tab ->
   - Program/script: `C:\Windows\System32\Robocopy.exe`
   - Add arguments:
     ```
     "D:\BudgetODMR_Data" "\\<samba-server>\<share>\BudgetODMR_Data" /MIR /Z /LOG+:D:\backup.log
     ```
     (swap in your actual server name/IP and share name -- same UNC path you'd
     see in Explorer's address bar when browsing the share.)

   Triggers tab -> On a schedule -> Daily -> **Repeat task every: 1 hour**
   (or whatever cadence you like), for a duration of **Indefinitely**.

   If the Samba share needs a username/password and you'd rather not deal
   with that under a non-interactive session, tick **"Run only when user is
   logged on"** on the General tab and keep using the `Z:\` mapping with "Reconnect
   at sign-in" + saved credentials checked when you first mapped it -- simpler,
   at the cost of only backing up while you're logged in.

   `/Z` enables restartable mode (resumes interrupted copies instead of
   restarting); `/LOG+:D:\backup.log` appends a log each run instead of
   overwriting it. Note robocopy's exit code is non-zero even on a fully
   successful run with files copied (e.g. `1`) -- that's normal, not a failure.

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
