"""
svchost_helper.py  –  Background desktop automation
PROD toggle : Ctrl+Alt+J   (high beep = ON, low beep+exit = OFF)
TEST toggle : Ctrl+Alt+K   (double beep = ON, single mid beep = OFF)
Failsafe: move mouse to top-left corner to emergency stop
Stealth:  no window, no tray  (test mode writes test_log.txt)
"""

import pyautogui
import keyboard
import winsound
import random
import time
import threading
import os

# ---------------------------------------------------------------------------
# pyautogui global config
# ---------------------------------------------------------------------------
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0          # we manage all sleeps ourselves

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
_running = False
_startup_cooldown = False
_test_running = False
_test_startup_cooldown = False
_stop_event = threading.Event()
_state_lock = threading.Lock()

# In-memory log buffer – no disk writes until the test session ends
_test_log_buffer: list[str] = []

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _var(value: float) -> float:
    """Apply ±25 % random variance to a base duration."""
    return value * random.uniform(0.75, 1.25)


def _screen_bounds():
    """Return (x_min, y_min, x_max, y_max) with 100 px margin."""
    w, h = pyautogui.size()
    m = 100
    return m, m, w - m, h - m


def _sleep(seconds: float) -> bool:
    """
    Interruptible sleep.
    Returns False immediately if stop_event is set, otherwise True after sleeping.
    """
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if _stop_event.is_set():
            return False
        time.sleep(0.20)
    return True


# ---------------------------------------------------------------------------
# Individual actions
# ---------------------------------------------------------------------------

def _mouse_move():
    """Smooth, eased movement to a random on-screen coordinate."""
    x1, y1, x2, y2 = _screen_bounds()
    tx = random.randint(x1, x2)
    ty = random.randint(y1, y2)
    dur = random.uniform(0.20, 1.00)
    pyautogui.moveTo(tx, ty, duration=dur, tween=pyautogui.easeInOutQuad)


def _scroll_burst():
    """
    Three scroll events with randomised 4-10 s gaps.
    Mostly scrolls down (70 %), occasionally up (30 %).
    """
    for i in range(3):
        if i > 0:
            gap = _var(random.uniform(3.0, 12.0))
            if not _sleep(gap):
                return
        amount = random.randint(3, 8)
        direction = -1 if random.random() < 0.70 else 1   # negative = down
        pyautogui.scroll(direction * amount)


def _alt_tab():
    """Simulate a natural Alt+Tab window switch."""
    keyboard.press("alt")
    time.sleep(random.uniform(0.10, 0.30))
    keyboard.press_and_release("tab")
    time.sleep(random.uniform(0.30, 0.80))
    keyboard.release("alt")


def _micro_move():
    """
    2-4 tiny nudges of 5-20 px around the current cursor position,
    mimicking a hand resting loosely on the mouse.
    """
    cx, cy = pyautogui.position()
    w, h = pyautogui.size()
    for _ in range(random.randint(2, 4)):
        dx = random.randint(-20, 20)
        dy = random.randint(-20, 20)
        nx = max(0, min(w - 1, cx + dx))
        ny = max(0, min(h - 1, cy + dy))
        pyautogui.moveTo(nx, ny, duration=random.uniform(0.05, 0.20))
        if not _sleep(random.uniform(0.10, 0.50)):
            return


def _random_click():
    """Left-click at the current cursor position to re-focus a window."""
    pyautogui.click()


def _page_updown():
    """Press Page Down or Page Up at random."""
    key = random.choice(["page down", "page up"])
    keyboard.press_and_release(key)


def _ctrl_home_end():
    """Jump to the top or bottom of the active document."""
    combo = random.choice(["ctrl+home", "ctrl+end"])
    keyboard.press_and_release(combo)


# ---------------------------------------------------------------------------
# Action pool
# ---------------------------------------------------------------------------

_ACTIONS = [
    _mouse_move,
    _scroll_burst,
    _alt_tab,
    _micro_move,
    _random_click,
    _page_updown,
    _ctrl_home_end,
]

# ---------------------------------------------------------------------------
# Test-mode helpers
# ---------------------------------------------------------------------------

