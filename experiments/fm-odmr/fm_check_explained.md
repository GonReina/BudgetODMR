# `fm_check_pc.py`: how it works, and why

`fm_check_pc.py` answers one question: **is frequency-modulated (FM) lock-in
detection better than plain DC ODMR on this rig, and at which modulation
frequency $f_\mathrm{mod}$?**

It measures both methods under the same conditions (same MW power, laser, focus
and detector) and puts both on the same footing: **the SNR reached in one second
of wall-clock time**. The acquisition script only records the data.
`plot_fm_check.py` does the spectral analysis and gives the verdict.

```
SMCV100B ──(MW, FM-modulated)──> isolator ──> amplifier ──> antenna ──> NV diamond
                                                                           │ PL
                                                       photodiode ──> Red Pitaya IN1
```

---

## 0. Setup (before any measurement)

1. **MW source.** `src.configure(MW_POWER_DBM)` connects to the SMCV100B. It also sets
   the level limit, both in software and in the instrument (−16.4 dBm with the
   ZHL-16W-43-S+ amplifier), selects CW mode and sets the power. Every later power
   change goes through `SMCV100B.set_power_dbm()`, so nothing can exceed the
   limit.
2. **Modulation off.** `teardown_smcv_modulation` switches the master modulation
   off, so step 1 is pure DC.
3. **FM remote control.** `SmcvFm` (in `common/lockin_common.py`) tries to set
   the FM parameters over SCPI. On the SMCV100B these are the **baseband
   "General" commands**:

   | setting | SCPI |
   |---|---|
   | FM on/off | `:SOURce1:BB:GENeral:FM:STATe ON\|OFF` |
   | shape | `:SOURce1:BB:GENeral:FM:SHAPe SINE` |
   | deviation $\Delta$ | `:SOURce1:BB:GENeral:FM:DEViation <Hz>` (0–4 MHz) |
   | modulation frequency $f_\mathrm{mod}$ | `:SOURce1:BB:GENeral:FM:FREQuency <Hz>` (0.1 Hz–100 kHz) |

   The commands in the SMBV/SMW manuals (`FM<ch>:STATe`, `LFOutput<ch>:FREQuency`)
   do not exist on the SMCV; it answers them with `-113 Undefined header`.

   Each setting counts as done remotely only if `SYSTem:ERRor?` reports no error
   **and** reading it back returns the value that was sent. Booleans read back as
   `1`/`0`. Anything the instrument refuses falls back to a prompt to set it in the
   touchscreen Modulation menu. The startup line reports which path was used, for
   example `SCPI control: state remote, shape remote, lf remote, dev remote`.
4. **Red Pitaya.** `RedPitayaADC` opens the fast ADC through its SCPI server.

---

## 1. DC ODMR: find the line

### 1a. The sweeps (`dc_sweeps`)

The script steps the MW frequency over `F_START … F_STOP` (from `config.json`) in
`DC_STEP_MHZ` = 0.25 MHz steps, `N_DC_SWEEPS` = 4 times. At every frequency $f$:

```
MW on  → wait SETTLE_S → V_on  = integrate()
MW off → wait SETTLE_S → V_off = integrate()
signal(f) = V_on / V_off
```

`integrate()` averages one Red Pitaya buffer over `subread_ms` (100 ms with the
config: decimation 1024, so $f_s$ = 122 kHz and 12 207 samples). Using the ratio
$V_\mathrm{on}/V_\mathrm{off}$ instead of $V_\mathrm{on}$ alone cancels slow
laser-power drift, because both readings are only a few hundred ms apart. Off
resonance the ratio is 1. On resonance the MW drives the NV into its dark
$m_s=\pm1$ states, so the PL drops:

$$
S(f) = \frac{V_\mathrm{on}}{V_\mathrm{off}} = 1 - C\,\mathcal L(f),\qquad
\mathcal L(f) = \frac{\gamma^2}{(f-f_0)^2+\gamma^2}
$$

Here $C$ is the contrast (dip depth), $f_0$ the line centre and $\gamma$ the
half-width at half-maximum (FWHM $= 2\gamma$). The four sweeps are averaged
point by point, and their standard deviation is saved as `std`.

### 1b. Dip, flank and width (`choose_line`)

The spectrum has **two lines about 5.3 MHz apart**, each about 4.5 MHz wide.
Together they look like one ~11 MHz dip. Treating that as a single line (as the
first version did) gives a 10 MHz "FWHM" and a park point between the lines,
where their slopes cancel.

So the script fits `N_LINES` = 2 Lorentzians (`calib_common.fit_odmr`) and
uses **one** line, the deeper one, or the one set by `LINE = "lower"`/`"upper"`:

- dip = that line's centre $f_0$;
- FWHM and depth = that line's own values;
- park point = the steepest point of its **outer** flank,
  $f_0 \pm \gamma/\sqrt3$, on the side away from the other line. This way the
  modulation doesn't reach the neighbouring line.

