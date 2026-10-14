"""
Step 2b: RELATIVE INTENSITY NOISE vs LASER CURRENT (PDA10A2 on Red Pitaya IN1).

At each current, adjust the ND filters so the photodiode sits at the SAME DC
voltage (V_TARGET), then record raw traces. With the detected light constant,
the shot-noise and detector floors stay constant, so any change of
    RIN(f) = S_V(f) / V_DC^2      [1/Hz]   (S_V = noise PSD, ASD^2)
with current comes from the laser itself. DPSS lasers often have quiet and
noisy current ranges (longitudinal mode competition); the quiet range is often
not the maximum current. plot_cal2_noise.py evaluates RIN at the candidate
modulation frequencies.

Where to sample: as close to the diamond as possible, where the light
matches what reaches it -- the dichroic leak, or the collimated beam just
before the objective (after the irises/filters, so clipping noise from beam
pointing is included).
Use the PDA10A2, not the power meter (average power only) and not the APD
(it would saturate).

  ** SAFETY ** attenuate BEFORE the detector; the script warns on clipping.

Run cal2_noise_floors.py first (same DECIMATION and IN1 jumper).

POWER MONITOR (MONITOR_POWER): the PM101A analog output on IN2 is recorded in
the same acquisitions as IN1. Put the S120C on a pick-off BEFORE the ND
filters, so it sees the laser power and not the attenuation. Without a saved
mW/V factor (cal0_check_power_meter.py) only its volts are meaningful.

Output: <data_dir>/calibration/rin_vs_current_<stamp>.npz
        (fs, current_mA, v_dc, label, tec_C, traces [n_current x N_REC x 16384],
         p_mon_mW, p_mon_std_mW, v_mon_V  -- the IN2 monitor, NaN if off)
        rewritten after every current, so Ctrl-C keeps the finished ones.
Next:   plot_cal2_noise.py

Run on the PC:  python cal2_rin_vs_current.py
"""

import numpy as np

from calib_common import (Photodiode, Stop, ask, ask_current, ask_tec, cal_path,
                          live_dc_monitor, pause, prepare_power_meter, stamp,
                          wait_stable)

# --- settings ---------------------------------------------------------------
CURRENTS_MA = [132.0, 134.0, 136.0, 138.0, 140.0, 142.0, 144.0, 147.0]  # above threshold
I_MAX_MA = 150.0           # never ask for more (set to your LDC200C limit)
V_TARGET = 0.50            # photodiode DC level to hold at every current (V)
V_TOL = 0.05               # accept within +/- 5 % of V_TARGET
DECIMATION = 1024          # same as cal2_noise_floors.py
GAIN = None                # None -> config.json redpitaya.input_gain
N_REC = 10                 # 134 ms records per current
SETTLE_MIN_S, SETTLE_MAX_S, SETTLE_TOL = 20.0, 240.0, 0.005
MONITOR_POWER = True       # also record the PM101A analog output on IN2


def main():
    if max(CURRENTS_MA) > I_MAX_MA:
        raise SystemExit(f"CURRENTS_MA goes above I_MAX_MA = {I_MAX_MA} mA.")
    path = cal_path(f"rin_vs_current_{stamp()}.npz")
    pd = Photodiode(DECIMATION, GAIN, monitor=MONITOR_POWER)
    cur_l, vdc_l, lab_l, tec_l, tr_l = [], [], [], [], []
    pm_l, pms_l, vm_l = [], [], []
    print(f"\nRIN vs CURRENT: hold the photodiode at {V_TARGET * 1e3:.0f} mV "
          f"(+/-{100 * V_TOL:.0f} %) with ND filters at every current -> {path}")
    try:
        pause("Detector at the dichroic leak / just before the objective, "
              "beam attenuated")
        if pd.pm is not None:
            print("Power monitor (S120C on a pick-off before the ND filters):")
            prepare_power_meter(pd.pm, required=False)
        for planned in CURRENTS_MA:
            cur = ask_current(planned, I_MAX_MA)
            if cur is None:
                continue
            print("  waiting for the laser output to settle (Ctrl-C to skip)...")
            wait_stable(pd.dc, 0.0, 10.0, SETTLE_TOL, SETTLE_MIN_S, SETTLE_MAX_S,
                        unit="mV", scale=1e3)
            while True:
                v = live_dc_monitor(pd, V_TARGET, V_TOL)
                if abs(v - V_TARGET) <= V_TOL * V_TARGET:
                    break
                if ask("  outside the tolerance: Enter = adjust again, "
                       "k = keep anyway").lower() == "k":
                    break
            label = ask("  attenuation used (e.g. 'ND1.0+ND0.3')", "")
            tec = ask_tec()
            print(f"  recording {N_REC} records...")
            tr = pd.records(N_REC)
            v_dc = float(tr.mean())
            print(f"  {cur:.2f} mA: DC {v_dc * 1e3:.2f} mV, "
                  f"rms {tr.std() * 1e3:.3f} mV")
            if pd.pm is not None:
                pm_l.append(float(pd.mon_mw.mean()))
                pms_l.append(float(pd.mon_mw.std(ddof=1)))
                vm_l.append(float(pd.mon_v.mean()))
                print(f"  monitor: {pm_l[-1]:.4f} mW ({vm_l[-1] * 1e3:.2f} mV)")
            else:
                pm_l.append(np.nan)
                pms_l.append(np.nan)
                vm_l.append(np.nan)
            cur_l.append(cur)
            vdc_l.append(v_dc)
            lab_l.append(label)
            tec_l.append(tec)
            tr_l.append(tr)
            np.savez(path, fs=pd.fs, decimation=DECIMATION, gain=pd.gain,
                     v_target=V_TARGET, current_mA=np.array(cur_l),
                     v_dc=np.array(vdc_l), label=np.array(lab_l),
                     tec_C=np.array(tec_l), traces=np.array(tr_l),
                     p_mon_mW=np.array(pm_l), p_mon_std_mW=np.array(pms_l),
                     v_mon_V=np.array(vm_l))
    except (Stop, KeyboardInterrupt):
        print("\nStopped -- finished currents are saved.")
    finally:
        pd.close()
    print(f"\n{len(cur_l)} current(s) -> {path}\nNext: plot_cal2_noise.py "
          "(then pick the quiet current for cal2_noise_vs_photocurrent.py)")


if __name__ == "__main__":
    main()
