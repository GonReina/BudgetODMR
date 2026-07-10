# An autonomous NV-centre sensor: deviations from self-oscillation as the measurement signal

*Demonstration package for the proposal "Use of deviations from autonomous
behaviour as signals of external perturbations for quantum sensing devices",
implemented on the existing BudgetODMR CW ODMR setup (SMCV100B + Red Pitaya,
FM lock-in with virtual demodulation at a fixed 5 kHz, no phase reference).*

## The idea in one paragraph

Our frequency-locked NV magnetometer is, viewed as a dynamical system, one gain
knob away from an **autonomous device**. Each lock cycle applies the discrete map
`f_{k+1} = f_k − (G/D_cal)·[R(f_k) − R_0]`, whose linearisation has multiplier
`1 − G_eff` with the dimensionless gain `G_eff = G·D_true/D_cal` proportional to
the local slope of the ODMR lock-in lobe. For `G_eff < 2` the loop is an ordinary
tracker; at `G_eff = 2` it undergoes a **flip (period-doubling) bifurcation** and
becomes a **self-oscillator** — a limit cycle generated entirely by the device,
with no external clock or drive, cascading to chaos at higher gain (fig. 2). The
device's *deviation from* or *onset of* autonomous behaviour is then used as the
sensor output, in direct analogy with the proposal's programme: what the
Josephson bifurcation amplifier does for superconducting circuits, this loop does
for a room-temperature spin ensemble.

## What is sensed, and by which observable

| Observable of the autonomous device | Physical quantity it senses | Why |
|---|---|---|
| Mean of the locked/oscillating orbit | Uniform magnetic field (DC) | Shift symmetry: a uniform field only translates the resonance; the loop re-centres. Ordinary magnetometry survives. |
| **Onset of self-oscillation** (critical gain G_c) | **Slope-changing perturbations**: field **gradients** across the ensemble (inhomogeneous broadening), MW/laser power, temperature/linewidth | G_c = 2·D_cal/D_true; anything that reshapes the line moves the threshold (figs. 3, 4). A *differential* quantity, separated by symmetry from the uniform field — the NV analogue of the proposal's multi-weak-link gradient sensing. |
| Critical fluctuations below onset | Same as above, continuously | Loop noise gain diverges as 1/√(2 − G_eff): the fluctuation level is a precursor "susceptibility" measurement. |
| **Limit-cycle statistics** (cycle-amplitude envelope, two-time correlations) | **Time-periodic fields** above the loop bandwidth | The period-2 cycle acts as an *internal local oscillator*: an applied AC field appears as a mixing sideband in the demodulated cycle spectrum (fig. 5) — detected through second-order statistics, exactly the "two-time / n-time distribution functions" route of the proposal. |

## Correspondence with the proposal text

* *"Deviations from autonomous behaviour as signals of external perturbations"* —
  realised literally: the sensor output is the change in the loop's dynamical
  state (fixed point ↔ limit cycle ↔ chaos), not a calibrated analog voltage.
* *"The onset of the self-oscillating regime could be made dependent on a
  specific offset"* — the critical gain is set by the lobe slope; biasing G just
  below/above 2 makes the oscillation onset conditional on a chosen perturbation
  strength (fig. 4: a sharp P(oscillation) discriminator under realistic noise).
* *"Higher order statistical quantities such as the two-time or n-time
  distribution functions"* — periodic signals are read out from the two-time
  statistics of the limit cycle (fig. 5); the same analysis applies unchanged to
  the electron-emission statistics of the autonomous single-electron source.
* *"Differential quantities such as magnetic field gradients"* — by symmetry the
  threshold observable is blind to uniform fields and responds to gradients and
  other line-reshaping perturbations, mirroring the multi-weak-link Josephson
  refrigerator proposal.
* *"Comparison with NV centres"* — this demo **is** the NV benchmark platform,
  running today; every observable proposed for the SES/Josephson devices has a
  measured NV counterpart to compare against.

## Status and files

* **Simulation (done)**: `proposal/autonomous_nv_sim.py` → figs 1–5
  (rig-realistic parameters: 10 mV lobe, 0.3 mV/reading noise, 20 cycles/s).
  - fig1: the FM lobe as the loop nonlinearity; cobweb maps below/above onset.
  - fig2: experimental-style bifurcation diagram; onset exactly at G_eff = 2,
    period-doubling cascade to chaos.
  - fig3: the onset moves with a slope perturbation (broadening as gradient
    proxy); critical gain tracks the perturbation linearly.
  - fig4: with realistic noise, P(self-oscillation) at fixed G is a sharp
    perturbation discriminator.
  - fig5: a 7 Hz applied field read out as a mixing sideband of the autonomous
    cycle — signal recovery from oscillation statistics alone.
* **Hardware protocol (ready to run)**: `smcv/odmr_selfosc_fm_pc.py` — measures
  the real bifurcation diagram (gain scan) and takes a long statistics run;
  repeat with/without a perturbation (move the magnet in for a gradient, change
  MW power, drive a coil from the Red Pitaya output) and compare G_c.
* All of this uses only the existing CW hardware and the phase-reference-free
  magnitude lock-in; no pulsed equipment is required.

## Honest limitations (worth stating in the proposal)

For Gaussian-noise-limited estimation of a *small analog* signal, a well-designed
linear readout with matched filtering is asymptotically optimal; the autonomous
mode does not beat it in raw SNR. Its advantages are of a different kind:
threshold/latching detection (binary output robust to gain and contrast drift),
symmetry-enforced selectivity to differential quantities, internal frequency
conversion of AC signals, and — scientifically — a table-top platform where the
sensing-through-bifurcation concepts of the proposal can be tested and
benchmarked against the same team's NV expertise before being deployed on
mesoscopic autonomous devices.
