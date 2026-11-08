"""Experiment 1: GPS jamming without fallback.

Takes off, hovers, jams GPS and requests RTL once a failsafe takes over.
SITL writes its flight log to logs/ in the current directory; summarize it
with scripts/summarize.py.

    ../ardupilot/.venv/bin/python scripts/1-baseline-jamming.py [hover_s]

hover_s (default 10) shifts when jamming starts. SITL's random generator has
a fixed seed, so identical runs repeat exactly; a different start time gives
a different jamming pattern.
"""
import sys
import time

from sim import HOVER_ALT_M, KEY_TEXTS, event, fly

WATCH_S = 60


def watch(m):
    """Print key events live; request RTL once a failsafe takes over."""
    start, mode, rtl_requested = time.time(), m.flightmode, False
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
        if mode != "GUIDED" and not rtl_requested:
            rtl_requested = True
            event(dt, "RTL requested")
            m.set_mode("RTL")
        if not m.motors_armed():
            return


if __name__ == "__main__":
    hover_s = float(sys.argv[1]) if len(sys.argv) > 1 else 10
    fly("Experiment 1 · GPS jamming without fallback",
        f"take off to {HOVER_ALT_M} m, hover {hover_s:g} s, jam GPS, watch up to {WATCH_S} s",
        hover_s, watch)
