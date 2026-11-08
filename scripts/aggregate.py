"""Aggregate several GPS-jamming flights, computed from their .BIN logs.

Writes summary.txt (statistics) and runs.csv (one row per flight) to the
current directory. Logs from several condition folders are summarized per
condition (e.g. onset/run-*/flight.BIN failsafe/run-*/flight.BIN).

    ../../../ardupilot/.venv/bin/python ../../scripts/aggregate.py run-*/flight.BIN
"""
import csv
import sys
from pathlib import Path
from statistics import median

from summarize import metrics

FIELDS = ["run", "jam_t_s", "jam_alt_m", "gps_err_max_m", "ekf_err_max_m", "ekf_err_pre_max_m",
          "gps_fix_ratio", "gps_samples", "failsafe_s", "failsafe_mode", "rtl",
          "ekf_err_end_m", "landed_from_home_m"]


def spread(values, fmt):
    if not values:
        return f"{'—':>10}  {'—':>10}  {'—':>10}"
    return f"{fmt(min(values)):>10}  {fmt(median(values)):>10}  {fmt(max(values)):>10}"


def block(runs):
    n = len(runs)
    meters = lambda v: f"{v:,.1f} m"
    secs = lambda v: f"{v:.1f} s"
    pct = lambda v: f"{v:.0%}"
    failsafes = [r["failsafe_s"] for r in runs if r["failsafe_mode"]]
    return [
        f"{n} flights: {', '.join(Path(r['run']).name for r in runs)}",
        "",
        f"{'':<26}{'min':>10}  {'median':>10}  {'max':>10}",
        f"{'Max GPS-reported error':<26}{spread([r['gps_err_max_m'] for r in runs], meters)}",
        f"{'Max EKF error':<26}{spread([r['ekf_err_max_m'] for r in runs], meters)}",
        f"{'Pre-jam max EKF error':<26}{spread([r['ekf_err_pre_max_m'] for r in runs], meters)}",
        f"{'GPS 3D fix while jammed':<26}{spread([r['gps_fix_ratio'] for r in runs], pct)}",
        f"{'Time to failsafe':<26}{spread(failsafes, secs)}",
        f"{'EKF error at end':<26}{spread([r['ekf_err_end_m'] for r in runs], meters)}",
        f"{'Landed from home':<26}{spread([r['landed_from_home_m'] for r in runs], meters)}",
        "",
        f"{'GPS error over 1 km':<26}{sum(r['gps_err_max_m'] > 1000 for r in runs):>3} / {n}",
        f"{'EKF failsafe fired':<26}{len(failsafes):>3} / {n}",
        f"{'Failsafe switched to LAND':<26}{sum(r['failsafe_mode'] == 'LAND' for r in runs):>3} / {n}",
        f"{'RTL refused':<26}{sum(r['rtl'] == 'refused' for r in runs):>3} / {n}",
        f"{'RTL accepted and held':<26}{sum(r['rtl'] == 'accepted' for r in runs):>3} / {n}",
    ]


def main():
    runs = [{"run": Path(p).parent.as_posix(), **metrics(p)[0]} for p in sys.argv[1:]]
    groups = {}
    for r in runs:
        groups.setdefault(Path(r["run"]).parent.as_posix(), []).append(r)
    if len(groups) == 1:
        lines = block(runs)
    else:
        lines = [line for name, group in groups.items() for line in [f"== {name}", *block(group), ""]][:-1]
    print("\n".join(lines))
    Path("summary.txt").write_text("\n".join(lines) + "\n")
    with open("runs.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in runs:
            writer.writerow({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()})


if __name__ == "__main__":
    main()
