"""
svchost_helper.py  –  Background desktop automation
Toggle:  Ctrl+Alt+J   (high beep = ON, low beep = OFF)
Failsafe: move mouse to top-left corner to emergency stop
Stealth:  no window, no tray, no logs, no disk writes
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
_stop_event = threading.Event()
_state_lock = threading.Lock()

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
    dur = random.uniform(0.30, 0.80)
    pyautogui.moveTo(tx, ty, duration=dur, tween=pyautogui.easeInOutQuad)


def _scroll_burst():
    """
    Three scroll events with randomised 4-10 s gaps.
    Mostly scrolls down (70 %), occasionally up (30 %).
    """
    for i in range(3):
        if i > 0:
            gap = _var(random.uniform(4.0, 10.0))
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
# Main automation loop (runs in its own daemon thread)
# ---------------------------------------------------------------------------

def _automation_loop():
    while not _stop_event.is_set():

        # Check if toggled on
        with _state_lock:
            active = _running

        if not active:
            time.sleep(0.50)
            continue

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
# Toggle callback  (Ctrl+Alt+J)
# ---------------------------------------------------------------------------

def _toggle():
    global _running
    with _state_lock:
        currently = _running

    if not currently:
        # OFF → ON
        with _state_lock:
            _running = True
        winsound.Beep(1000, 200)   # high beep → ON
    else:
        # ON → kill process entirely
        winsound.Beep(400, 200)    # low beep  → OFF + EXIT
        _stop_event.set()
        os._exit(0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    keyboard.add_hotkey("ctrl+alt+j", _toggle)

    worker = threading.Thread(target=_automation_loop, daemon=True)
    worker.start()

    # Block the main thread indefinitely; daemon thread exits when process ends.
    keyboard.wait()   # blocks until the process is killed externally


if __name__ == "__main__":
    main()
