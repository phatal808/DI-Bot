# Image Monitor & Auto\u2011Clicker for **Diablo\u202fImmortal**
# (F8 pause/resume \u00b7 pydirectinput Shift+Alt click \u00b7 fixed search region)
"""
**Now using pydirectinput** – DirectInput bypasses the SendInput filters that
likely blocked the previous clicks.

Changes
-------
1. **click_with_mods** uses `pydirectinput` for key downs, mouse move, click,
   and key ups. Keys are pressed only for ~100\u202fms around each colour click.
2. All other logic (colour mask, template search, timing, F8 hot\u2011key) stays the
   same.

Install once:
```powershell
pip install pydirectinput
```
Run both game and script at the same privilege level (Admin if needed).
"""
from __future__ import annotations

import helpers  # helper utilities
import main  # main automation routine
import time
from datetime import datetime
from pathlib import Path
import json
import re
import pyautogui

import cv2
import pytesseract
import mss
import numpy as np
import pydirectinput as pdi       # ← DirectInput wrapper
import random
import keyboard
import win32api
import win32con
import win32gui
import winsound

# --------------------------- CONFIG -----------------------------------------
WINDOW_TITLE  = "Diablo Immortal"
TEMPLATE_PATH = Path("template.png")
THRESHOLD     = 0.80
FPS           = 5
SEARCH_REGION = {"left": 390, "top": 160, "width": 1735, "height": 1015}
COLOR_HEX     = "E0BE83"
TOLERANCE     = 5
CLICK_OFFSET_Y = 145
COLOR_PAUSE_SEC, TEMPLATE_WINDOW_SEC = 2.5, 2.0

# debug paths
INFO_JSON = Path("info_debug.json")
INFO_DIR = Path("info_shots")

# --------------------- PREP --------------------------------------------------
if not TEMPLATE_PATH.exists():
    raise FileNotFoundError("template.png missing")

template_gray = cv2.imread(str(TEMPLATE_PATH), cv2.IMREAD_GRAYSCALE)
TEMP_W, TEMP_H = template_gray.shape[::-1]
print(f"Template size: {TEMP_W}\u00d7{TEMP_H}")

rgb = tuple(int(COLOR_HEX[i:i+2], 16) for i in (0, 2, 4))
BGR = (rgb[2], rgb[1], rgb[0])
arr = np.array(BGR, dtype=np.int16)
LOWER = np.clip(arr - TOLERANCE, 0, 255).astype(np.uint8)
UPPER = np.clip(arr + TOLERANCE, 0, 255).astype(np.uint8)
print(f"Target colour BGR: {BGR} ±{TOLERANCE}")

# --------------------- INPUT HELPERS ----------------------------------------

def bring_game_foreground():
    hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)


def click_with_mods(x: int, y: int):
    """DirectInput: press LShift+LAlt, click, release (≈100\u202fms total)."""
    bring_game_foreground()
    pdi.keyDown("shift")      # left Shift
    pdi.keyDown("alt")        # left Alt
    pdi.moveTo(x, y)
    time.sleep(0.03)
    pdi.click()
    time.sleep(0.05)
    pdi.keyUp("alt")
    pdi.keyUp("shift")


def raw_click(x: int, y: int):
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)


def capture_region_text(window, left, top, width, height):
    """Return OCR text and the screenshot image for the region."""
    x = window.left + left
    y = window.top + top
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray).replace("\u00e9", "?")
    return text, screenshot


def _save_debug(json_path: Path, img_dir: Path, name: str | None, raw_text: str, image):
    img_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = re.sub(r"[^A-Za-z0-9-]", "", name) if name else "unknown"
    image.save(img_dir / f"{base}_{ts}.png")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    data.append({"time": ts, "name": name, "text": raw_text})
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_info_debug(name: str | None, raw_text: str, image):
    _save_debug(INFO_JSON, INFO_DIR, name, raw_text, image)

