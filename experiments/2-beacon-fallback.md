# 2. Beacon fallback

**Location:** Yeonpyeong Island, West Sea (37.665, 125.699) · **Runs:** 10 per condition, paired with experiment 1

## Goal

With radio beacons as a fallback position source, can the drone keep an accurate position and return home (RTL) under GPS jamming? Does it matter when the switch happens?

## Setup

- Same flight and jamming as [experiment 1](1-baseline-jamming.md), including the same 10 jamming start times (hover 10–19 s), so run-*k* here pairs with run-*k* there.
- Beacons: [`params/2-beacon-fallback.parm`](../params/2-beacon-fallback.parm). SITL places 4 beacons in a 10 m × 20 m rectangle around the take-off point. EKF source set 1 = GPS, set 2 = beacon position + baro height + compass yaw, no horizontal velocity source (beacons cannot provide one).
- Flight: [`scripts/2-beacon-fallback.py`](../scripts/2-beacon-fallback.py) `<hover_s> onset|failsafe`. After switching to set 2 (`MAV_CMD_SET_EKF_SOURCE_SET`), RTL is requested every 2 s until accepted.
- Two conditions:
  - **onset**: switch the moment jamming starts (instant detection).
  - **failsafe**: switch when ArduPilot's EKF failsafe fires (ArduPilot's own, later detection).
- Raw logs and results: [`results/2-beacon-fallback/onset/`](../results/2-beacon-fallback/onset/) and [`failsafe/`](../results/2-beacon-fallback/failsafe/), each with `run-01` … `run-10`, `summary.txt`, `runs.csv`.
- Both conditions side by side: [`results/2-beacon-fallback/summary.txt`](../results/2-beacon-fallback/summary.txt), all 20 runs in [`runs.csv`](../results/2-beacon-fallback/runs.csv).

## Result

| Metric (median, min–max) | No fallback (exp. 1) | Beacons at failsafe | Beacons at onset |
|---|---|---|---|
| Max EKF position error | 312.8 m (94.7–1,855.9) | 2.2 m (1.1–103.0) | 1.6 m (1.6–1.7) |
| EKF error at landing | 302.4 m (94.7–1,855.9) | 1.8 m (1.0–103.0) | 1.1 m (1.0–1.1) |
| Landing point from take-off point (true) | 13.0 m (0.8–70.4) | 4.7 m (1.7–5.6) | 1.1 m (1.1–1.1) |

| Outcome | No fallback | At failsafe | At onset |
|---|---|---|---|
| EKF failsafe fired | 10 / 10 | 10 / 10 | 0 / 10 |
| RTL accepted, returned home | 0 / 10 | 3 / 10 | 10 / 10 |
| RTL refused ("requires position") | 10 / 10 | 7 / 10 | 0 / 10 |

## Why RTL is refused after a late switch

Beacons restore an accurate position in both conditions, yet after a late switch RTL was refused in 7 of 10 runs. The cause is in ArduPilot's EKF3:

1. While GPS is jammed, the EKF's velocity test ratio (`XKF4.SV`) climbs far above the failsafe threshold.
2. The ratio is only recomputed when GPS velocity is fused ([`AP_NavEKF3_PosVelFusion.cpp:563, 961, 982`](https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_NavEKF3/AP_NavEKF3_PosVelFusion.cpp)). Source set 2 has no velocity source, so after the switch the last jammed value stays frozen.
3. Copter's EKF failsafe reads that frozen value (`AP_NavEKF3_Outputs.cpp:486`, `ArduCopter/ekf_check.cpp`), never clears, and `position_ok()` stays false while it is set (`ArduCopter/system.cpp:218`), so RTL is refused.

The frozen value at the moment of the switch decides every run:

| failsafe run | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| `XKF4.SV` at switch | 112.25 | 66.75 | 0.02 | 75.74 | 0.03 | 86.29 | 83.45 | 43.15 | 75.16 | 0.02 |
| RTL | refused | refused | **accepted** | refused | **accepted** | refused | refused | refused | refused | **accepted** |

This looks like an unhandled edge case rather than intended behavior: EKF3 resets these test ratios when aiding stops entirely (`AP_NavEKF3_Control.cpp:425`, "to avoid false failing bad fusion tests") but not on a source-set change, and with beacons used from boot the same ratio stays at 0. No matching ArduPilot issue was found. Checked on master (`a485091ab4`) only.

## Notes

- **Detection timing decides recovery.** Switching at onset avoided the failsafe entirely and RTL landed within 1.1 m of home in every run. This makes fast, reliable jamming detection the key problem, not the fallback source itself.
- **Best case for beacons:** SITL beacons have no range limit or ranging noise, and the drone hovers inside the beacon field. Real UWB beacons reach only tens of meters, so this only applies near a beacon-equipped base such as an island landing pad.
- The drone never leaves the take-off point before jamming, so RTL only has to land in place. Flying out over the sea first would test a real return.
