"""Experiment 2: radio beacons as a fallback position source.

Same flight as experiment 1, with beacons set up as EKF source set 2
(params/2-beacon-fallback.parm). After the switch, RTL is requested every
2 s until accepted. When to switch:
  onset     as soon as jamming starts (instant detection)
  failsafe  when the EKF failsafe fires (ArduPilot's own late detection)
  <s>       s seconds after jamming starts, or at failsafe if that comes first

SITL writes its flight log to logs/ in the current directory; summarize it
with scripts/summarize.py.

    ../ardupilot/.venv/bin/python scripts/2-beacon-fallback.py [hover_s] [onset|failsafe|<s>]
"""
import sys
import time
from pathlib import Path

from pymavlink import mavutil

from sim import HOVER_ALT_M, KEY_TEXTS, event, fly

PARAMS = Path(__file__).resolve().parents[1] / "params" / "2-beacon-fallback.parm"
WATCH_S = 90
BEACON_SOURCE_SET = 2
RTL_RETRY_S = 2


def recover(m, delay):
    """Switch to beacons delay s after jamming or at failsafe, then request RTL until accepted."""
    start, mode = time.time(), m.flightmode
    switched = False
    last_rtl = None
    while time.time() - start < WATCH_S:
        msg = m.recv_match(blocking=True, timeout=1)
        if msg is None:
            continue
        dt = time.time() - start
        if msg.get_type() == "STATUSTEXT" and any(k in msg.text for k in KEY_TEXTS):
            event(dt, msg.text)
        if m.flightmode != mode:
            event(dt, f"mode {mode} → {m.flightmode}")
            mode = m.flightmode
        if not switched and (dt >= delay or mode != "GUIDED"):
            switched = True
            event(dt, "EKF source → beacons")
            m.mav.command_long_send(m.target_system, m.target_component,
                                    mavutil.mavlink.MAV_CMD_SET_EKF_SOURCE_SET,
                                    0, BEACON_SOURCE_SET, 0, 0, 0, 0, 0, 0)
        if switched and mode != "RTL" and (last_rtl is None or dt - last_rtl > RTL_RETRY_S):
            last_rtl = dt
            event(dt, "RTL requested")
            m.set_mode("RTL")
        if not m.motors_armed():
            return


if __name__ == "__main__":
    hover_s = float(sys.argv[1]) if len(sys.argv) > 1 else 10
    trigger = sys.argv[2] if len(sys.argv) > 2 else "failsafe"
    delays = {"onset": 0, "failsafe": float("inf")}
    try:
        delay = delays[trigger] if trigger in delays else float(trigger)
    except ValueError:
        sys.exit("trigger must be onset, failsafe or seconds after jamming")
    fly(f"Experiment 2 · Beacon fallback ({trigger})",
        f"take off to {HOVER_ALT_M} m, hover {hover_s:g} s, jam GPS, switch to beacons at {trigger}, RTL",
        hover_s, lambda m: recover(m, delay), extra_defaults=[PARAMS])