If the fit fails, it falls back to the old fit-free read-out (`find_points`):

1. **Smooth** the averaged spectrum with a `SMOOTH` = 3 point moving average,
   ignoring the end points, which the moving average biases.
2. **Dip** $f_\mathrm{dip}$ = the minimum of the smoothed spectrum.
3. **Baseline** = the median of the 5 outermost points on each side.
4. **Depth** $C = 1 - S_\mathrm{min}/\text{baseline}$.
5. **FWHM** = walk outwards from the dip until the curve rises above
   half-depth, $\text{baseline} - C\cdot\text{baseline}/2$, on each side.
6. **Steepest flank** $f_\mathrm{slope}$ = the maximum of $|dS/df|$ within one FWHM
   of the dip. The search is restricted so that it doesn't pick the flank of a
   neighbouring line.

For a Lorentzian the steepest point is at $f_0 \pm \gamma/\sqrt3$, where

$$
\left|\frac{dS}{df}\right|_\max = \frac{3\sqrt3}{8}\,\frac{C}{\gamma}\approx 0.65\,\frac{C}{\gamma}.
$$

### 1c. DC benchmark (`dc_benchmark`)

This is the reference that FM has to beat. The script parks the MW **at the
dip** and takes `N_DC_PAIRS` = 30 MW-off / MW-on pairs:

$$
d_k = V_{\mathrm{off},k} - V_{\mathrm{on},k}.
$$

Each pair is one measurement of the ODMR signal $C\cdot V_\mathrm{PL}$. Its
single-shot SNR is $\bar d/\sigma_d$. Averaging $N$ independent pairs improves
it by $\sqrt N$, and one pair takes $t_\mathrm{pair}$ of wall-clock time, so in
one second:

$$
\mathrm{SNR}_{1\,\mathrm s}^\mathrm{DC} = \frac{\bar d}{\sigma_d}\sqrt{\frac{1\,\mathrm s}{t_\mathrm{pair}}}
$$

This number includes everything real: the settle times, the SCPI and network
overhead, and laser noise at the ~1 Hz on/off rate. That last one is usually
the limit: switching the MW at about 1 Hz puts the signal in the $1/f$ region
of the laser noise.

### 1d. Where to park

The script proposes $f_\mathrm{slope}$ (with `PARK = "slope"`) or
$f_\mathrm{dip}$ (with `"dip"`), lets you edit it, and saves everything to
`dc_odmr.csv`. The next section explains why the choice matters.

---

## 2. FM: move the signal to a quiet frequency

### 2a. The idea

Without modulation the ODMR signal is a DC level, and DC is where the rig is
noisiest (laser drift, $1/f$, mains). FM shakes the MW frequency sinusoidally
around the park point $f_p$:

$$
f(t) = f_p + \Delta\cos(2\pi f_\mathrm{mod} t)
$$

The PL follows the line shape, $V(t) = V_\mathrm{PL}\,S(f(t))$, so the ODMR
information now appears as **AC tones at $f_\mathrm{mod}$ and its harmonics**.
Choose $f_\mathrm{mod}$ where the detector noise floor is low, and the same
signal is measured against much less noise.

### 2b. What the tones are (Taylor expansion, small $\Delta$)

$$
S(f_p+\Delta\cos\omega t)\approx S(f_p) + S'(f_p)\,\Delta\cos\omega t
 + \tfrac12 S''(f_p)\,\Delta^2\cos^2\omega t + \dots
$$

Using $\cos^2 x = \tfrac12(1+\cos 2x)$:

| component | amplitude (× $V_\mathrm{PL}$) | meaning |
|---|---|---|
| DC | $S(f_p) + \tfrac14 S''\Delta^2$ | the PL level |
| **$f_\mathrm{mod}$** | $S'(f_p)\,\Delta$ | **slope** of the line |
| $2f_\mathrm{mod}$ | $\tfrac14 S''(f_p)\,\Delta^2$ | **curvature** of the line |

Consequences:

- **At the dip centre** $S'=0$, so the $f_\mathrm{mod}$ tone vanishes and only
  $2f_\mathrm{mod}$ remains. That is why `PARK = "slope"` is the default: on the
  steepest flank the $f_\mathrm{mod}$ tone is as large as possible,
  $\approx 0.65\,C\,V_\mathrm{PL}\,\Delta/\gamma$. If you park at the dip, as in
  the 2026-10-15 run, the $2f$ tone comes out larger than the $f$ tone.
- **For a magnetometer** the useful quantity is $S'$: a field shift $\delta B$
  moves the line by $\gamma_e\,\delta B$ (28 MHz/T). The $f_\mathrm{mod}$ tone
  changes by $S'\cdot\gamma_e\,\delta B$. The tone is also exactly the
  derivative-shaped signal used for locking to the line.
