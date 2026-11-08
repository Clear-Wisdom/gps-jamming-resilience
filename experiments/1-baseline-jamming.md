# 1. Baseline: GPS jamming without fallback

**Location:** Yeonpyeong Island, West Sea (37.665, 125.699) · **Runs:** 10

## Goal

What happens to the position estimate and failsafes when GPS is jammed mid-flight, with no alternative position source?

## Setup

- ArduCopter SITL, default copter params, GPS jamming via `SIM_GPS1_JAM=1`
- Flight: [`scripts/1-baseline-jamming.py`](../scripts/1-baseline-jamming.py) · per-run summary: [`scripts/summarize.py`](../scripts/summarize.py) · statistics: [`scripts/aggregate.py`](../scripts/aggregate.py)
- Raw logs and per-run results: [`results/1-baseline-jamming/run-01`](../results/1-baseline-jamming/run-01) … `run-10` (`flight.BIN`, `summary.txt`, `data.csv`)
- Statistics: [`results/1-baseline-jamming/summary.txt`](../results/1-baseline-jamming/summary.txt), [`runs.csv`](../results/1-baseline-jamming/runs.csv)

SITL's random generator has a fixed seed, so identical runs repeat exactly. Each run therefore starts jamming at a different time: run *k* hovers 9 + *k* seconds (10–19 s) first.

## Steps

1. Take off to 20 m in GUIDED mode and hover 10–19 s.
2. Enable jamming.
3. When a failsafe takes over, request RTL once.
4. Stop when the vehicle disarms or after 60 s.

All numbers are computed from `flight.BIN`, measured against the true position SITL logs in `SIM` messages.

## Result

| Metric | Min | Median | Max |
|---|---|---|---|
| Max GPS-reported position error | 431.0 m | 1,121.0 m | 1,989.5 m |
| Max EKF position error | 94.7 m | 312.8 m | 1,855.9 m |
| GPS still reporting 3D fix while jammed | 61% | 65% | 70% |
| Time from jamming to failsafe | 4.4 s | 5.3 s | 13.1 s |
| EKF position error at landing | 94.7 m | 302.4 m | 1,855.9 m |
| Landing point from take-off point (true) | 0.8 m | 13.0 m | 70.4 m |

| Outcome | Runs |
|---|---|
| GPS error over 1 km | 9 / 10 |
| EKF failsafe switched to LAND | 10 / 10 |
| RTL refused ("requires position") | 10 / 10 |

Before jamming, EKF error was below 0.1 m in every run.

## Notes

- **Consistent across all runs:** the receiver kept reporting a 3D fix most of the time while its position was hundreds of meters to 2 km off, so the fix status alone does not reveal jamming. Every run ended in LAND with RTL unavailable: the vehicle cannot return home.
- LAND descends roughly where the vehicle is, so it physically lands near the take-off point (median 13 m) even though its own position estimate is off by hundreds of meters. It just cannot fly anywhere on purpose.
- **Varies widely:** error size and time to failsafe depend on the jamming pattern. SITL's jamming is a simple random model, not a physical one, so the meter values describe this model rather than real-world jamming.
- Runs are not fully independent: run-01 and run-10 produced nearly identical results.
- Jamming starts above the island, not over open sea.
- Next: radio beacons as a fallback position source.