# --------------------- TOGGLE ------------------------------------------------
_enabled = True
_quit = False
recent_color_clicks = []  # (x, y, timestamp) to avoid re-clicks


def _toggle():
    global _enabled
    _enabled = not _enabled
    state = "ENABLED" if _enabled else "PAUSED"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bot {state}")
    winsound.Beep(1000 if _enabled else 600, 120)

def _stop():
    global _quit
    _quit = True
    print("Bot stopping...")

keyboard.add_hotkey("f8", _toggle, suppress=False)
keyboard.add_hotkey("f9", _stop, suppress=False)
print("Press F8 to toggle bot on/off. Press F9 to quit.")

# --------------------- MAIN LOOP -------------------------------------------
state = "color"
next_color_time   = 0.0
template_deadline = 0.0

with mss.mss() as sct:
    try:
        while not _quit:
            now = time.time()
            if not _enabled:
                time.sleep(0.1)
                continue

            frame = np.array(sct.grab(SEARCH_REGION))
            bgr   = frame[:, :, :3]

            if state == "color" and now >= next_color_time:
                mask = cv2.inRange(bgr, LOWER, UPPER)
                ys, xs = np.where(mask)
                if xs.size:
                    recent_color_clicks = [(x, y, t) for x, y, t in recent_color_clicks if now - t < 180]
                    candidates = []
                    for px, py in zip(xs, ys):
                        cx = SEARCH_REGION["left"] + int(px)
                        cy = SEARCH_REGION["top"] + int(py) + CLICK_OFFSET_Y
                        if all(abs(cx - rx) > 10 or abs(cy - ry) > 10 for rx, ry, _ in recent_color_clicks):
                            candidates.append((cx, cy))

                    if candidates:
                        cx, cy = random.choice(candidates)
                        print(f"Colour → click ({cx},{cy})")
                        click_with_mods(cx, cy)
                        recent_color_clicks.append((cx, cy, now))
                        winsound.Beep(1400, 120)
                        state = "template"
                        template_deadline = now + TEMPLATE_WINDOW_SEC
                        next_color_time   = now + COLOR_PAUSE_SEC

            elif state == "template":
                if now <= template_deadline:
                    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                    _, val, _, loc = cv2.minMaxLoc(cv2.matchTemplate(gray, template_gray, cv2.TM_CCOEFF_NORMED))
                    if val >= THRESHOLD:
                        tx = SEARCH_REGION["left"] + loc[0] + TEMP_W // 2
                        ty = SEARCH_REGION["top"]  + loc[1] + TEMP_H // 2

                        window = helpers.bring_window_to_foreground(WINDOW_TITLE)

                        # The small info panel appears near the template.
                        # Derive its top-left corner relative to where the
                        # template was detected.
                        info_left = tx - 35 - window.left
                        info_top = ty - 160 - window.top
                        info_text, info_img = capture_region_text(
                            window, info_left, info_top, 498, 105
                        )
                        clan = None
                        warband = None
                        name_candidate = None
                        for line in info_text.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            if name_candidate is None:
                                name_candidate = re.sub(r"[^A-Za-z0-9-]", "", line)
                            if line.lower().startswith("clan:"):
                                clan = line.split(":", 1)[1].strip()
                            elif line.lower().startswith("warband:"):
                                warband = line.split(":", 1)[1].strip()
                        save_info_debug(name_candidate, info_text, info_img)

                        print(f"Template {val:.2f} → click ({tx},{ty})")
                        raw_click(tx, ty)
                        winsound.Beep(1800, 200)
                        print("Launching automation...")
                        try:
                            main.main(clan=clan, warband=warband)
                        except Exception as e:
                            print(f"automation failed: {e}")
                        state = "color"
                        next_color_time = time.time() + COLOR_PAUSE_SEC
                        continue
                else:
                    state = "color"

            time.sleep(max(0, 1/FPS - (time.time() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        keyboard.unhook_all_hotkeys()
