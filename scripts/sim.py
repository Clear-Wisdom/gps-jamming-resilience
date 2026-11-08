"""Shared SITL flight helpers for the experiment scripts.

Starts a headless ArduCopter SITL on instance $SITL_INSTANCE (default 1,
TCP 5760 + 10 * instance) so a running sim_vehicle.py on instance 0 is left
alone; give parallel runs different instances. SITL writes its files (logs/,
eeprom.bin, sitl.log) to the current directory.
"""
import contextlib
import io
import os
import subprocess
import sys
import time
from pathlib import Path

from pymavlink import mavutil

AP = Path(os.environ.get("ARDUPILOT", Path(__file__).resolve().parents[2] / "ardupilot"))
HOME = "37.6650,125.6990,0,0"
HOME_NAME = "Yeonpyeong Island, West Sea"
INSTANCE = int(os.environ.get("SITL_INSTANCE", 1))
HOVER_ALT_M = 20
STEPS = 5
KEY_TEXTS = ("Failsafe:", "RTL", "Disarming", "Hit ground", "Glitch")

COLOR = sys.stdout.isatty()


def style(text, code):
    return f"\033[{code}m{text}\033[0m" if COLOR else text


def bold(t): return style(t, "1")
def dim(t): return style(t, "2")
def red(t): return style(t, "31")
def green(t): return style(t, "32")
def yellow(t): return style(t, "33")


def header(title, plan):
    print("\n" + bold(f"━━ {title} " + "━" * max(3, 58 - len(title))))
    print(f"  {dim('Location')}  {HOME_NAME} ({HOME.split(',')[0]}, {HOME.split(',')[1]})")
    print(f"  {dim('Plan    ')}  {plan}\n")


@contextlib.contextmanager
def step(n, label):
    print(f"  [{n}/{STEPS}] {label:<40}", end="", flush=True)
    start = time.time()
    try:
        yield
    except BaseException:
        print(red("stopped"))
        raise
    print(green(f"done ({time.time() - start:.0f} s)"))


def event(dt, text):
    color = red if "Failsafe" in text or "failed" in text else yellow if "→" in text else dim
    print(f"        {dim(f't+{dt:5.1f} s')}  {color(text)}")


def drain(m, seconds):
    end = time.time() + seconds
    while time.time() < end:
        m.recv_match(blocking=True, timeout=1)


def start_sitl(extra_defaults=()):
    defaults = ",".join(str(p) for p in [AP / "Tools/autotest/default_params/copter.parm", *extra_defaults])
    log = open("sitl.log", "w")
    sitl = subprocess.Popen(
        [AP / "build/sitl/bin/arducopter", "--model", "+", "-w", "-I", str(INSTANCE),
         "--home", HOME, "--defaults", defaults],
        stdout=log, stderr=subprocess.STDOUT)
    with contextlib.redirect_stdout(io.StringIO()):  # hide pymavlink's retry chatter
        m = mavutil.mavlink_connection(f"tcp:127.0.0.1:{5760 + 10 * INSTANCE}", retries=30)
    m.wait_heartbeat(timeout=30)
    m.mav.request_data_stream_send(m.target_system, m.target_component,
                                   mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1)
    return sitl, m


def arm(m):
    end = time.time() + 120
    while not m.motors_armed():
        if time.time() > end:
            raise TimeoutError("arming")
        m.set_mode("GUIDED")
        m.arducopter_arm()
        m.recv_match(type="HEARTBEAT", blocking=True, timeout=2)


def take_off(m):
    m.mav.command_long_send(m.target_system, m.target_component,
                            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                            0, 0, 0, 0, 0, 0, 0, HOVER_ALT_M)
    end = time.time() + 60
    while time.time() < end:
        pos = m.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=1)
        if pos and pos.relative_alt / 1000 > HOVER_ALT_M * 0.95:
            return
    raise TimeoutError("takeoff")


def fly(title, plan, hover_s, after_jam, extra_defaults=()):
    """Start SITL, take off, hover, then hand over to after_jam(m)."""
    header(title, plan)
    sitl = None
    try:
        with step(1, "Starting SITL"):
            sitl, m = start_sitl(extra_defaults)
        with step(2, "Waiting for EKF/GPS (30-60 s)"):
            arm(m)
        with step(3, f"Taking off to {HOVER_ALT_M} m"):
            take_off(m)
        with step(4, f"Hovering {hover_s:g} s before jamming"):
            drain(m, hover_s)
        print(f"  [5/{STEPS}] Jamming on")
        m.param_set_send("SIM_GPS1_JAM", 1)
        after_jam(m)
    except KeyboardInterrupt:
        print(f"\n  {yellow('Interrupted.')}")
    finally:
        if sitl:
            sitl.terminate()
            sitl.wait()
    if Path("logs/LASTLOG.TXT").exists():
        print(f"\n  {dim('Flight log')}  logs/{int(Path('logs/LASTLOG.TXT').read_text()):08d}.BIN\n")
