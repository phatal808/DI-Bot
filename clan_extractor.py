import json
import re
import time
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
import pyautogui
import keyboard
import pytesseract

import helpers
import main

TEMPLATE_PATH = Path("template.png")
THRESHOLD = 0.80

_enabled = True
_quit = False

def _toggle():
    global _enabled
    _enabled = not _enabled
    state = "ENABLED" if _enabled else "PAUSED"
    print(f"Clan extractor {state}")


def _stop():
    global _quit
    _quit = True
    print("Clan extractor stopping...")

keyboard.add_hotkey("f8", _toggle)
keyboard.add_hotkey("f9", _stop)


# column capture constants
# Table row region for a single clan member entry
# Coordinates match earlier working version
COL_REGION = (860, 395, 2485, 570)

LAST_ONLINE_JSON = Path("last_online_debug.json")
LAST_ONLINE_DIR = Path("last_online_shots")


def capture_region_text(window, left, top, width, height):
    """Return OCR text and the screenshot image for the region."""
    x = window.left + left
    y = window.top + top
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray).replace("\u00e9", "?")
    return text, screenshot


def save_last_online_debug(name, raw_text, image):
    LAST_ONLINE_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = re.sub(r"[^A-Za-z0-9-]", "", name) if name else "unknown"
    img_path = LAST_ONLINE_DIR / f"{base}_{ts}.png"
    image.save(img_path)

    try:
        with open(LAST_ONLINE_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    data.append({"time": ts, "name": name, "text": raw_text})
    with open(LAST_ONLINE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)



def parse_member_entry(window):
    left, top, right, bottom = COL_REGION
    width_total = right - left
    height = bottom - top
    col_w = width_total // 4
    col3_w = col_w + 150  # widen third column to capture more last_online text
    col4_x = left + col_w * 2 + col3_w
    last_w = right - col4_x

    col1 = helpers.ocr_region(window, left, top, col_w, height)
    name, level, paragon = helpers.parse_player_info(col1)

    # Trim the last_online region so it doesn't include neighboring columns
    col3_x = left + col_w * 2 + 150
    col3_y = top + 70
    col3_w_narrow = col3_w - 200
    col3_h_narrow = height - 125
    col3_text, col3_img = capture_region_text(window, col3_x, col3_y, col3_w_narrow, col3_h_narrow)
    col3_text = " ".join(l.strip() for l in col3_text.splitlines() if l.strip())
    save_last_online_debug(name, col3_text, col3_img)

    clean = col3_text.strip()

    month_match = re.search(r"(\d+)\s*months", clean, re.IGNORECASE)
    if month_match:
        last_online = f"{month_match.group(1)} months"
    else:
        m = re.search(r"\[(Hell|Inferno)\s+([IVX!|1]+)\]", clean, re.IGNORECASE)
        if m:
            word = m.group(1).capitalize()
            numeral = re.sub(r"[!|1]", "I", m.group(2))
            last_online = f"{word} {numeral}"
        else:
            last_online = clean

    if len(last_online.strip()) < 2:
        last_online = None

    # Rank is taken from the fourth column of the row
    col4 = helpers.ocr_region(window, col4_x, top, last_w, height)
    rank_text = " ".join(l.strip() for l in col4.splitlines() if l.strip())
    rank_text = rank_text.replace("|", "I")
    parts = rank_text.split()
    if len(parts) >= 2:
        rank = f"{parts[-2]} {parts[-1]}"
    elif parts:
        rank = parts[-1]
    else:
        rank = ""
    return name, level, paragon, last_online, rank


def find_template(window):
    if not TEMPLATE_PATH.exists():
        return None
    template = cv2.imread(str(TEMPLATE_PATH), cv2.IMREAD_GRAYSCALE)
    h, w = template.shape

    screenshot = pyautogui.screenshot(region=(window.left, window.top, window.width, window.height))
    gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
    res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, val, _, loc = cv2.minMaxLoc(res)
    if val >= THRESHOLD:
        cx = window.left + loc[0] + w // 2
        cy = window.top + loc[1] + h // 2
        return cx, cy
    return None


def run():
    window = helpers.bring_window_to_foreground(helpers.WINDOW_TITLE)

    # Assume there are 96 members and iterate until the last player repeats.
    pyautogui.moveTo(window.left + 1382, window.top + 446)

    last_seen = None
    found_repeat = False
    for _ in range(96):
        if _quit:
            break
        while not _enabled and not _quit:
            time.sleep(0.1)
        if _quit:
            break

        name, level, paragon, last_online, rank = parse_member_entry(window)
        if (
            name is not None
            and level is not None
            and paragon is not None
            and last_seen == (name, level, paragon)
        ):
            print("Reached previously seen player; stopping")
            found_repeat = True
            break
        last_seen = (name, level, paragon)

        # Click where the player row is to trigger the template image to appear
        pyautogui.click(window.left + 1382, window.top + 446)

        pos = None
        end_time = time.time() + 4
        while time.time() < end_time and not _quit:
            if not _enabled:
                time.sleep(0.1)
                continue
            pos = find_template(window)
            if pos:
                break
            time.sleep(0.25)

        if pos:
            pyautogui.click(*pos)
            time.sleep(1)
            try:
                main.main(last_online=last_online, rank=rank)
            except Exception as e:
                print(f"automation failed: {e}")
        else:
            print("template not found")

        pyautogui.moveTo(window.left + 1382, window.top + 446)
        for _ in range(2):
            if _quit:
                break
            pyautogui.scroll(-500)
            time.sleep(0.1)

    # Always capture the final four rows after iterating the list.
    # This runs even when we stopped early because the same player
    # appeared twice (tracked via ``found_repeat``).
    for y_offset in (610, 787, 945, 1105):
        if _quit:
            break
        while not _enabled and not _quit:
            time.sleep(0.1)
        if _quit:
            break

        pyautogui.moveTo(window.left + 1382, window.top + y_offset)
        name, level, paragon, last_online, rank = parse_member_entry(window)
        pyautogui.click(window.left + 1382, window.top + y_offset)

        pos = None
        end_time = time.time() + 4
        while time.time() < end_time and not _quit:
            if not _enabled:
                time.sleep(0.1)
                continue
            pos = find_template(window)
            if pos:
                break
            time.sleep(0.25)

        if pos:
            pyautogui.click(*pos)
            time.sleep(1)
            try:
                main.main(last_online=last_online, rank=rank)
            except Exception as e:
                print(f"automation failed: {e}")
        else:
            print("template not found")

        pyautogui.moveTo(window.left + 1382, window.top + y_offset)

    keyboard.unhook_all_hotkeys()


if __name__ == "__main__":
    run()
