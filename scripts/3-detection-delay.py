"""Experiment 3: how fast can simple detectors notice GPS jamming?

The flights for the delay sweep come from scripts/2-beacon-fallback.py with
a switch delay in seconds. This script replays simple jamming detectors over
existing flight logs (.BIN).

Each detector only uses signals a real drone has on board (GPS receiver
status, accuracy, speed, EKF test ratios). For each flight it reports the
delay from jamming onset to the first alarm, and false alarms before jamming.
Writes detection.txt and detection.csv to the current directory.

    ../../../ardupilot/.venv/bin/python ../../scripts/3-detection-delay.py ../1-baseline-jamming/run-*/flight.BIN
"""
import csv
import sys
from pathlib import Path
from statistics import median

from pymavlink import mavutil

MAX_SPEED_MS = 30  # far above this copter's top speed

DETECTORS = {
    "GPS fix lost (Status < 3)": ("GPS", lambda m: m.Status < 3),
    "Satellites < 6": ("GPS", lambda m: m.NSats < 6),
    "Reported accuracy > 10 m": ("GPA", lambda m: m.HAcc > 10),
    f"GPS speed > {MAX_SPEED_MS} m/s": ("GPS", lambda m: m.Spd > MAX_SPEED_MS),
    "EKF test ratio > 1 (SV or SP)": ("XKF4", lambda m: max(m.SV, m.SP) > 1),
}


def replay(path):
    """Per detector: delay after jam (None if never) and alarms after GPS lock but before jam."""
    log = mavutil.mavlink_connection(path)
    t0 = jam_t = locked_t = None
    delay = dict.fromkeys(DETECTORS)
    false_alarms = dict.fromkeys(DETECTORS, 0)
    while (m := log.recv_match(type=["GPS", "GPA", "XKF4", "PARM"])) is not None:
        t0 = m.TimeUS / 1e6 if t0 is None else t0
        t = m.TimeUS / 1e6 - t0
        kind = m.get_type()
        if kind == "PARM":
            if m.Name == "SIM_GPS1_JAM" and m.Value and jam_t is None:
                jam_t = t
            continue
        if getattr(m, "I", 0) or getattr(m, "C", 0):  # first GPS, first EKF core only
            continue
        if kind == "GPS" and m.Status >= 3 and locked_t is None:
            locked_t = t
        if locked_t is None:  # still acquiring GPS on the ground
            continue
        for name, (msg, fires) in DETECTORS.items():
            if msg != kind or not fires(m):
                continue
            if jam_t is None:
                false_alarms[name] += 1
            elif delay[name] is None:
                delay[name] = t - jam_t
    return delay, false_alarms, jam_t - locked_t


def main():
    flights = [(Path(p).parent.name, *replay(p)) for p in sys.argv[1:]]
    pre_s = sum(clean_s for *_, clean_s in flights)
    lines = [f"{len(flights)} flights, {pre_s:.0f} s with GPS lock before jamming", "",
             f"{'Detector':<32}{'detected':>9}  {'delay min':>9}  {'median':>7}  {'max':>6}  {'false alarms':>12}"]
    for name in DETECTORS:
        delays = [d[name] for _, d, _, _ in flights if d[name] is not None]
        fa = sum(f[name] for _, _, f, _ in flights)
        spread = (f"{min(delays):>8.1f}s  {median(delays):>6.1f}s  {max(delays):>5.1f}s"
                  if delays else f"{'—':>9}  {'—':>7}  {'—':>6}")
        lines.append(f"{name:<32}{len(delays):>5} / {len(flights)}  {spread}  {fa:>12}")
    print("\n".join(lines))
    Path("detection.txt").write_text("\n".join(lines) + "\n")
    with open("detection.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "detector", "delay_s", "false_alarms"])
        for run, d, fa, _ in flights:
            for name in DETECTORS:
                w.writerow([run, name, None if d[name] is None else round(d[name], 2), fa[name]])


if __name__ == "__main__":
    main()
