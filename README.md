# OffTheGrid

Windowless background automation stub compiled as `svchost_helper.exe`.

---

## What it does

Fires 1 of 7 natural-looking desktop actions every 35-50 s (±20 % variance).  
30 % of cycles are skipped outright to mimic real inactivity.

| # | Action | Details |
|---|--------|---------|
| 1 | **Mouse move** | Smooth eased movement to random screen coords, 0.3-0.8 s duration, 100 px screen margin |
| 2 | **Scroll burst** | 3 scrolls spaced 4-10 s apart, 3-8 clicks each, 70 % down / 30 % up |
| 3 | **Alt+Tab** | Natural window switch with realistic key-hold timing |
| 4 | **Micro move** | 2-4 tiny 5-20 px nudges, simulates hand resting on mouse |
| 5 | **Random click** | Left-click at current cursor position to re-focus window |
| 6 | **Page Up/Down** | Random Page Up or Page Down keypress |
| 7 | **Ctrl+Home/End** | Jump to top or bottom of active document |

---

## Toggle

| Hotkey | Effect |
|--------|--------|
| `Ctrl+Alt+J` | Start → **high beep (1000 Hz)** / Stop → **low beep (400 Hz)** |

---

## Failsafe

Move the mouse to the **top-left corner** of the screen to trigger pyautogui's
failsafe and kill the automation immediately.

---

## Status check (no files, no logs)

```cmd
tasklist | findstr svchost_helper
```

---

## Build

```cmd
pip install -r requirements.txt
build.bat
```

Output: `dist\svchost_helper.exe`

Run it directly — it starts silently with no window, no tray icon, no UI.

> **Note:** Global hotkeys via the `keyboard` library may require the process
> to be run as **Administrator** on some Windows configurations.

---

## Dependencies

- [pyautogui](https://pyautogui.readthedocs.io/) — mouse / keyboard / scroll control  
- [keyboard](https://github.com/boppreh/keyboard) — global hotkey registration  
- [PyInstaller](https://pyinstaller.org/) — compile to single `.exe`
