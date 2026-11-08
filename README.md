# GPS Jamming Resilience

How does a drone behave when GPS is jammed over the West Sea of Korea, and can an alternative position source keep it on track? Experiments run on ArduPilot SITL.

## Setup

```bash
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python pymavlink MAVProxy empy==3.3.4 lxml pexpect wxPython
```

On recent Xcode (no `-ld_classic`), replace `-ld_classic` with `-no_fixup_chains` in `Tools/ardupilotwaf/boards.py` before building.

## How to start

From the `ardupilot/` directory:

```bash
export PATH="$PWD/.venv/bin:$PWD/Tools/autotest:$PATH"
sim_vehicle.py -v ArduCopter --console --map --custom-location=37.6650,125.6990,0,0
```

Start location: Yeonpyeong Island, West Sea (lat, lon, alt m, heading °).

## Run an experiment

Scripts write into the current directory; move the outputs into `results/<experiment>/run-XX/` afterwards.

```bash
PY=~/Desktop/skaigen/ardupilot/.venv/bin/python
mkdir -p /tmp/run && cd /tmp/run
$PY <repo>/scripts/1-baseline-jamming.py 10     # fly; hover 10 s before jamming -> logs/00000001.BIN
# or: $PY <repo>/scripts/2-beacon-fallback.py 10 onset   (onset | failsafe)
# parallel runs: give each its own SITL_INSTANCE=1,2,... (TCP 5760 + 10 * instance)
$PY <repo>/scripts/summarize.py logs/00000001.BIN  # -> summary.txt, data.csv
```

Statistics over runs, from `results/<experiment>/`:

```bash
$PY ../../scripts/aggregate.py run-*/flight.BIN    # -> summary.txt, runs.csv
```

## Experiments

| # | Experiment | Result (10 runs) |
|---|---|---|
| 1 | [Baseline: GPS jamming without fallback](experiments/1-baseline-jamming.md) | 10/10 failsafe LAND (median 5.3 s), 10/10 RTL refused, GPS error median 1.1 km |
| 2 | [Beacon fallback](experiments/2-beacon-fallback.md) | EKF error ~2 m with beacons; RTL home 10/10 if switched at jamming onset, 3/10 if switched at failsafe (stale EKF velocity test ratio) |
