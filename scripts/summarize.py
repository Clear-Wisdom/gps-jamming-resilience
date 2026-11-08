"""Summarize a GPS-jamming flight from its ArduPilot DataFlash log (.BIN).

Errors are measured against the true position SITL logs in SIM messages.
Writes summary.txt and data.csv to the current directory.

    ../ardupilot/.venv/bin/python scripts/summarize.py flight.BIN
"""
import csv
import sys

from pymavlink import mavutil
from pymavlink.mavextra import distance_lat_lon

FIELDS = ["t_s", "jammed", "mode", "rel_alt_m", "gps_fix", "gps_sats", "est_err_m", "gps_err_m"]


def read(path):
    log = mavutil.mavlink_connection(path)
    rows, events, gps_err, gps_fix = [], [], [], []
    sim = gps = home = None
    jam, jam_t, t0 = False, None, None
    while (m := log.recv_match(type=["SIM", "GPS", "POS", "MODE", "MSG", "PARM"])) is not None:
        t0 = m.TimeUS / 1e6 if t0 is None else t0
        t = m.TimeUS / 1e6 - t0
        kind = m.get_type()
        if kind == "SIM":
            sim = m
            home = home or m  # logging starts at arming, on the take-off point
        elif kind == "PARM" and m.Name == "SIM_GPS1_JAM" and bool(m.Value) != jam:
            jam = bool(m.Value)  # PARM rows repeat; only act on changes
            jam_t = t if jam and jam_t is None else jam_t
            events.append((t, f"SIM_GPS1_JAM = {m.Value:g}"))
        elif kind == "MODE":
            events.append((t, f"mode → {log.flightmode}"))
        elif kind == "MSG":
            events.append((t, m.Message))
        elif kind == "GPS" and m.I == 0 and sim:
            gps = m
            if jam:
                gps_err.append(distance_lat_lon(sim.Lat, sim.Lng, m.Lat, m.Lng))
                gps_fix.append(m.Status >= 3)
        elif kind == "POS" and sim and gps:
            rows.append({
                "t_s": round(t, 2),
                "jammed": int(jam),
                "mode": log.flightmode,
                "rel_alt_m": round(m.RelHomeAlt, 1),
                "gps_fix": gps.Status,
                "gps_sats": gps.NSats,
                "est_err_m": round(distance_lat_lon(sim.Lat, sim.Lng, m.Lat, m.Lng), 1),
                "gps_err_m": round(distance_lat_lon(sim.Lat, sim.Lng, gps.Lat, gps.Lng), 1),
            })
    landed_from_home = distance_lat_lon(home.Lat, home.Lng, sim.Lat, sim.Lng)
    return rows, events, jam_t, gps_err, gps_fix, landed_from_home


def rtl_outcome(after):
    modes = [(dt, e) for dt, e in after if e.startswith("mode →")]
    i = next((i for i, (_, e) in enumerate(modes) if e == "mode → RTL"), None)
    if i is None:
        return "refused" if any("RTL failed" in e for _, e in after) else "not attempted"
    if i + 1 < len(modes):
        return f"accepted, then {modes[i + 1][1]} after {modes[i + 1][0] - modes[i][0]:.1f} s"
    return "accepted"


def metrics(path):
    """Per-flight metrics plus the rows and post-jam events they came from."""
    rows, events, jam_t, gps_err, gps_fix, landed_from_home = read(path)
    if jam_t is None:
        sys.exit(f"{path}: no SIM_GPS1_JAM=1 found")
    # Commands sent right after the jam can be logged just before its PARM row.
    after = [(t - jam_t, e) for t, e in events if t > jam_t - 1 and not e.startswith("SIM_GPS1_JAM = 1")]
    # The scripts only command RTL after jamming, so any other mode change is a failsafe.
    failsafe = next(((dt, e) for dt, e in after if e.startswith("mode →") and e != "mode → RTL"),
                    (None, None))
    return {
        "jam_t_s": jam_t,
        "jam_alt_m": min(rows, key=lambda r: abs(r["t_s"] - jam_t))["rel_alt_m"],
        "gps_err_max_m": max(gps_err),
        "ekf_err_max_m": max(r["est_err_m"] for r in rows if r["jammed"]),
        "ekf_err_pre_max_m": max(r["est_err_m"] for r in rows if r["t_s"] < jam_t),
        "gps_fix_ratio": sum(gps_fix) / len(gps_fix),
        "gps_samples": len(gps_fix),
        "failsafe_s": failsafe[0],
        "failsafe_mode": failsafe[1].removeprefix("mode → ") if failsafe[1] else None,
        "rtl": rtl_outcome(after),
        "ekf_err_end_m": rows[-1]["est_err_m"],
        "landed_from_home_m": landed_from_home,
    }, rows, after


def summarize(m):
    lines = [
        ("Jamming started", f"t={m['jam_t_s']:.1f} s", f"at {m['jam_alt_m']:.1f} m"),
        ("Max GPS-reported error", f"{m['gps_err_max_m']:,.1f} m", ""),
        ("Max EKF error", f"{m['ekf_err_max_m']:,.1f} m", f"pre-jam {m['ekf_err_pre_max_m']:.1f} m"),
        ("GPS 3D fix while jammed", f"{m['gps_fix_ratio']:.0%}", f"of {m['gps_samples']} GPS samples"),
        ("Time to failsafe", f"{m['failsafe_s']:.1f} s" if m["failsafe_mode"] else "none",
         f"mode → {m['failsafe_mode']}" if m["failsafe_mode"] else ""),
        ("RTL", m["rtl"], ""),
        ("EKF error at end", f"{m['ekf_err_end_m']:,.1f} m", ""),
        ("Landed from home", f"{m['landed_from_home_m']:,.1f} m", "true position"),
    ]
    return [f"{label:<26}{value:>12}  {note}".rstrip() for label, value, note in lines]


def main():
    m, rows, after = metrics(sys.argv[1])
    table = summarize(m)
    after = [f"  t+{dt:6.1f} s  {e}" for dt, e in after]
    print("\n".join(table))
    with open("summary.txt", "w") as f:
        f.write("\n".join(table + ["", "Events after jamming:"] + after) + "\n")
    with open("data.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