def _tlog(msg: str) -> None:
    """Append a timestamped entry to the in-memory buffer."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    _test_log_buffer.append(f"[{ts}]  {msg}")


def _flush_log() -> None:
    """Write the entire buffer to disk in one shot, then clear it."""
    if not _test_log_buffer:
        return
    log_path = os.path.join(
        os.environ.get("TEMP", os.environ.get("TMP", os.path.expanduser("~"))),
        "etw_diag.log",
    )
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(_test_log_buffer) + "\n")
        _test_log_buffer.clear()
    except Exception:
        pass


def _ta_mouse_move() -> str:
    """Test: fast, large mouse movement."""
    x1, y1, x2, y2 = _screen_bounds()
    tx, ty = random.randint(x1, x2), random.randint(y1, y2)
    dur = random.uniform(0.08, 0.35)
    pyautogui.moveTo(tx, ty, duration=dur, tween=pyautogui.easeInOutQuad)
    return f"mouse_move  target=({tx},{ty})  dur={dur:.2f}s"


def _ta_scroll() -> str:
    """Test: aggressive multi-scroll burst."""
    count = random.randint(4, 8)
    direction = -1 if random.random() < 0.70 else 1
    amount = random.randint(8, 20)
    for i in range(count):
        if i > 0 and not _sleep(random.uniform(0.2, 1.0)):
            return f"scroll  count={i}/{count}  dir={'down' if direction<0 else 'up'}  amt={amount}  INTERRUPTED"
        pyautogui.scroll(direction * amount)
    return f"scroll  count={count}  dir={'down' if direction<0 else 'up'}  amt={amount}"


def _ta_alt_tab() -> str:
    """Test: alt+tab switch."""
    keyboard.press("alt")
    time.sleep(random.uniform(0.08, 0.20))
    keyboard.press_and_release("tab")
    time.sleep(random.uniform(0.15, 0.40))
    keyboard.release("alt")
    return "alt_tab"


def _ta_micro_move() -> str:
    """Test: rapid micro-nudges around current cursor."""
    cx, cy = pyautogui.position()
    w, h = pyautogui.size()
    count = random.randint(4, 8)
    for _ in range(count):
        dx, dy = random.randint(-35, 35), random.randint(-35, 35)
        nx = max(0, min(w - 1, cx + dx))
        ny = max(0, min(h - 1, cy + dy))
        pyautogui.moveTo(nx, ny, duration=random.uniform(0.02, 0.12))
        if not _sleep(random.uniform(0.05, 0.20)):
            return f"micro_move  count={count}  INTERRUPTED"
    return f"micro_move  count={count}"


def _ta_click() -> str:
    """Test: click at current position."""
    x, y = pyautogui.position()
    pyautogui.click()
    return f"click  pos=({x},{y})"


def _ta_page_key() -> str:
    """Test: page up/down or ctrl+home/end."""
    key = random.choice(["page down", "page up", "ctrl+home", "ctrl+end"])
    keyboard.press_and_release(key)
    return f"key  {key}"


_TEST_ACTIONS = [
    _ta_mouse_move,
    _ta_scroll,
    _ta_alt_tab,
    _ta_micro_move,
    _ta_click,
    _ta_page_key,
]

# ---------------------------------------------------------------------------
# Main automation loop (runs in its own daemon thread)
# ---------------------------------------------------------------------------

def _automation_loop():
    while not _stop_event.is_set():

        # Check which mode is active (test takes priority)
        with _state_lock:
            test_active = _test_running
            prod_active = _running

        # ── TEST MODE ────────────────────────────────────────────────────
        if test_active:
            global _test_startup_cooldown
            with _state_lock:
                do_cooldown = _test_startup_cooldown
            if do_cooldown:
                _test_startup_cooldown = False
                _tlog("=" * 52)
                _tlog("TEST SESSION STARTED")
                _tlog("=" * 52)
                if not _sleep(3.0):
                    return

            cycle = random.uniform(4.0, 8.0)   # short cycle
            action = random.choice(_TEST_ACTIONS)
            try:
                desc = action()
                _tlog(f"{action.__name__:<20}  {desc}")
            except pyautogui.FailSafeException:
                _tlog("FAILSAFE triggered – emergency stop")
                _stop_event.set()
                return
            except Exception as exc:
                _tlog(f"ERROR  {exc}")

            if not _sleep(cycle):
                return
            continue

        # ── PROD MODE ────────────────────────────────────────────────────
        if not prod_active:
            time.sleep(0.50)
            continue

        # Initial cooldown when first activated
        global _startup_cooldown
        with _state_lock:
            do_cooldown = _startup_cooldown
        if do_cooldown:
            _startup_cooldown = False
            if not _sleep(10.0):
                return

        # Base cycle length with ±20 % variance
        cycle = _var(random.uniform(35.0, 50.0))

        # 30 % chance to skip this cycle (natural inactivity)
        if random.random() < 0.30:
            if not _sleep(cycle):
                return
            continue

        # Pick and execute a random action
        action = random.choice(_ACTIONS)
        try:
            action()
        except pyautogui.FailSafeException:
            # Mouse reached top-left corner – treat as emergency stop
            _stop_event.set()
            return
        except Exception:
            pass  # silently swallow; no logging, no disk writes

        # Rest for the remainder of the cycle
        if not _sleep(cycle):
            return


# ---------------------------------------------------------------------------
# Toggle callback  (Ctrl+Alt+J)  –  PROD
# ---------------------------------------------------------------------------

def _toggle():
    global _running, _startup_cooldown
    with _state_lock:
        currently = _running

    if not currently:
        # OFF → ON
        with _state_lock:
            _running = True
            _startup_cooldown = True
        winsound.Beep(1000, 200)   # high beep → ON
    else:
        # ON → kill process entirely
        winsound.Beep(400, 200)    # low beep  → OFF + EXIT
        _stop_event.set()
        os._exit(0)


# ---------------------------------------------------------------------------
# Toggle callback  (Ctrl+Alt+K)  –  TEST
# ---------------------------------------------------------------------------

def _toggle_test():
    global _test_running, _test_startup_cooldown
    with _state_lock:
        currently = _test_running

    if not currently:
        # OFF → ON
        with _state_lock:
            _test_running = True
            _test_startup_cooldown = True
        winsound.Beep(750, 150)    # double beep → test ON
        time.sleep(0.08)
        winsound.Beep(750, 150)
    else:
        # ON → OFF  (does not exit; just stops test mode)
        with _state_lock:
            _test_running = False
        _tlog("TEST SESSION ENDED")
        _flush_log()               # single disk write here, nowhere else
        winsound.Beep(600, 350)    # single mid beep → test OFF


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    keyboard.add_hotkey("ctrl+alt+j", _toggle)
    keyboard.add_hotkey("ctrl+alt+k", _toggle_test)

    worker = threading.Thread(target=_automation_loop, daemon=True)
    worker.start()

    # Block the main thread indefinitely; daemon thread exits when process ends.
    keyboard.wait()   # blocks until the process is killed externally


if __name__ == "__main__":
    main()
