"""
Step 1a: LOSS BUDGET and INFRARED CHECK (do this once).

Measures the 532 nm power at points along the free-space excitation path, at
a few laser currents:

    laser_output -> before_objective -> after_objective

so plot_cal1_power.py can give the transmission of each stage and the
objective transmission T_obj (used to turn the before-objective sweep into
power at the sample). Once a fibre is in the path, add "after_fibre" to
POSITIONS (between laser_output and before_objective) to get its coupling.

INFRARED CHECK. The S120C is a silicon sensor: it also sees the 808 nm pump and
1064 nm leakage of the DPSS. At the positions in BP_POSITIONS each reading is
repeated with a 532 nm bandpass filter in front of the sensor. If
P_bandpass / T_bandpass(532) differs from the open reading, part of the
"power" is infrared and the power axis must be corrected (plot_cal1_power.py
does this).

  ** SAFETY **
  * after_objective: put the sensor 2-3 mm PAST the focus, never at the focus.
    The focused full power can damage the S120C surface. Past the focus the
    cone widens fast (about 1.7x the distance for NA 0.65, 2.3x for NA 0.75),
    so by ~5 mm it overfills the 9.5 mm aperture; 2-3 mm gives a spot a few mm
    across.
  * The S120C reads up to 50 mW. Check the laser output is below that first.
  * Goggles on.

Procedure (the script prompts each step):
  For each position: place the sensor, block the beam and zero, then for each
  current in CURRENTS_MA set the LDC200C, wait for the reading to settle, log
  LOG_S seconds (and again with the bandpass filter where requested).

Output: <data_dir>/calibration/loss_budget_<stamp>.csv
        position,current_mA,filter,P_mW,P_std_mW,slope_mW_per_s,n,tec_C,settle_s
Next:   cal1_power_vs_current.py, then plot_cal1_power.py

Run on the PC:  python cal1_loss_budget.py
"""

from calib_common import (PowerMeter, Stop, TableWriter, ask_current, ask_tec,
                          cal_path, pause, stamp)

# --- settings ---------------------------------------------------------------
CURRENTS_MA = [135.0, 140.0, 147.0]   # "a few powers" above threshold
I_MAX_MA = 150.0                      # never ask for more (set to your LDC200C limit)
LOG_S = 20.0                          # logging time per reading
SETTLE_MIN_S, SETTLE_MAX_S = 20.0, 180.0
WAVELENGTH_NM = 532.0
MANUAL_PM = False                     # True: type the readings in even if USB works

POSITIONS = ["laser_output", "before_objective", "after_objective"]
# with a fibre: ["laser_output", "after_fibre", "before_objective", "after_objective"]
BP_POSITIONS = ["laser_output", "before_objective"]   # also measure with the 532 nm bandpass
BP_T532 = 0.90         # bandpass transmission at 532 nm (datasheet / measure it)

WHERE = {
    "laser_output": "right after the laser head (before any optics)",
    "after_fibre": "right after the fibre output collimator",
    "before_objective": "in the collimated beam just before the objective "
                        "(after the dichroic)",
    "after_objective": "2-3 mm PAST the focus (NOT at the focus)",
}


def main():
    path = cal_path(f"loss_budget_{stamp()}.csv")
    pm = PowerMeter(WAVELENGTH_NM, manual=MANUAL_PM)
    out = TableWriter(path, ["position", "current_mA", "filter", "P_mW", "P_std_mW",
                             "slope_mW_per_s", "n", "tec_C", "settle_s"],
                      meta=dict(experiment="loss_budget", wavelength_nm=WAVELENGTH_NM,
                                bp_T532=BP_T532, log_s=LOG_S, power_meter=pm.idn))
    print(f"\nLOSS BUDGET -> {path}")
    print(f"Positions: {', '.join(POSITIONS)};  currents: {CURRENTS_MA} mA\n")

    try:
        for pos in POSITIONS:
            print("=" * 72)
            pause(f"POSITION '{pos}': put the S120C {WHERE[pos]}")
            pm.zero()
            for planned in CURRENTS_MA:
                cur = ask_current(planned, I_MAX_MA)
                if cur is None:
                    continue
                settle_s = pm.settle(SETTLE_MIN_S, SETTLE_MAX_S)
                tec = ask_tec()
                r = pm.log(LOG_S)
                print(f"  {pos} @ {cur:.2f} mA: {r['mean']:.5f} mW")
                out.row(pos, cur, "none", r["mean"], r["std"], r["slope"], r["n"],
                        tec, settle_s)
                if pos in BP_POSITIONS:
                    pause("  Put the 532 nm BANDPASS filter in front of the sensor")
                    b = pm.log(LOG_S)
                    ratio = b["mean"] / BP_T532 / r["mean"] if r["mean"] else float("nan")
                    print(f"  with bandpass: {b['mean']:.5f} mW -> 532 nm fraction "
                          f"= {ratio:.3f}" + ("" if abs(ratio - 1) < 0.03 else
                                              "   <-- INFRARED present?"))
                    out.row(pos, cur, "bp532", b["mean"], b["std"], b["slope"],
                            b["n"], tec, 0.0)
                    pause("  Remove the bandpass filter")
    except (Stop, KeyboardInterrupt):
        print("\nStopped -- rows so far are saved.")
    finally:
        out.close()
        pm.close()
    print(f"\nSaved {path}\nNext: cal1_power_vs_current.py, then plot_cal1_power.py")


if __name__ == "__main__":
    main()
