"""
Step 1b: 532 nm POWER vs LASER CURRENT, up-and-down sweep.

The DPSS output is nonlinear in the pump current (threshold, crystal
temperature), so at every current the script waits until the PM101A reading
stops drifting (TEC settled), asks for the TEC temperature, and LOGS for LOG_S
seconds instead of taking one reading. The currents are swept up and then
back down to show any hysteresis.

Run it twice:
  POSITION = "before_objective"  (the calibration itself: the collimated beam
                                  just before the objective, times T_obj from
                                  the loss budget = power at the sample)
  POSITION = "laser_output"      (optional: the same sweep at the laser head.
                                  DPSS beam pointing and size move with pump
                                  current; the ratio of the two sweeps shows
                                  whether that changes the path transmission,
                                  e.g. clipping on irises or the objective
                                  pupil. Essential once a fibre is in the
                                  path, as the coupling then depends on it.)

Power meter: the PM101A analog output on Red Pitaya IN2 (see
cal0_check_power_meter.py), set BY HAND to 532 nm and a FIXED range covering
the top current. At the start it is zeroed with the beam blocked, then the
saved mW/V factor is reused or measured at the top current against Optical
Power Monitor. Do cal1_loss_budget.py first so the infrared check and T_obj
exist.

Output: <data_dir>/calibration/
          power_vs_current_<POSITION>_<stamp>.csv       one row per current step
              step,direction,current_mA,P_mW,P_std_mW,slope_mW_per_s,n,tec_C,settle_s,
              V_mean,V_zero
          power_vs_current_<POSITION>_<stamp>_log.csv   every logged reading
              step,current_mA,t_s,P_mW,V      (V = IN2 volts above zero)
Next:   plot_cal1_power.py -> power_calibration.csv (the x-axis for steps 2-3)

Run on the PC:  python cal1_power_vs_current.py
"""

from calib_common import (PowerMeter, Stop, TableWriter, ask_current, ask_tec,
                          cal_path, pause, prepare_power_meter, stamp)

# --- settings ---------------------------------------------------------------
POSITION = "before_objective"    # or "laser_output" (optional path-transmission check)
CURRENTS_MA = [120.0, 125.0, 128.0, 130.0, 132.0, 134.0, 136.0, 138.0,
               140.0, 142.0, 145.0, 147.0]      # dense near threshold (~130 mA)
SWEEP_DOWN = True                # then back down for the hysteresis check
I_MAX_MA = 150.0                 # never ask for more (set to your LDC200C limit)
LOG_S = 45.0                     # 30-60 s of logging per current
LOG_PERIOD_S = 0.2
SETTLE_MIN_S, SETTLE_MAX_S = 30.0, 300.0
SETTLE_TOL = 0.005               # stable = < 0.5 % drift over 10 s
WAVELENGTH_NM = 532.0            # set on the PM101A; recorded only


def main():
    if max(CURRENTS_MA) > I_MAX_MA:
        raise SystemExit(f"CURRENTS_MA goes above I_MAX_MA = {I_MAX_MA} mA.")
    plan = [(i, "up") for i in CURRENTS_MA]
    if SWEEP_DOWN:
        plan += [(i, "down") for i in reversed(CURRENTS_MA[:-1])]

    tag = f"power_vs_current_{POSITION}_{stamp()}"
    pm = PowerMeter()
    summ = log = None
    print(f"\nPOWER vs CURRENT at '{POSITION}': {len(plan)} steps "
          f"({'up + down' if SWEEP_DOWN else 'up'}), ~{LOG_S:.0f} s logging each\n")

    try:
        pause(f"Put the S120C at '{POSITION}'")
        prepare_power_meter(pm, max(CURRENTS_MA), I_MAX_MA, SETTLE_MIN_S,
                            SETTLE_MAX_S)
        meta = dict(experiment="power_vs_current", position=POSITION,
                    wavelength_nm=WAVELENGTH_NM, log_s=LOG_S, **pm.meta())
        summ = TableWriter(cal_path(tag + ".csv"),
                           ["step", "direction", "current_mA", "P_mW", "P_std_mW",
                            "slope_mW_per_s", "n", "tec_C", "settle_s", "V_mean",
                            "V_zero"], meta)
        log = TableWriter(cal_path(tag + "_log.csv"),
                          ["step", "current_mA", "t_s", "P_mW", "V"], meta)
        print(f"-> {summ.path}")
        for step, (planned, direction) in enumerate(plan):
            print("-" * 72 + f"\nstep {step + 1}/{len(plan)} ({direction})")
            cur = ask_current(planned, I_MAX_MA)
            if cur is None:
                continue
            settle_s = pm.settle(SETTLE_MIN_S, SETTLE_MAX_S, SETTLE_TOL)
            tec = ask_tec()
            r = pm.log(LOG_S, LOG_PERIOD_S)
            rel = 100 * r["std"] / r["mean"] if r["mean"] else float("nan")
            print(f"  {cur:.2f} mA ({direction}): {r['mean']:.5f} mW "
                  f"+/- {r['std']:.5f} ({rel:.2f} %)")
            summ.row(step, direction, cur, r["mean"], r["std"], r["slope"], r["n"],
                     tec, settle_s, r["v"].mean(), pm.v_zero)
            for t, p, v in zip(r["t"], r["p"], r["v"]):
                log.row(step, cur, t, p, v)
    except (Stop, KeyboardInterrupt):
        print("\nStopped -- steps so far are saved.")
    finally:
        for w in (summ, log):
            if w is not None:
                w.close()
        pm.close()
    if summ is None:
        return
    print(f"\nSaved {summ.path}")
    if POSITION != "laser_output":
        print("Next: plot_cal1_power.py (optionally first repeat with POSITION = "
              "'laser_output' to check the path transmission vs current)")
    else:
        print("Next: plot_cal1_power.py")


if __name__ == "__main__":
    main()
