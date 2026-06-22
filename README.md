# BudgetODMR

A budget optically-detected magnetic resonance (ODMR) rig for an NV-diamond
sample. An ADF4351 synthesizer sweeps microwaves across the NV resonance
(~2.87 GHz) while a photodiode watches the photoluminescence dip. A RedPitaya
drives the ADF4351 over SPI and digitizes the photodiode on its fast ADC.

## Repository layout

```
redpitaya/   Scripts that run ON the RedPitaya (Python 3, needs `rp` + `spidev`, run as root)
  diag_spi_alive.py     Diagnostic: prove the SPI path by forcing LD high/low via R5 (no lock needed). Run first.
  set_frequency.py      Continuously output any single frequency; LD read as a status flag only.
  odmr_sweep_robust.py  Averaged repeated sweeps using a FIXED settle time (never blocks on LD).  <- main experiment
  odmr_redpitaya.py     Original single sweep: per point, wait for the LD lock edge then average IN1.
  odmr_repeat_sweeps.py Run odmr_redpitaya.py's sweep N times, one CSV per run.
  record_photodiode.py  Log IN1 (photodiode) for a fixed duration, e.g. 10 minutes.
  lock_diagnostic_sweep.py  Dwell at each frequency so a human can watch the scope + D3 LED.
  test_500mhz_locktime.py   Bench test: program 500 MHz, time the PLL lock.
  outputsine.py         Quick OUT2 sine generator sanity check.

See TROUBLESHOOTING_GUIDE.md for the full hardware/software debugging roadmap.

  All three data-producing scripts write under a `data/` subfolder relative
  to wherever they're run (e.g. `/root/data/...`), so one Task Scheduler job
  on the PC can sync everything at once -- see "Backing up data" below.

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
   python3 redpitaya/odmr_redpitaya.py        # writes data/odmr_spectrum_2.csv
   ```
2. Data backs up to the PC automatically (see below) — or copy it manually:
   ```bash
   scp -r root@rp-XXXXXXXX.local:/root/data ./
   python3 analysis/plot_odmr.py
   ```

### Averaging repeated sweeps (better SNR)
```bash
python3 redpitaya/odmr_repeat_sweeps.py        # writes data/odmr_runs/run_01.csv ...
python3 analysis/average_sweeps.py             # -> data/odmr_average.csv + .png
```

### Recording the photodiode over time
```bash
python3 redpitaya/record_photodiode.py         # 10 min by default -> data/photodiode_*.csv
python3 analysis/plot_photodiode.py
```

All scripts are configured by editing the variables at the top of each file —
there are no command-line arguments by design. The `analysis/` scripts find the
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