- **Deviation.** The tone grows linearly with $\Delta$ only while $\Delta \ll \gamma$.
  Beyond that it saturates and the line effectively broadens. For the flank
  tone, $\Delta\approx\gamma$ = FWHM/2 **of one line** is about the best, and it
  is the script's default. Using the FWHM of the two overlapping lines instead
  (5.1 MHz on 2026-10-15) sweeps over both lines and shrinks the tone about 7×.
- **Modulation frequency.** It must stay well below the rate at which the NV
  responds (optical pumping takes µs, so up to ~100 kHz is fine). It must also
  avoid known pickup lines: mains harmonics and the 26.19 kHz Red Pitaya line.
  `F_MODS_HZ` = 500 Hz … 33 kHz covers the useful range.

### 2c. The loop over $f_\mathrm{mod}$

The script sets the deviation, switches FM on, enables the master modulation
switch and turns the RF on. Then, for each $f_\mathrm{mod}$:

1. Set the modulation frequency (remotely, or by prompt).
2. **On resonance:** MW to $f_p$, wait 0.2 s, record `N_REC` = 30 raw buffers.
3. **Off resonance:** MW to `OFF_RES_MHZ` (50 MHz below the sweep, far from any
   line), wait, record 30 buffers. Any tone at $f_\mathrm{mod}$ here cannot be
   ODMR. It is **electrical pickup** (modulation leaking from the generator or
   the cabling), and it must be much smaller than the on-resonance tone for the
   result to mean anything.
4. Save `fm_<f_mod>Hz.npz`: the raw records, $f_s$, $\Delta$, $f_p$, the
   wall-clock time per record `t_rec_s`, and `contiguous` (see 2d).

Raw records: decimation 256 gives $f_s$ = 488.3 kHz. A buffer is 16 384 samples
= **33.6 ms**, so the FFT bins are $1/T$ = 29.8 Hz wide. A record takes about
330 ms of wall-clock time, mostly for transferring the data as SCPI text, so
the **duty cycle** is about 10 %.

### 2d. The records must be continuous

A lock-in adds up $v(t)\,e^{-i\omega t}$ over the record. That only works if
the record is one continuous stretch of time. The Red Pitaya buffer is circular.
With the old sequence (`ACQ:TRIG:DLY 0`, trigger in the middle of the buffer),
the half before the trigger and the half after it **were not continuous**.

The 2026-10-15 run showed this as a random phase jump of the tone at the
mid-record seam:

- The full-record magnitude scattered by 25 %.
- The post-trigger half alone scattered by 0.5–1.7 %.

`redpitaya_scope.py` now triggers at the **start** of the buffer
(`ACQ:TRIG:DLY 8192`), so every sample comes after the trigger and is continuous.
Files are tagged `contiguous=True`. For older files without the tag, the
plotter analyses only the post-trigger half.

---

## 3. The analysis (`plot_fm_check.py`)

For each $f_\mathrm{mod}$:

### 3a. Spectrum

Each record has its mean removed and is multiplied by a Hann window $w$. The
one-sided power spectral density (PSD, V²/Hz) is then averaged over the records:

$$
P(f) = \frac{2\,|\mathrm{FFT}(v\,w)|^2}{f_s\sum w^2}
$$

### 3b. The tone and the floor

- **Tone** $A_\mathrm{rms}$: search for the peak within ±3 % of the nominal
  $f_\mathrm{mod}$ (the real frequency can be slightly off), then sum the PSD over
  ±3 bins, which is the Hann main lobe:
  $A_\mathrm{rms}=\sqrt{\sum P\,\delta f}$. The same is done at $2f_\mathrm{mod}$, and
  in the same bin off resonance (the pickup check).
- **Floor** $e$ (V/√Hz): $\sqrt{\mathrm{median}\,P}$ over $f_\mathrm{mod}(1\pm0.15)$,
  leaving out ±8 bins around the tone. The median ignores stray lines.

### 3c. Ideal SNR: a lock-in that never stops

A lock-in estimates the tone's in-phase amplitude
$X = \frac{2}{T}\int_0^T v(t)\cos\omega t\,dt$. For white noise of one-sided
density $e$, the variance of that estimate is

$$
\sigma_X^2=\frac{4}{T^2}\cdot\frac{e^2}{2}\cdot\frac{T}{2}=\frac{e^2}{T}
\;\Rightarrow\;\sigma_X=\frac{e}{\sqrt T}.
$$

The tone's peak amplitude is $\sqrt2A_\mathrm{rms}$, so after $T$ = 1 s of
continuous acquisition:

$$
\mathrm{SNR}_{1\,\mathrm s}^\mathrm{ideal} = \frac{\sqrt2\,A_\mathrm{rms}}{e}
$$

