"""
Step 1a: LOSS BUDGET (do this once).

Measures the 532 nm power at points along the free-space excitation path, at
a few laser currents:

    laser_output -> before_objective -> after_objective

so plot_cal1_power.py can give the transmission of each stage and the
objective transmission T_obj (used to turn the before-objective sweep into
power at the sample). Once a fibre is in the path, add "after_fibre" to
POSITIONS (between laser_output and before_objective) to get its coupling.

INFRARED. The S120C is a silicon sensor: it also sees the 808 nm pump and
1064 nm leakage of the DPSS. Here the 532 nm bandpass filter stays IN the beam
for the whole run (the setup is not touched while it runs), so every reading
is already 532 nm only and no separate bandpass reading is taken. The rows
are marked filter = "bp532_fixed"; plot_cal1_power.py then applies no
infrared correction (f532 = 1).

  ** SAFETY **
  * after_objective: put the sensor 2-3 mm PAST the focus, never at the focus.
    The focused full power can damage the S120C surface. Past the focus the
    cone widens fast (about 1.7x the distance for NA 0.65, 2.3x for NA 0.75),
    so by ~5 mm it overfills the 9.5 mm aperture; 2-3 mm gives a spot a few mm
    across.
  * The S120C reads up to 50 mW. Check the laser output is below that first.
  * Goggles on.

The PM101A is read through its analog output on Red Pitaya IN2 (see
cal0_check_power_meter.py): FIXED range, 532 nm, for the whole run.

Procedure (the script prompts each step):
  At the first position: zero, then reuse the saved mW/V factor or measure
  it at the top current against Optical Power Monitor. For each position:
  place the sensor, block the beam and zero, then for each current in
  CURRENTS_MA set the LDC200C, wait for the reading to settle, log LOG_S
  seconds.

Output: <data_dir>/calibration/loss_budget_<stamp>.csv
        position,current_mA,filter,P_mW,P_std_mW,slope_mW_per_s,n,tec_C,settle_s,
        V_mean,V_zero          (IN2 volts above zero, and the zero offset)
Next:   cal1_power_vs_current.py, then plot_cal1_power.py

Run on the PC:  python cal1_loss_budget.py
"""

from calib_common import (PowerMeter, Stop, TableWriter, ask_current, ask_tec,
                          cal_path, pause, prepare_power_meter, stamp)
import numpy as np

# --- settings ---------------------------------------------------------------
CURRENTS_MA = np.arange(0, 280, 20).tolist()   # "a few powers" above threshold
I_MAX_MA = 280.0                      # never ask for more (set to your LDC200C limit)
LOG_S = 20.0                          # logging time per reading
SETTLE_MIN_S, SETTLE_MAX_S = 10.0, 180.0
WAVELENGTH_NM = 532.0                 # set on the PM101A; recorded only

# POSITIONS = ["before_objective", "after_objective"]
POSITIONS = ["after_objective"]

# with a fibre: ["laser_output", "after_fibre", "before_objective", "after_objective"]
FILTER = "bp532_fixed"  # the 532 nm bandpass stays in the beam for the whole run

WHERE = {
    "laser_output": "right after the laser head (before any optics)",
    "after_fibre": "right after the fibre output collimator",
    "before_objective": "in the collimated beam just before the objective "
                        "(after the dichroic)",
    "after_objective": "2-3 mm PAST the focus (NOT at the focus)",
}


def main():
    path = cal_path(f"loss_budget_{stamp()}.csv")
    pm = PowerMeter()
    out = None
    print(f"\nLOSS BUDGET -> {path}")
    print(f"Positions: {', '.join(POSITIONS)};  currents: {CURRENTS_MA} mA\n")

    try:
        for pos in POSITIONS:
            print("=" * 72)
            pause(f"POSITION '{pos}': put the S120C {WHERE[pos]}")
            if out is None:
                prepare_power_meter(pm, max(CURRENTS_MA), I_MAX_MA, SETTLE_MIN_S,
                                    SETTLE_MAX_S)
                out = TableWriter(path, ["position", "current_mA", "filter", "P_mW",
                                         "P_std_mW", "slope_mW_per_s", "n", "tec_C",
                                         "settle_s", "V_mean", "V_zero"],
                                  meta=dict(experiment="loss_budget",
                                            wavelength_nm=WAVELENGTH_NM,
                                            bandpass="always in", log_s=LOG_S,
                                            **pm.meta()))
            else:
                pm.zero()
            for planned in CURRENTS_MA:
                cur = ask_current(planned, I_MAX_MA)
                if cur is None:
                    continue
                settle_s = pm.settle(SETTLE_MIN_S, SETTLE_MAX_S)
                tec = ask_tec()
                r = pm.log(LOG_S)
                print(f"  {pos} @ {cur:.2f} mA: {r['mean']:.5f} mW")
                out.row(pos, cur, FILTER, r["mean"], r["std"], r["slope"], r["n"],
                        tec, settle_s, r["v"].mean(), pm.v_zero)
    except (Stop, KeyboardInterrupt):
        print("\nStopped -- rows so far are saved.")
    finally:
        if out is not None:
            out.close()
        pm.close()
    print(f"\nSaved {path}\nNext: cal1_power_vs_current.py, then plot_cal1_power.py")


if __name__ == "__main__":
    main()
