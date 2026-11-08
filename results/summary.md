# Results summary

All flights run on ArduPilot SITL over Yeonpyeong Island. Each one hovers at 20 m, then GPS is jammed (`SIM_GPS1_JAM=1`). Each condition has 10 runs with jamming start times paired across experiments. Medians are given with the min–max range in parentheses.

## Main finding

The drone returned home only when it switched to beacons within 3 s of jamming onset. Simple GPS receiver checks noticed jamming in 0.2–1.6 s. ArduPilot's own EKF-based detection took 3.6 s or more, which was too late.

| Beacon switch after jamming onset | RTL home | EKF failsafe fired | Landing point from take-off point |
|---|---|---|---|
| No fallback (exp. 1) | 0 / 10 | 10 / 10 | 13.0 m (0.8–70.4) |
| 0 s, at onset (exp. 2) | 10 / 10 | 0 / 10 | 1.1 m (1.1–1.1) |
| 1 s (exp. 3) | 10 / 10 | 0 / 10 | 1.3 m (1.2–1.3) |
| 2 s (exp. 3) | 10 / 10 | 0 / 10 | 1.5 m (1.4–1.5) |
| 3 s (exp. 3) | 10 / 10 | 0 / 10 | 1.1 m (1.1–1.2) |
| 4 s (exp. 3) | 5 / 10 | 5 / 10 | 3.1 m (0.3–5.6) |
| At EKF failsafe, 4.5–13.1 s (exp. 2) | 3 / 10 | 10 / 10 | 4.7 m (1.7–5.6) |

- In the five failed 4 s runs, RTL started, but the EKF failsafe fired 0.4–0.5 s later and switched the drone to LAND.
- The limit between 3 s and 4 s matches the time when the EKF test ratio crosses 1 (3.5–4.4 s after onset). After that, the failsafe either fires or blocks RTL. See [experiment 2](../experiments/2-beacon-fallback.md#why-rtl-is-refused-after-a-late-switch).

## Detection delay

[`scripts/3-detection-delay.py`](../scripts/3-detection-delay.py) replays simple detectors over the 10 experiment 1 logs. Each detector uses only signals that a real drone has on board.

| Detector | Detected | Delay after onset | False alarms before jamming |
|---|---|---|---|
| GPS fix lost (Status < 3) | 10 / 10 | 0.2 s (0.1–0.2) | 0 |
| Satellites < 6 | 10 / 10 | 0.2 s (0.1–0.2) | 0 |
| Reported accuracy > 10 m | 10 / 10 | 1.6 s (1.5–1.6) | 0 |
| GPS speed > 30 m/s | 10 / 10 | 1.6 s (1.5–1.6) | 0 |
| EKF test ratio > 1 (close to ArduPilot's check) | 10 / 10 | 3.6 s (3.5–4.4) | 0 |

## Caveats

- SITL jamming drops the receiver's fix almost instantly, so receiver checks look easier here than in reality. A spoofer that keeps a valid fix would defeat the 0.2 s detectors.
- The false-alarm check covers only 589 s of clean simulated flight with GPS lock. That is too short to estimate a real false-alarm rate.
- SITL beacons have no range limit or noise, and the drone never leaves the take-off point.

## Raw data

| Experiment | Flights | Results |
|---|---|---|
| 1. Baseline jamming | 10 | [`1-baseline-jamming/`](1-baseline-jamming/) |
| 2. Beacon fallback at onset and at failsafe | 20 | [`2-beacon-fallback/`](2-beacon-fallback/) |
| 3. Beacon switch 1–4 s after onset | 40 | [`3-detection-delay/`](3-detection-delay/) ([`summary.txt`](3-detection-delay/summary.txt), [`detection.txt`](3-detection-delay/detection.txt)) |

Each `run-XX/` folder holds the raw log `flight.BIN`, a per-flight `summary.txt`, and `data.csv`.