This is the best FM could do on this rig with a streaming lock-in and no dead
time.

### 3d. Measured SNR: what the rig really gets

The script demodulates each record on its own (`lockin_mags`): Hann-weighted, at
the frequency within ±1 bin that maximises the mean power, which keeps phase
errors small. That gives one magnitude $|z_k|$ per record. Then, as for DC:

$$
\mathrm{SNR}_{1\,\mathrm s}^\mathrm{meas} = \frac{\overline{|z|}}{\sigma_{|z|}}\sqrt{\frac{1\,\mathrm s}{t_\mathrm{rec}}}
$$

This uses the **wall-clock** time per record, so dead time counts against it.
If the only loss were dead time, then

$$
\frac{\mathrm{SNR}^\mathrm{ideal}}{\mathrm{SNR}^\mathrm{meas}}\approx\sqrt{\frac{t_\mathrm{rec}}{T_\mathrm{record}}}
\qquad(\approx 3\text{ for 330 ms per 33.6 ms record}).
$$

The plotter prints both numbers. A ratio well above the dead-time value means
the records disagree with each other more than the noise explains: drift between
records, or glitches like the old trigger seam.

### 3e. The verdict

$$
\text{gain} = \frac{\max_{f_\mathrm{mod}}\mathrm{SNR}^\mathrm{meas}_{1\,\mathrm s}}{\mathrm{SNR}^\mathrm{DC}_{1\,\mathrm s}}
$$

- gain > 1: FM helps, and the best $f_\mathrm{mod}$ is printed.
- An off-resonance tone above 30 % of the on-resonance tone is flagged as
  **pickup**. If that happens, the gain is not ODMR.

For an ODMR **sweep** this is the right comparison: the DC signal is the dip
depth at the centre, and the FM signal is the tone on the flank. Each is the
largest signal its method produces anywhere in the spectrum.

The plotter also prints the median noise floor near $f_\mathrm{mod}$. A clean
run gave about 250 nV/√Hz. A floor many times higher, with the tone also
present OFF resonance, means electrical interference: FM sits right next to it,
while the 100 ms DC readings average it away.

Results on 2026-10-15 (FM best measured SNR in 1 s, compared with DC on/off):

| run | DC | FM | why |
|---|---|---|---|
| 13:31 | 7.7 | 355 (7 kHz) | laser noisy (0.5 % drift between readings): DC suffers, FM doesn't |
| 14:34 | 155 | 135 | laser quiet; Δ = 5.1 MHz and park between the two lines → tone only ~100 µV |
| 15:05 | 173 | 109 | park and Δ fixed (tone ~700 µV), but ~1 mV interference near 10.5 kHz and a 6 µV/√Hz floor, also off resonance |

---

## 4. Outputs

| file | content |
|---|---|
| `dc_odmr.csv` | averaged DC spectrum (`freq_MHz,signal,std`); metadata: dip, flank, FWHM, depth, park point, DC benchmark |
| `dc_pairs.csv` | the 30 off/on readings of the DC benchmark |
| `fm_<f>Hz.npz` | raw records on/off resonance, $f_s$, $\Delta$, $f_p$, `t_rec_s`, `contiguous` |
| `fm_check_*.png`, `fm_check_summary.*` | from `plot_fm_check.py`: per-$f_\mathrm{mod}$ spectra, raster, SNR vs $f_\mathrm{mod}$ |

## 5. Settings worth changing

| setting | default | when to change |
|---|---|---|
| `MW_POWER_DBM` | −18 | it must stay ≤ −16.4 dBm with the amplifier (the script enforces this) |
| `PARK` / `PARK_MHZ` | `"slope"` | `"dip"` to study the $2f$ signal; `PARK_MHZ` to force a frequency |
| `FM_DEV_KHZ` | `None` (asks; default FWHM/2) | set a value to skip the prompt |
| `F_MODS_HZ` | 500 … 33 000 | keep clear of mains harmonics and 26.19 kHz |
| `DECIMATION` | 256 | longer records (higher decimation) give finer bins and less relative dead time, but the frequency range is lower ($f_s/2$) |
| `N_REC` | 30 | more records give a tighter SNR estimate |

## 6. Limits of the method

- It measures the **magnitude** of the $f_\mathrm{mod}$ tone, not its sign. To
  lock to the line you need phase-sensitive detection with the LF reference on IN2
  (`odmr_lockin_fm_deriv_pc.py`).
- The measured SNR is limited by the roughly 10 % duty cycle of SCPI transfers.
  Longer records or a streaming lock-in (on the Red Pitaya FPGA, or an MFLI)
  would get close to the ideal column.
- The DC benchmark and the FM records are taken a few minutes apart. Large laser
  drift between them biases the comparison; `dc_pairs.csv` and the DC level in
  each npz show it.
